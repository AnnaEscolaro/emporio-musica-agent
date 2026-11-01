from __future__ import annotations

import hashlib
import re
from pathlib import Path

import chromadb
from pypdf import PdfReader

from emporio_agent.config import CHROMA_DIR, POLICIES_HASH_FILE, policies_pdf_path

COLLECTION_NAME = "store_policies"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_pdf_text(pdf_path: Path | None = None) -> str:
    pdf_path = pdf_path or policies_pdf_path()
    reader = PdfReader(str(pdf_path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return _normalize_text("\n".join(parts))


def _chunk_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def _pdf_hash(pdf_path: Path) -> str:
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def ensure_policy_index(force: bool = False) -> None:
    pdf_path = policies_pdf_path()
    current_hash = _pdf_hash(pdf_path)
    stored_hash = POLICIES_HASH_FILE.read_text(encoding="utf-8").strip() if POLICIES_HASH_FILE.exists() else ""

    if not force and stored_hash == current_hash and CHROMA_DIR.exists():
        return

    text = extract_pdf_text(pdf_path)
    chunks = _chunk_text(text)
    if not chunks:
        raise RuntimeError("Nenhum texto extraído do PDF de políticas.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)
    POLICIES_HASH_FILE.write_text(current_hash, encoding="utf-8")


def search_policies(query: str, top_k: int = 4) -> list[dict[str, str]]:
    ensure_policy_index()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    result = collection.query(query_texts=[query], n_results=top_k)
    documents = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    out: list[dict[str, str]] = []
    for doc, dist in zip(documents, distances, strict=False):
        out.append({"excerpt": doc, "distance": str(dist)})
    return out

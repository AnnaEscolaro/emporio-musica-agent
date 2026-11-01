from __future__ import annotations

import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pypdf import PdfReader

from emporio_agent.config import CHROMA_DIR, POLICIES_HASH_FILE, policies_pdf_path

COLLECTION_NAME = "store_policies"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
INDEX_VERSION = f"sections-v1|{EMBEDDING_MODEL}"
MAX_CHUNK_CHARS = 480

# The PDF extractor emits one token per line. After joining those tokens,
# headings like "4.1 Direito" are the only reliable section boundaries.
# The dot is required so times ("18:00 Sábado") and the CNPJ suffix do not split.
_SECTION_SPLIT = re.compile(
    r"(?<![\d.])(?<!Versão )(?=\d{1,2}\.(?:\d{1,2})?(?!\d)\s+[A-ZÀ-Ý][a-zà-ÿ])"
)
_RUNNING_HEADER = re.compile(
    r"Empório da Música\s+Manual de Políticas e Procedimentos",
    re.IGNORECASE,
)
_PAGE_MARKER = re.compile(r"Página\s+\d+", re.IGNORECASE)
_HEADING = re.compile(r"^(\d{1,2}\.(?:\d{1,2})?(?!\d)\s+[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+\S+){0,6})")


def normalize_extracted_text(raw: str) -> str:
    """Join the PDF's one-word lines, then drop repeated page furniture."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = _RUNNING_HEADER.sub(" ", text)
    text = _PAGE_MARKER.sub(" ", text)
    return re.sub(r" {2,}", " ", text).strip()


def extract_pdf_text(pdf_path: Path | None = None) -> str:
    pdf_path = pdf_path or policies_pdf_path()
    reader = PdfReader(str(pdf_path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return normalize_extracted_text("\n".join(parts))


def _pack_section(section: str) -> list[str]:
    section = section.strip()
    if not section:
        return []
    if len(section) <= MAX_CHUNK_CHARS:
        return [section]

    heading_match = _HEADING.match(section)
    heading = heading_match.group(1).strip() if heading_match else ""
    body = section[len(heading) :].strip() if heading else section
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", body) if part.strip()]
    if not sentences:
        return [section]

    chunks: list[str] = []
    current = heading
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current == heading or len(candidate) <= MAX_CHUNK_CHARS:
            current = candidate
            continue
        chunks.append(current.strip())
        current = f"{heading} {sentence}".strip()
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_policy_text(text: str) -> list[str]:
    """Split the manual on numbered sections so one chunk does not mix topics."""
    sections = [part.strip() for part in _SECTION_SPLIT.split(text) if part.strip()]
    chunks: list[str] = []
    for section in sections:
        chunks.extend(_pack_section(section))
    return chunks


def _embedding_function() -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        device="cpu",
        normalize_embeddings=True,
    )


def _index_fingerprint(pdf_path: Path) -> str:
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return f"{INDEX_VERSION}:{digest}"


def ensure_policy_index(force: bool = False) -> None:
    pdf_path = policies_pdf_path()
    current_hash = _index_fingerprint(pdf_path)
    stored_hash = POLICIES_HASH_FILE.read_text(encoding="utf-8").strip() if POLICIES_HASH_FILE.exists() else ""

    if not force and stored_hash == current_hash and CHROMA_DIR.exists():
        return

    chunks = chunk_policy_text(extract_pdf_text(pdf_path))
    if not chunks:
        raise RuntimeError("Nenhum texto extraído do PDF de políticas.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(documents=chunks, ids=[f"chunk_{i}" for i in range(len(chunks))])
    POLICIES_HASH_FILE.write_text(current_hash, encoding="utf-8")


def search_policies(query: str, top_k: int = 4) -> list[dict[str, str]]:
    ensure_policy_index()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME, embedding_function=_embedding_function())
    result = collection.query(query_texts=[query], n_results=top_k)
    documents = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {"excerpt": doc, "distance": str(dist)}
        for doc, dist in zip(documents, distances, strict=False)
    ]

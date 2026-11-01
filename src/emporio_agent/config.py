from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("EMPORIO_DATA_DIR", PROJECT_ROOT / "data"))
DB_PATH = DATA_DIR / "store.db"
CHROMA_DIR = DATA_DIR / "chroma_policies"
POLICIES_HASH_FILE = DATA_DIR / ".policies_pdf_hash"

CSV_FILES = {
    "categories": "desafio_tecnico_ai_eng - categories.csv",
    "customers": "desafio_tecnico_ai_eng - customers.csv",
    "orders": "desafio_tecnico_ai_eng - orders.csv",
    "order_items": "desafio_tecnico_ai_eng - order_items.csv",
    "products": "desafio_tecnico_ai_eng - products.csv",
    "promotions": "desafio_tecnico_ai_eng - promotions.csv",
}


def policies_pdf_path() -> Path:
    for path in DATA_DIR.glob("*.pdf"):
        if "pol" in path.name.lower() or "loja" in path.name.lower():
            return path
    raise FileNotFoundError(f"PDF de políticas não encontrado em {DATA_DIR}")


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

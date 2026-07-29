import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
EMBEDDING_MODEL = "models/embedding-001"
LLM_MODEL = "models/gemini-2.0-flash-lite"

CHROMA_COLLECTION = "mental_health_papers"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
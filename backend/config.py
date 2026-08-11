import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "Qwen/Qwen3-4B"
CALIBRATION_WORD_TARGET = 500  # ≥ 500 words
CALIBRATION_TIME_SECONDS = 1800  # 30 min
SAFETY_CLASSIFIER_MODEL = "distilbert-base-uncased"

CHROMA_COLLECTION = "mental_health_papers"
MEMORY_COLLECTION = "user_memory"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 5
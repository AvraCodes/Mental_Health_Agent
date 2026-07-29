"""In-memory session store + long-term user memory via ChromaDB."""

import json
import uuid
from datetime import datetime
from typing import Optional

from backend.config import MEMORY_COLLECTION, CHROMA_DIR

# ---------------------------------------------------------------------------
# Short-term session memory (in-memory dict)
# ---------------------------------------------------------------------------
_sessions: dict[str, list[dict]] = {}

def get_session_history(session_id: str) -> list[dict]:
    return _sessions.get(session_id, [])

def append_to_session(session_id: str, role: str, content: str):
    _sessions.setdefault(session_id, []).append({
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    })

def clear_session(session_id: str):
    _sessions.pop(session_id, None)

# ---------------------------------------------------------------------------
# Long-term user memory via ChromaDB
# ---------------------------------------------------------------------------
_client = None
_collection = None

def _ensure_collection():
    global _client, _collection
    if _collection is None:
        import chromadb
        from chromadb.config import Settings
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=MEMORY_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def store_fact(session_id: str, fact: str):
    col = _ensure_collection()
    fact_id = str(uuid.uuid4())
    col.add(
        ids=[fact_id],
        documents=[fact],
        metadatas=[{"session_id": session_id, "timestamp": datetime.utcnow().isoformat()}],
    )


def retrieve_facts(session_id: str, query: str, top_k: int = 3) -> list[str]:
    col = _ensure_collection()
    results = col.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    docs = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            if meta.get("session_id") == session_id:
                docs.append(doc)
    return docs


def generate_session_summary(session_id: str) -> str:
    history = get_session_history(session_id)
    if not history:
        return ""
    return json.dumps([
        {"role": m["role"], "content": m["content"]} for m in history[-10:]
    ], indent=2)
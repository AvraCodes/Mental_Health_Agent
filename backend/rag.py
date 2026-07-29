import chromadb
from chromadb.config import Settings
from backend.config import CHROMA_DIR, CHROMA_COLLECTION, TOP_K
from backend.embeddings import embed_text


_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False),
)

_collection = _client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    query_embedding = embed_text(query)
    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    if results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            docs.append({
                "text": doc,
                "source": metadata.get("source", "unknown"),
                "page": metadata.get("page", None),
                "score": results["distances"][0][i] if results["distances"] else 0,
            })
    return docs


def add_documents(docs: list[dict]):
    ids = []
    metadatas = []
    documents = []
    for i, doc in enumerate(docs):
        ids.append(doc.get("id", str(hash(doc["text"]))))
        metadatas.append({
            "source": doc.get("source", "unknown"),
            "page": doc.get("page", ""),
        })
        documents.append(doc["text"])
    _collection.add(ids=ids, metadatas=metadatas, documents=documents)
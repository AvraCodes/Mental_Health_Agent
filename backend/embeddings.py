from google import genai

_client = None


def _get_client():
    global _client
    if _client is None:
        from backend.config import GOOGLE_API_KEY
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


def embed_text(text: str) -> list[float]:
    from backend.config import EMBEDDING_MODEL
    client = _get_client()
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return result.embeddings[0].values


def embed_texts(texts: list[str]) -> list[list[float]]:
    from backend.config import EMBEDDING_MODEL
    client = _get_client()
    result = client.models.embed_content(model=EMBEDDING_MODEL, contents=texts)
    return [e.values for e in result.embeddings]
from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.rag import search

SYSTEM_PROMPT = """You are a compassionate AI mental health support assistant.
You use evidence-based therapeutic techniques (CBT, DBT, ACT) to support users.
You NEVER diagnose, prescribe medication, or claim to replace a licensed therapist.
If someone is in crisis, you encourage them to contact emergency services or a crisis hotline.
Keep responses warm, empathetic, and grounded in the context provided."""


def _get_client():
    return genai.Client(api_key=GOOGLE_API_KEY)


def build_context(query: str) -> str:
    results = search(query)
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(f"[Source: {r['source']}]\n{r['text']}")
    return "\n\n".join(parts)


def generate_reply(user_message: str, session_id: str) -> str:
    context = build_context(user_message)
    client = _get_client()
    prompt = f"Relevant context:\n{context}\n\nUser: {user_message}\n\nRespond empathetically using the context if helpful:"
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
        },
    )
    return response.text
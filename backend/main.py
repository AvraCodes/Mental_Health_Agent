from fastapi import FastAPI
from uuid import uuid4
from backend.models import ChatRequest, ChatResponse
from backend.orchestrator import generate_reply

app = FastAPI(title="Mental Health Agent API", version="0.2.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())
    reply, agents = generate_reply(req.message, session_id)
    return ChatResponse(reply=reply, session_id=session_id, agents=agents)
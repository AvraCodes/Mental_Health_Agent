"""FastAPI entry point for the Zoya mental health agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4

from backend.models import ChatRequest, ChatResponse
from backend.orchestrator import generate_reply

app = FastAPI(title="Zoya Mental Health Agent", version="0.3.0")

# Allow the Next.js dev server (port 3000) to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid4())
    result = generate_reply(req.message, session_id)
    return ChatResponse(
        reply=result["reply"],
        session_id=session_id,
        calibrated=result["calibrated"],
        progress=int(result["progress"]),
    )
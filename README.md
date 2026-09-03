# Mental Health Agent

Hub-and-Spoke multi-agent system for mental health support. Built with FastAPI, ChromaDB RAG, and Google Generative AI.

## Structure

```
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Settings
│   ├── models.py               # Pydantic schemas
│   ├── embeddings.py           # Google text-embedding-004 wrapper
│   ├── rag.py                  # ChromaDB retrieval layer (research papers)
│   ├── orchestrator.py         # Routes input through all sub-agents & synthesizes
│   ├── requirements.txt
│   └── app/
│       ├── memory.py           # Session history + long-term user facts in ChromaDB
│       └── agents/
│           ├── base.py         # Abstract base agent
│           ├── crisis_agent.py # Keyword + LLM risk scoring; overrides on high risk
│           ├── empathy_agent.py# Emotion analysis + validating reflection
│           ├── clinical_agent.py# RAG + CBT/DBT/ACT technique suggestions
│           ├── memory_agent.py # Past context retrieval + fact extraction
│           └── action_agent.py # Grounding exercises / behavioral activation
├── scripts/
│   └── ingest_papers.py        # PDF ingestion into ChromaDB
└── data/
    └── chroma_db/              # Vector store (gitignored)
```

## Setup

```bash
pip install -r backend/requirements.txt
```

Set your Google API key:

```bash
# PowerShell
$env:GOOGLE_API_KEY="your-key-here"
```

## Ingest Research Papers

Drop PDFs in the project root, then:

```bash
python scripts/ingest_papers.py
```

Chunks PDFs, generates Google embeddings, and stores them in `data/chroma_db/`.

## Run the API

```bash
uvicorn backend.main:app --reload --port 8000
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Send a message (returns empathetic + context-aware reply) |

```json
// POST /chat
{ "message": "I've been feeling anxious lately", "session_id": "optional-uuid" }

// Response includes agent-level breakdown:
{ "reply": "...", "session_id": "...", "agents": { "crisis": {...}, "empathy": {...}, ... } }
```

## Agent Workflow

1. **Crisis & Triage Agent** runs first — keyword match + Gemini risk scoring. If risk is **high**, it overrides and returns a crisis intervention immediately.
2. **Empathy & Active Listening Agent** analyzes emotional tone and generates a validating reflection.
3. **Memory & Context Agent** retrieves session history and stored user facts from ChromaDB.
4. **Clinical Reasoning Agent** searches research papers via RAG and suggests evidence-based techniques (CBT/DBT/ACT).
5. **Action & Resource Agent** proposes grounding exercises or journaling prompts.
6. **Orchestrator** synthesizes all agent outputs into a single warm, empathetic response.

## Architecture

- **Orchestrator** routes user input through all 5 sub-agents, then synthesizes their outputs via Gemini.
- **RAG layer** uses ChromaDB (cosine similarity) + Google `text-embedding-004` for semantic search over mental health literature.
- **Memory** stores session history in-memory and long-term user facts in a separate ChromaDB collection.
- **Safety** — crisis agent runs first on every message; system prompts prohibit diagnosis/medication advice.

<!-- last-updated: 2026-09-03T11:32:42Z -->
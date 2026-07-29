# Mental Health Agent

Hub-and-Spoke multi-agent system for mental health support. Built with FastAPI, ChromaDB RAG, and Google Generative AI.

## Structure

```
backend/
├── main.py           # FastAPI entry point
├── config.py         # Settings
├── models.py         # Pydantic schemas
├── embeddings.py     # Google embeddings wrapper
├── rag.py            # ChromaDB retrieval layer
├── orchestrator.py   # Agent orchestration + LLM calls
└── requirements.txt

scripts/
└── ingest_papers.py  # PDF ingestion into ChromaDB
```

## Setup

```bash
pip install -r backend/requirements.txt
```

Set your Google API key:

```bash
# PowerShell
$env:GOOGLE_API_KEY="your-key-here"

# or create a .env file
```

## Ingest Research Papers

Drop PDFs in the project root, then:

```bash
python scripts/ingest_papers.py
```

This chunks PDFs, generates Google embeddings, and stores them in `data/chroma_db/`.

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
```

## Architecture

- **Orchestrator** routes user input, retrieves RAG context from research papers, and generates responses via Gemini.
- **RAG layer** uses ChromaDB with cosine similarity + Google `text-embedding-004` for semantic search over mental health literature.
- **Safety** is handled via system prompting (no diagnosis, no medication advice, crisis escalation guidance).
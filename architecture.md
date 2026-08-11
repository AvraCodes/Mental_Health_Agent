# Zoya -- Architecture Guide

One-stop reference for understanding the entire system: what runs, in what
order, what each module does, and where data flows.

---

## Directory Structure

```
Mental_Health_Agent/
├── backend/
│   ├── main.py               # FastAPI entry point (POST /chat, GET /health)
│   ├── config.py             # All constants (model IDs, thresholds, paths)
│   ├── models.py             # Pydantic request/response schemas
│   ├── inference.py          # Qwen-3.4B loader + generate() function
│   ├── safety.py             # Pre/post-generation safety classifier (STUB)
│   ├── session.py            # Calibration tracking + questionnaire state
│   ├── questionnaire.py      # PHQ-9 / GAD-7 item list + round-robin scheduler
│   ├── orchestrator.py       # Main pipeline: safety → calibration → questionnaire → LLM → safety
│   ├── embeddings.py         # Google text-embedding-004 wrapper (used by RAG)
│   ├── rag.py                # ChromaDB retrieval layer for research papers
│   ├── requirements.txt
│   ├── eval/
│   │   └── harness_test.py   # BeaverTails eval harness placeholder
│   └── app/
│       ├── memory.py         # In-memory session history + ChromaDB user facts
│       └── agents/           # LEGACY: Gemini-based agents (kept for reference)
│           ├── base.py
│           ├── crisis_agent.py
│           ├── empathy_agent.py
│           ├── clinical_agent.py
│           ├── memory_agent.py
│           └── action_agent.py
├── frontend/                 # Next.js chat UI
│   ├── pages/
│   │   ├── _app.tsx
│   │   └── index.tsx         # Main chat page with calibration progress bar
│   ├── styles/
│   │   └── globals.css
│   ├── utils/
│   │   └── api.ts            # fetch wrapper for /api/chat
│   ├── next.config.js        # Proxy rewrites: /api/* → localhost:8000/*
│   ├── package.json
│   └── tsconfig.json
├── scripts/
│   └── ingest_papers.py      # PDF chunking → ChromaDB ingestion
├── data/
│   └── chroma_db/            # Vector store (gitignored)
├── decisions.md              # Architectural decision log
├── architecture.md           # This file
└── AGENT_GUIDE.md            # Quick-start for future AI agents
```

---

## Request Lifecycle (POST /chat)

```
  User types message
       │
       ▼
  ┌─────────────────────────────────────────────┐
  │ Frontend (Next.js, port 3000)               │
  │   POST /api/chat { message, session_id }    │
  │   next.config.js rewrites → localhost:8000   │
  └─────────────────┬───────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────┐
  │ main.py: chat()                             │
  │   • generate session_id if missing          │
  │   • call orchestrator.generate_reply()      │
  │   • wrap result in ChatResponse             │
  └─────────────────┬───────────────────────────┘
                    │
                    ▼
  ┌─────────────────────────────────────────────┐
  │ orchestrator.py: generate_reply()           │
  │                                             │
  │   1. safety.classify(user_message)          │
  │      → "safe" or "unsafe"                   │
  │      → if unsafe: return crisis message     │
  │                                             │
  │   2. session.update_calibration()           │
  │      → accumulate word count + time         │
  │      → compute progress (0-100%)            │
  │                                             │
  │   3. Build prompt context:                  │
  │      a. Recent conversation history (last 6)│
  │      b. IF calibrated AND turn % 3 == 0:    │
  │         → questionnaire.next_item()         │
  │         → inject item into prompt context   │
  │                                             │
  │   4. inference.generate(prompt)             │
  │      → Qwen-3.4B generates reply            │
  │                                             │
  │   5. safety.classify(reply)                 │
  │      → if unsafe: replace with safe fallback│
  │                                             │
  │   Return { reply, calibrated, progress,     │
  │            questionnaire }                  │
  └─────────────────────────────────────────────┘
```

---

## Module Reference

### backend/main.py
**Entry point.** Creates the FastAPI app, adds CORS middleware for the
Next.js dev server, exposes two endpoints:
- `GET /health` -- returns `{"status": "ok"}`
- `POST /chat` -- accepts `ChatRequest`, delegates to `orchestrator.generate_reply()`,
  returns `ChatResponse`

### backend/config.py
**Constants.** All tuneable values live here:
- `LLM_MODEL` -- HuggingFace repo ID for the generation model
- `CALIBRATION_WORD_TARGET` -- minimum words before calibration completes (500)
- `CALIBRATION_TIME_SECONDS` -- minimum seconds before calibration completes (1800)
- `SAFETY_CLASSIFIER_MODEL` -- model ID for the safety classifier (placeholder)
- ChromaDB paths and collection names

### backend/models.py
**Pydantic schemas.**
- `ChatRequest` -- `{ message: str, session_id: str? }`
- `ChatResponse` -- `{ reply: str, session_id: str, calibrated: bool, progress: int, agents: AgentResults }`
- Legacy agent data models (`CrisisData`, `EmpathyData`, etc.) are retained
  for backward compatibility but not actively populated by the new pipeline.

### backend/inference.py
**LLM wrapper.** Lazy-loads Qwen-3.4B with `BitsAndBytesConfig(load_in_4bit=True)`
on first call. Uses the model's chat template with a system prompt defining
Zoya's persona. Exposes a single function:
- `generate(prompt: str) -> str`

### backend/safety.py
**Safety classifier (STUB).** Always returns `"safe"`. Contains a
`TODO(BLOCKING)` comment gating real deployment on replacing this with a
calibrated BERT/RoBERTa model. The orchestrator calls it twice per request:
once on user input (pre-safety) and once on model output (post-safety).

### backend/session.py
**Session metadata.** Manages a per-session `_meta` dict containing:
- `calibration_words` -- cumulative word count
- `calibration_start` -- epoch timestamp of first message
- `questionnaire_asked` -- list of already-asked item indices

Key functions:
- `update_calibration(session_id, message)` -- adds word count, sets start time
- `calibration_progress(session_id) -> float` -- returns 0-100
- `is_calibrated(session_id) -> bool` -- True when progress >= 100

### backend/questionnaire.py
**Questionnaire controller.** Contains the full PHQ-9 (9 items) and GAD-7
(7 items) item lists. Tracks which items have been asked per session.
- `next_item(session_id) -> dict | None` -- returns the next unanswered item
- `items_remaining(session_id) -> int` -- count of pending items
- `INJECTION_INTERVAL` -- how many turns between injections (default: 3)

### backend/orchestrator.py
**Pipeline coordinator.** The `generate_reply()` function is the single
entry point that chains all pipeline stages. It also manages a per-session
turn counter to pace questionnaire injection.

### backend/app/memory.py
**Session history store.** Two layers:
- Short-term: in-memory dict `_sessions[session_id] -> list[dict]` with
  `get_session_history()`, `append_to_session()`, `clear_session()`
- Long-term: ChromaDB collection storing extracted user facts with
  `store_fact()`, `retrieve_facts()`

### backend/app/agents/ (LEGACY)
Five specialised agents from the original Gemini-based architecture. They
are NOT called by the current pipeline but are kept for reference:
- `crisis_agent.py` -- keyword + Gemini risk scoring
- `empathy_agent.py` -- emotion analysis
- `clinical_agent.py` -- RAG + CBT technique suggestions
- `memory_agent.py` -- context retrieval + fact extraction
- `action_agent.py` -- grounding exercises

### backend/eval/harness_test.py
**Evaluation harness placeholder.** Contains stub tests for the safety
classifier and TODO instructions for integrating BeaverTails.

---

## Frontend

### How it works
1. User opens `http://localhost:3000`
2. Types a message; it is sent to `/api/chat` (proxied to FastAPI)
3. If `calibrated: false` in the response, the progress bar updates
4. If `calibrated: true`, the assistant reply is displayed
5. Calibration progress bar disappears once it hits 100%

### Styling
Vanilla CSS. Dark gradient background, clean chat bubbles, subtle
animations on new messages. No Tailwind.

---

## Calibration Flow (Seamless)

The user is never asked to "calibrate". They just start chatting.

1. Every message updates `session.update_calibration()` with word count
2. `calibration_progress()` returns `max(word_pct, time_pct) * 100`
3. The frontend shows a small progress bar (not a modal, not a blocker)
4. Once progress >= 100%, `is_calibrated()` returns True
5. Questionnaire items start injecting into prompts

The LLM responds to every message regardless of calibration state.
Calibration only gates questionnaire injection.

---

## Current Phase

**Phase 4: Self-hosted LLM + Safety Classifiers + Seamless Calibration + Questionnaire**

Prior phases (research, RAG ingestion, Gemini multi-agent) are complete and
their code remains in the repository. See `decisions.md` for the rationale
behind each architectural change.

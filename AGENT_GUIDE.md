# Agent Guide -- Quick-Start for Future AI Agents

This document helps any AI agent (or human developer) quickly understand
the Zoya project, its current state, and what to work on next.

---

## What is Zoya?

A mental health conversational agent that:
- Conducts CBT-grounded text conversations
- Embeds PHQ-9 and GAD-7 questionnaire items naturally into dialogue
- Tracks emotional state over sessions
- Uses a self-hosted open-source LLM (currently Qwen-3.4B, 4-bit quantised)
- Runs safety classification independently of the LLM (separate classifier)

---

## Current Phase: Phase 4

**Self-hosted LLM + Safety Classifiers + Seamless Calibration + Questionnaire**

### What exists and works:
- FastAPI backend with `/chat` endpoint (`backend/main.py`)
- Qwen-3.4B inference wrapper with 4-bit quantisation (`backend/inference.py`)
- Seamless calibration system: 500 words or 30 min (`backend/session.py`)
- Round-robin questionnaire injection for PHQ-9/GAD-7 (`backend/questionnaire.py`)
- Safety classifier STUB -- always returns "safe" (`backend/safety.py`)
- Eval harness placeholder referencing BeaverTails (`backend/eval/harness_test.py`)
- Next.js chat frontend with calibration progress bar (`frontend/`)
- In-memory session history + ChromaDB long-term facts (`backend/app/memory.py`)
- RAG layer over research papers (`backend/rag.py`)
- Legacy Gemini-based agents kept for reference (`backend/app/agents/`)

### What does NOT exist yet (ordered by priority):
1. **Real safety classifier** -- the stub must be replaced with a calibrated
   BERT/RoBERTa model BEFORE any user-facing testing. See `backend/safety.py`
   and `backend/eval/harness_test.py` for TODOs.
2. **BeaverTails evaluation harness** -- must be fully implemented and passing
   before user testing.
3. **QLoRA fine-tuning pipeline** -- for training the generation model on
   CBT/counseling datasets (Counsel Chat, MentalChat16K, EmpatheticDialogues,
   plus custom synthetic questionnaire-flow data).
4. **Questionnaire scoring** -- the controller tracks which items are asked
   but does not yet score user responses.
5. **Persistent session storage** -- sessions are in-memory and lost on restart.
6. **Facial emotion recognition** -- future phase (video input).
7. **Speech emotion recognition** -- future phase (voice input).

---

## Key Files to Read First

| Priority | File | Why |
|----------|------|-----|
| 1 | `architecture.md` | Full system flow, module reference, request lifecycle |
| 2 | `decisions.md` | Why each major choice was made |
| 3 | `backend/orchestrator.py` | The main pipeline -- read this to understand what happens per request |
| 4 | `backend/config.py` | All tuneable constants |
| 5 | `backend/safety.py` | Understand the safety gap (BLOCKING TODO) |

---

## Build Order Constraint (MUST follow)

This is the dependency-driven build order. Do not skip steps:

1. **Safety classifier + BeaverTails eval harness** -- nothing user-facing
   should proceed until this is calibrated.
2. **Session controller** -- conversation state + questionnaire coverage
   (already implemented).
3. **Generation model fine-tune** -- iterate against the eval harness.
4. **Output safety filter** -- reapply the classifier to generated output
   (already wired in orchestrator, needs real classifier).
5. **Frontend polish** -- only after the pipeline is safe and functional.

---

## Constraints to Respect

- Do NOT implement safety as an LLM prompt/instruction alone.
- Do NOT hardcode a specific base model as final -- re-evaluate at
  implementation time.
- Do NOT deploy to users without a passing BeaverTails eval.
- Keep the questionnaire conversational, not a form UI.
- The calibration phase must be seamless (no explicit prompt to the user).

---

## How to Run

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
Requires a GPU with enough VRAM for 4-bit Qwen-3.4B (~3-4 GB).

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Opens at http://localhost:3000. Proxies API calls to the backend.

### Tests
```bash
python -m pytest backend/eval/harness_test.py -v
```

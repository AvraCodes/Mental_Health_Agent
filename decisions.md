# Decisions Log

This file tracks major architectural decisions, the reasoning behind each,
and what each solves compared to the prior approach.

---

## D-001: Switch from Google Gemini API to self-hosted Qwen-3.4B

**Date:** 2026-08-12
**Status:** Active

**Context:** The original system called the Google Gemini API for all LLM
inference (orchestrator synthesis, agent prompts, memory extraction). This
means every user message results in multiple external API calls, which
introduces latency, cost, and a hard dependency on Google's availability.

**Decision:** Replace the Gemini API with a locally-loaded Qwen-3.4B model
(`Qwen/Qwen3-4B`) using `transformers` + `bitsandbytes` 4-bit quantisation.

**Why Qwen-3.4B:** Good instruction-following for its size class, fits in
4-bit on a single consumer GPU, active HuggingFace community. The specific
base model is not hardcoded as final -- it should be re-evaluated against
current leaderboards before any production deployment.

**What it solves:**
- Removes external API dependency and per-request cost.
- Enables future QLoRA fine-tuning on CBT/counseling datasets.
- Keeps the model resident in memory; each message is a single local
  inference call instead of a network round-trip.

**Trade-off:** Requires a GPU-capable host to run the backend.

---

## D-002: Safety as a separate classifier, not an LLM prompt

**Date:** 2026-08-12
**Status:** Stub implemented, real model pending (BLOCKING for user testing)

**Context:** The original system relied on Gemini's system prompt to enforce
safety ("You NEVER diagnose..."). Prompt-based safety is fragile -- it can
be bypassed by adversarial inputs and provides no measurable guarantees.

**Decision:** Implement safety as a dedicated classifier component
(`backend/safety.py`) that runs both pre-generation (on user input) and
post-generation (on model output). The classifier is independent of the
LLM and will be a fine-tuned BERT/RoBERTa model.

**What it solves:**
- Decouples safety from the generation model's compliance.
- Enables measurable false-negative rate tracking via BeaverTails eval.
- Fine-tuned BERT-base and RoBERTa-large models beat GPT-3.5 zero/few-shot
  at detecting unsafe responses (~70% accuracy).

**Current state:** Stub that always returns "safe". See `backend/eval/harness_test.py`.

---

## D-003: Seamless calibration (500 words / 30 min)

**Date:** 2026-08-12
**Status:** Active

**Context:** The system needs a baseline understanding of the user before
activating the full therapeutic pipeline (questionnaire injection, clinical
reasoning). An explicit "calibration phase" that blocks the user from
chatting would feel unnatural.

**Decision:** Calibration runs under the hood during normal conversation.
The user starts chatting immediately; the backend tracks word count and
elapsed time. Once either threshold is met (500 words OR 30 minutes), the
session is marked as calibrated and questionnaire items begin injecting.

**What it solves:**
- No friction at session start -- user is never told to "complete
  calibration first".
- Frontend shows a small progress indicator so the user has a sense of
  session progression without understanding the mechanism.
- 500 words provides meaningful linguistic signal for future NLP analysis
  (sentiment baseline, vocabulary patterns, emotional expression style).

---

## D-004: Round-robin questionnaire injection (PHQ-9, GAD-7)

**Date:** 2026-08-12
**Status:** Active (v1)

**Context:** Standardised psychological questionnaires (PHQ-9, GAD-7) need
to be administered, but presenting them as a form breaks the conversational
flow.

**Decision:** The backend tracks which items have been asked and injects
them into the LLM prompt every N turns (currently every 3rd turn after
calibration). The model is instructed to weave the question naturally into
its response. Scoring happens in the background.

**What it solves:**
- Questionnaire feels like part of the conversation, not a clinical form.
- Round-robin ensures all items are covered regardless of conversation
  direction.

**Future improvement:** Context-aware injection that picks the most
relevant item based on conversation content.

---

## D-005: Preserve existing Gemini-based agents

**Date:** 2026-08-12
**Status:** Active

**Context:** The original codebase has 5 specialised agents (crisis,
empathy, clinical, memory, action) that use the Gemini API.

**Decision:** Keep all agent files in `backend/app/agents/` untouched.
The new orchestrator does not call them, but they remain for reference
and potential future integration.

**Why:** Need full understanding of their behaviour before deciding
whether to port, merge, or retire them.

---

## D-006: Next.js frontend with proxy to FastAPI

**Date:** 2026-08-12
**Status:** Active

**Context:** Need a usable UI for testing the backend.

**Decision:** Minimal Next.js app on port 3000 with `next.config.js`
rewrites proxying `/api/*` to `http://localhost:8000/*`.

**What it solves:**
- Single-origin requests from the browser (no CORS issues in production).
- Frontend and backend can be developed independently.
- Vanilla CSS styling -- no Tailwind dependency.

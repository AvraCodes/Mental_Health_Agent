"""Orchestrator -- routes each user message through the Zoya pipeline.

Pipeline stages:
  1. Pre-safety   -- classify incoming user message
  2. Calibration  -- accumulate baseline data (seamless, under the hood)
  3. Questionnaire -- inject PHQ-9/GAD-7 items when due (post-calibration only)
  4. LLM inference -- Qwen-3.4B generation
  5. Post-safety  -- classify generated reply before returning it

During calibration the user can chat normally; the LLM still responds.
The difference is that questionnaire items are NOT injected until
calibration is complete.
"""

from backend.safety import classify as safety_classify
from backend.inference import generate as llm_generate
from backend.questionnaire import next_item, INJECTION_INTERVAL
from backend.session import (
    update_calibration,
    calibration_progress,
    is_calibrated,
)
from backend.app.memory import append_to_session, get_session_history


# ---------------------------------------------------------------------------
# Internal turn counter (per session) for questionnaire injection pacing
# ---------------------------------------------------------------------------
_turn_counts: dict[str, int] = {}


def _increment_turn(session_id: str) -> int:
    _turn_counts[session_id] = _turn_counts.get(session_id, 0) + 1
    return _turn_counts[session_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_reply(user_message: str, session_id: str) -> dict:
    """Process a single user message and return a response dict.

    Returns
    -------
    dict with keys:
        reply        : str   -- assistant response text
        calibrated   : bool  -- whether calibration is complete
        progress     : float -- calibration progress 0-100
        questionnaire: dict | None -- injected questionnaire item, if any
    """
    # 1. Pre-safety check on user input
    if safety_classify(user_message) != "safe":
        return {
            "reply": (
                "I want to make sure you're safe. If you're in immediate danger, "
                "please contact emergency services (911) or the 988 Suicide & "
                "Crisis Lifeline."
            ),
            "calibrated": is_calibrated(session_id),
            "progress": calibration_progress(session_id),
            "questionnaire": None,
        }

    # Always record the user message in session history
    append_to_session(session_id, "user", user_message)

    # 2. Calibration -- always update, even if already calibrated
    update_calibration(session_id, user_message)
    progress = calibration_progress(session_id)
    calibrated = is_calibrated(session_id)

    # 3. Build the prompt context
    history = get_session_history(session_id)
    recent = history[-6:] if history else []
    history_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content'][:300]}" for m in recent
    )

    questionnaire_item = None
    questionnaire_context = ""

    if calibrated:
        turn = _increment_turn(session_id)
        if turn % INJECTION_INTERVAL == 0:
            questionnaire_item = next_item(session_id)
            if questionnaire_item:
                questionnaire_context = (
                    f"\n[Internal instruction: Naturally weave this assessment "
                    f"question into your response -- do NOT present it as a "
                    f"formal questionnaire. Question: \"{questionnaire_item['text']}\"]\n"
                )

    prompt = (
        f"Conversation so far:\n{history_text}\n"
        f"{questionnaire_context}"
        f"\nUser: {user_message}\n"
        f"\nRespond warmly and therapeutically."
    )

    # 4. LLM inference
    reply = llm_generate(prompt)

    # 5. Post-safety check on generated reply
    if safety_classify(reply) != "safe":
        reply = (
            "I appreciate you sharing that with me. I want to make sure "
            "we're having a safe conversation. Could you tell me more about "
            "how you're feeling right now?"
        )

    # Store assistant response
    append_to_session(session_id, "assistant", reply)

    return {
        "reply": reply,
        "calibrated": calibrated,
        "progress": progress,
        "questionnaire": questionnaire_item,
    }
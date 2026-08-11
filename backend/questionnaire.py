"""Questionnaire controller -- PHQ-9 and GAD-7 items.

Tracks which items have been asked per session and returns the next pending
item in round-robin order. The model is expected to weave the question into
conversation naturally; this module only decides *what* to ask next.

Injection strategy (v1): round-robin. Every N turns (currently every 3rd
user message after calibration), the orchestrator checks next_item(). If an
item is returned it gets prepended to the LLM prompt context.
"""

from backend.session import get_questionnaire_asked, mark_questionnaire_asked

# PHQ-9 items (Patient Health Questionnaire)
PHQ9_ITEMS = [
    "Over the last 2 weeks, how often have you been bothered by little interest or pleasure in doing things?",
    "Over the last 2 weeks, how often have you been bothered by feeling down, depressed, or hopeless?",
    "Over the last 2 weeks, how often have you had trouble falling or staying asleep, or sleeping too much?",
    "Over the last 2 weeks, how often have you felt tired or had little energy?",
    "Over the last 2 weeks, how often have you had poor appetite or been overeating?",
    "Over the last 2 weeks, how often have you felt bad about yourself, or that you are a failure, or have let yourself or your family down?",
    "Over the last 2 weeks, how often have you had trouble concentrating on things, such as reading or watching TV?",
    "Over the last 2 weeks, how often have you been moving or speaking so slowly that other people could have noticed, or the opposite?",
    "Over the last 2 weeks, how often have you had thoughts that you would be better off dead, or of hurting yourself?",
]

# GAD-7 items (Generalized Anxiety Disorder)
GAD7_ITEMS = [
    "Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
    "Over the last 2 weeks, how often have you not been able to stop or control worrying?",
    "Over the last 2 weeks, how often have you worried too much about different things?",
    "Over the last 2 weeks, how often have you had trouble relaxing?",
    "Over the last 2 weeks, how often have you been so restless that it is hard to sit still?",
    "Over the last 2 weeks, how often have you become easily annoyed or irritable?",
    "Over the last 2 weeks, how often have you felt afraid, as if something awful might happen?",
]

ALL_ITEMS = PHQ9_ITEMS + GAD7_ITEMS

# How many user turns between questionnaire item injections (after calibration)
INJECTION_INTERVAL = 3


def next_item(session_id: str) -> dict | None:
    """Return the next unanswered questionnaire item, or None if all are done."""
    asked = get_questionnaire_asked(session_id)
    for idx, item in enumerate(ALL_ITEMS):
        if idx not in asked:
            mark_questionnaire_asked(session_id, idx)
            source = "PHQ-9" if idx < len(PHQ9_ITEMS) else "GAD-7"
            return {"id": idx, "text": item, "source": source}
    return None


def items_remaining(session_id: str) -> int:
    asked = get_questionnaire_asked(session_id)
    return len(ALL_ITEMS) - len(asked)

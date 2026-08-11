"""Session state management.

Extends the existing in-memory session store (backend.app.memory) with
calibration tracking and questionnaire state.

Short-term session messages live in backend.app.memory._sessions.
This module adds a parallel _meta dict keyed by session_id that holds:
  - calibration_words: int   -- cumulative word count from user messages
  - calibration_start: float -- timestamp (UTC epoch) of first message
  - questionnaire_asked: list[int] -- indices of questionnaire items already asked
"""

from datetime import datetime, timezone
from backend.config import CALIBRATION_WORD_TARGET, CALIBRATION_TIME_SECONDS

_meta: dict[str, dict] = {}


def _get_meta(session_id: str) -> dict:
    return _meta.setdefault(session_id, {
        "calibration_words": 0,
        "calibration_start": None,
        "questionnaire_asked": [],
    })


def update_calibration(session_id: str, user_message: str) -> None:
    """Accumulate words and set start timestamp on first call."""
    meta = _get_meta(session_id)
    words = len(user_message.split())
    meta["calibration_words"] += words
    if meta["calibration_start"] is None:
        meta["calibration_start"] = datetime.now(timezone.utc).timestamp()


def calibration_progress(session_id: str) -> float:
    """Return calibration progress as a percentage (0-100).

    Calibration completes when EITHER the word target OR the time target is met.
    """
    meta = _get_meta(session_id)
    words = meta["calibration_words"]
    start = meta["calibration_start"]

    if start is None:
        return 0.0

    elapsed = datetime.now(timezone.utc).timestamp() - start
    word_pct = min(words / CALIBRATION_WORD_TARGET, 1.0)
    time_pct = min(elapsed / CALIBRATION_TIME_SECONDS, 1.0)
    return max(word_pct, time_pct) * 100


def is_calibrated(session_id: str) -> bool:
    return calibration_progress(session_id) >= 100.0


def get_questionnaire_asked(session_id: str) -> list[int]:
    return _get_meta(session_id)["questionnaire_asked"]


def mark_questionnaire_asked(session_id: str, item_index: int) -> None:
    asked = _get_meta(session_id)["questionnaire_asked"]
    if item_index not in asked:
        asked.append(item_index)

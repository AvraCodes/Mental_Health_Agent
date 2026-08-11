"""Placeholder evaluation harness for the safety classifier.

TODO(BLOCKING): Before any real demo or user testing, this file must be
expanded to run the full pipeline against BeaverTails (700 questions across
14 harm categories). Track false negative rate on crisis/self-harm detection
specifically -- false negatives are the dangerous failure mode.

Current state: only tests the stub classifier, which always returns "safe".
This test exists so the harness file is not forgotten.
"""

import sys
import os

# allow running as `python -m pytest backend/eval/harness_test.py` from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_stub_safety_returns_safe():
    """The stub classifier must always return 'safe'."""
    from backend.safety import classify
    assert classify("I am feeling great today") == "safe"
    assert classify("I want to hurt myself") == "safe"  # stub -- real model must flag this


def test_stub_safety_accepts_empty():
    from backend.safety import classify
    assert classify("") == "safe"


# ---------------------------------------------------------------------------
# TODO: BeaverTails evaluation
# ---------------------------------------------------------------------------
# 1. Download BeaverTails dataset (700 questions, 14 harm categories)
# 2. Run each question through safety.classify()
# 3. Compare predictions against ground truth labels
# 4. Report:
#    - Overall accuracy
#    - Per-category precision / recall / F1
#    - FALSE NEGATIVE RATE on crisis/self-harm categories (critical metric)
# 5. Gate: do not proceed with user testing if FNR > threshold (TBD)
# ---------------------------------------------------------------------------

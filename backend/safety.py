"""Safety classifier stub.

TODO(BLOCKING): Replace this stub with a calibrated BERT/RoBERTa classifier
before any real demo or user testing. This is a hard gate -- the stub always
returns "safe" and provides zero actual protection.

The real classifier should detect:
  - crisis / self-harm intent
  - therapy-seeking signals
  - unsafe user prompts

See eval/harness_test.py for the BeaverTails evaluation harness placeholder.
Fine-tuned BERT-base and RoBERTa-large models beat GPT-3.5 zero/few-shot at
this task (~70% accuracy on detecting unsafe responses).
"""


def classify(text: str) -> str:
    """Classify text as 'safe' or 'unsafe'.

    STUB: always returns 'safe'. Must be replaced before any user-facing
    deployment.
    """
    # TODO(BLOCKING): replace with real model inference
    return "safe"

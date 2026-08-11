"""Inference wrapper for Qwen-3.4B using transformers + bitsandbytes 4-bit quantisation.

Loads the model once at import time. Each call to generate() runs inference
against the already-resident model.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from backend.config import LLM_MODEL


SYSTEM_PROMPT = (
    "You are Zoya, a compassionate AI mental health support assistant. "
    "You use evidence-based therapeutic techniques (CBT, DBT, ACT) to support users. "
    "You NEVER diagnose, prescribe medication, or claim to replace a licensed therapist. "
    "If someone is in crisis, you encourage them to contact emergency services or a crisis hotline. "
    "Keep responses warm, empathetic, and grounded in the context provided."
)


class QwenInference:
    def __init__(self):
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        self._tokenizer = AutoTokenizer.from_pretrained(
            LLM_MODEL, trust_remote_code=True
        )
        quant_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            LLM_MODEL,
            quantization_config=quant_cfg,
            device_map="auto",
            trust_remote_code=True,
        )
        self._model.eval()

    def generate(self, prompt: str, max_new_tokens: int = 512) -> str:
        self._load()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
        # strip the input tokens from the output
        generated = output[0][inputs["input_ids"].shape[-1]:]
        return self._tokenizer.decode(generated, skip_special_tokens=True).strip()


_engine = QwenInference()


def generate(prompt: str) -> str:
    """Run inference against the loaded Qwen model."""
    return _engine.generate(prompt)

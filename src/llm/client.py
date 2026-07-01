from __future__ import annotations
import hashlib
from .parser import LLMDecision, parse_llm_output

class LLMClient:
    def __init__(self, mode: str = "dry_run", backbone: str = "gpt-4o", temperature: float = 0.0, max_tokens: int = 500):
        self.mode = mode
        self.backbone = backbone
        self.temperature = temperature
        self.max_tokens = max_tokens

    def decide(self, prompt: str, p_bert: float, uncertainty: float) -> LLMDecision:
        if self.mode == "dry_run":
            h = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
            p = min(0.99, max(0.01, 0.65 * float(p_bert) + 0.35 * (0.25 + 0.5 * h) + 0.10 * float(uncertainty)))
            return LLMDecision(probability=p, label="SBR" if p >= 0.5 else "NSBR", justification="Dry-run deterministic LLM proxy.", raw="")
        if self.mode == "openai_compatible":
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=self.backbone,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return parse_llm_output(resp.choices[0].message.content or "{}")
        raise ValueError(f"Unsupported LLM mode: {self.mode}")

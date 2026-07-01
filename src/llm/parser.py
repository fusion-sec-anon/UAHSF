from __future__ import annotations
import json
import re
from dataclasses import dataclass

@dataclass
class LLMDecision:
    probability: float
    label: str
    justification: str = ""
    raw: str = ""


def parse_llm_output(raw: str) -> LLMDecision:
    text = raw.strip()
    try:
        obj = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        obj = json.loads(m.group(0)) if m else {}
    pct = obj.get("likelihood_percent", obj.get("probability", obj.get("p_llm", 0)))
    try:
        p = float(pct) / (100.0 if float(pct) > 1 else 1.0)
    except Exception:
        p = 0.0
    label = str(obj.get("label", "SBR" if p >= 0.5 else "NSBR")).upper()
    return LLMDecision(max(0.0, min(1.0, p)), label, str(obj.get("justification", "")), raw)

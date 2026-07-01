from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class FusionResult:
    p_final: float
    alpha_bert: float
    uncertainty: float


def uncertainty_weighted_fusion(p_bert: float, p_llm: float, max_local_conflict: float, global_completeness: float, beta: float = 0.5, k: float = 10.0) -> FusionResult:
    p_bert = min(max(float(p_bert), 0.0), 1.0)
    p_llm = min(max(float(p_llm), 0.0), 1.0)
    c = min(max(float(max_local_conflict), 0.0), 1.0)
    m = min(max(float(global_completeness), 0.0), 1.0)
    beta = min(max(float(beta), 0.0), 1.0)
    u = beta * c + (1.0 - beta) * (1.0 - m)
    z = float(k) * (abs(2.0 * p_bert - 1.0) - u)
    alpha = 1.0 / (1.0 + math.exp(-z))
    return FusionResult(p_final=alpha * p_bert + (1.0 - alpha) * p_llm, alpha_bert=alpha, uncertainty=u)

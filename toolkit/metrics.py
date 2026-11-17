"""metrics.py

Lightweight metric implementations used in the paper:
- pd (probability of detection / recall on positive class)
- pf (probability of false alarm / false positive rate)
- g-measure (harmonic mean between pd and specificity)

"""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ConfusionMatrix:
    tp: int
    fp: int
    tn: int
    fn: int

def pd(cm: ConfusionMatrix) -> float:
    """Probability of detection: TP / (TP + FN)."""
    denom = cm.tp + cm.fn
    return (cm.tp / denom) if denom else 0.0

def pf(cm: ConfusionMatrix) -> float:
    """Probability of false alarm: FP / (FP + TN)."""
    denom = cm.fp + cm.tn
    return (cm.fp / denom) if denom else 0.0

def g_measure(cm: ConfusionMatrix) -> float:
    """g-measure: 2*pd*(1-pf) / (pd + (1-pf))."""
    _pd = pd(cm)
    _spec = 1.0 - pf(cm)
    denom = _pd + _spec
    return (2.0 * _pd * _spec / denom) if denom else 0.0

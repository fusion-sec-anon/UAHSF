"""io_schema.py

These schemas reflect the paper-aligned symbols:
- X: bug report text (summary + description)
- S_KWD: key contradiction terms
- C_scores: contradiction scores
- M: completeness score
- P_CWE: matched CWE patterns
- P_BERT: BERT anchor prediction
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class ContradictionTerm:
    s_j: str
    C_score: Optional[float] = None
    note: Optional[str] = None

@dataclass
class PromptPayload:
    bug_id: Optional[str]
    X: str
    S_KWD: List[ContradictionTerm]
    M: float
    P_CWE: List[str]
    missing_triggers: List[str]
    P_BERT: Dict[str, Any]  # {"label": str, "confidence": float}

@dataclass
class LLMDecision:
    label: str  # "SBR" or "NSBR"
    probability: int  # 0..100
    rationale: str
    disambiguation: List[Dict[str, Any]]
    completeness: Dict[str, Any]
    anchors: Dict[str, Any]

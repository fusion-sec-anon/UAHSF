from __future__ import annotations
from pathlib import Path
from uncertainty.local_conflict import TermConflict
from uncertainty.global_completeness import PatternCoverage


def build_uncertainty_prompt(text: str, conflicts: list[TermConflict], low_patterns: list[PatternCoverage], p_bert: float, completeness: float) -> str:
    term = conflicts[0].term if conflicts else "N/A"
    c_score = conflicts[0].contradiction_score if conflicts else 0.0
    pattern = low_patterns[0].pattern_id + ": " + low_patterns[0].name if low_patterns else "N/A"
    return f'''{text} {term} {c_score:.4f} {pattern} {completeness:.4f} {p_bert:.4f}'''

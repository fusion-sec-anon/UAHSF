from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import re
from typing import Any


SECURITY_TERMS = {
    "access", "authentication", "authorization", "bypass", "buffer", "command",
    "confidentiality", "corruption", "credential", "csrf", "directory", "disclose",
    "dos", "execute", "execution", "exposure", "file", "injection", "leak",
    "memory", "overflow", "permission", "privilege", "sandbox", "script", "sql",
    "token", "traversal", "validate", "validation", "xss", "crash", "stack",
}

AMBIGUOUS_TERMS = {
    "crash", "leak", "injection", "stack", "overflow", "privilege", "permission",
    "access", "token", "sandbox", "script", "file",
}

BENIGN_CONTEXT = {
    "ui", "button", "display", "layout", "loading", "test", "mock", "dependency",
    "injected", "logging", "performance", "slow", "cosmetic", "message", "tooltip",
}

TRIGGER_TERMS = {
    "input", "request", "payload", "parameter", "argument", "url", "uri", "file",
    "upload", "open", "parse", "when", "via", "send", "submit", "crafted",
}

IMPACT_TERMS = {
    "execute", "execution", "read", "write", "overwrite", "disclose", "expose",
    "leak", "corrupt", "crash", "dos", "bypass", "escalate", "privilege",
    "confidentiality", "arbitrary", "unauthorized", "compromise",
}

CWE_PATTERNS = [
    ("CWE-20", "Improper Input Validation", {"input", "validate", "validation", "parameter", "crafted"}),
    ("CWE-79", "Cross-site Scripting", {"xss", "script", "html", "sanitize", "browser"}),
    ("CWE-89", "SQL Injection", {"sql", "injection", "query", "database"}),
    ("CWE-119", "Memory Buffer Errors", {"buffer", "overflow", "memory", "bounds", "overwrite"}),
    ("CWE-200", "Exposure of Sensitive Information", {"expose", "leak", "disclose", "credential", "token", "confidentiality"}),
    ("CWE-22", "Path Traversal", {"path", "directory", "traversal", "file"}),
    ("CWE-287", "Improper Authentication", {"authentication", "login", "credential", "session"}),
    ("CWE-269", "Improper Privilege Management", {"privilege", "permission", "escalate", "access"}),
]


@dataclass
class TermRecord:
    term: str
    contradiction_score: float
    note: str


@dataclass
class PatternRecord:
    pattern_id: str
    name: str
    coverage: float
    matched_terms: list[str]


@dataclass
class DemoDecision:
    label: str
    p_bert: float
    p_llm: float
    p_final: float
    alpha_bert: float
    uncertainty: float
    local_conflict: float
    global_completeness: float
    matched_terms: list[str]
    contradiction_terms: list[TermRecord]
    low_coverage_patterns: list[PatternRecord]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _window_tokens(tokens: list[str], term: str, size: int = 6) -> list[str]:
    try:
        idx = tokens.index(term)
    except ValueError:
        return []
    lo = max(0, idx - size)
    hi = min(len(tokens), idx + size + 1)
    return tokens[lo:hi]


def analyze_demo_report(text: str, beta: float = 0.5, k: float = 8.0) -> DemoDecision:

    toks = _tokens(text)
    tok_set = set(toks)
    length_norm = min(len(toks) / 120.0, 1.0)

    matched = sorted(tok_set.intersection(SECURITY_TERMS))
    trigger_hits = tok_set.intersection(TRIGGER_TERMS)
    impact_hits = tok_set.intersection(IMPACT_TERMS)
    benign_hits = tok_set.intersection(BENIGN_CONTEXT)

    evidence = 0.55 * len(matched) + 0.75 * len(trigger_hits) + 0.9 * len(impact_hits)
    penalty = 0.55 * len(benign_hits)
    p_bert = _clip(_sigmoid(-2.0 + 0.38 * evidence - 0.22 * penalty))

    contradiction_terms: list[TermRecord] = []
    for term in sorted(tok_set.intersection(AMBIGUOUS_TERMS)):
        win = _window_tokens(toks, term)
        sec_context = len(set(win).intersection(SECURITY_TERMS | TRIGGER_TERMS | IMPACT_TERMS))
        benign_context = len(set(win).intersection(BENIGN_CONTEXT))
        instability = 0.25 + 0.12 * sec_context + 0.18 * benign_context
        dependence = 0.25 + 0.10 * (1 if term in IMPACT_TERMS else 0) + 0.06 * len(matched)
        score = _clip(dependence * instability)
        note = "ambiguous security term; inspect local context"
        if benign_context > 0:
            note = "ambiguous term appears with benign/reliability context"
        if sec_context >= 3 and benign_context == 0:
            note = "term is supported by nearby security evidence"
        contradiction_terms.append(TermRecord(term, round(score, 3), note))

    local_conflict = max((x.contradiction_score for x in contradiction_terms), default=0.0)

    pattern_records: list[PatternRecord] = []
    for pid, name, terms in CWE_PATTERNS:
        hits = sorted(tok_set.intersection(terms))
        # Coverage proxy: pattern evidence + report has trigger/impact chain.
        coverage = _clip(0.15 + 0.16 * len(hits) + 0.12 * bool(trigger_hits) + 0.14 * bool(impact_hits) + 0.08 * length_norm)
        pattern_records.append(PatternRecord(pid, name, round(coverage, 3), hits))

    related = [p for p in pattern_records if p.matched_terms]
    pool = related if related else pattern_records
    low_patterns = sorted(pool, key=lambda p: (p.coverage, -len(p.matched_terms)))[:3]

    chain_score = 0.35 * bool(trigger_hits) + 0.35 * bool(impact_hits) + 0.15 * (len(matched) >= 2) + 0.15 * length_norm
    global_completeness = _clip(chain_score)

    # LLM-like reasoning proxy: conservative when completeness is low, stronger when trigger+impact exist.
    p_llm = _clip(0.20 + 0.50 * bool(trigger_hits and impact_hits) + 0.12 * min(len(matched), 3) / 3.0 - 0.10 * bool(benign_hits))

    uncertainty = _clip(beta * local_conflict + (1.0 - beta) * (1.0 - global_completeness))
    alpha_bert = _sigmoid(k * (abs(2.0 * p_bert - 1.0) - uncertainty))
    p_final = _clip(alpha_bert * p_bert + (1.0 - alpha_bert) * p_llm)
    label = "SBR" if p_final >= 0.5 else "NSBR"

    if label == "SBR":
        rationale = "The report contains security-relevant terms and enough trigger/impact evidence for an SBR-oriented decision."
    else:
        rationale = "The report lacks a sufficiently complete vulnerability chain or the matched terms appear mostly ambiguous/benign."

    return DemoDecision(
        label=label,
        p_bert=round(p_bert, 3),
        p_llm=round(p_llm, 3),
        p_final=round(p_final, 3),
        alpha_bert=round(alpha_bert, 3),
        uncertainty=round(uncertainty, 3),
        local_conflict=round(local_conflict, 3),
        global_completeness=round(global_completeness, 3),
        matched_terms=matched,
        contradiction_terms=contradiction_terms[:5],
        low_coverage_patterns=low_patterns,
        rationale=rationale,
    )

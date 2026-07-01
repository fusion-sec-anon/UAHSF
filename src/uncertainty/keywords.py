from __future__ import annotations
from pathlib import Path
import json
import re
from typing import Iterable

DEFAULT_SECURITY_TERMS = {""}

def load_security_terms(*paths: str | Path | None) -> list[str]:
    terms = set(DEFAULT_SECURITY_TERMS)
    for path in paths:
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            continue
        if p.suffix == ".txt":
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    terms.add(line)
        elif p.suffix in {".json", ".jsonl"}:
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            _collect_terms(obj, terms)
    return sorted(terms, key=lambda x: (-len(x), x))


def _collect_terms(obj, terms: set[str]):
    if isinstance(obj, str):
        s = obj.strip().lower()
        if 2 <= len(s) <= 80:
            terms.add(s)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_terms(v, terms)
    elif isinstance(obj, list):
        for v in obj:
            _collect_terms(v, terms)


def find_terms(text: str, terms: Iterable[str], max_terms: int = 8) -> list[str]:
    t = text.lower()
    found = []
    for term in terms:
        pat = r"(?<![a-z0-9_])" + re.escape(term.lower()) + r"(?![a-z0-9_])"
        if re.search(pat, t):
            found.append(term)
            if len(found) >= max_terms:
                break
    return found

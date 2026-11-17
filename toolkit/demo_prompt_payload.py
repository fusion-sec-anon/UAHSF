from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any

def load_terms_txt(path: Path) -> List[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def build_demo_payload() -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[1]

    terms_txt = root / "uncertainty_quantification" / "security_keywords" / "source_cwe_terms.txt"
    terms_idx = root / "uncertainty_quantification" / "security_keywords" / "cwe_security_terms_index.json"
    cross_idx = root / "uncertainty_quantification" / "security_cross_words" / "security_cross_words_index.json"

    cwe_terms = load_terms_txt(terms_txt)
    cwe_index = load_json(terms_idx)
    cross_index = load_json(cross_idx) if cross_idx.exists() else {}

    payload = {
        "bug_id": "15301",
        "X": "Summary: ...\n\nDescription: ...",
        "S_KWD": [
            {"s_j": "crash", "C_score": 0.83, "note": "Ambiguous term: reliability vs DoS."}
        ],
        "M": 0.42,
        "P_CWE": ["CWE-20 (Improper Input Validation)"],
        "missing_triggers": ["impact not described"],
        "P_BERT": {"label": "NSBR", "confidence": 0.73},
        "artifacts_loaded": {
            "num_cwe_terms": len(cwe_terms),
            "num_index_terms": int(cwe_index.get("term_count", 0)),
            "cross_words_datasets": list(cross_index.get("datasets", {}).keys()) if isinstance(cross_index, dict) else [],
        },
    }
    return payload

if __name__ == "__main__":
    payload = build_demo_payload()
    print(json.dumps(payload, ensure_ascii=False, indent=2))

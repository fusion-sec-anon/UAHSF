from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import pandas as pd

LABEL_MAP = {"SBR": 1, "NSBR": 0, "security": 1, "non-security": 0, "non_security": 0, 1: 1, 0: 0}


def _infer_column(columns: Iterable[str], candidates: List[str]) -> str | None:
    lower = {str(c).lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def load_bug_reports(path: str | Path, text_columns: list[str] | None = None, label_column: str | None = None, id_column: str | None = None) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    if id_column is None or id_column not in df.columns:
        id_column = _infer_column(df.columns, ["bug_id", "id", "Issue ID", "Bug ID", "issue_id"])
    if label_column is None or label_column not in df.columns:
        label_column = _infer_column(df.columns, ["label", "class", "security", "is_security", "Security"])
    if not text_columns:
        summary = _infer_column(df.columns, ["summary", "title", "short_desc", "Summary"])
        desc = _infer_column(df.columns, ["description", "desc", "body", "Description"])
        text_columns = [c for c in [summary, desc] if c]
    else:
        text_columns = [c for c in text_columns if c in df.columns]

    if not text_columns:
        raise ValueError(f"Cannot infer text columns from {list(df.columns)}")

    out = pd.DataFrame()
    out["bug_id"] = df[id_column].astype(str) if id_column else [str(i) for i in range(len(df))]
    out["text"] = df[text_columns].fillna("").astype(str).agg("\n".join, axis=1)
    if label_column:
        out["label"] = df[label_column].map(lambda x: LABEL_MAP.get(x, LABEL_MAP.get(str(x).strip(), x)))
    return out

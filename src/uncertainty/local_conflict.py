from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import re

import numpy as np


@dataclass
class TermConflict:
    term: str
    dependence: float
    instability: float
    contradiction_score: float

    semantic_density: float = 0.0
    window_size: int = 3
    token_span: tuple[int, int] | None = None




def _mask_term(text: str, term: str) -> str:
    return re.sub(
        r"(?<![a-zA-Z0-9_])" + re.escape(term) + r"(?![a-zA-Z0-9_])",
        "[MASK]",
        text,
        flags=re.IGNORECASE,
    )


def _context_tokens(text: str, term: str, window: int) -> list[str]:
    toks = re.findall(r"[A-Za-z0-9_:/.-]+", text)
    low = [x.lower() for x in toks]
    term_parts = term.lower().split()

    positions = []

    for i in range(len(low)):
        if low[i : i + len(term_parts)] == term_parts:
            positions.append(i)

    ctx = []

    for pos in positions[:2]:
        lo = max(0, pos - window)
        hi = min(len(toks), pos + len(term_parts) + window)

        for j in range(lo, hi):
            if j < pos or j >= pos + len(term_parts):
                ctx.append(toks[j])

    return ctx[: 2 * window]


def _mask_first_token(text: str, token: str) -> str:
    return re.sub(
        re.escape(token),
        "[MASK]",
        text,
        count=1,
        flags=re.IGNORECASE,
    )


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []

    lo = min(values)
    hi = max(values)

    if abs(hi - lo) < 1e-12:
        return [0.5 for _ in values]

    return [(v - lo) / (hi - lo) for v in values]


def _safe_float(x: Any) -> float:
    if hasattr(x, "probability"):
        return float(x.probability)

    return float(x)



def _cosine(a: Any, b: Any) -> float:
    try:
        import torch

        if isinstance(a, torch.Tensor):
            denom = torch.norm(a) * torch.norm(b) + 1e-12
            return float(torch.dot(a, b) / denom)
    except Exception:
        pass

    a = np.asarray(a)
    b = np.asarray(b)

    denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-12
    return float(np.dot(a, b) / denom)


def _semantic_density(
    hidden_states: Any,
    center_index: int,
    k_init: int,
) -> float:
    seq_len = len(hidden_states)

    lo = max(0, center_index - k_init)
    hi = min(seq_len, center_index + k_init + 1)

    if lo >= hi:
        return 0.0

    center_vec = hidden_states[center_index]
    sims = []

    for i in range(lo, hi):
        sims.append(_cosine(center_vec, hidden_states[i]))

    if not sims:
        return 0.0

    return float(np.mean(sims))


def _select_adaptive_window(
    density: float,
    tau_low: float,
    tau_high: float,
    k_small: int,
    k_medium: int,
    k_large: int,
) -> int:
    if density >= tau_high:
        return k_small

    if density <= tau_low:
        return k_large

    return k_medium


def _span_center(start: int, end: int) -> int:
    return int((start + end - 1) / 2)


def _valid_context_indices(
    seq_len: int,
    start: int,
    end: int,
    window: int,
) -> list[int]:
    center = _span_center(start, end)

    lo = max(1, center - window)
    hi = min(seq_len - 1, center + window + 1)

    indices = []

    for i in range(lo, hi):
        if start <= i < end:
            continue
        indices.append(i)

    return indices


def _get_probability(
    text: str,
    prob_fn: Callable[[str], float] | None = None,
    scorer: Any | None = None,
) -> float:
    if scorer is not None and hasattr(scorer, "predict_proba"):
        return _safe_float(scorer.predict_proba(text))

    if prob_fn is not None:
        return float(prob_fn(text))

    raise ValueError("Either scorer or prob_fn must be provided.")


def _get_bert_scoring_result(text: str, scorer: Any) -> Any:
    if hasattr(scorer, "predict_with_encoding"):
        return scorer.predict_with_encoding(text)

    if hasattr(scorer, "encode") and hasattr(scorer, "predict_proba"):
        encoding = scorer.encode(text)
        pred = scorer.predict_proba(text)

        class _Result:
            probability = _safe_float(pred)
            tokens = encoding.tokens
            hidden_states = encoding.hidden_states
            logits = getattr(pred, "logits", None)

        return _Result()

    raise ValueError(
        "The scorer must provide predict_with_encoding() or encode()+predict_proba()."
    )


def _find_term_spans_with_scorer(
    text: str,
    term: str,
    scorer: Any,
) -> list[tuple[int, int]]:
    if hasattr(scorer, "find_token_spans"):
        try:
            return list(scorer.find_token_spans(text, term))
        except Exception:
            return []

    return []



def _compute_local_conflicts_neural(
    text: str,
    terms: list[str],
    scorer: Any,
    k_init: int = 3,
    k_small: int = 1,
    k_medium: int = 3,
    k_large: int = 6,
    tau_low: float = 0.35,
    tau_high: float = 0.70,
) -> list[TermConflict]:
    if not terms:
        return []

    bert_result = _get_bert_scoring_result(text, scorer)

    p0 = float(bert_result.probability)
    hidden_states = bert_result.hidden_states
    seq_len = len(bert_result.tokens)

    raw: list[tuple[str, float, float, float, int, tuple[int, int] | None]] = []

    for term in terms:
        spans = _find_term_spans_with_scorer(text, term, scorer)

        if not spans:
            p_mask_term = _get_probability(
                _mask_term(text, term),
                prob_fn=None,
                scorer=scorer,
            )

            delta_j = p0 - p_mask_term
            dependence = abs(delta_j)

            deltas = []

            for tok in _context_tokens(text, term, k_medium):
                p_mask_ctx = _get_probability(
                    _mask_first_token(text, tok),
                    prob_fn=None,
                    scorer=scorer,
                )
                deltas.append(p0 - p_mask_ctx)

            instability = (
                float(np.mean([(d - delta_j) ** 2 for d in deltas]))
                if deltas
                else 0.0
            )

            raw.append(
                (
                    term,
                    dependence,
                    instability,
                    0.0,
                    k_medium,
                    None,
                )
            )
            continue

        occurrence_records = []

        for start, end in spans:
            if start <= 0 or end >= seq_len:
                continue

            center = _span_center(start, end)

            density = _semantic_density(
                hidden_states=hidden_states,
                center_index=center,
                k_init=k_init,
            )

            window = _select_adaptive_window(
                density=density,
                tau_low=tau_low,
                tau_high=tau_high,
                k_small=k_small,
                k_medium=k_medium,
                k_large=k_large,
            )

            p_mask_term = _safe_float(
                scorer.predict_proba_with_masked_span(
                    text,
                    start,
                    end,
                )
            )

            delta_j = p0 - p_mask_term
            dependence = abs(delta_j)

            context_indices = _valid_context_indices(
                seq_len=seq_len,
                start=start,
                end=end,
                window=window,
            )

            deltas = []

            for idx in context_indices:
                p_mask_ctx = _safe_float(
                    scorer.predict_proba_with_masked_token(
                        text,
                        idx,
                    )
                )

                delta_ctx = p0 - p_mask_ctx
                deltas.append(delta_ctx)

            instability = (
                float(np.mean([(d - delta_j) ** 2 for d in deltas]))
                if deltas
                else 0.0
            )

            occurrence_records.append(
                (
                    dependence,
                    instability,
                    density,
                    window,
                    (start, end),
                )
            )

        if not occurrence_records:
            continue

        best = max(
            occurrence_records,
            key=lambda x: x[0] * x[1],
        )

        dependence, instability, density, window, span = best

        raw.append(
            (
                term,
                dependence,
                instability,
                density,
                window,
                span,
            )
        )

    if not raw:
        return []

    dep_n = _minmax([x[1] for x in raw])
    ins_n = _minmax([x[2] for x in raw])

    results = []

    for i, (term, dependence, instability, density, window, span) in enumerate(raw):
        contradiction = float(dep_n[i] * ins_n[i])

        results.append(
            TermConflict(
                term=term,
                dependence=float(dependence),
                instability=float(instability),
                contradiction_score=contradiction,
                semantic_density=float(density),
                window_size=int(window),
                token_span=span,
            )
        )

    return sorted(
        results,
        key=lambda x: x.contradiction_score,
        reverse=True,
    )


def compute_local_conflicts(
    text: str,
    terms: list[str],
    prob_fn: Callable[[str], float] | None = None,
    scorer: Any | None = None,
    k_init: int = 3,
    k_small: int = 1,
    k_medium: int = 3,
    k_large: int = 6,
    tau_low: float = 0.35,
    tau_high: float = 0.70,
    mode: str = "auto",
) -> list[TermConflict]:
    terms = [t for t in terms if t and str(t).strip()]
    terms = list(dict.fromkeys([str(t).strip() for t in terms]))

    if not terms:
        return []

    if mode == "neural":
        if scorer is None:
            raise ValueError("scorer is required when mode='neural'.")

        return _compute_local_conflicts_neural(
            text=text,
            terms=terms,
            scorer=scorer,
            k_init=k_init,
            k_small=k_small,
            k_medium=k_medium,
            k_large=k_large,
            tau_low=tau_low,
            tau_high=tau_high,
        )

    if scorer is not None and all(
        hasattr(scorer, name)
        for name in [
            "predict_proba",
            "predict_with_encoding",
            "predict_proba_with_masked_token",
            "predict_proba_with_masked_span",
            "find_token_spans",
        ]
    ):
        try:
            return _compute_local_conflicts_neural(
                text=text,
                terms=terms,
                scorer=scorer,
                k_init=k_init,
                k_small=k_small,
                k_medium=k_medium,
                k_large=k_large,
                tau_low=tau_low,
                tau_high=tau_high,
            )
        except Exception:
            pass

    raise ValueError("Either scorer or prob_fn must be provided.")
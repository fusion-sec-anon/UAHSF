from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict
import pandas as pd

from bert.bert_sbr import BertSBRScorer
from uncertainty.keywords import load_security_terms, find_terms
from uncertainty.local_conflict import compute_local_conflicts
from uncertainty.global_completeness import load_cwe_patterns, compute_global_completeness
from llm.prompt_builder import build_uncertainty_prompt
from llm.client import LLMClient
from fusion.uncertainty_weighted_fusion import uncertainty_weighted_fusion


class UAHSFPipeline:
    def __init__(self, config: Dict[str, Any], repo_root: str | Path = ".", dry_run: bool = True):
        self.cfg = config
        self.root = Path(repo_root)
        self.bert = BertSBRScorer(
            model_name=config.get("bert", {}).get("model_name", "bert-base-uncased"),
            device=config.get("bert", {}).get("device", "auto"),
            max_length=int(config.get("bert", {}).get("max_length", 512)),
            dry_run=dry_run,
            dry_run_probability=float(config.get("bert", {}).get("dry_run_probability", 0.5)),
        )
        cwe_cfg = config.get("cwe", {})
        self.patterns = load_cwe_patterns(self.root / cwe_cfg.get("pattern_file", ""))
        self.terms = load_security_terms(self.root / cwe_cfg.get("keywords_file", ""))
        llm_cfg = config.get("llm", {})
        self.llm = LLMClient(
            mode=llm_cfg.get("mode", "dry_run"),
            backbone=llm_cfg.get("backbone", "gpt-4o"),
            temperature=float(llm_cfg.get("temperature", 0)),
            max_tokens=int(llm_cfg.get("max_tokens", 500)),
        )

    def predict_one(self, bug_id: str, text: str) -> dict:
        p_bert = self.bert.predict_proba(text).probability
        local_cfg = self.cfg.get("local_uncertainty", {})
        terms = find_terms(text, self.terms, max_terms=int(local_cfg.get("max_terms", 8)))
        conflicts = compute_local_conflicts(text, terms, lambda t: self.bert.predict_proba(t).probability, k_medium=int(local_cfg.get("k_medium", 3)))
        conflicts = sorted(conflicts, key=lambda c: c.contradiction_score, reverse=True)
        global_result = compute_global_completeness(text, self.patterns, top_k_missing=int(self.cfg.get("cwe", {}).get("top_k_missing_patterns", 3)))
        max_c = conflicts[0].contradiction_score if conflicts else 0.0
        prelim_u = 0.5 * max_c + 0.5 * (1.0 - global_result.completeness)
        prompt = build_uncertainty_prompt(text, conflicts, global_result.low_coverage_patterns, p_bert, global_result.completeness)
        llm_decision = self.llm.decide(prompt, p_bert=p_bert, uncertainty=prelim_u)
        fusion_cfg = self.cfg.get("fusion", {})
        fused = uncertainty_weighted_fusion(
            p_bert=p_bert,
            p_llm=llm_decision.probability,
            max_local_conflict=max_c,
            global_completeness=global_result.completeness,
            beta=float(fusion_cfg.get("beta", 0.5)),
            k=float(fusion_cfg.get("k", 10.0)),
        )
        threshold = float(self.cfg.get("threshold", 0.5))
        return {
            "bug_id": bug_id,
            "p_bert": p_bert,
            "max_local_conflict": max_c,
            "global_completeness": global_result.completeness,
            "p_llm": llm_decision.probability,
            "alpha_bert": fused.alpha_bert,
            "uncertainty": fused.uncertainty,
            "p_final": fused.p_final,
            "prediction": int(fused.p_final >= threshold),
            "prediction_label": "SBR" if fused.p_final >= threshold else "NSBR",
            "matched_terms": ";".join([c.term for c in conflicts[:5]]),
            "low_coverage_patterns": ";".join([p.pattern_id for p in global_result.low_coverage_patterns]),
        }

    def predict_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for _, row in df.iterrows():
            rows.append(self.predict_one(str(row.get("bug_id", len(rows))), str(row["text"])))
        out = pd.DataFrame(rows)
        if "label" in df.columns:
            out["label"] = df["label"].values
        return out

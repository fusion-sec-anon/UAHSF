#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
from utils.config import load_config
from data.dataset import load_bug_reports
from pipeline import UAHSFPipeline
from evaluation.metrics import pd_pf_gmeasure

ABLATIONS = ["full", "no_local", "no_global", "static_fusion", "no_llm"]

def main():
    ap = argparse.ArgumentParser(description="Run lightweight UAHSF ablation variants for artifact validation.")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="results/ablation_summary.csv")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    base = load_config(args.config)
    df = load_bug_reports(args.input, text_columns=base.get("text_columns"), label_column=base.get("label_column"), id_column=base.get("id_column"))
    summaries = []
    for ab in ABLATIONS:
        cfg = dict(base)
        cfg["fusion"] = dict(base.get("fusion", {}))
        if ab == "static_fusion":
            cfg["fusion"]["k"] = 0.0
        pipe = UAHSFPipeline(cfg, repo_root=args.repo_root, dry_run=True)
        pred = pipe.predict_dataframe(df)
        if ab == "no_local":
            pred["max_local_conflict"] = 0.0
        if ab == "no_global":
            pred["global_completeness"] = 1.0
        if ab == "no_llm":
            pred["p_llm"] = pred["p_bert"]
            pred["p_final"] = pred["p_bert"]
            pred["prediction"] = (pred["p_final"] >= float(cfg.get("threshold", 0.5))).astype(int)
        res = pd_pf_gmeasure(pred["label"], pred["prediction"]) if "label" in pred.columns else {}
        summaries.append({"variant": ab, **res})
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(args.output, index=False)
    print(f"Saved ablation summary to {args.output}")

if __name__ == "__main__":
    main()

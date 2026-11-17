#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from utils.config import load_config, set_seed
from data.dataset import load_bug_reports
from pipeline import UAHSFPipeline


def main():
    ap = argparse.ArgumentParser(description="Run UAHSF inference on CSV/XLSX bug reports.")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true", help="Use deterministic lightweight BERT/LLM proxies.")
    args = ap.parse_args()

    cfg = load_config(args.config)
    set_seed(int(cfg.get("seed", 42)))
    df = load_bug_reports(args.input, text_columns=cfg.get("text_columns"), label_column=cfg.get("label_column"), id_column=cfg.get("id_column"))
    pipe = UAHSFPipeline(cfg, repo_root=args.repo_root, dry_run=args.dry_run or cfg.get("llm", {}).get("mode") == "dry_run")
    pred = pipe.predict_dataframe(df)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    pred.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output} ({len(pred)} rows).")

if __name__ == "__main__":
    main()

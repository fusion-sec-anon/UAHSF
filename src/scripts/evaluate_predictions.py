#!/usr/bin/env python
from __future__ import annotations
import argparse
import json
import pandas as pd
from evaluation.metrics import pd_pf_gmeasure


def main():
    ap = argparse.ArgumentParser(description="Evaluate UAHSF predictions using pd, pf, and g-measure.")
    ap.add_argument("--pred", required=True)
    ap.add_argument("--label-column", default="label")
    ap.add_argument("--prediction-column", default="prediction")
    args = ap.parse_args()
    df = pd.read_csv(args.pred)
    if args.label_column not in df.columns:
        raise SystemExit(f"No label column found in {args.pred}; available columns: {list(df.columns)}")
    res = pd_pf_gmeasure(df[args.label_column], df[args.prediction_column])
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()

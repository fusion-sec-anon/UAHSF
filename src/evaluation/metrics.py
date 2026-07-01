from __future__ import annotations
import numpy as np


def pd_pf_gmeasure(y_true, y_pred):
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    pd_ = tp / (tp + fn) if tp + fn else 0.0
    pf = fp / (fp + tn) if fp + tn else 0.0
    specificity = 1.0 - pf
    g = (2 * pd_ * specificity / (pd_ + specificity)) if (pd_ + specificity) else 0.0
    return {"pd": pd_, "pf": pf, "g_measure": g, "tp": tp, "fp": fp, "tn": tn, "fn": fn}

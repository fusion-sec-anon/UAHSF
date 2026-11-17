# CWE Pattern Construction (CWE Top-25 → P_CWE)

This folder provides a **paper-aligned, reproducible** implementation for constructing the CWE pattern set **P_CWE** used in UAHSF.


---


## Inputs
- `cwe_pattern_top_25.csv`  
  The original CWE Top-25 export.

## Generated artifacts
- `cwe_patterns.json`
  For each CWE entry it stores:
  - concatenated entry text T_e (built from paper-used fields)
  - extracted causal fragments F_e
  - key term set K_e
  - IDF_e (and the reference corpus used)
  - cosine-similarity clusters with representative examples

- `cwe_fragments.jsonl`  
  All extracted fragments with `(cwe_id, fragment_id)` identifiers.

- `cwe_patterns_preview.md`
  Human-readable preview (key terms + sample fragments per CWE).

- `fragment_tfidf_vocab.json`  
  Offline embedding/prototype fallback (TF-IDF vectors + vocabulary).

---

## Method mapping to the paper

For each CWE entry e:
1) Concatenate fields to form T_e  
2) CausalExtract(T_e) → causal fragments F_e  
3) Encode fragments + cosine clustering to merge redundancy  
4) Prototype vector v_e = centroid( centroid(cluster_i) )  
5) KeyTerms(F_e) → K_e  
6) IDF_e = log(|D| + 1 / (n_e + 1)) on a reference corpus D


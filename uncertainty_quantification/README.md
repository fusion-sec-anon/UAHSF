# 🔍 Uncertainty Quantification Resources

This directory contains the public resources used to construct and support UAHSF’s uncertainty signals.
They complement the paper by making the underlying vocabularies and pattern artifacts explicit and reusable
under the same datasets and evaluation setting.

UAHSF relies on three types of resources:
- **Global incompleteness cues** via CWE Top-25 pattern artifacts (`P_CWE`)
- **Local ambiguity cues** via FARSEC-style security cross words that are high-frequency terms shared by SBR and NSBR (`S_KWD`)
- **Security keyword references** via CWE-derived security terms (`S_KWD`)

## Content

### 1) `cwe_patterns/` — CWE Top-25 pattern artifacts (`P_CWE`)
Artifacts derived from the CWE Top-25 corpus and organized for completeness assessment.
Typical contents include:
- `cwe_pattern_top_25.csv`: source export used to build the pattern set
- `cwe_patterns.json`: structured pattern entries + metadata
- `cwe_fragments.jsonl`: extracted causal fragments with identifiers
- `fragment_tfidf_vocab.json`: vocabulary metadata for offline matching / indexing

See `cwe_patterns/README.md` for the construction convention and file-level descriptions.

### 2) `security_keywords/` — CWE-derived security terms (`S_KWD`)
A cleaned CWE-derived term list and a structured index for downstream use:
- `source_cwe_terms.txt`: authoritative term list (one term per line)
- `cwe_security_terms_index.json`: enriched index (provenance/tags/groups + lookup indexes)

See `security_keywords/README.md` for the term normalization rules and index schema.

### 3) `security_cross_words/` — FARSEC-style cross words (`S_KWD`)
Dataset-specific cross-word vocabularies and a global index:
- `security_cross_words_by_dataset_lower.json`: compact per-dataset lists
- `security_cross_words_index.json`: global index (dataset coverage + counts)

See `security_cross_words/README.md` for definitions and JSON fields.

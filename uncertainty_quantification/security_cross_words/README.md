# Security Cross Words (FARSEC-style) — Cleaned & Packaged

This folder provides the **security cross words** used in our paper as an external, empirically-derived vocabulary source.
Cross words are **high-frequency terms appearing in both SBR and NSBR**, which often induce *local semantic confusion* and thus are useful signals for our contradiction-aware module.


---

## Files

### Global index (JSON)
- `security_cross_words_index.json`


It contains:
- `datasets.<DATASET>.terms`: the cleaned list for each dataset
- `datasets.<DATASET>.count`: number of terms
- `global_index.<TERM>.datasets`: which datasets contain the term
- `global_index.<TERM>.dataset_count`: in how many datasets the term appears
- `global_term_count`: number of unique cross terms across all datasets

### Compact loader helper (JSON)
- `security_cross_words_by_dataset_lower.json`

A compact mapping:
- `dataset -> [lowercased terms]`

This is convenient for fast membership checks in downstream scripts.

---

## Cleaning policy

We remove obvious noise while keeping domain meaning:

1. **Stopword removal**  
   We remove terms that are:
   - single English stopwords (e.g., *the/of/and/to*), or
   - phrases composed entirely of stopwords.

   Stopword list: scikit-learn's standard English stopwords.

2. **Non-lexical / invalid tokens removal**  
   We remove:
   - pure numbers / punctuation tokens,
   - extremely short letter-only tokens (length < 3), unless they are acronyms.

3. **Bug-report generic noise removal (single-token only)**  
   We also remove a small set of extremely generic bug-report tokens **when they appear as single words**, e.g.:
   `issue, error, bug, test, file, line, code, build, change, version, ...`

4. **Normalization & de-duplication**
   - normalize whitespace (collapse multiple spaces)
   - preserve original surface form (first occurrence)
   - de-duplicate case-insensitively
   - sort alphabetically


---

## Usage in our pipeline

### 1) Build the final security keyword reference set (SKWD)
In the paper, we form a comprehensive reference set by combining:
- CWE-derived terms (see `security_keywords/source_cwe_terms.txt`)
- FARSEC-style cross words (this folder)

A common practice is:
- **SKWD = CWE_terms ∪ CrossWords(dataset)**

### 2) Extract terms for a given report
For a report text `X` and a reference vocabulary `V` (SKWD or its subset), a simple and reproducible policy is:
- tokenize / lowercase `X`
- keep terms in `V` that match tokens


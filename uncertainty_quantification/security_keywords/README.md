# CWE Security Words (CWE-derived Terms) — TXT + JSON Index

This folder provides the **CWE-derived security words** used in our paper to construct the security keyword reference set (**S_KWD**).

---

## Files

### 1) `source_cwe_terms.txt`
- **One term per line** (UTF-8), de-duplicated (case-insensitive) and sorted.
- This is the **authoritative** list of CWE-derived terms used as the CWE-side vocabulary source for S_KWD.

### 2) `cwe_security_terms_index.json`
A structured index **derived from `source_cwe_terms.txt`** that adds:
- `provenance` for each term
- semantic `tags` and higher-level `families` (e.g., injection / memory-safety / traversal / XSS / CSRF)
- human-readable `concept_groups` (quick scan of coverage)
- convenience `indexes` (by_tag / by_family) for downstream scripts

---

## How this relates to the paper

In the paper, the final security keyword reference set is built by combining:
- **CWE-derived terms** (this folder), and
- **FARSEC-style security cross words** (see `security_cross_words/`).

The construction is:
- **S_KWD = CWE_terms ∪ CrossWords(dataset)**

---

## Construction summary

### Candidate sources
We mine candidate terms from CWE Top-25 artifacts (CSV) using:
- **`Alternate Terms`**: structured entries of the form `::TERM:<term>`
- **`Name`**: quoted aliases written like `('Path Traversal')`

### Cleaning policy
We apply conservative filtering:
- remove **English stopwords** (and phrases composed entirely of stopwords)
- remove obvious **academic/generic words** (e.g., analysis/method/performance/dataset)
- normalize whitespace and punctuation variants
- de-duplicate case-insensitively and sort

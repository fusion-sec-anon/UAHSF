from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal
import json
import math
import re

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except Exception:  # pragma: no cover
    torch = None
    nn = None
    F = None


BackendName = Literal["allennlp", "stanza", "spacy", "auto"]


@dataclass
class PatternCoverage:
    pattern_id: str
    name: str
    coverage: float
    matched_terms: list[str]


@dataclass
class CompletenessResult:
    completeness: float
    coverages: list[PatternCoverage]
    low_coverage_patterns: list[PatternCoverage]


@dataclass
class CWEPrototype:
    pattern_id: str
    name: str
    vector: Any
    key_terms: list[str]
    idf: float


@dataclass
class CausalFragment:
    subject: str
    predicate: str
    object: str
    modifier: str = ""

    def to_text(self) -> str:
        parts = []

        if self.subject:
            parts.append(self.subject.strip())

        if self.predicate:
            parts.append(f"-> {self.predicate.strip()} ->")

        if self.object:
            parts.append(self.object.strip())

        if self.modifier:
            parts.append(f"({self.modifier.strip()})")

        return " ".join(parts).strip()




def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower()))


def _tokenize_terms(text: str) -> list[str]:
    stop = {
        "this",
        "that",
        "with",
        "from",
        "will",
        "when",
        "then",
        "than",
        "into",
        "such",
        "have",
        "been",
        "product",
        "software",
        "system",
        "user",
        "users",
        "can",
        "may",
        "could",
        "would",
        "should",
    }

    terms = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    return [t for t in terms if t not in stop]


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text))
    text = text.replace("–", "-").replace("—", "-")
    return text.strip()


def _clean_phrase(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text))
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip(" -;:,.[]()")


def _split_sentences(text: str) -> list[str]:
    text = _clean_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _join_nonempty(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def _security_terms() -> set[str]:
    return {
        "input",
        "validation",
        "validate",
        "sanitize",
        "sanitization",
        "script",
        "xss",
        "sql",
        "injection",
        "inject",
        "overflow",
        "buffer",
        "memory",
        "bounds",
        "privilege",
        "permission",
        "access",
        "authorization",
        "authentication",
        "confidentiality",
        "exposure",
        "leak",
        "token",
        "credential",
        "command",
        "execution",
        "execute",
        "crash",
        "corruption",
        "file",
        "path",
        "directory",
        "traversal",
        "csrf",
        "bypass",
        "arbitrary",
        "denial",
        "dos",
        "overflow",
        "underflow",
        "race",
        "deadlock",
        "sandbox",
    }


def _security_predicates() -> set[str]:
    return {
        "cause",
        "lead",
        "result",
        "allow",
        "trigger",
        "execute",
        "bypass",
        "expose",
        "leak",
        "overflow",
        "inject",
        "validate",
        "sanitize",
        "crash",
        "corrupt",
        "overwrite",
        "read",
        "write",
        "access",
        "escalate",
        "disclose",
        "compromise",
        "permit",
        "enable",
        "open",
    }


def _contains_security_term(text: str) -> bool:
    text = str(text).lower()
    return any(term in text for term in _security_terms())


def _is_security_predicate(predicate: str) -> bool:
    predicate = str(predicate).lower()
    return predicate in _security_predicates()


def _extract_keywords_from_obj(obj: Any) -> list[str]:
    terms = []

    if isinstance(obj, str):
        terms.extend(_tokenize_terms(obj))

    elif isinstance(obj, dict):
        for key, val in obj.items():
            if str(key).lower() in {
                "id",
                "cwe_id",
                "name",
                "description",
                "extended_description",
                "common_consequences",
                "background_details",
                "detection_methods",
                "keywords",
                "key_terms",
                "consequences",
                "background",
                "detection",
            }:
                terms.extend(_extract_keywords_from_obj(val))
            elif isinstance(val, (list, dict)):
                terms.extend(_extract_keywords_from_obj(val))

    elif isinstance(obj, list):
        for val in obj:
            terms.extend(_extract_keywords_from_obj(val))

    return terms


def _read_json_or_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)

    if not p.exists():
        return []

    if p.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip()
        ]

    obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))

    if isinstance(obj, list):
        return obj

    if isinstance(obj, dict) and isinstance(obj.get("entries"), list):
        return obj["entries"]

    if isinstance(obj, dict):
        return list(obj.values())

    return []


def _default_cwe_rows() -> list[dict]:
    return [
        {
            "id": "",
            "name": "",
            "description": "",
            "keywords": [""],
        },
    ]


def load_cwe_patterns(path: str | Path | None) -> list[dict]:
    if path and Path(path).exists():
        rows = _read_json_or_jsonl(path)
    else:
        rows = []

    if not rows:
        rows = _default_cwe_rows()

    patterns = []

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            row = {
                "id": f"CWE-P{i}",
                "name": str(row)[:60],
                "keywords": _extract_keywords_from_obj(row),
            }

        pid = str(
            row.get("id")
            or row.get("cwe_id")
            or row.get("CWE-ID")
            or row.get("cwe")
            or f"CWE-P{i}"
        )

        name = str(row.get("name") or row.get("Name") or pid)

        raw_text = _concat_cwe_fields(row)
        if not raw_text:
            raw_text = " ".join(str(x) for x in row.values())

        kws = (
            row.get("keywords")
            or row.get("key_terms")
            or row.get("Ke")
            or _extract_keywords_from_obj(row)
        )

        kws = sorted(set(str(k).lower() for k in kws if len(str(k)) > 2))[:120]

        patterns.append(
            {
                "id": pid,
                "name": name,
                "keywords": kws,
                "raw_text": raw_text,
                "raw": row,
            }
        )

    return patterns


def _concat_cwe_fields(row: dict) -> str:
    fields = []

    for key in [
        "name",
        "Name",
        "description",
        "Description",
        "extended_description",
        "Extended_Description",
        "common_consequences",
        "Common_Consequences",
        "consequences",
        "Consequences",
        "background_details",
        "Background_Details",
        "background",
        "Background",
        "detection_methods",
        "Detection_Methods",
        "detection",
        "Detection",
    ]:
        val = row.get(key)

        if val is None:
            continue

        if isinstance(val, str):
            fields.append(val)
        elif isinstance(val, list):
            fields.extend(str(x) for x in val)
        elif isinstance(val, dict):
            fields.extend(str(x) for x in val.values())

    return _clean_text(" ".join(fields))



class CausalFragmentExtractor:
    def __init__(
        self,
        backend: BackendName = "auto",
        spacy_model: str = "en_core_web_sm",
        stanza_lang: str = "en",
        allennlp_srl_model: str | None = None,
        max_fragments: int = 32,
    ):
        self.backend = backend
        self.spacy_model = spacy_model
        self.stanza_lang = stanza_lang
        self.allennlp_srl_model = allennlp_srl_model
        self.max_fragments = max_fragments

        self._spacy_nlp = None
        self._stanza_nlp = None
        self._allennlp_predictor = None

    def extract(self, text: str) -> list[str]:
        text = _clean_text(text)

        if not text:
            return []

        if self.backend == "allennlp":
            fragments = self._extract_with_allennlp(text)
        elif self.backend == "stanza":
            fragments = self._extract_with_stanza(text)
        elif self.backend == "spacy":
            fragments = self._extract_with_spacy(text)
        else:
            fragments = self._extract_auto(text)

        fragments = self._normalize_fragments(fragments)

        if not fragments:
            fragments = self._fallback_sentence_fragments(text)

        return fragments[: self.max_fragments]

    def _extract_auto(self, text: str) -> list[str]:
        for method in [
            self._extract_with_allennlp,
            self._extract_with_stanza,
            self._extract_with_spacy,
        ]:
            try:
                fragments = method(text)
                fragments = self._normalize_fragments(fragments)
                if fragments:
                    return fragments
            except Exception:
                continue

        return self._fallback_sentence_fragments(text)


    def _load_allennlp(self):
        if self._allennlp_predictor is not None:
            return self._allennlp_predictor

        from allennlp.predictors.predictor import Predictor
        import allennlp_models.structured_prediction  # noqa: F401

        model_url = (
            self.allennlp_srl_model
            or "https://storage.googleapis.com/allennlp-public-models/"
            "structured-prediction-srl-bert.2020.12.15.tar.gz"
        )

        self._allennlp_predictor = Predictor.from_path(model_url)
        return self._allennlp_predictor

    def _extract_with_allennlp(self, text: str) -> list[str]:
        predictor = self._load_allennlp()
        fragments: list[str] = []

        for sent in _split_sentences(text):
            result = predictor.predict(sentence=sent)
            words = result.get("words", [])

            for verb_frame in result.get("verbs", []):
                tags = verb_frame.get("tags", [])

                if not words or not tags:
                    continue

                predicate = self._collect_srl_role(words, tags, "V")
                arg0 = self._collect_srl_role(words, tags, "ARG0")
                arg1 = self._collect_srl_role(words, tags, "ARG1")
                arg2 = self._collect_srl_role(words, tags, "ARG2")

                cause = self._collect_srl_role(words, tags, "ARGM-CAU")
                manner = self._collect_srl_role(words, tags, "ARGM-MNR")
                purpose = self._collect_srl_role(words, tags, "ARGM-PRP")
                location = self._collect_srl_role(words, tags, "ARGM-LOC")
                temporal = self._collect_srl_role(words, tags, "ARGM-TMP")

                obj = _join_nonempty([arg1, arg2])
                modifier = _join_nonempty([cause, manner, purpose, location, temporal])

                if (
                    _is_security_predicate(predicate)
                    or _contains_security_term(arg0)
                    or _contains_security_term(obj)
                    or _contains_security_term(modifier)
                ):
                    frag = CausalFragment(
                        subject=arg0,
                        predicate=predicate,
                        object=obj,
                        modifier=modifier,
                    ).to_text()

                    if frag:
                        fragments.append(frag)

        return fragments

    def _collect_srl_role(self, words: list[str], tags: list[str], role: str) -> str:
        collected = []

        for word, tag in zip(words, tags):
            if tag == f"B-{role}" or tag == f"I-{role}":
                collected.append(word)

        return _clean_phrase(" ".join(collected))


    def _load_stanza(self):
        if self._stanza_nlp is not None:
            return self._stanza_nlp

        import stanza

        self._stanza_nlp = stanza.Pipeline(
            lang=self.stanza_lang,
            processors="tokenize,pos,lemma,depparse",
            tokenize_no_ssplit=False,
            use_gpu=False,
            verbose=False,
        )

        return self._stanza_nlp

    def _extract_with_stanza(self, text: str) -> list[str]:
        nlp = self._load_stanza()
        doc = nlp(text)
        fragments: list[str] = []

        for sent in doc.sentences:
            words = sent.words
            by_id = {w.id: w for w in words}
            children: dict[int, list[Any]] = {}

            for w in words:
                children.setdefault(w.head, []).append(w)

            for w in words:
                if w.upos not in {"VERB", "AUX"}:
                    continue

                predicate = w.lemma or w.text

                if not _is_security_predicate(predicate) and not self._has_stanza_security_dependent(
                    w.id,
                    children,
                ):
                    continue

                subj = self._collect_stanza_dependents(
                    root_id=w.id,
                    by_id=by_id,
                    children=children,
                    allowed_deps={"nsubj", "nsubj:pass", "csubj"},
                )

                obj = self._collect_stanza_dependents(
                    root_id=w.id,
                    by_id=by_id,
                    children=children,
                    allowed_deps={
                        "obj",
                        "iobj",
                        "obl",
                        "xcomp",
                        "ccomp",
                        "advcl",
                        "nmod",
                        "acl",
                    },
                )

                modifier = self._collect_stanza_dependents(
                    root_id=w.id,
                    by_id=by_id,
                    children=children,
                    allowed_deps={
                        "advmod",
                        "amod",
                        "compound",
                        "nummod",
                        "case",
                    },
                )

                frag = CausalFragment(
                    subject=subj,
                    predicate=predicate,
                    object=obj,
                    modifier=modifier,
                ).to_text()

                if frag:
                    fragments.append(frag)

        return fragments

    def _collect_stanza_dependents(
        self,
        root_id: int,
        by_id: dict[int, Any],
        children: dict[int, list[Any]],
        allowed_deps: set[str],
    ) -> str:
        phrases = []

        for child in children.get(root_id, []):
            if child.deprel in allowed_deps:
                phrases.append(self._stanza_subtree_text(child.id, by_id, children))

        return _clean_phrase(" ".join(phrases))

    def _stanza_subtree_text(
        self,
        root_id: int,
        by_id: dict[int, Any],
        children: dict[int, list[Any]],
    ) -> str:
        node_ids = []

        def visit(node_id: int):
            node_ids.append(node_id)
            for child in children.get(node_id, []):
                visit(child.id)

        visit(root_id)

        node_ids = sorted(set(node_ids))
        tokens = [by_id[i].text for i in node_ids if i in by_id]

        return _clean_phrase(" ".join(tokens))

    def _has_stanza_security_dependent(
        self,
        root_id: int,
        children: dict[int, list[Any]],
    ) -> bool:
        queue = list(children.get(root_id, []))
        seen = set()

        while queue:
            node = queue.pop(0)

            if node.id in seen:
                continue

            seen.add(node.id)

            if _contains_security_term(node.text) or _contains_security_term(
                getattr(node, "lemma", "") or ""
            ):
                return True

            queue.extend(children.get(node.id, []))

        return False


    def _load_spacy(self):
        if self._spacy_nlp is not None:
            return self._spacy_nlp

        import spacy

        self._spacy_nlp = spacy.load(self.spacy_model)
        return self._spacy_nlp

    def _extract_with_spacy(self, text: str) -> list[str]:
        nlp = self._load_spacy()
        doc = nlp(text)
        fragments: list[str] = []

        for sent in doc.sents:
            for token in sent:
                if token.pos_ not in {"VERB", "AUX"}:
                    continue

                predicate = token.lemma_ or token.text

                if not _is_security_predicate(predicate) and not self._has_spacy_security_dependent(token):
                    continue

                subjects = []
                objects = []
                modifiers = []

                for child in token.children:
                    if child.dep_ in {"nsubj", "nsubjpass", "csubj"}:
                        subjects.append(self._spacy_subtree_text(child))

                    elif child.dep_ in {
                        "dobj",
                        "obj",
                        "iobj",
                        "attr",
                        "oprd",
                        "xcomp",
                        "ccomp",
                        "advcl",
                        "acl",
                        "relcl",
                        "prep",
                        "pobj",
                    }:
                        objects.append(self._spacy_subtree_text(child))

                    elif child.dep_ in {
                        "advmod",
                        "amod",
                        "npadvmod",
                        "agent",
                        "compound",
                    }:
                        modifiers.append(self._spacy_subtree_text(child))

                frag = CausalFragment(
                    subject=_join_nonempty(subjects),
                    predicate=predicate,
                    object=_join_nonempty(objects),
                    modifier=_join_nonempty(modifiers),
                ).to_text()

                if frag:
                    fragments.append(frag)

        return fragments

    def _spacy_subtree_text(self, token: Any) -> str:
        subtree = sorted(list(token.subtree), key=lambda x: x.i)
        return _clean_phrase(" ".join(t.text for t in subtree))

    def _has_spacy_security_dependent(self, token: Any) -> bool:
        for t in token.subtree:
            if _contains_security_term(t.text) or _contains_security_term(t.lemma_):
                return True
        return False


    def _fallback_sentence_fragments(self, text: str) -> list[str]:
        fragments = []

        for sent in _split_sentences(text):
            if _contains_security_term(sent):
                fragments.append(_clean_phrase(sent))

        if not fragments:
            fragments = [_clean_phrase(s) for s in _split_sentences(text)]

        return fragments

    def _normalize_fragments(self, fragments: list[str]) -> list[str]:
        seen = set()
        normalized = []

        for frag in fragments:
            frag = _clean_phrase(frag)

            if not frag:
                continue

            key = frag.lower()

            if key in seen:
                continue

            seen.add(key)
            normalized.append(frag)

        return normalized


def CAUSALEXTRACT(
    text: str,
    backend: BackendName = "auto",
    max_fragments: int = 32,
) -> list[str]:
    extractor = CausalFragmentExtractor(
        backend=backend,
        max_fragments=max_fragments,
    )

    return extractor.extract(text)


def default_causal_extract(text: str) -> list[str]:
    """
    Backward-compatible wrapper.
    """
    return CAUSALEXTRACT(
        text,
        backend="auto",
        max_fragments=32,
    )




class BertTextEncoder(nn.Module if nn is not None else object):
    """
    Shared BERT encoder used for both bug-report text and CWE fragments.
    """

    def __init__(self, model_name: str = "bert-base-uncased"):
        if nn is None:
            raise ImportError("PyTorch is required for BertTextEncoder.")

        super().__init__()

        from transformers import AutoModel, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.bert = AutoModel.from_pretrained(model_name)
        self.hidden_size = self.bert.config.hidden_size

    def encode_cls(self, texts: list[str], device: Any) -> Any:
        batch = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(device)

        out = self.bert(**batch)
        return out.last_hidden_state[:, 0, :]

    def encode_tokens(self, text: str, device: Any) -> tuple[Any, list[str]]:
        batch = self.tokenizer(
            text,
            padding=False,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(device)

        out = self.bert(**batch)
        token_vecs = out.last_hidden_state[0]
        tokens = self.tokenizer.convert_ids_to_tokens(batch["input_ids"][0])

        return token_vecs, tokens


def _cluster_fragment_vectors(
    fragment_vectors: Any,
    distance_threshold: float = 0.18,
) -> Any:
    if torch is None or F is None:
        raise ImportError("PyTorch is required for neural CWE prototype construction.")

    if fragment_vectors.size(0) == 1:
        return fragment_vectors[0]

    try:
        from sklearn.cluster import AgglomerativeClustering

        vec_np = F.normalize(fragment_vectors, dim=-1).detach().cpu().numpy()

        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=distance_threshold,
        )

        labels = clustering.fit_predict(vec_np)

        centroids = []
        for lab in sorted(set(labels)):
            idx = np.where(labels == lab)[0]
            centroids.append(fragment_vectors[idx].mean(dim=0))

        return torch.stack(centroids, dim=0).mean(dim=0)

    except Exception:
        return fragment_vectors.mean(dim=0)


def _extract_key_terms_from_fragments(
    fragments: list[str],
    top_k: int = 80,
) -> list[str]:
    freq: dict[str, int] = {}

    for frag in fragments:
        for tok in _tokenize_terms(frag):
            freq[tok] = freq.get(tok, 0) + 1

    terms = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [t for t, _ in terms[:top_k]]


def build_cwe_prototypes(
    patterns: list[dict],
    training_texts: list[str],
    encoder: BertTextEncoder,
    causal_extract: Callable[[str], list[str]] = default_causal_extract,
    device: str | Any | None = None,
) -> list[CWEPrototype]:
    if torch is None:
        raise ImportError("PyTorch is required for build_cwe_prototypes().")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    device = torch.device(device)

    encoder.to(device)
    encoder.eval()

    prototypes: list[CWEPrototype] = []

    with torch.no_grad():
        for i, row in enumerate(patterns):
            pid = str(row.get("id") or row.get("cwe_id") or f"CWE-P{i}")
            name = str(row.get("name") or pid)

            cwe_text = row.get("raw_text") or _concat_cwe_fields(row.get("raw", row)) or name
            fragments = causal_extract(cwe_text)

            if not fragments:
                fragments = [cwe_text]

            fragment_vectors = encoder.encode_cls(fragments, device)
            proto_vec = _cluster_fragment_vectors(fragment_vectors)

            key_terms = _extract_key_terms_from_fragments(fragments)

            if not key_terms:
                key_terms = list(row.get("keywords", []))

            term_set = set(key_terms)

            n_p = 0
            for x in training_texts:
                toks = set(_tokenize_terms(x))
                if toks.intersection(term_set):
                    n_p += 1

            idf = math.log((len(training_texts) + 1) / (n_p + 1)) if training_texts else 1.0

            prototypes.append(
                CWEPrototype(
                    pattern_id=pid,
                    name=name,
                    vector=proto_vec.detach().cpu(),
                    key_terms=key_terms,
                    idf=float(idf),
                )
            )

    return prototypes



class GlobalCompletenessModel(nn.Module if nn is not None else object):

    def __init__(
        self,
        bert_hidden_size: int = 768,
        gru_hidden_size: int = 128,
        projection_size: int = 128,
        dropout: float = 0.2,
    ):
        if nn is None:
            raise ImportError("PyTorch is required for GlobalCompletenessModel.")

        super().__init__()

        self.bigru = nn.GRU(
            input_size=bert_hidden_size,
            hidden_size=gru_hidden_size,
            batch_first=True,
            bidirectional=True,
        )

        self.dropout = nn.Dropout(dropout)

        self.global_size = gru_hidden_size * 2

        self.proj_proto = nn.Linear(bert_hidden_size, projection_size)
        self.proj_report = nn.Linear(self.global_size, projection_size)

        self.coverage_scorer = nn.Linear(
            bert_hidden_size + self.global_size,
            1,
        )

    def forward(
        self,
        token_vectors: Any,
        prototypes: list[CWEPrototype],
        report_text: str,
    ) -> tuple[Any, list[PatternCoverage]]:
        if torch is None:
            raise ImportError("PyTorch is required for GlobalCompletenessModel.forward().")

        device = token_vectors.device

        x = token_vectors.unsqueeze(0)
        g, _ = self.bigru(x)
        g = self.dropout(g.squeeze(0))

        report_terms = _tokenize_terms(report_text)
        report_term_freq: dict[str, int] = {}

        for t in report_terms:
            report_term_freq[t] = report_term_freq.get(t, 0) + 1

        raw_freqs = []
        matched_terms_list = []

        for p in prototypes:
            matched = [t for t in p.key_terms if t in report_term_freq]
            matched_terms_list.append(matched)
            raw_freqs.append(sum(report_term_freq.get(t, 0) for t in p.key_terms))

        f_max = max(raw_freqs) if raw_freqs and max(raw_freqs) > 0 else 1.0

        coverage_values = []
        omega_values = []
        coverage_records: list[PatternCoverage] = []

        for p, f_p, matched_terms in zip(prototypes, raw_freqs, matched_terms_list):
            vp = p.vector.to(device)

            proto_q = self.proj_proto(vp)
            report_k = torch.tanh(self.proj_report(g))

            e = torch.matmul(report_k, proto_q)
            attn = torch.softmax(e, dim=0)

            report_context = torch.sum(attn.unsqueeze(-1) * g, dim=0)

            pair = torch.cat([vp, report_context], dim=-1)
            coverage = torch.sigmoid(self.coverage_scorer(pair)).squeeze()

            tf = float(f_p) / float(f_max)
            omega = tf * p.idf

            if omega <= 0:
                omega = 1e-6

            coverage_values.append(coverage)
            omega_values.append(torch.tensor(omega, dtype=torch.float32, device=device))

            coverage_records.append(
                PatternCoverage(
                    pattern_id=p.pattern_id,
                    name=p.name,
                    coverage=float(coverage.detach().cpu()),
                    matched_terms=matched_terms,
                )
            )

        if not coverage_values:
            return torch.tensor(0.0, device=device), []

        cov_tensor = torch.stack(coverage_values)
        omega_tensor = torch.stack(omega_values)

        M = torch.sum(omega_tensor * cov_tensor) / torch.sum(omega_tensor)

        return M, coverage_records


def compute_global_completeness(
    text: str,
    encoder: BertTextEncoder,
    completeness_model: GlobalCompletenessModel,
    prototypes: list[CWEPrototype],
    top_k_missing: int = 3,
    device: str | Any | None = None,
) -> CompletenessResult:
    if torch is None:
        raise ImportError("PyTorch is required for compute_global_completeness().")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    device = torch.device(device)

    encoder.to(device)
    completeness_model.to(device)

    encoder.eval()
    completeness_model.eval()

    with torch.no_grad():
        token_vectors, _ = encoder.encode_tokens(text, device)
        M, coverages = completeness_model(token_vectors, prototypes, text)

    related = [c for c in coverages if len(c.matched_terms) > 0]
    pool = related if related else coverages

    low = sorted(
        pool,
        key=lambda c: (c.coverage, -len(c.matched_terms)),
    )[:top_k_missing]

    return CompletenessResult(
        completeness=float(M.detach().cpu()),
        coverages=coverages,
        low_coverage_patterns=low,
    )



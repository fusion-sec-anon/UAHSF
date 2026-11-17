from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
import hashlib
import re

import numpy as np


SECURITY_HINTS = [""]


BertMode = Literal[
    "dry_run_heuristic",
    "hf_sequence_classification",
    "hf_sequence_classification_with_hidden_states",
]


@dataclass
class BertPrediction:
    probability: float
    mode: str = "hf_sequence_classification"
    logits: list[float] | None = None


@dataclass
class BertEncoding:
    tokens: list[str]
    input_ids: Any
    attention_mask: Any
    token_type_ids: Any | None
    hidden_states: Any


@dataclass
class BertScoringResult:
    probability: float
    tokens: list[str]
    hidden_states: Any
    logits: list[float] | None = None


class BertSBRScorer:

    def __init__(
        self,
        model_name: str = "bert-base-uncased",
        device: str = "auto",
        max_length: int = 512,
        dry_run: bool = False,
        dry_run_probability: float = 0.5,
        positive_label_id: int = 1,
        output_hidden_states: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.dry_run = dry_run
        self.dry_run_probability = float(dry_run_probability)
        self.positive_label_id = positive_label_id
        self.output_hidden_states = output_hidden_states

        self._model = None
        self._tokenizer = None
        self._torch = None

        if not dry_run:
            self._load_hf()


    def _load_hf(self) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self.device == "auto":
            dev = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            dev = self.device

        self._torch = torch

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            output_hidden_states=self.output_hidden_states,
        ).to(dev)

        self._model.eval()
        self.device = dev


    def predict_proba(self, text: str) -> BertPrediction:
        if self.dry_run:
            return BertPrediction(
                probability=self._heuristic_probability(text),
                mode="dry_run_heuristic",
                logits=None,
            )

        result = self.predict_with_encoding(text)

        return BertPrediction(
            probability=result.probability,
            mode="hf_sequence_classification",
            logits=result.logits,
        )

    def predict_batch_proba(self, texts: list[str], batch_size: int = 16) -> list[BertPrediction]:
        if self.dry_run:
            return [
                BertPrediction(
                    probability=self._heuristic_probability(t),
                    mode="dry_run_heuristic",
                    logits=None,
                )
                for t in texts
            ]

        predictions: list[BertPrediction] = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            predictions.extend(self._predict_hf_batch(batch_texts))

        return predictions

    def encode(self, text: str) -> BertEncoding:
        if self.dry_run:
            raise RuntimeError(
                "encode() is not available in dry_run mode. "
                "Use dry_run=False with a HuggingFace checkpoint."
            )

        torch = self._torch

        encoded = self._tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt",
            return_token_type_ids=True,
        )

        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self._model(**encoded, output_hidden_states=True)

        tokens = self._tokenizer.convert_ids_to_tokens(encoded["input_ids"][0])
        hidden_states = outputs.hidden_states[-1][0]

        return BertEncoding(
            tokens=tokens,
            input_ids=encoded["input_ids"][0],
            attention_mask=encoded["attention_mask"][0],
            token_type_ids=encoded.get("token_type_ids", None)[0]
            if encoded.get("token_type_ids", None) is not None
            else None,
            hidden_states=hidden_states,
        )

    def predict_with_encoding(self, text: str) -> BertScoringResult:
        if self.dry_run:
            return BertScoringResult(
                probability=self._heuristic_probability(text),
                tokens=self._simple_tokens(text),
                hidden_states=None,
                logits=None,
            )

        torch = self._torch

        encoded = self._tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt",
            return_token_type_ids=True,
        )

        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self._model(**encoded, output_hidden_states=True)
            logits = outputs.logits[0]
            prob = self._positive_probability_from_logits(logits)

        tokens = self._tokenizer.convert_ids_to_tokens(encoded["input_ids"][0])
        hidden_states = outputs.hidden_states[-1][0]

        return BertScoringResult(
            probability=float(prob),
            tokens=tokens,
            hidden_states=hidden_states,
            logits=[float(x) for x in logits.detach().cpu().tolist()],
        )

    def predict_proba_with_masked_token(
        self,
        text: str,
        token_index: int,
    ) -> BertPrediction:
        if self.dry_run:
            return BertPrediction(
                probability=self._heuristic_probability(text),
                mode="dry_run_heuristic",
                logits=None,
            )

        encoding = self._encode_inputs(text)
        input_ids = encoding["input_ids"].clone()

        if token_index <= 0 or token_index >= input_ids.size(1) - 1:
            return self._predict_from_encoded_inputs(encoding)

        mask_id = self._tokenizer.mask_token_id

        if mask_id is None:
            raise RuntimeError("The tokenizer does not define a mask token.")

        input_ids[0, token_index] = mask_id
        encoding["input_ids"] = input_ids

        return self._predict_from_encoded_inputs(encoding)

    def predict_proba_with_masked_span(
        self,
        text: str,
        start: int,
        end: int,
    ) -> BertPrediction:
        if self.dry_run:
            return BertPrediction(
                probability=self._heuristic_probability(text),
                mode="dry_run_heuristic",
                logits=None,
            )

        encoding = self._encode_inputs(text)
        input_ids = encoding["input_ids"].clone()

        mask_id = self._tokenizer.mask_token_id

        if mask_id is None:
            raise RuntimeError("The tokenizer does not define a mask token.")

        seq_len = input_ids.size(1)

        start = max(1, start)
        end = min(seq_len - 1, end)

        if start >= end:
            return self._predict_from_encoded_inputs(encoding)

        input_ids[0, start:end] = mask_id
        encoding["input_ids"] = input_ids

        return self._predict_from_encoded_inputs(encoding)

    def find_token_spans(
        self,
        text: str,
        term: str,
    ) -> list[tuple[int, int]]:
        if self.dry_run:
            spans = []
            words = self._simple_tokens(text)
            term_words = self._simple_tokens(term)
            m = len(term_words)

            for i in range(0, len(words) - m + 1):
                if words[i : i + m] == term_words:
                    spans.append((i, i + m))

            return spans

        encoded = self._tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_offsets_mapping=True,
            return_tensors="pt",
        )

        offsets = encoded["offset_mapping"][0].tolist()
        tokens = self._tokenizer.convert_ids_to_tokens(encoded["input_ids"][0])

        text_lower = text.lower()
        term_lower = term.lower()

        spans: list[tuple[int, int]] = []

        for match in re.finditer(re.escape(term_lower), text_lower):
            char_start, char_end = match.span()
            token_indices = []

            for i, (s, e) in enumerate(offsets):
                if tokens[i] in {
                    self._tokenizer.cls_token,
                    self._tokenizer.sep_token,
                    self._tokenizer.pad_token,
                }:
                    continue

                if e <= char_start or s >= char_end:
                    continue

                token_indices.append(i)

            if token_indices:
                spans.append((min(token_indices), max(token_indices) + 1))

        return spans

    def _encode_inputs(self, text: str) -> dict[str, Any]:
        encoded = self._tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors="pt",
            return_token_type_ids=True,
        )

        return {k: v.to(self.device) for k, v in encoded.items()}

    def _predict_from_encoded_inputs(self, encoded: dict[str, Any]) -> BertPrediction:
        torch = self._torch

        with torch.no_grad():
            outputs = self._model(**encoded)
            logits = outputs.logits[0]
            prob = self._positive_probability_from_logits(logits)

        return BertPrediction(
            probability=float(prob),
            mode="hf_sequence_classification",
            logits=[float(x) for x in logits.detach().cpu().tolist()],
        )

    def _predict_hf_batch(self, texts: list[str]) -> list[BertPrediction]:
        torch = self._torch

        encoded = self._tokenizer(
            texts,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
            return_token_type_ids=True,
        )

        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self._model(**encoded)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)

        results = []

        for i in range(len(texts)):
            p = probs[i, self.positive_label_id]
            row_logits = logits[i].detach().cpu().tolist()

            results.append(
                BertPrediction(
                    probability=float(p.detach().cpu()),
                    mode="hf_sequence_classification",
                    logits=[float(x) for x in row_logits],
                )
            )

        return results

    def _positive_probability_from_logits(self, logits: Any) -> float:
        torch = self._torch

        if logits.dim() == 0:
            return float(torch.sigmoid(logits).detach().cpu())

        if logits.numel() == 1:
            return float(torch.sigmoid(logits.view(-1)[0]).detach().cpu())

        probs = torch.softmax(logits, dim=-1)
        return float(probs[self.positive_label_id].detach().cpu())


    def _heuristic_probability(self, text: str) -> float:
        t = text.lower()

        hits = sum(1 for w in SECURITY_HINTS if w in t)

        jitter = (
            int(hashlib.md5(t.encode("utf-8")).hexdigest()[:4], 16)
            / 65535
            * 0.04
            - 0.02
        )

        p = 0.12 + min(hits, 8) * 0.085 + jitter

        if re.search(r"(arbitrary|remote).{0,30}(code|command|execution)", t):
            p += 0.18

        if re.search(r"(ui|layout|typo|button|font|youtube doesn't load)", t):
            p -= 0.08

        return max(0.01, min(0.99, p))

    def _simple_tokens(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())


__all__ = [
    "BertPrediction",
    "BertEncoding",
    "BertScoringResult",
    "BertSBRScorer",
]
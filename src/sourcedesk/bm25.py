"""Okapi BM25 over words and over 5-grams.

Module 1.1 treats a higher-order gram as confident when the count is large.
A 5-gram is stored as its own term beside the words, so a rare name or figure
can outrank a shared function word.
"""

from __future__ import annotations

import math
from collections import Counter

from sourcedesk.chunk import Span, tokens

K1 = 1.5
B = 0.75
STOP = {
    "the", "a", "an", "of", "and", "or", "to", "for", "in", "on", "is", "are",
    "what", "which", "who", "how", "when", "where", "does", "do", "did",
    "be", "was", "were", "his", "her", "their", "its", "with", "from", "that", "this",
}


def terms_of(text: str) -> list[str]:
    words = [tok.lower() for tok in tokens(text) if tok.lower() not in STOP]
    grams = [" ".join(words[i : i + 5]) for i in range(0, max(0, len(words) - 4))]
    return words + grams


class BM25Index:
    def __init__(self, spans: list[Span]):
        self.spans = spans
        self.doc_terms = [Counter(terms_of(span.text)) for span in spans]
        self.doc_len = [sum(counter.values()) for counter in self.doc_terms]
        self.avg_len = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.n = len(spans)
        df: Counter[str] = Counter()
        for counter in self.doc_terms:
            df.update(counter.keys())
        self.idf = {
            term: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query: str) -> list[float]:
        qterms = terms_of(query)
        if not self.spans or not qterms:
            return [0.0] * len(self.spans)
        scores = []
        for counter, length in zip(self.doc_terms, self.doc_len):
            total = 0.0
            denom_norm = K1 * (1.0 - B + B * (length / self.avg_len)) if self.avg_len else K1
            for term in qterms:
                freq = counter.get(term, 0)
                if not freq:
                    continue
                idf = self.idf.get(term, 0.0)
                total += idf * (freq * (K1 + 1.0)) / (freq + denom_norm)
            scores.append(total)
        return scores

"""Two Okapi BM25 indexes: words, and 5-grams.

A 5-gram stored in the same bag would inflate document length and dampen the
word score. Module 1.1 keeps the orders separate and trusts the higher order
only when it actually matched. Otherwise the score falls back to words.
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


def words_of(text: str) -> list[str]:
    return [tok.lower() for tok in tokens(text) if tok.lower() not in STOP]


def grams_of(words: list[str]) -> list[str]:
    if len(words) < 5:
        return []
    return [" ".join(words[i : i + 5]) for i in range(len(words) - 4)]


class _Okapi:
    def __init__(self, docs: list[list[str]]):
        self.docs = [Counter(doc) for doc in docs]
        self.doc_len = [sum(counter.values()) for counter in self.docs]
        self.n = len(docs)
        self.avg_len = (sum(self.doc_len) / self.n) if self.n else 0.0
        df: Counter[str] = Counter()
        for counter in self.docs:
            df.update(counter.keys())
        self.idf = {
            term: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score_terms(self, qterms: list[str]) -> list[float]:
        if not self.n or not qterms:
            return [0.0] * self.n
        scores = []
        for counter, length in zip(self.docs, self.doc_len):
            total = 0.0
            denom_norm = K1 * (1.0 - B + B * (length / self.avg_len)) if self.avg_len else K1
            for term in qterms:
                freq = counter.get(term, 0)
                if not freq:
                    continue
                total += self.idf.get(term, 0.0) * (freq * (K1 + 1.0)) / (freq + denom_norm)
            scores.append(total)
        return scores


class BM25Index:
    def __init__(self, spans: list[Span]):
        self.spans = spans
        word_docs = []
        gram_docs = []
        for span in spans:
            words = words_of(span.text)
            word_docs.append(words)
            gram_docs.append(grams_of(words))
        self.words = _Okapi(word_docs)
        self.grams = _Okapi(gram_docs)

    def score(self, query: str) -> list[float]:
        words = words_of(query)
        word_scores = self.words.score_terms(words)
        gram_scores = self.grams.score_terms(grams_of(words))
        blended = []
        for word_score, gram_score in zip(word_scores, gram_scores):
            if gram_score > 0 and word_score > 0:
                blended.append(0.45 * word_score + 0.55 * gram_score)
            elif gram_score > 0:
                blended.append(gram_score)
            else:
                blended.append(word_score)
        return blended

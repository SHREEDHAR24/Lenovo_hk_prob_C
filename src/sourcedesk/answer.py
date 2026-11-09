"""Extractive answers. The stitcher may only repeat a quote."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sourcedesk.chunk import Span, tokens
from sourcedesk.verify import unsupported

STOP = {
    "the", "a", "an", "of", "and", "or", "to", "for", "in", "on", "is", "are",
    "what", "which", "who", "whom", "how", "when", "where", "does", "do", "did",
    "his", "her", "their", "its", "with", "from", "that", "this", "be", "was",
}

LINE_SPLIT = re.compile(r"\n+|(?<=\.)\s+")


@dataclass
class Quote:
    text: str
    doc_id: str
    locator: str
    ocr_confidence: float | None

    @property
    def low_ocr(self) -> bool:
        return self.ocr_confidence is not None and self.ocr_confidence < 0.8


def content_terms(text: str) -> set[str]:
    return {tok.lower() for tok in tokens(text) if tok.lower() not in STOP and len(tok) > 2}


def best_line(span: Span, query: str) -> str:
    query_terms = content_terms(query)
    lines = [line.strip() for line in LINE_SPLIT.split(span.text) if line.strip()]
    if not lines:
        return span.text.strip()
    ranked = sorted(lines, key=lambda line: len(content_terms(line) & query_terms), reverse=True)
    choice = ranked[0]
    if choice not in span.text:
        return span.text.strip()
    return choice


def stitch(quote: Quote) -> str:
    """Greedy template. It copies the quote and adds no number of its own."""
    return f"According to {quote.doc_id} ({quote.locator}): {quote.text}"


def checked_stitch(quote: Quote) -> tuple[str | None, list[str]]:
    sentence = stitch(quote)
    if quote.text not in sentence:
        return None, ["quote missing from the sentence"]
    claim = sentence.split(": ", 1)[-1]
    missing = unsupported(claim, quote.text)
    if missing:
        return None, missing
    return sentence, []

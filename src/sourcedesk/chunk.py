"""Pack source lines into spans of at most 512 tokens, with a 64-token overlap.

The product tokenizer is byte-pair encoding, as in CS781 Module 1.4. This
prototype counts words so it can run with no downloaded vocabulary. Each span
text is an exact slice of the source line, so a quote can be checked as a
substring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sourcedesk.ingest import Corpus, Page

TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[A-Za-z]+(?:'[A-Za-z]+)?")
SPAN_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class Span:
    span_id: str
    doc_id: str
    path: str
    locator: str
    text: str
    ocr_confidence: float | None
    n_tokens: int


def tokens(text: str) -> list[str]:
    found = []
    for tok in TOKEN.findall(text):
        tok = tok.rstrip(",")
        if tok.lower().endswith("'s") and len(tok) > 2:
            tok = tok[:-2]
        if tok:
            found.append(tok)
    return found


def pack_pages(corpus: Corpus, span_tokens: int = SPAN_TOKENS, overlap_tokens: int = OVERLAP_TOKENS) -> list[Span]:
    spans: list[Span] = []
    for page in corpus.pages:
        spans.extend(_pack_page(page, span_tokens, overlap_tokens, len(spans)))
    return spans


def _pack_page(page: Page, span_tokens: int, overlap_tokens: int, start: int) -> list[Span]:
    lines = [line.strip() for line in page.text.splitlines() if line.strip()]
    if not lines:
        lines = [page.text.strip()]
    sized = [(line, len(tokens(line)) or 1) for line in lines]
    spans: list[Span] = []
    index = 0
    while index < len(sized):
        taken = []
        count = 0
        cursor = index
        while cursor < len(sized) and count + sized[cursor][1] <= span_tokens:
            taken.append(sized[cursor][0])
            count += sized[cursor][1]
            cursor += 1
        if not taken:
            taken = [sized[index][0]]
            count = sized[index][1]
            cursor = index + 1
        spans.append(
            Span(
                span_id=f"s{start + len(spans)}",
                doc_id=page.doc_id,
                path=page.path,
                locator=page.locator,
                text="\n".join(taken),
                ocr_confidence=page.ocr_confidence,
                n_tokens=count,
            )
        )
        if cursor >= len(sized):
            break
        rewind = count
        back = cursor
        while back > index and rewind > overlap_tokens:
            back -= 1
            rewind -= sized[back][1]
        index = max(back, index + 1)
    return spans

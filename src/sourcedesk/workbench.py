"""Index, blend, and answer. No socket is opened."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from sourcedesk.answer import Quote, best_line, checked_stitch, content_terms
from sourcedesk.bm25 import BM25Index
from sourcedesk.chunk import Span, pack_pages
from sourcedesk.dense import cosine, embed
from sourcedesk.ingest import Corpus, load_dir, load_path, source_files
from sourcedesk.privacy import log_event
from sourcedesk.tiers import Tier, probe, serving_mode
from sourcedesk.verify import NUMBER

LEXICAL = 0.75
DENSE = 0.25
TOP_K = 8


@dataclass
class Hit:
    span: Span
    score: float
    lexical: float
    dense: float


@dataclass
class Answer:
    status: str
    text: str
    quotes: list[Quote] = field(default_factory=list)
    mode: str = "full"
    stitcher: str = "template"
    dropped: list[str] = field(default_factory=list)


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high <= low:
        return [0.0 if high == 0 else 1.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _numbers(text: str) -> set[str]:
    return set(NUMBER.findall(text))


class Workbench:
    def __init__(self, folder: Path, tier: Tier | None = None, log_path: Path | None = None):
        self.folder = Path(folder)
        self.tier = tier if tier is not None else probe()
        self.log_path = Path(log_path) if log_path else self.folder / ".sourcedesk" / "events.log"
        self.corpus = load_dir(self.folder)
        if not self.tier.opens_corpus:
            self.spans = []
            self.bm25 = BM25Index([])
            self.vectors = np.zeros((0, 256))
            self.manifest = ""
            return
        self.spans = pack_pages(self.corpus)
        self._reindex()
        self._snap = self._snapshot()
        self._cache: dict[tuple[str, str, str], Answer] = {}

    def _reindex(self) -> None:
        self.bm25 = BM25Index(self.spans)
        self.vectors = np.vstack([embed(span.text) for span in self.spans]) if self.spans else np.zeros((0, 256))
        self.manifest = self._manifest()

    def _snapshot(self) -> dict[str, tuple[int, int]]:
        snap = {}
        for path in source_files(self.folder):
            stat = path.stat()
            snap[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
        return snap

    def refresh(self) -> bool:
        """Reparse only files whose size or modified time changed, then replace their postings."""
        if not self.tier.opens_corpus:
            return False
        snap = self._snapshot()
        if snap == self._snap:
            return False
        changed = {path for path, sig in snap.items() if self._snap.get(path) != sig}
        removed = set(self._snap) - set(snap)
        touched = changed | removed
        kept = [span for span in self.spans if str(Path(span.path).resolve()) not in touched]
        added: list[Span] = []
        for path in sorted(changed & set(snap)):
            added.extend(pack_pages(Corpus(load_path(Path(path)))))
        self.spans = kept + added
        self._reindex()
        self._snap = snap
        self._cache.clear()
        return True

    def _manifest(self) -> str:
        digest = hashlib.sha256()
        for span in self.spans:
            digest.update(span.doc_id.encode())
            digest.update(span.text.encode())
        return digest.hexdigest()

    def search(self, query: str, k: int = TOP_K) -> list[Hit]:
        if not self.spans:
            return []
        lexical = self.bm25.score(query)
        query_vec = embed(query)
        dense_scores = [cosine(query_vec, row) for row in self.vectors]
        lex_n = _minmax(lexical)
        dense_n = [(score + 1.0) / 2.0 for score in dense_scores]
        blended = []
        for lex_raw, lex_unit, dense_unit in zip(lexical, lex_n, dense_n):
            mixed = LEXICAL * lex_unit + DENSE * dense_unit
            if lex_raw <= 0:
                mixed = min(mixed, 0.01)
            blended.append(mixed)
        order = sorted(range(len(self.spans)), key=lambda i: blended[i], reverse=True)
        hits = []
        for index in order[:k]:
            hits.append(
                Hit(
                    span=self.spans[index],
                    score=blended[index],
                    lexical=lexical[index],
                    dense=dense_scores[index],
                )
            )
        return hits

    def ask(
        self,
        query: str,
        gpu_busy: bool = False,
        battery_pct: float = 100.0,
        free_disk_gb: float = 64.0,
    ) -> Answer:
        if not self.tier.opens_corpus:
            return Answer("refuse", "This laptop is below the 16 GB floor, so the set stays closed.", mode="reduced", stitcher="none")
        mode = serving_mode(gpu_busy, battery_pct, free_disk_gb)
        key = (query.strip(), self.manifest, mode)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        started = time.perf_counter()
        hits = self.search(query)
        answer = self._from_hits(query, hits, mode)
        elapsed = (time.perf_counter() - started) * 1000.0
        doc_id = answer.quotes[0].doc_id if answer.quotes else "none"
        log_event(self.log_path, doc_id, elapsed)
        self._cache[key] = answer
        return answer

    def _from_hits(self, query: str, hits: list[Hit], mode: str) -> Answer:
        stitcher = "none" if mode == "reduced" or self.tier.stitcher == "none" else "template"
        if not hits or hits[0].lexical <= 0.0 or not (content_terms(query) & content_terms(hits[0].span.text)):
            return Answer(
                "refuse",
                "The documents do not say.",
                mode=mode,
                stitcher=stitcher,
            )
        query_terms = content_terms(query)
        strong = [
            hit
            for hit in hits
            if hit.score >= 0.72 * hits[0].score and query_terms & content_terms(hit.span.text)
        ]
        quotes = []
        for hit in strong[:3]:
            line = best_line(hit.span, query)
            if line and line in hit.span.text:
                quotes.append(
                    Quote(
                        text=line,
                        doc_id=hit.span.doc_id,
                        locator=hit.span.locator,
                        ocr_confidence=hit.span.ocr_confidence,
                    )
                )
        if not quotes:
            return Answer("refuse", "The documents do not say.", mode=mode, stitcher=stitcher)

        number_sets = [_numbers(quote.text) for quote in quotes]
        flat = set().union(*number_sets) if number_sets else set()
        distinct_docs = {quote.doc_id for quote in quotes}
        if len(flat) >= 2 and len(distinct_docs) >= 2:
            lines = [f"{quote.doc_id} ({quote.locator}): {quote.text}" for quote in quotes if _numbers(quote.text)]
            return Answer(
                "conflict",
                "The documents disagree.\n" + "\n".join(lines),
                quotes=quotes,
                mode=mode,
                stitcher="none",
            )

        quote = quotes[0]
        if quote.low_ocr and _numbers(quote.text):
            return Answer(
                "refuse",
                "The only page is a low-confidence scan, so a figure from it is not shown.",
                quotes=[],
                mode=mode,
                stitcher="none",
            )
        if stitcher == "none":
            return Answer(
                "answer",
                f"{quote.doc_id} ({quote.locator}): {quote.text}",
                quotes=[quote],
                mode=mode,
                stitcher="none",
            )
        sentence, missing = checked_stitch(quote)
        if sentence is None:
            return Answer(
                "answer",
                f"{quote.doc_id} ({quote.locator}): {quote.text}",
                quotes=[quote],
                mode=mode,
                stitcher=stitcher,
                dropped=missing,
            )
        return Answer("answer", sentence, quotes=[quote], mode=mode, stitcher=stitcher)


    def summarize(self, query: str, limit: int = 5) -> Answer:
        """At most five source lines, each a substring of its span."""
        if not self.tier.opens_corpus:
            return Answer("refuse", "This laptop is below the 16 GB floor, so the set stays closed.", mode="reduced", stitcher="none")
        query_terms = content_terms(query)
        quotes: list[Quote] = []
        seen: set[str] = set()
        for hit in self.search(query):
            if hit.lexical <= 0 or not (query_terms & content_terms(hit.span.text)):
                continue
            line = best_line(hit.span, query)
            if not line or line not in hit.span.text or line in seen:
                continue
            seen.add(line)
            quote = Quote(line, hit.span.doc_id, hit.span.locator, hit.span.ocr_confidence)
            if quote.low_ocr and _numbers(line):
                continue
            quotes.append(quote)
            if len(quotes) == limit:
                break
        if not quotes:
            return Answer("refuse", "The documents do not say.", stitcher="none")
        text = "\n".join(f"{quote.doc_id} ({quote.locator}): {quote.text}" for quote in quotes)
        return Answer("summary", text, quotes=quotes, stitcher="none")

    def draft(self, query: str) -> Answer:
        """A note copied from quotes. A conflict is not collapsed into one figure."""
        base = self.ask(query)
        if base.status != "answer" or not base.quotes:
            return Answer(base.status, base.text, quotes=base.quotes, mode=base.mode, stitcher="none", dropped=base.dropped)
        note = f"Note: {base.quotes[0].text}"
        from sourcedesk.verify import unsupported

        missing = unsupported(note, base.quotes[0].text)
        if missing:
            return Answer(
                "refuse",
                "The draft added a figure that is not in the quote.",
                quotes=base.quotes,
                mode=base.mode,
                stitcher="none",
                dropped=missing,
            )
        return Answer("draft", note, quotes=base.quotes, mode=base.mode, stitcher="none")


def compare_texts(left: str, right: str) -> dict[str, list[str]]:
    def sentences(text: str) -> list[str]:
        parts = [part.strip() for part in text.replace("\n", " ").split(".")]
        return [part + "." for part in parts if part]

    a = sentences(left)
    b = sentences(right)
    b_set = set(b)
    a_set = set(a)
    return {
        "only_left": [line for line in a if line not in b_set],
        "only_right": [line for line in b if line not in a_set],
    }

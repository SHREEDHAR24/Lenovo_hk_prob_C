"""A stitched sentence may not introduce a number, a date, or a name."""

from __future__ import annotations

import re

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
DATE = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}\b",
    re.I,
)
NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


def _squash(text: str) -> str:
    return text.replace(",", "").replace(" ", "").lower()


def unsupported(sentence: str, source: str) -> list[str]:
    missing = []
    flat_source = _squash(source)
    for number in NUMBER.findall(sentence):
        if number not in source and _squash(number) not in flat_source:
            missing.append(number)
    for date in DATE.findall(sentence):
        if date.lower() not in source.lower():
            missing.append(date)
    for name in NAME.findall(sentence):
        if name not in source:
            missing.append(name)
    return missing


def accept(sentence: str, source: str) -> bool:
    return sentence.strip() != "" and not unsupported(sentence, source)

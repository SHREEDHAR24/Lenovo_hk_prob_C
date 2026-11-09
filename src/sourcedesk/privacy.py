"""Logs without passage text, and an index sealed with Windows DPAPI.

DPAPI binds the blob to this Windows user. It is the local stand-in for a
key sealed by Windows Hello. The blob is not a cloud call.
"""

from __future__ import annotations

import ctypes
import json
from ctypes import wintypes
from pathlib import Path


def log_event(path: Path, doc_id: str, latency_ms: float) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"doc_id": doc_id, "latency_ms": round(float(latency_ms), 3)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _protect(data: bytes, encrypt: bool) -> bytes:
    holder = ctypes.create_string_buffer(data, len(data))
    blob_in = _BLOB(len(data), ctypes.cast(holder, ctypes.POINTER(ctypes.c_char)))
    blob_out = _BLOB()
    function = ctypes.windll.crypt32.CryptProtectData if encrypt else ctypes.windll.crypt32.CryptUnprotectData
    ok = function(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("DPAPI failed" if encrypt else "DPAPI unprotect failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def seal(data: bytes) -> bytes:
    return _protect(data, encrypt=True)


def open_seal(data: bytes) -> bytes:
    return _protect(data, encrypt=False)

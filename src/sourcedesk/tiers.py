"""Laptop tier. The checker does not change. The stitcher does."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    stitcher: str
    reason: str

    @property
    def opens_corpus(self) -> bool:
        return self.name != "refuse"


def classify(ram_gb: float, has_cuda: bool, has_npu: bool = False) -> Tier:
    """16 GB is the floor. A reported 15.5 GB is treated as a 16 GB machine."""
    if ram_gb < 15.5:
        return Tier("refuse", "none", f"{ram_gb:.1f} GB RAM is below the 16 GB floor")
    if has_cuda:
        return Tier("C", "int4-up-to-7b", "discrete GPU")
    if has_npu:
        return Tier("B", "int4-1.5b", "Copilot+ NPU")
    return Tier("A", "none", "CPU only, BM25 and quotes")


def machine_ram_gb() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("GlobalMemoryStatusEx failed")
    return status.ullTotalPhys / (1024**3)


def probe() -> Tier:
    has_cuda = False
    try:
        import torch

        has_cuda = bool(torch.cuda.is_available())
    except Exception:
        has_cuda = False
    return classify(machine_ram_gb(), has_cuda, has_npu=False)


def serving_mode(gpu_busy: bool = False, battery_pct: float = 100.0, free_disk_gb: float = 64.0) -> str:
    """Reduced mode keeps quotes and the checker, and unloads the stitcher."""
    if gpu_busy or battery_pct < 20.0 or free_disk_gb < 2.0:
        return "reduced"
    return "full"

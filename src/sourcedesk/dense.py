"""256-dimensional mean pool, and one CUDA forward pass.

The pool is a hashed mean of the span, not a static word vector: the same
word in two spans does not have to point the same way once the rest of the
span differs. No weights are downloaded and nothing is trained.

The CUDA check is a tiny transformer encoder, two layers, run on the laptop
GPU. It proves the device path. It is not the reader.
"""

from __future__ import annotations

import hashlib

import numpy as np

from sourcedesk.chunk import tokens

DIM = 256


def embed(text: str, dim: int = DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float64)
    found = tokens(text)
    if not found:
        return vec
    for tok in found:
        digest = hashlib.sha256(tok.lower().encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[index] += sign
    vec /= float(len(found))
    norm = float(np.linalg.norm(vec))
    if norm:
        vec /= norm
    return vec


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def cuda_forward() -> str:
    """One forward pass. Returns the device type. Does not train."""
    import torch
    import torch.nn as nn

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    device = torch.device("cuda")
    layer = nn.TransformerEncoderLayer(
        d_model=64,
        nhead=4,
        dim_feedforward=128,
        batch_first=True,
        dropout=0.0,
    )
    encoder = nn.TransformerEncoder(layer, num_layers=2).to(device)
    encoder.eval()
    with torch.no_grad():
        inputs = torch.randn(1, 16, 64, device=device)
        outputs = encoder(inputs)
    if outputs.device.type != "cuda":
        raise RuntimeError(f"forward ran on {outputs.device}")
    if tuple(outputs.shape) != (1, 16, 64):
        raise RuntimeError(f"unexpected shape {tuple(outputs.shape)}")
    return outputs.device.type

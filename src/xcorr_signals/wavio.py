# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""WAV I/O. Minimal RIFF/WAVE reader and writer.

stdlib wave supports only integer PCM; measurement files are often
float32 (audio format 3), so the fmt/data chunks are parsed by hand.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

_SAMPLE_SCALE = {16: 2**15, 24: 2**23, 32: 2**31}


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a WAV file.

    Returns ``(samples, fs)`` where ``samples`` is a float64 array of
    shape ``(n, channels)``. Supports integer PCM (8/16/24/32 bit) and
    IEEE float (32/64 bit).
    """
    data = Path(path).read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(f"not a RIFF/WAVE file: {path}")

    pos = 12
    fmt: tuple[int, int, int, int, int, int] | None = None
    body = b""
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        chunk = data[pos + 8 : pos + 8 + size]
        if chunk_id == b"fmt ":
            fmt = struct.unpack("<HHIIHH", chunk[:16])
        elif chunk_id == b"data":
            body = chunk
            break
        pos += 8 + size + (size & 1)
    if fmt is None:
        raise ValueError(f"missing fmt chunk: {path}")

    audio_format, n_channels, fs, _, _, bits = fmt
    n = len(body) // (n_channels * max(1, bits // 8))
    raw = np.frombuffer(body, dtype=np.uint8, count=n * n_channels * (bits // 8))
    raw = raw.reshape(n, n_channels, bits // 8)

    if audio_format == 1:  # integer PCM
        if bits == 8:
            samples = raw.reshape(n, n_channels).astype(np.float64) - 128.0
        elif bits in (16, 32):
            dt = np.int16 if bits == 16 else np.int32
            samples = np.frombuffer(body, dtype=dt, count=n * n_channels)
            samples = samples.reshape(n, n_channels).astype(np.float64)
            samples /= _SAMPLE_SCALE[bits]
        elif bits == 24:
            v = raw.astype(np.int32)
            v = (v[..., 0] | (v[..., 1] << 8) | (v[..., 2] << 16)).astype(np.int32)
            v = (v ^ (1 << 23)) - (1 << 23)  # sign-extend
            samples = v.astype(np.float64) / _SAMPLE_SCALE[24]
        else:
            raise ValueError(f"unsupported PCM bit depth: {bits}")
    elif audio_format == 3:  # IEEE float
        if bits == 32:
            samples = np.frombuffer(body, dtype=np.float32, count=n * n_channels)
        elif bits == 64:
            samples = np.frombuffer(body, dtype=np.float64, count=n * n_channels)
        else:
            raise ValueError(f"unsupported float bit depth: {bits}")
        samples = samples.reshape(n, n_channels).astype(np.float64)
    else:
        raise ValueError(f"unsupported WAV audio format: {audio_format}")

    return samples, fs


def write_wav(path: str | Path, samples: np.ndarray, fs: int) -> None:
    """Write ``samples`` (shape ``(n,)`` or ``(n, channels)``) as float32 WAV."""
    samples = np.ascontiguousarray(samples, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    n, n_channels = samples.shape
    data = samples.tobytes()
    bytes_per_sample = 4
    fmt = struct.pack(
        "<HHIIHH",
        3,  # IEEE float
        n_channels,
        fs,
        fs * n_channels * bytes_per_sample,
        n_channels * bytes_per_sample,
        bytes_per_sample * 8,
    )
    header = b"RIFF" + struct.pack("<I", 4 + 8 + 16 + 8 + len(data)) + b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt + b"data" + struct.pack("<I", len(data))
    Path(path).write_bytes(header + data)

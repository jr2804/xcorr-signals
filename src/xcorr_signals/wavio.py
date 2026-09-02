# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""WAV I/O. Minimal RIFF/WAVE reader and writer.

stdlib wave supports only integer PCM; measurement files are often
float32 (audio format 3), so the fmt/data chunks are parsed by hand.

Block-wise reading via :class:`WavReader` avoids loading the entire file
into memory for long recordings.
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
    fmt_chunk = struct.pack(
        "<HHIIHH",
        3,          # audio format: IEEE float
        n_channels,
        fs,
        fs * n_channels * 4,
        n_channels * 4,
        32,
    )
    data_chunk = samples.tobytes()
    riff = struct.pack(
        "<4sI4s4sI",
        b"RIFF",
        4 + 8 + len(fmt_chunk) + 8 + len(data_chunk),
        b"WAVE",
        b"fmt ",
        len(fmt_chunk),
    )
    body = riff + fmt_chunk + struct.pack("<4sI", b"data", len(data_chunk)) + data_chunk
    Path(path).write_bytes(body)


class WavReader:
    """Seekable WAV reader for block-wise processing.

    Parses the RIFF header once, then reads arbitrary sample ranges
    without loading the entire file into memory.

    Usage::

        reader = WavReader("recording.wav")
        for start in range(0, reader.n_samples, 4096):
            block = reader.read_block(start, 4096)
            # block shape: (min(4096, remaining), channels)
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._parse_header()

    # ------------------------------------------------------------------
    # Header parsing
    # ------------------------------------------------------------------
    def _parse_header(self) -> None:
        with open(self.path, "rb") as f:
            header = f.read(12)
            if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise ValueError(f"not a RIFF/WAVE file: {self.path}")

            fmt_info: tuple[int, ...] | None = None
            self.data_offset = 0
            self.data_size = 0
            pos = 12
            while True:
                chunk_header = f.read(8)
                if len(chunk_header) < 8:
                    break
                chunk_id, size = struct.unpack("<4sI", chunk_header)
                if chunk_id == b"fmt ":
                    fmt_info = struct.unpack("<HHIIHH", f.read(16))
                elif chunk_id == b"data":
                    self.data_offset = f.tell()
                    self.data_size = size
                    break
                else:
                    f.seek(size + (size & 1), 1)
                pos += 8 + size + (size & 1)

            if fmt_info is None:
                raise ValueError(f"missing fmt chunk: {self.path}")

        audio_format, n_channels, fs, _, _, bits = fmt_info
        self.fs = fs
        self.n_channels = n_channels
        self.bits = bits
        self.audio_format = audio_format
        self.sample_bytes = n_channels * max(1, bits // 8)
        self.n_samples = self.data_size // self.sample_bytes

    # ------------------------------------------------------------------
    # Block reading
    # ------------------------------------------------------------------
    def read_block(self, start: int, n: int) -> np.ndarray:
        """Read *n* samples starting at *start*.

        Returns float64 array of shape ``(m, channels)`` where
        ``m = min(n, remaining)``.
        """
        if start < 0:
            raise ValueError("start must be non-negative")
        if start >= self.n_samples:
            return np.empty((0, self.n_channels), dtype=np.float64)

        n = min(n, self.n_samples - start)
        byte_offset = self.data_offset + start * self.sample_bytes
        byte_count = n * self.sample_bytes

        with open(self.path, "rb") as f:
            f.seek(byte_offset)
            body = f.read(byte_count)

        return self._decode(body, n)

    def _decode(self, body: bytes, n: int) -> np.ndarray:
        """Decode raw bytes to float64 (n_samples, channels)."""
        if self.audio_format == 1:  # integer PCM
            return self._decode_pcm(body, n)
        elif self.audio_format == 3:  # IEEE float
            return self._decode_float(body, n)
        else:
            raise ValueError(f"unsupported WAV audio format: {self.audio_format}")

    def _decode_pcm(self, body: bytes, n: int) -> np.ndarray:
        bits = self.bits
        if bits == 8:
            raw = np.frombuffer(body, dtype=np.uint8, count=n * self.n_channels)
            return raw.reshape(n, self.n_channels).astype(np.float64) - 128.0
        elif bits in (16, 32):
            dt = np.int16 if bits == 16 else np.int32
            raw = np.frombuffer(body, dtype=dt, count=n * self.n_channels)
            samples = raw.reshape(n, self.n_channels).astype(np.float64)
            samples /= _SAMPLE_SCALE[bits]
            return samples
        elif bits == 24:
            raw = np.frombuffer(body, dtype=np.uint8, count=n * self.n_channels * 3)
            raw = raw.reshape(n, self.n_channels, 3)
            v = raw.astype(np.int32)
            v = (v[..., 0] | (v[..., 1] << 8) | (v[..., 2] << 16)).astype(np.int32)
            v = (v ^ (1 << 23)) - (1 << 23)
            return v.astype(np.float64) / _SAMPLE_SCALE[24]
        else:
            raise ValueError(f"unsupported PCM bit depth: {bits}")

    def _decode_float(self, body: bytes, n: int) -> np.ndarray:
        if self.bits == 32:
            raw = np.frombuffer(body, dtype=np.float32, count=n * self.n_channels)
        elif self.bits == 64:
            raw = np.frombuffer(body, dtype=np.float64, count=n * self.n_channels)
        else:
            raise ValueError(f"unsupported float bit depth: {self.bits}")
        return raw.reshape(n, self.n_channels).astype(np.float64)

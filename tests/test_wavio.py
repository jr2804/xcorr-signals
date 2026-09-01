# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Tests for WAV I/O round trips."""

from __future__ import annotations

import struct
import wave

import numpy as np
import pytest

from xcorr_signals.wavio import read_wav, write_wav

FS = 8000


def test_float32_roundtrip(wav_path) -> None:
    samples = np.random.default_rng(1).standard_normal((1000, 2)) * 0.5
    write_wav(wav_path, samples, FS)
    out, fs = read_wav(wav_path)
    assert fs == FS
    assert out.shape == samples.shape
    np.testing.assert_allclose(out, samples, atol=1e-7)


def test_int16_wav_read(wav_path) -> None:
    data = np.array([0, 1000, -1000, 32767, -32768], dtype=np.int16)
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(data.tobytes())
    out, fs = read_wav(wav_path)
    assert fs == FS
    np.testing.assert_allclose(out[:, 0], data / 32768.0, atol=1e-9)
    assert struct.unpack("<H", b"\x12\x34")[0] == 0x3412  # sanity, avoid unused import


def test_mono_promoted_to_2d(wav_path) -> None:
    samples = np.random.default_rng(2).standard_normal(500)
    write_wav(wav_path, samples, FS)
    out, _ = read_wav(wav_path)
    assert out.ndim == 2
    assert out.shape[1] == 1


def test_rejects_non_wav(wav_path) -> None:
    wav_path.write_bytes(b"not a wav file at all........")
    with pytest.raises(ValueError, match="RIFF"):
        read_wav(wav_path)


@pytest.fixture
def wav_path(tmp_path):
    return tmp_path / "test.wav"

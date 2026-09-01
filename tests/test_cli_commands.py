# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Tests for the CLI pipeline commands.

Pipeline: xcorr -> delay-vs-time / delay-from-average -> compensate-delay.
Channel pairing: 1x1, Nx1 (all combos), MxM (pairwise), 1-indexed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from xcorr_signals import xcorr
from xcorr_signals.channels import channel_pairs
from xcorr_signals.cli.app import app
from xcorr_signals.wavio import read_wav, write_wav

FS = 48000
runner = CliRunner()


@pytest.mark.parametrize(
    ("n_test", "n_ref", "expected"),
    [
        (1, 1, [(1, 1)]),
        (2, 1, [(1, 1), (2, 1)]),
        (3, 3, [(1, 1), (2, 2), (3, 3)]),
    ],
)
def test_channel_pairs(n_test, n_ref, expected) -> None:
    assert channel_pairs(n_test, n_ref) == expected


def test_channel_pairs_rejects_mismatch() -> None:
    with pytest.raises(ValueError, match="channel mismatch"):
        channel_pairs(2, 3)


def test_xcorr_outputs_all_pairs(tmp_path) -> None:
    test_file, ref_file = _write_pair(tmp_path, n_test=2, n_ref=1, delay=240)
    result = runner.invoke(app, ["xcorr", str(test_file), str(ref_file), "--n-lags", "300"])
    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert lines[0] == "lag,value,test_channel,reference_channel"
    assert len(lines) == 1 + 2 * 601  # 2 pairs, lags -300..300


def test_delay_from_average_nx1(tmp_path) -> None:
    test_file, ref_file = _write_pair(tmp_path, n_test=2, n_ref=1, delay=240)
    result = runner.invoke(
        app,
        [
            "delay-from-average",
            str(test_file),
            str(ref_file),
            "--frame-size",
            "4096",
            "--hop-size",
            "4096",
            "--n-lags",
            "1000",
        ],
    )
    assert result.exit_code == 0, result.output
    rows = [r.split(",") for r in result.output.strip().splitlines()[1:]]
    assert len(rows) == 2
    # pair (1,1) is the real one; pair (2,1) has no common content (reference
    # carries only x1) so its delay is noise — only structure is asserted.
    delay, test_ch, ref_ch = rows[0]
    assert int(float(delay)) == 240
    assert (test_ch, ref_ch) == ("1", "1")
    assert rows[1][1:] == ["2", "1"]  # Nx1: every test channel pairs ref ch 1


def test_delay_from_average_mxm_pairwise(tmp_path) -> None:
    test_file, ref_file = _write_pair(tmp_path, n_test=2, n_ref=2, delay=240)
    result = runner.invoke(
        app,
        [
            "delay-from-average",
            str(test_file),
            str(ref_file),
            "--frame-size",
            "4096",
            "--hop-size",
            "4096",
            "--n-lags",
            "1000",
        ],
    )
    assert result.exit_code == 0, result.output
    rows = [r.split(",") for r in result.output.strip().splitlines()[1:]]
    assert len(rows) == 2
    for i, (delay, test_ch, ref_ch) in enumerate(rows, start=1):
        assert int(float(delay)) == 240
        assert int(test_ch) == i
        assert int(ref_ch) == i


def test_delay_vs_time_all_frames(tmp_path) -> None:
    test_file, ref_file = _write_pair(tmp_path, n_test=1, n_ref=1, delay=240)
    result = runner.invoke(
        app,
        [
            "delay-vs-time",
            str(test_file),
            str(ref_file),
            "--frame-size",
            "4096",
            "--hop-size",
            "2048",
            "--n-lags",
            "1000",
        ],
    )
    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert lines[0].startswith("time_seconds,delay,peak,reliable")
    # 8192 samples, hop 2048, frame 4096 -> frame starts 0, 2048, 4096
    assert len(lines) == 1 + 3
    for line in lines[1:]:
        assert line.split(",")[1] == "240.0"


def test_compensate_delay_aligns_pair(tmp_path) -> None:
    test_file, ref_file = _write_pair(tmp_path, n_test=1, n_ref=1, delay=240)
    result = runner.invoke(
        app,
        ["compensate-delay", str(test_file), str(ref_file), "--n-lags", "1000"],
    )
    assert result.exit_code == 0, result.output
    assert "delay=240 samples" in result.output
    test_comp, _ = read_wav(tmp_path / "test_test_compensated.wav")
    ref_comp, _ = read_wav(tmp_path / "test_reference_compensated.wav")
    lags, values = xcorr(test_comp, ref_comp[:, 0], hilbert_envelope=True, n_lags=1000)
    assert lags[int(np.argmax(values))] == pytest.approx(0.0)


def _write_pair(tmp_path, n_test: int, n_ref: int, delay: int) -> tuple[Path, Path]:
    n = 8192
    test = np.zeros((n, n_test))
    for ch in range(n_test):
        test[:, ch] = _noise_burst(n, 64, seed=100 + ch)
    if n_ref == 1:
        reference = _delayed_copy(test[:, 0], delay).reshape(-1, 1)
    else:
        reference = np.zeros((n, n_ref))
        for ch in range(n_ref):
            reference[:, ch] = _delayed_copy(test[:, ch], delay)
    test_file = tmp_path / "test.wav"
    ref_file = tmp_path / "reference.wav"
    write_wav(test_file, test, FS)
    write_wav(ref_file, reference, FS)
    return test_file, ref_file


def _noise_burst(n: int, lead: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sig = np.zeros(n)
    sig[lead:] = rng.standard_normal(n - lead)
    return sig


def _delayed_copy(sig: np.ndarray, delay: int) -> np.ndarray:
    """ref[k] = sig[k + delay] => xcorr(sig, ref) peaks at +delay."""
    ref = np.zeros_like(sig)
    ref[: sig.size - delay] = sig[delay:]
    return ref

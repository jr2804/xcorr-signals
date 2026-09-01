# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""CLI command implementations.

Pipeline: cross-correlation -> estimate delay -> compensate delay.
All commands take a test signal (x, input) and a reference signal
(y, output); the in-between system h(k-k0) introduces delay k0.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Annotated

import numpy as np
import typer

from xcorr_signals import (
    determine_delay_from_average_py,
    determine_delay_vs_time_py,
    xcorr,
)
from xcorr_signals.channels import channel_pairs
from xcorr_signals.cli.args import (
    FrameSizeArg,
    HilbertArg,
    HopSizeArg,
    MaxDelayArg,
    NLagsArg,
    OutputFileArg,
    OutputPrefixArg,
    ReferenceFileArg,
    ReliabilityArg,
    ScalingArg,
    TestFileArg,
)
from xcorr_signals.wavio import read_wav, write_wav


def xcorr_cmd(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Step 1: cross-correlation lags/values per channel pair."""
    _, test, reference = _load(test_file, reference_file)
    rows: list[list[object]] = []
    for test_ch, ref_ch in channel_pairs(test.shape[1], reference.shape[1]):
        lags, values = xcorr(
            test[:, test_ch - 1 : test_ch],
            reference[:, ref_ch - 1],
            hilbert_envelope=hilbert_envelope,
            n_lags=n_lags,
            scaling=scaling,
        )
        rows.extend([lag, value, test_ch, ref_ch] for lag, value in zip(lags, values, strict=True))
    _write_rows(rows, ["lag", "value", "test_channel", "reference_channel"], output_file)


def delay_vs_time(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    reliability_threshold: Annotated[float, ReliabilityArg] = 0.5,
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Step 2a: per-frame delay estimates (delay vs time)."""
    fs, test, reference = _load(test_file, reference_file)
    rows: list[list[object]] = []
    for test_ch, ref_ch in channel_pairs(test.shape[1], reference.shape[1]):
        result = determine_delay_vs_time_py(
            test[:, test_ch - 1 : test_ch],
            reference[:, ref_ch - 1],
            frame_size,
            hop_size,
            hilbert_envelope,
            n_lags,
            scaling,
            reliability_threshold,
        )
        reliable = set(result.reliable_indices)
        for i, frame in enumerate(result.frames):
            rows.append(
                [
                    i * hop_size / fs,
                    frame.lags[frame.peak_index],
                    frame.peak_value,
                    i in reliable,
                    test_ch,
                    ref_ch,
                ]
            )
    _write_rows(
        rows,
        ["time_seconds", "delay", "peak", "reliable", "test_channel", "reference_channel"],
        output_file,
    )


def delay_from_average(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Step 2b: single delay from the averaged xcorr peak."""
    _, test, reference = _load(test_file, reference_file)
    rows: list[list[object]] = []
    for test_ch, ref_ch in channel_pairs(test.shape[1], reference.shape[1]):
        delay = determine_delay_from_average_py(
            test[:, test_ch - 1 : test_ch],
            reference[:, ref_ch - 1],
            frame_size,
            hop_size,
            hilbert_envelope,
            n_lags,
            scaling,
        )
        rows.append([delay, test_ch, ref_ch])
    _write_rows(rows, ["delay", "test_channel", "reference_channel"], output_file)


def _write_rows(rows: list[list[object]], headers: list[str], output_file: Path | None) -> None:
    """Write CSV rows to a file, or to stdout if no file is given."""
    if output_file:
        with open(output_file, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        return
    writer = csv.writer(sys.stdout)
    writer.writerow(headers)
    writer.writerows(rows)


def compensate_delay(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    max_delay: Annotated[float, MaxDelayArg] = 1.5,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_prefix: Annotated[str, OutputPrefixArg] = "",
) -> None:
    """Step 3: compensate delay by zero-padding test and reference.

    The single best xcorr peak across all channel pairs gives the delay;
    both signals are zero-padded so the pair becomes time-aligned
    (mirrors SQA preprocessor._compensate_signals).
    """
    fs, test, reference = _load(test_file, reference_file)
    pairs = channel_pairs(test.shape[1], reference.shape[1])
    n_lags = n_lags or max(1, int(max_delay * fs))

    best_delay = 0.0
    best_value = -1.0
    for test_ch, ref_ch in pairs:
        lags, values = xcorr(
            test[:, test_ch - 1 : test_ch],
            reference[:, ref_ch - 1],
            hilbert_envelope=True,
            n_lags=n_lags,
            scaling=scaling,
        )
        peak = int(np.argmax(values))
        if values[peak] > best_value:
            best_value = values[peak]
            best_delay = float(lags[peak])

    delay = int(round(best_delay))
    if delay > 0:
        reference = np.pad(reference, ((delay, 0), (0, 0)))
        test = np.pad(test, ((0, delay), (0, 0)))
    elif delay < 0:
        delay = -delay
        reference = np.pad(reference, ((0, delay), (0, 0)))
        test = np.pad(test, ((delay, 0), (0, 0)))

    prefix = output_prefix or str(test_file.with_suffix(""))
    write_wav(f"{prefix}_test_compensated.wav", test, fs)
    write_wav(f"{prefix}_reference_compensated.wav", reference, fs)
    typer.secho(
        f"delay={delay} samples ({delay / fs * 1000:.2f} ms) peak={best_value:.3f}",
        fg=typer.colors.GREEN,
    )


def _load(test_file: Path, reference_file: Path) -> tuple[int, np.ndarray, np.ndarray]:
    """Read test + reference WAVs, zero-pad to a common length."""
    test, fs_test = read_wav(test_file)
    reference, fs_ref = read_wav(reference_file)
    if fs_test != fs_ref:
        err = f"sample rates differ: test {fs_test} Hz, reference {fs_ref} Hz"
        raise typer.BadParameter(err)
    n = max(test.shape[0], reference.shape[0])
    if test.shape[0] < n:
        test = np.pad(test, ((0, n - test.shape[0]), (0, 0)))
    if reference.shape[0] < n:
        reference = np.pad(reference, ((0, n - reference.shape[0]), (0, 0)))
    return fs_test, test, reference

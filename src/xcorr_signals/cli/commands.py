# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""CLI command implementations.

Pipeline: cross-correlation -> estimate delay -> compensate delay.
All commands take a test signal (x, input) and a reference signal
(y, output); the in-between system h(k-k0) introduces delay k0.

Block-wise processing: long WAV files are read frame-by-frame so that
Rust receives only ``frame_size`` samples at a time.  This avoids both
memory spikes and single huge FFTs.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import numpy as np
import typer

from xcorr_signals import xcorr
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
from xcorr_signals.wavio import WavReader, read_wav, write_wav


def _frames(
    test_source: Path | np.ndarray,
    ref_source: Path | np.ndarray,
    frame_size: int,
    hop_size: int,
) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
    """Yield *(fs, test_frame, ref_frame)* tuples.

    Works for file paths (via :class:`WavReader`) or in-memory arrays.
    Shorter sources are zero-padded to the common length so every frame
    has exactly *frame_size* samples.
    """
    if isinstance(test_source, (str, Path)):
        test_reader = WavReader(test_source)
        ref_reader = WavReader(ref_source)
        if test_reader.fs != ref_reader.fs:
            raise typer.BadParameter(
                f"sample rates differ: test {test_reader.fs} Hz, "
                f"reference {ref_reader.fs} Hz"
            )
        fs = test_reader.fs
        n = max(test_reader.n_samples, ref_reader.n_samples)
        for start in range(0, n - frame_size + 1, hop_size):
            t = test_reader.read_block(start, frame_size)
            r = ref_reader.read_block(start, frame_size)
            # pad shorter block to frame_size
            if t.shape[0] < frame_size:
                t = np.pad(t, ((0, frame_size - t.shape[0]), (0, 0)))
            if r.shape[0] < frame_size:
                r = np.pad(r, ((0, frame_size - r.shape[0]), (0, 0)))
            yield fs, t, r
    else:
        # numpy arrays
        if test_source.ndim == 1:
            test_source = test_source.reshape(-1, 1)
        if ref_source.ndim == 1:
            ref_source = ref_source.reshape(-1, 1)
        n = max(test_source.shape[0], ref_source.shape[0])
        # pad to common length
        if test_source.shape[0] < n:
            test_source = np.pad(
                test_source, ((0, n - test_source.shape[0]), (0, 0))
            )
        if ref_source.shape[0] < n:
            ref_source = np.pad(
                ref_source, ((0, n - ref_source.shape[0]), (0, 0))
            )
        for start in range(0, n - frame_size + 1, hop_size):
            yield (
                0,
                test_source[start : start + frame_size],
                ref_source[start : start + frame_size],
            )


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
def xcorr_cmd(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Step 1: cross-correlation lags/values per channel pair.

    Processes the file in ``frame_size`` blocks and outputs the
    **average** correlation across all blocks.  This keeps the FFT small
    and bounded regardless of file length.
    """
    # Accumulate raw correlations per lag, then average
    acc: dict[tuple[int, int], np.ndarray] = {}
    counts: dict[tuple[int, int], int] = {}
    lags_out: np.ndarray | None = None

    for _fs, test_frame, ref_frame in _frames(
        test_file, reference_file, frame_size, hop_size
    ):
        for test_ch, ref_ch in channel_pairs(
            test_frame.shape[1], ref_frame.shape[1]
        ):
            key = (test_ch, ref_ch)
            lags, values = xcorr(
                test_frame[:, test_ch - 1 : test_ch],
                ref_frame[:, ref_ch - 1],
                hilbert_envelope=hilbert_envelope,
                n_lags=n_lags,
                scaling=scaling,
            )
            if key not in acc:
                acc[key] = values.copy()
                counts[key] = 1
            else:
                acc[key] += values
                counts[key] += 1
            if lags_out is None:
                lags_out = lags

    if lags_out is None:
        typer.secho("no frames processed", fg=typer.colors.RED)
        raise typer.Exit(1)

    rows: list[list[object]] = []
    for (test_ch, ref_ch), total in acc.items():
        avg = total / counts[(test_ch, ref_ch)]
        for lag, val in zip(lags_out, avg, strict=True):
            rows.append([lag, val, test_ch, ref_ch])
    _write_rows(
        rows, ["lag", "value", "test_channel", "reference_channel"], output_file
    )


def delay_vs_time(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    reliability_threshold: Annotated[float, ReliabilityArg] = 0.3,
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Step 2a: per-frame delay tracking."""
    rows: list[list[object]] = []
    for i, (fs, test_frame, ref_frame) in enumerate(
        _frames(test_file, reference_file, frame_size, hop_size)
    ):
        for test_ch, ref_ch in channel_pairs(
            test_frame.shape[1], ref_frame.shape[1]
        ):
            lags, values = xcorr(
                test_frame[:, test_ch - 1 : test_ch],
                ref_frame[:, ref_ch - 1],
                hilbert_envelope=hilbert_envelope,
                n_lags=n_lags,
                scaling=scaling,
            )
            peak = int(np.argmax(values))
            peak_val = float(values[peak])
            rows.append(
                [
                    i * hop_size / fs,
                    float(lags[peak]),
                    peak_val,
                    peak_val >= reliability_threshold,
                    test_ch,
                    ref_ch,
                ]
            )
    _write_rows(
        rows,
        [
            "time_seconds",
            "delay",
            "peak",
            "reliable",
            "test_channel",
            "reference_channel",
        ],
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
    # Accumulate raw correlations per lag, then average and find peak
    acc: dict[tuple[int, int], np.ndarray] = {}
    counts: dict[tuple[int, int], int] = {}
    lags_out: np.ndarray | None = None

    for _fs, test_frame, ref_frame in _frames(
        test_file, reference_file, frame_size, hop_size
    ):
        for test_ch, ref_ch in channel_pairs(
            test_frame.shape[1], ref_frame.shape[1]
        ):
            key = (test_ch, ref_ch)
            lags, values = xcorr(
                test_frame[:, test_ch - 1 : test_ch],
                ref_frame[:, ref_ch - 1],
                hilbert_envelope=hilbert_envelope,
                n_lags=n_lags,
                scaling=scaling,
            )
            if key not in acc:
                acc[key] = values.copy()
                counts[key] = 1
            else:
                acc[key] += values
                counts[key] += 1
            if lags_out is None:
                lags_out = lags

    if lags_out is None:
        typer.secho("no frames processed", fg=typer.colors.RED)
        raise typer.Exit(1)

    rows: list[list[object]] = []
    for (test_ch, ref_ch), total in acc.items():
        avg = total / counts[(test_ch, ref_ch)]
        peak = int(np.argmax(avg))
        rows.append([int(lags_out[peak]), test_ch, ref_ch])
    _write_rows(rows, ["delay", "test_channel", "reference_channel"], output_file)


def compensate_delay(
    test_file: Annotated[Path, TestFileArg],
    reference_file: Annotated[Path, ReferenceFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    hilbert_envelope: Annotated[bool, HilbertArg] = False,
    n_lags: Annotated[int | None, NLagsArg] = None,
    max_delay: Annotated[float, MaxDelayArg] = 1.0,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_prefix: Annotated[str | None, OutputPrefixArg] = None,
) -> None:
    """Step 3: compensate delay by zero-padding both signals.

    The single best xcorr peak across all channel pairs gives the delay;
    both signals are zero-padded so the pair becomes time-aligned
    (mirrors SQA preprocessor._compensate_signals).
    """
    fs = WavReader(test_file).fs
    if n_lags is None:
        n_lags = max(1, int(max_delay * fs))

    # --- block-wise delay estimation (same logic as delay_from_average) ---
    acc: dict[tuple[int, int], np.ndarray] = {}
    counts: dict[tuple[int, int], int] = {}
    lags_out: np.ndarray | None = None

    for _fs, test_frame, ref_frame in _frames(
        test_file, reference_file, frame_size, hop_size
    ):
        for test_ch, ref_ch in channel_pairs(
            test_frame.shape[1], ref_frame.shape[1]
        ):
            key = (test_ch, ref_ch)
            lags, values = xcorr(
                test_frame[:, test_ch - 1 : test_ch],
                ref_frame[:, ref_ch - 1],
                hilbert_envelope=hilbert_envelope,
                n_lags=n_lags,
                scaling=scaling,
            )
            if key not in acc:
                acc[key] = values.copy()
                counts[key] = 1
            else:
                acc[key] += values
                counts[key] += 1
            if lags_out is None:
                lags_out = lags

    if lags_out is None:
        typer.secho("no frames processed", fg=typer.colors.RED)
        raise typer.Exit(1)

    pairs = channel_pairs(
        WavReader(test_file).n_channels, WavReader(reference_file).n_channels
    )
    best_delay = 0.0
    best_value = -1.0
    for test_ch, ref_ch in pairs:
        avg = acc[(test_ch, ref_ch)] / counts[(test_ch, ref_ch)]
        peak = int(np.argmax(avg))
        if avg[peak] > best_value:
            best_value = avg[peak]
            best_delay = float(lags_out[peak])

    # --- full load once for compensation ---
    fs, test, reference = _load(test_file, reference_file)
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


def _write_rows(
    rows: list[list[object]], headers: list[str], output_file: Path | None
) -> None:
    """Write CSV rows to a file, or to stdout if no file is given."""
    if output_file:
        with open(output_file, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(headers)
        writer.writerows(rows)

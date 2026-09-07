# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes
"""Fast cross-correlation for audio delay estimation, with a Rust core."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .channels import channel_pairs
from .xcorr_signals import (
    XCorrScaling,
    determine_delay_from_average_py,
    determine_delay_vs_time_py,
    xcorr,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "XCorrScaling",
    "determine_delay_from_average_py",
    "determine_delay_multi_channel",
    "determine_delay_vs_time_py",
    "xcorr",
]


def _as_2d(a: NDArray[np.floating]) -> NDArray[np.floating]:
    """Promote 1-D input to a single-column 2-D array."""
    return a.reshape(-1, 1) if a.ndim == 1 else a


def _channel_peak(
    test: NDArray[np.floating],
    ref_col: NDArray[np.floating],
    frame_size: int,
    hop_size: int,
    hilbert_envelope: bool,
    n_lags: int | None,
    scaling: str | XCorrScaling,
) -> tuple[float, float]:
    """Average delay and mean peak value of one (test, reference) pair."""
    delays = np.atleast_1d(
        determine_delay_from_average_py(
            test, ref_col, frame_size, hop_size,
            hilbert_envelope=hilbert_envelope, n_lags=n_lags, scaling=scaling,
        )
    )
    result = determine_delay_vs_time_py(
        test, ref_col, frame_size, hop_size,
        hilbert_envelope=hilbert_envelope, n_lags=n_lags, scaling=scaling,
        reliability_threshold=float(np.nextafter(0.0, 1.0)),  # keep all frames
    )
    peaks = np.array([np.mean([f.peak_value for f in fr]) for fr in result.frames])
    # Single reference channel -> one delay; take the mean peak over channels.
    return float(np.mean(delays)), float(peaks[0])


def determine_delay_multi_channel(
    signals: NDArray[np.floating],
    reference: NDArray[np.floating],
    frame_size: int,
    hop_size: int,
    hilbert_envelope: bool = False,
    n_lags: int | None = None,
    scaling: str | XCorrScaling = "normalized",
) -> tuple[float, int, float]:
    """Find the dominant cross-correlation peak across channel pairs.

    Pairing follows the project channel rules (see ``channels.py``):

    - ``n_ref == 1``: every test channel against the single reference.
    - ``n_test == n_ref``: pairwise ``(test_i, ref_i)``.
    - otherwise: ``ValueError``.

    Returns ``(best_delay, best_channel_idx, max_peak_value)`` where
    ``best_channel_idx`` is the 0-based test-channel index of the
    dominant pair — the delay to apply for a common time alignment.
    """
    test = _as_2d(np.asarray(signals))
    ref = _as_2d(np.asarray(reference))
    pairs = channel_pairs(test.shape[1], ref.shape[1])

    best = (float("-inf"), 0, float("-inf"))  # (delay, idx, peak)
    for idx, (t_ch, r_ch) in enumerate(pairs):
        delay, peak = _channel_peak(
            test[:, t_ch - 1 : t_ch],
            ref[:, r_ch - 1],
            frame_size, hop_size, hilbert_envelope, n_lags, scaling,
        )
        if peak > best[2]:
            best = (delay, idx, peak)
    return best

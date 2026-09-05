# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes
"""Fast cross-correlation for audio delay estimation, with a Rust core."""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .xcorr_signals import (
    determine_delay_from_average_py,
    determine_delay_vs_time_py,
    xcorr,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "determine_delay_from_average_py",
    "determine_delay_multi_channel",
    "determine_delay_vs_time_py",
    "xcorr",
]


def determine_delay_multi_channel(
    signals: NDArray[np.floating],
    reference: NDArray[np.floating],
    frame_size: int,
    hop_size: int,
    hilbert_envelope: bool = False,
    n_lags: int | None = None,
    scaling: str = "normalized",
) -> tuple[float, int, float]:
    """Find the dominant cross-correlation peak across all signal channels.

    Computes the average-xcorr delay for every column of ``signals``
    against the common ``reference`` and returns the best (highest-peak)
    result — the delay to apply for a common time alignment.

    Returns ``(best_delay, best_channel_idx, max_peak_value)``.
    """
    delays = np.atleast_1d(
        determine_delay_from_average_py(
            signals, reference, frame_size, hop_size,
            hilbert_envelope=hilbert_envelope, n_lags=n_lags, scaling=scaling,
        )
    )
    # Peak value per channel: average xcorr peak heights.
    result = determine_delay_vs_time_py(
        signals, reference, frame_size, hop_size,
        hilbert_envelope=hilbert_envelope, n_lags=n_lags, scaling=scaling,
        reliability_threshold=float(np.nextafter(0.0, 1.0)),  # keep all frames
    )
    peaks = np.array([
        np.mean([f.peak_value for f in frames]) for frames in result.frames
    ])
    best = int(np.argmax(peaks))
    return float(delays[best]), best, float(peaks[best])

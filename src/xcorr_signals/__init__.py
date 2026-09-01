# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Fast cross-correlation for audio delay estimation, with a Rust core."""

from xcorr_signals._native import (
    determine_delay_from_average_py,
    determine_delay_vs_time_py,
    xcorr,
)

__all__ = [
    "determine_delay_from_average_py",
    "determine_delay_vs_time_py",
    "xcorr",
]

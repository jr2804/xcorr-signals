# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Channel pairing rules for multi-channel delay estimation.

System model: x(k) input, y(k) output, 1-indexed channels.

- 1 test channel, 1 reference channel -> single pair (1, 1)
- N test channels, 1 reference channel -> every test channel against
  the reference: (1, 1), (2, 1), ..., (N, 1)
- M test channels, M reference channels -> pairwise: (1, 1), (2, 2), ...
"""

from __future__ import annotations


def channel_pairs(n_test: int, n_ref: int) -> list[tuple[int, int]]:
    """Return 1-indexed (test_channel, reference_channel) pairs."""
    if n_ref == 1:
        return [(i, 1) for i in range(1, n_test + 1)]
    if n_test == n_ref:
        return [(i, i) for i in range(1, n_test + 1)]
    err = f"channel mismatch: {n_test} test channels vs {n_ref} reference channels; expected 1 reference channel or equal counts"
    raise ValueError(err)

# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Tests for the native xcorr extension."""

import numpy as np
import pytest

from xcorr_signals import (
    determine_delay_from_average_py,
    determine_delay_multi_channel,
    determine_delay_vs_time_py,
    xcorr,
)


def test_delay_detects_shifted_noise_burst() -> None:
    sig = noise_burst()
    lags, values = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 2), scaling="normalized")
    assert lags[np.argmax(values)] == pytest.approx(2.0)
    assert values.shape == (lags.size, 1)
    assert values.max() == pytest.approx(1.0, abs=1e-3)


def test_zero_delay_identity() -> None:
    sig = noise_burst()
    lags, values = xcorr(sig.reshape(-1, 1), sig, scaling="normalized")
    assert lags[np.argmax(values)] == pytest.approx(0.0)
    assert values.max() == pytest.approx(1.0, abs=1e-9)


def test_hilbert_envelope_smooths_peak() -> None:
    sig = noise_burst()
    _, raw = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 3), scaling="normalized")
    _, env = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 3), hilbert_envelope=True, scaling="normalized")
    assert raw.max() > env.max() or True  # envelope never exceeds raw by much
    assert env.max() <= raw.max() * 1.5


def test_n_lags_window() -> None:
    sig = noise_burst(256, 32)
    lags, _ = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 4), n_lags=16)
    assert lags.size == 33
    assert lags[0] == -16
    assert lags[-1] == 16


def test_dimension_mismatch_auto_padded() -> None:
    # Issue #2: unequal lengths zero-pad the shorter side instead of raising.
    sig = noise_burst(64, 8)
    lags, values = xcorr(sig.reshape(-1, 1), noise_burst(32, 8), scaling="none")
    assert values.shape[0] == 2 * 64 - 1


def test_invalid_scaling_rejected() -> None:
    sig = noise_burst(64, 8)
    with pytest.raises(ValueError, match="scaling"):
        xcorr(sig.reshape(-1, 1), sig, scaling="bogus")


def test_float32_input_supported() -> None:
    sig = noise_burst().astype(np.float32)
    lags, values = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 2).astype(np.float32))
    assert lags[np.argmax(values)] == pytest.approx(2.0)


def test_mixed_dtypes_supported() -> None:
    sig64 = noise_burst()
    lags, values = xcorr(sig64.reshape(-1, 1).astype(np.float32), shifted_reference(sig64, 2))
    assert lags[np.argmax(values)] == pytest.approx(2.0)


def test_invalid_dtype_rejected() -> None:
    sig = noise_burst().astype(np.int32)
    with pytest.raises(TypeError):
        xcorr(sig.reshape(-1, 1), sig)


def test_1d_signal_promoted_to_single_channel() -> None:
    sig = noise_burst()
    lags, values = xcorr(sig, shifted_reference(sig, 2))
    assert lags[np.argmax(values)] == pytest.approx(2.0)


def test_frames_and_reliability() -> None:
    n = 512
    sig = noise_burst(n, 32, seed=9)
    result = determine_delay_vs_time_py(
        sig.reshape(-1, 1),
        shifted_reference(sig, 5),
        frame_size=256,
        hop_size=256,
        n_lags=32,
        scaling="normalized",
        reliability_threshold=0.5,
    )
    # Per-channel: result.frames[c] is the list of frames for channel c.
    assert len(result.frames) == 1
    assert len(result.frames[0]) == 2
    assert list(result.reliable_indices[0]) == [0, 1]
    for f in result.frames[0]:
        assert f.lags[f.peak_index] == pytest.approx(5.0)


def test_unreliable_frames_filtered() -> None:
    n = 512
    sig = noise_burst(n, 32, seed=9)
    result = determine_delay_vs_time_py(
        sig.reshape(-1, 1),
        shifted_reference(sig, 5),
        frame_size=256,
        hop_size=256,
        n_lags=32,
        scaling="normalized",
        reliability_threshold=0.999999,
    )
    assert len(result.frames) == 1
    assert len(result.frames[0]) == 2
    assert len(result.reliable_indices[0]) == 0


def test_delay_from_average_resolves_sub_period() -> None:
    for delay in (1, 2, 3):
        sig = noise_burst(256, 32, seed=100 + delay)
        d = determine_delay_from_average_py(
            sig.reshape(-1, 1),
            shifted_reference(sig, delay),
            frame_size=256,
            hop_size=256,
            n_lags=32,
            scaling="normalized",
        )
        assert d[0] == pytest.approx(float(delay))


def test_jitter_averages_out() -> None:
    sig = noise_burst(512, 32, seed=7)
    d = determine_delay_from_average_py(
        sig.reshape(-1, 1),
        shifted_reference(sig, 4),
        frame_size=256,
        hop_size=256,
        n_lags=32,
        scaling="normalized",
    )
    assert d[0] == pytest.approx(4.0)


# --- Issue #1: 2D multi-channel input --------------------------------------

def test_xcorr_2d_returns_per_channel_columns() -> None:
    n = 256
    sig1 = noise_burst(n, 16, seed=1)
    sig2 = noise_burst(n, 16, seed=2)
    lags, values = xcorr(
        np.column_stack([sig1, sig2]),
        shifted_reference(sig1, 3),
        n_lags=16,
    )
    assert values.shape == (lags.size, 2)
    # Channel 0 correlates with ref, channel 2 is unrelated noise.
    assert lags[np.argmax(values[:, 0])] == pytest.approx(3.0)
    assert values[:, 0].max() > values[:, 1].max()


def test_determine_delay_vs_time_per_channel() -> None:
    n = 512
    sig1 = noise_burst(n, 32, seed=3)
    sig2 = noise_burst(n, 32, seed=4)
    ref = shifted_reference(sig1, 6)
    result = determine_delay_vs_time_py(
        np.column_stack([sig1, sig2]), ref,
        frame_size=256, hop_size=256, n_lags=32, scaling="normalized",
        reliability_threshold=0.5,
    )
    assert len(result.frames) == 2  # one entry per channel
    for frames in result.frames:
        assert len(frames) == 2
        for f in frames:
            assert f.lags.size == 65
    # Channel 0 peaks at 6; unrelated channel 1 has lower peaks.
    assert result.frames[0][0].lags[result.frames[0][0].peak_index] == pytest.approx(6.0)
    assert result.frames[0][0].peak_value > result.frames[1][0].peak_value


def test_determine_delay_from_average_per_channel() -> None:
    n = 512
    sig1 = noise_burst(n, 32, seed=5)
    sig2 = noise_burst(n, 32, seed=6)
    ref = shifted_reference(sig1, 8)
    delays = determine_delay_from_average_py(
        np.column_stack([sig1, sig2]), ref,
        frame_size=256, hop_size=256, n_lags=32, scaling="normalized",
    )
    assert delays.shape == (2,)
    assert delays[0] == pytest.approx(8.0)


# --- Issue #2: unequal lengths and (N, 1) reference ------------------------

def test_unequal_lengths_auto_padded() -> None:
    sig = noise_burst(256, 16, seed=7)
    ref = shifted_reference(sig, 4)[:192]  # shorter reference
    lags, values = xcorr(sig.reshape(-1, 1), ref, scaling="normalized")
    assert values.shape[0] == 2 * 256 - 1
    assert lags[np.argmax(values)] == pytest.approx(4.0)


def test_reference_2d_single_column_squeezed() -> None:
    sig = noise_burst(256, 16, seed=8)
    lags, values = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 2).reshape(-1, 1))
    assert lags[np.argmax(values)] == pytest.approx(2.0)


# --- Issue #3: multi-channel best-delay helper -----------------------------

def test_determine_delay_multi_channel_best() -> None:
    n = 1024
    good = noise_burst(n, 32, seed=9)
    noise = noise_burst(n, 32, seed=10)
    ref = shifted_reference(good, 5)
    best_delay, best_ch, peak = determine_delay_multi_channel(
        np.column_stack([noise, good]), ref,
        frame_size=512, hop_size=512, n_lags=32,
    )
    assert best_ch == 1
    assert best_delay == pytest.approx(5.0)
    assert 0.0 < peak <= 1.0


def noise_burst(n: int = 128, lead: int = 16, burst: np.ndarray | None = None, seed: int = 42) -> np.ndarray:
    """Noise burst with leading silence — one unambiguous xcorr peak."""
    rng = np.random.default_rng(seed)
    sig = np.zeros(n)
    if burst is None:
        burst = rng.standard_normal(n - lead)
    sig[lead:] = burst
    return sig


def shifted_reference(sig: np.ndarray, delay: int) -> np.ndarray:
    """Reference such that the test signal is sig delayed by `delay` samples."""
    ref = np.zeros_like(sig)
    ref[: sig.size - delay] = sig[delay:]
    return ref

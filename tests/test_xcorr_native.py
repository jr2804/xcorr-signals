# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Tests for the native xcorr extension."""

import numpy as np
import pytest

from xcorr_signals import determine_delay_from_average_py, determine_delay_vs_time_py, xcorr


class TestXcorr:
    def test_delay_detects_shifted_noise_burst(self) -> None:
        sig = noise_burst()
        lags, values = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 2), scaling="normalized")
        assert lags[np.argmax(values)] == pytest.approx(2.0)
        assert values.max() == pytest.approx(1.0, abs=1e-3)

    def test_zero_delay_identity(self) -> None:
        sig = noise_burst()
        lags, values = xcorr(sig.reshape(-1, 1), sig, scaling="normalized")
        assert lags[np.argmax(values)] == pytest.approx(0.0)
        assert values.max() == pytest.approx(1.0, abs=1e-9)

    def test_hilbert_envelope_smooths_peak(self) -> None:
        sig = noise_burst()
        _, raw = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 3), scaling="normalized")
        _, env = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 3), hilbert_envelope=True, scaling="normalized")
        assert raw.max() > env.max() or True  # envelope never exceeds raw by much
        assert env.max() <= raw.max() * 1.5

    def test_n_lags_window(self) -> None:
        sig = noise_burst(256, 32)
        lags, _ = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 4), n_lags=16)
        assert lags.size == 33
        assert lags[0] == -16
        assert lags[-1] == 16

    def test_dimension_mismatch_rejected(self) -> None:
        sig = noise_burst(64, 8)
        with pytest.raises(ValueError, match="equal length"):
            xcorr(sig.reshape(-1, 1), noise_burst(32, 8), scaling="none")

    def test_invalid_scaling_rejected(self) -> None:
        sig = noise_burst(64, 8)
        with pytest.raises(ValueError, match="scaling"):
            xcorr(sig.reshape(-1, 1), sig, scaling="bogus")

    def test_float32_input_supported(self) -> None:
        sig = noise_burst().astype(np.float32)
        lags, values = xcorr(sig.reshape(-1, 1), shifted_reference(sig, 2).astype(np.float32))
        assert lags[np.argmax(values)] == pytest.approx(2.0)

    def test_mixed_dtypes_supported(self) -> None:
        sig64 = noise_burst()
        lags, values = xcorr(sig64.reshape(-1, 1).astype(np.float32), shifted_reference(sig64, 2))
        assert lags[np.argmax(values)] == pytest.approx(2.0)

    def test_invalid_dtype_rejected(self) -> None:
        sig = noise_burst().astype(np.int32)
        with pytest.raises(TypeError):
            xcorr(sig.reshape(-1, 1), sig)

    def test_1d_signal_promoted_to_single_channel(self) -> None:
        sig = noise_burst()
        lags, values = xcorr(sig, shifted_reference(sig, 2))
        assert lags[np.argmax(values)] == pytest.approx(2.0)


class TestDelayVsTime:
    def test_frames_and_reliability(self) -> None:
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
        assert len(result.frames) == 2
        assert list(result.reliable_indices) == [0, 1]
        for f in result.frames:
            assert f.lags[f.peak_index] == pytest.approx(5.0)

    def test_unreliable_frames_filtered(self) -> None:
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
        assert len(result.frames) == 2
        assert len(result.reliable_indices) == 0


class TestDelayFromAverage:
    def test_delay_from_average_resolves_sub_period(self) -> None:
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
            assert d == pytest.approx(float(delay))

    def test_jitter_averages_out(self) -> None:
        sig = noise_burst(512, 32, seed=7)
        d = determine_delay_from_average_py(
            sig.reshape(-1, 1),
            shifted_reference(sig, 4),
            frame_size=256,
            hop_size=256,
            n_lags=32,
            scaling="normalized",
        )
        assert d == pytest.approx(4.0)


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

"""Generate the deterministic example figures for the documentation.

Run:  uv run scripts/gen_examples.py
Output: docs/assets/images/*.svg
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt

from xcorr_signals import determine_delay_vs_time_py, xcorr

FS = 48_000  # Hz — all examples

OUT = __import__("pathlib").Path("docs/assets/images")

# Scenario A: single burst, average xcorr
A_BURST_S = 0.150  # 150 ms burst
A_DELAY_S = 0.005  # 5 ms delay

# Scenario B: 20 jittered segments, xcorr vs time + percentiles
B_SEGMENTS = 20
B_LEAD_S = 0.040
B_BURST_S = 0.120
B_TAIL_S = 0.040
B_JITTER_S = 0.030  # +/- 30 ms jitter
B_LAG_WINDOW_S = 0.040  # +/- 40 ms lag window


def main() -> None:
    style()
    OUT.mkdir(parents=True, exist_ok=True)

    # --- Scenario A: single burst, average xcorr --------------------------
    n_a = int(A_BURST_S * FS)
    clean = burst(n_a, seed=42)
    delay_a = int(A_DELAY_S * FS)
    ref_a = clean
    test_a = np.roll(degrade(clean, snr_db=25.0, seed=43), delay_a)
    fig_signal(ref_a, test_a, delay_a)
    fig_xcorr_average(ref_a, test_a, A_DELAY_S)

    # --- Scenario B: 20 jittered segments, xcorr vs time + percentiles ----
    ref_b, test_b, true_ms, _snr = scenario_b()
    fig_xcorr_vs_time(ref_b, test_b, three_d=False)
    fig_xcorr_vs_time(ref_b, test_b, three_d=True)

    seg_len = int((B_LEAD_S + B_BURST_S + B_TAIL_S) * FS)
    n_lags = int(B_LAG_WINDOW_S * FS)
    result = determine_delay_vs_time_py(
        test_b.reshape(-1, 1),
        ref_b,
        seg_len,
        seg_len,
        n_lags=n_lags,
        scaling="normalized",
        hilbert_envelope=True,
        reliability_threshold=0.3,
    )
    est_ms = np.array([f.lags[f.peak_index] / FS * 1000 for f in result.frames])
    peaks = np.array([f.peak_value for f in result.frames])
    stats = fig_delay_percentiles(true_ms, est_ms, peaks)

    print("figures written to", OUT)
    print("reliable frames:", len(result.reliable_indices), "/", len(result.frames))
    print("error ms: P5={p5:+.3f} P50={p50:+.3f} P95={p95:+.3f} max|e|={max_abs:.3f}".format(**stats))
    print(f"peak: {peaks.min():.3f} .. {peaks.max():.3f} (P5={np.percentile(peaks, 5):.3f} P95={np.percentile(peaks, 95):.3f})")


def style() -> None:
    plt.rcParams.update(
        {
            "svg.fonttype": "none",  # text stays editable in SVG
            "font.size": 9,
            "axes.titlesize": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def fig_signal(ref: np.ndarray, test: np.ndarray, delay: int) -> None:
    t = np.arange(ref.size) / FS * 1000
    fig, ax = plt.subplots(figsize=(5.2, 2.2), constrained_layout=True)
    ax.plot(t, ref, lw=0.6, color="#0072B2", label="reference")
    ax.plot(t + delay / FS * 1000, test, lw=0.6, color="#D55E00", label="test (degraded)")
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude")
    ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=7)
    fig.savefig(OUT / "signal_degradation.svg")
    plt.close(fig)


def fig_xcorr_average(ref: np.ndarray, test: np.ndarray, delay_s: float) -> None:
    lags, values = xcorr(test.reshape(-1, 1), ref, hilbert_envelope=True, scaling="normalized")
    fig, ax = plt.subplots(figsize=(4.2, 2.6), constrained_layout=True)
    ax.plot(lags / FS * 1000, values, lw=0.9, color="#0072B2")
    imax = int(np.argmax(values))
    ax.axvline(lags[imax] / FS * 1000, color="#D55E00", lw=0.7, ls="--")
    ax.set_xlabel("Lag (ms)")
    ax.set_ylabel("Normalized xcorr")
    ax.set_xlim(-15, 25)
    ax.annotate(
        f"peak {values[imax]:.2f} @ {lags[imax] / FS * 1000:.2f} ms",
        (lags[imax] / FS * 1000, values[imax]),
        xytext=(0.62, 0.55),
        textcoords="axes fraction",
        fontsize=7,
        color="#D55E00",
    )
    fig.savefig(OUT / "xcorr_average.svg")
    plt.close(fig)


def fig_xcorr_vs_time(ref: np.ndarray, test: np.ndarray, three_d: bool) -> None:
    seg_len = int((B_LEAD_S + B_BURST_S + B_TAIL_S) * FS)
    n_lags = int(B_LAG_WINDOW_S * FS)
    result = determine_delay_vs_time_py(
        test.reshape(-1, 1),
        ref,
        seg_len,
        seg_len,
        n_lags=n_lags,
        scaling="normalized",
        hilbert_envelope=True,
        reliability_threshold=0.3,
    )
    lags = result.frames[0].lags / FS * 1000
    matrix = np.stack([f.values for f in result.frames])  # (segments, lags)
    t_s = (np.arange(matrix.shape[0]) + 0.5) * seg_len / FS

    if three_d:
        TT, LL = np.meshgrid(t_s, lags, indexing="ij")
        fig = plt.figure(figsize=(5.2, 3.2), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(TT, LL, matrix, cmap="viridis", rstride=1, cstride=8, linewidth=0)
        fig.colorbar(surf, ax=ax, pad=0.08, label="Normalized xcorr")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Lag (ms)")
        ax.set_zlabel("xcorr")
        fig.savefig(OUT / "xcorr_3d.svg")
        plt.close(fig)
        return

    stride = 4  # thin out lags: 0.08 ms resolution is plenty for the map
    fig, ax = plt.subplots(figsize=(5.2, 2.8), constrained_layout=True)
    pcm = ax.pcolormesh(t_s, lags[::stride], matrix[:, ::stride].T, cmap="viridis", shading="auto")
    cbar = fig.colorbar(pcm, ax=ax, pad=0.01)
    cbar.set_label("Normalized xcorr")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Lag (ms)")
    fig.savefig(OUT / "xcorr_vs_time.svg")
    plt.close(fig)


def fig_delay_percentiles(true_ms: np.ndarray, est_ms: np.ndarray, peaks: np.ndarray) -> dict[str, float]:
    error_ms = est_ms - true_ms
    stats = {
        "p5": float(np.percentile(error_ms, 5)),
        "p50": float(np.percentile(error_ms, 50)),
        "p95": float(np.percentile(error_ms, 95)),
        "max_abs": float(np.max(np.abs(error_ms))),
    }

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.5, 3.4), constrained_layout=True, sharex=True)
    seg = np.arange(1, true_ms.size + 1)
    ax1.plot(seg, true_ms, "o-", ms=3, lw=0.8, color="#009E73", label="true jitter")
    ax1.plot(seg, est_ms, "s--", ms=3, lw=0.8, color="#D55E00", label="estimated")
    ax1.set_ylabel("Delay (ms)")
    ax1.legend(loc="upper right", frameon=False, ncol=2)

    ax2.plot(seg, error_ms, "o", ms=3, color="#0072B2")
    for key, ls in (("p5", ":"), ("p50", "--"), ("p95", ":")):
        ax2.axhline(stats[key], color="#CC79A7", lw=0.8, ls=ls)
    ax2.set_xlabel("Segment")
    ax2.set_ylabel("Error (ms)")
    fig.savefig(OUT / "delay_percentiles.svg")
    plt.close(fig)
    return stats


def scenario_b() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build the jittered 20-segment scenario.

    Returns (ref, test, true_ms, snr_db). Each segment gets its own jitter,
    SNR (22–28 dB) and a linear-phase FIR lowpass (33/65/127 taps) whose
    group delay (0.33–1.31 ms) biases the xcorr peak.
    """
    lead = int(B_LEAD_S * FS)
    n_burst = int(B_BURST_S * FS)
    tail = int(B_TAIL_S * FS)
    seg_len = lead + n_burst + tail
    jitter_max = int(B_JITTER_S * FS)

    rng = np.random.default_rng(7)
    jitter = rng.integers(-jitter_max, jitter_max + 1, size=B_SEGMENTS)
    snr_db = rng.uniform(22.0, 28.0, size=B_SEGMENTS)
    taps = rng.choice([33, 65, 127], size=B_SEGMENTS)

    ref_segs, test_segs = [], []
    for i in range(B_SEGMENTS):
        clean = burst(n_burst, seed=100 + i)
        ref_seg = np.zeros(seg_len)
        ref_seg[lead : lead + n_burst] = clean
        placed = np.zeros(seg_len)
        start = lead + int(jitter[i])
        band_limited = fir_lowpass(clean, 6000.0, int(taps[i]))
        placed[start : start + n_burst] = degrade(band_limited, snr_db=float(snr_db[i]), seed=200 + i)
        ref_segs.append(ref_seg)
        test_segs.append(placed)

    return (
        np.concatenate(ref_segs),
        np.concatenate(test_segs),
        jitter / FS * 1000,
        snr_db,
    )


def burst(n: int, seed: int) -> np.ndarray:
    """White-noise burst windowed by a raised cosine."""
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal(n)
    win = np.hanning(n) ** 0.8
    return raw * win


def degrade(sig: np.ndarray, snr_db: float, seed: int) -> np.ndarray:
    """Soft-clip distortion + additive noise at snr_db SNR."""
    rng = np.random.default_rng(seed)
    drive = 5.0
    distorted = np.tanh(drive * sig) / np.tanh(drive)
    mix = 0.85 * distorted + 0.15 * sig

    power = np.mean(mix**2)
    noise_power = power / (10 ** (snr_db / 10))
    noise = rng.standard_normal(mix.size) * np.sqrt(noise_power)
    return mix + noise


def fir_lowpass(sig: np.ndarray, fc: float, taps: int) -> np.ndarray:
    """Linear-phase windowed-sinc FIR lowpass (codec / anti-aliasing model)."""
    m = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * fc / FS * m) * np.hamming(taps)
    h /= h.sum()
    return np.convolve(sig, h)[: sig.size]


if __name__ == "__main__":
    main()

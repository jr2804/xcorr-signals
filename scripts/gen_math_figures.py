"""Generate math-primer figures for the documentation, using xy.

Run:  uv run scripts/gen_math_figures.py
Output: docs/assets/images/math_*.svg

Figures use a light-grey figure background so they stay readable on the
dark-mode documentation theme.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from matplotlib import pyplot as plt

from xcorr_signals import xcorr

FS = 48_000  # Hz — all examples

OUT = Path("docs/assets/images")

# Colorblind-safe palette (Tol bright), consistent with gen_examples.py
BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
GREY = "#999999"

# Light-grey canvas so SVGs don't glare on dark-mode backgrounds
BG = "#EAEAEA"
FG = "#222222"


def style() -> None:
    plt.rcParams.update(
        {
            "svg.fonttype": "none",  # text stays editable in SVG
            "font.size": 9,
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "axes.edgecolor": FG,
            "axes.labelcolor": FG,
            "xtick.color": FG,
            "ytick.color": FG,
            "text.color": FG,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _frame(ax: Any, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(colors=FG)


def main() -> None:
    style()
    OUT.mkdir(parents=True, exist_ok=True)
    _fig_definition()
    _fig_conv_vs_corr()
    _fig_hilbert()
    _fig_ccfht()
    _fig_scaling()
    print(f"figures written to {OUT}")


# --------------------------------------------------------------------------
# 1. Sliding dot product: x shifted over y, shaded overlap, xcorr below
# --------------------------------------------------------------------------
def _fig_definition() -> None:
    rng = np.random.default_rng(7)
    n = 300
    x = np.zeros(n)
    burst = rng.standard_normal(80) * 0.8
    x[40:120] = burst
    y = x.copy()

    # full xcorr for the noisy burst pair
    y_noisy = y + rng.standard_normal(n) * 0.15
    x_noisy = x + rng.standard_normal(n) * 0.15
    lags, corr = xcorr(x_noisy.reshape(-1, 1), y_noisy, hilbert_envelope=False, scaling="normalized")

    fig = plt.figure(figsize=(7.0, 4.0))
    fig.set_facecolor(BG)
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], wspace=0.22, hspace=0.35,
                          left=0.07, right=0.98, top=0.92, bottom=0.08)

    shift_vals = [-30, 0, 60]
    axs_top = [fig.add_subplot(gs[0, i]) for i in range(3)]
    for ax, s in zip(axs_top, shift_vals, strict=True):
        ax.plot(x, color=BLUE, lw=1.0, label="x")
        ys = np.full(n, np.nan)
        if s >= 0:
            ys[s:] = y[:-s] if s else y
            ov_start, ov_end = s, n
        else:
            ys[:n + s] = y[-s:]
            ov_start, ov_end = 0, n + s
        ax.plot(ys, color=ORANGE, lw=1.0, label="y shifted")
        ax.axvline(s, color=GREY, lw=0.6, ls=":")
        ax.fill_between(np.arange(ov_start, ov_end), -2.8, 2.8, color=GREY, alpha=0.12)
        ax.set_xlim(0, n)
        ax.set_ylim(-2.8, 2.8)
        ax.set_xticks([0, 100, 200, 300])
        ax.set_title(f"$\tau$ = {s} samples", fontsize=8)
        _frame(ax, "$k$ (samples)", "amplitude")
        if s == shift_vals[0]:
            ax.legend(frameon=False, loc="upper right", fontsize=7)
        plt.setp(ax.get_yticklabels(), fontsize=7)

    ax_bot = fig.add_subplot(gs[1, :])
    ax_bot.plot(lags, corr, color=BLUE, lw=1.0, label="xcorr")
    for s in shift_vals:
        idx = int(np.argmin(np.abs(lags - s)))
        ax_bot.plot(lags[idx], corr[idx], "o", color=ORANGE, ms=4)
    ax_bot.axvline(0, color=GREY, lw=0.6, ls=":")
    ax_bot.set_xlim(-150, 150)
    _frame(ax_bot, "lag $\tau$ (samples)", "correlation")
    ax_bot.legend(frameon=False, fontsize=7)
    ax_bot.set_title("Sum of overlapping products = cross-correlation", fontsize=8)
    fig.savefig(OUT / "math_sliding_dot.svg", facecolor=BG)
    plt.close(fig)


def _fig_conv_vs_corr() -> None:
    n = 200
    k = np.arange(n)
    x = np.zeros(n)
    x[30:90] = np.sin(2 * np.pi * 3 * np.arange(60) / 60)  # short burst
    h = np.zeros(n)
    h[70:100] = 0.8  # delayed rectangular "channel impulse response"

    # convolution = x * h : flip h, slide; correlation = x corr h : slide, no flip
    xc = np.correlate(x, h, mode="full")
    cv = np.convolve(x, h, mode="full")
    lags_full = np.arange(-n + 1, n)

    fig, axes = plt.subplots(1, 3, figsize=(8.2, 2.3), constrained_layout=True)
    fig.set_facecolor(BG)
    ax = axes[0]
    ax.plot(k, x, color=BLUE, lw=1.0, label="x")
    ax.plot(k, h, color=ORANGE, lw=1.0, label="h")
    ax.set_title("signals", fontsize=8)
    _frame(ax, "$k$ (samples)", "amplitude")
    ax.legend(frameon=False, fontsize=7)
    ax = axes[1]
    ax.plot(lags_full, cv, color=PURPLE, lw=1.1)
    ax.axvline(0, color=GREY, lw=0.6, ls=":")
    ax.set_title("convolution x*h (flipped h)", fontsize=8)
    _frame(ax, "lag (samples)", "x*h")
    ax = axes[2]
    ax.plot(lags_full, xc, color=GREEN, lw=1.1)
    ax.axvline(0, color=GREY, lw=0.6, ls=":")
    ax.set_title("cross-correlation (no flip)", fontsize=8)
    _frame(ax, "lag (samples)", "x⋆h")
    fig.savefig(OUT / "math_conv_vs_corr.svg", facecolor=BG)
    plt.close(fig)


# --------------------------------------------------------------------------
# 3. Hilbert transform: 90-degree phase shift and envelope
# --------------------------------------------------------------------------
def _fig_hilbert() -> None:
    n = 400
    t = np.arange(n) / FS
    f0 = 400.0
    x = np.sin(2 * np.pi * f0 * t) * np.exp(-((t - 0.004) ** 2) / (2 * 5e-4))
    h = np.fft.ifft(-1j * np.sign(np.fft.fftfreq(n, 1 / FS) + 1e-300) * np.fft.fft(x)).real
    env = np.abs(x + 1j * h)

    fig, ax = plt.subplots(figsize=(6.8, 2.4), constrained_layout=True)
    fig.set_facecolor(BG)
    ax.plot(t * 1000, x, color=BLUE, lw=1.0, label="x(t)")
    ax.plot(t * 1000, h, color=ORANGE, lw=1.0, label="H[x(t)] (90° shift)")
    ax.plot(t * 1000, env, color=GREEN, lw=1.2, label="envelope |x + jH[x]|")
    ax.axhline(0, color=GREY, lw=0.6)
    _frame(ax, "time (ms)", "amplitude")
    ax.legend(frameon=False, loc="upper right", fontsize=7)
    fig.savefig(OUT / "math_hilbert.svg", facecolor=BG)
    plt.close(fig)


# --------------------------------------------------------------------------
# 4. CCF vs CCFHT: zero-crossing of Hilbert-transformed CCF (Hanus 2019)
# --------------------------------------------------------------------------
def _fig_ccfht() -> None:
    n = 1024
    tau0 = 120
    rng = np.random.default_rng(11)
    x = np.zeros(n)
    x[100:180] = rng.standard_normal(80) * 0.8
    x[250:350] = rng.standard_normal(100) * 0.8
    y = np.zeros(n)
    y[tau0 : tau0 + n] = x[: n - tau0]  # y is x delayed by tau0

    # slight noise so the peak is not perfect
    xn = x + 0.05 * rng.standard_normal(n)
    yn = y + 0.05 * rng.standard_normal(n)

    lags, ccf = xcorr(xn.reshape(-1, 1), yn, hilbert_envelope=False, scaling="normalized")
    ccfht = np.fft.ifft(-1j * np.sign(np.fft.fftfreq(ccf.size, 1.0) + 1e-300) * np.fft.fft(ccf)).real

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 3.6), sharex=True)
    fig.set_facecolor(BG)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.10, hspace=0.45)

    peak = lags[int(np.argmax(ccf))]
    ax = axes[0]
    ax.plot(lags, ccf, color=BLUE, lw=1.0)
    ax.axvline(peak, color=ORANGE, lw=0.8, ls="--")
    ax.annotate(
        f"peak at $\\tau_0$={peak}",
        xy=(peak, ccf.max()),
        xytext=(peak + 260, ccf.max() - 0.25),
        fontsize=7,
        color=FG,
        arrowprops={"arrowstyle": "->", "color": FG, "lw": 0.8},
    )
    ax.set_title("CCF (cross-correlation function)", fontsize=8)
    _frame(ax, "", "CCF(τ)")

    # find zero-crossing closest to peak
    sign_changes = np.where(np.diff(np.sign(ccfht)))[0]
    zc_lags = lags[sign_changes]
    zc = zc_lags[np.argmin(np.abs(zc_lags - peak))]
    ax = axes[1]
    ax.plot(lags, ccfht, color=GREEN, lw=1.0)
    ax.axvline(zc, color=ORANGE, lw=0.8, ls="--")
    ax.axhline(0, color=GREY, lw=0.6)
    ax.annotate(
        f"zero crossing at $\\tau_0$={zc}",
        xy=(zc, 0),
        xytext=(zc - 420, 0.5),
        fontsize=7,
        color=FG,
        arrowprops={"arrowstyle": "->", "color": FG, "lw": 0.8},
    )
    ax.set_title("CCFHT (Hilbert transform of CCF) — zero crossing", fontsize=8)
    _frame(ax, "lag (samples)", "H[CCF](τ)")

    fig.savefig(OUT / "math_ccfht.svg", facecolor=BG)
    plt.close(fig)


# --------------------------------------------------------------------------
# 5. Scaling options compared (MATLAB/elephant-compatible)
# --------------------------------------------------------------------------
def _fig_scaling() -> None:
    rng = np.random.default_rng(13)
    n = 512
    tau0 = 120
    x = rng.standard_normal(n)
    y = np.zeros(n)
    y[: n - tau0] = x[tau0:]
    y += 0.2 * rng.standard_normal(n)

    fig, axes = plt.subplots(2, 2, figsize=(7.0, 3.6), constrained_layout=True)
    fig.set_facecolor(BG)
    cases = [
        ("none", "raw"),
        ("biased", "R/N"),
        ("unbiased", "R/(N−|τ|)"),
        ("normalized", "R/√(Σx²Σy²)"),
    ]
    for (name, label), ax in zip(cases, axes.ravel(), strict=True):
        lags, v = xcorr(x.reshape(-1, 1), y, hilbert_envelope=False, scaling=name)
        lags_ms = lags / FS * 1000
        ax.plot(lags_ms, v, color=BLUE, lw=1.0)
        ax.axvline(tau0 / FS * 1000, color=ORANGE, lw=0.7, ls="--")
        ax.set_title(f"'{name}'  =  {label}", fontsize=8)
        _frame(ax, "lag (ms)", "value")
        ma = float(np.max(np.abs(v)))
        ax.set_ylim(-1.2 * ma, 1.2 * ma)
    fig.savefig(OUT / "math_scaling.svg", facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    main()

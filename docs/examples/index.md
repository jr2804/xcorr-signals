---
title: Examples
---

All examples run at $f_s = 48\;\mathrm{kHz}$ on deterministic noise bursts.
The test signals are degraded — soft-clip distortion plus noise at
22–28 dB SNR, and per-segment linear-phase FIR filtering — so correlation
peaks stay clearly below 100 %, as with real recordings. Regenerate every
figure with `uv run scripts/gen_examples.py`.

## Signal degradation

The test burst (orange) is soft-clipped, band-limited, and noisy compared to
the clean reference (blue):

![Reference burst vs degraded, delayed test burst](../assets/images/signal_degradation.svg)

## Average xcorr

Mode 2 on a single degraded burst delayed by 5 ms: the normalized
**Hilbert-envelope** correlation peaks at 87 % — below 100 % because part of
the signal energy is distortion and noise. Using the envelope instead of
the raw CCF removes ringing side-lobes and produces a single clean peak that
is easier to locate:

![Average cross-correlation with Hilbert envelope and peak marker](../assets/images/xcorr_average.svg)

## XCorr vs time

Mode 1 over 20 segments of 200 ms, one burst each. The delay follows a
**sawtooth drift** — a linear ramp from $-25\;\mathrm{ms}$ to
$+25\;\mathrm{ms}$ across segments (a clock-drift model) plus $\pm 2\;\mathrm{ms}$
residual jitter — so the correlation ridge sweeps diagonally while peak
heights vary with the per-segment SNR and FIR filtering. The **Hilbert
envelope** keeps the ridge sharp:

![XCorr heatmap over time and lag (Hilbert envelope)](../assets/images/xcorr_vs_time.svg)

The same data as a 3D surface:

![3D surface of xcorr over time and lag (Hilbert envelope)](../assets/images/xcorr_3d.svg)

## Percentile analysis

All 20 frames pass a 0.3 reliability threshold. For **delay
compensation** the goal is a single robust delay for the whole signal pair —
not the per-segment values. The delay-vs-time estimates are therefore
analysed statistically: percentiles quantify the spread of the estimated
delays, and the median (P50) is the robust compensation delay. It absorbs
both the drift and the small FIR group-delay bias ($0.33$–$1.31\;\mathrm{ms}$);
what remains is residual error:

| Statistic | Value |
| --------- | ----- |
| P5 | $-20.81$ ms |
| P50 (compensation delay) | $+0.31$ ms |
| P95 | $+22.21$ ms |
| max \|error\| of P50 | $1.31$ ms |

![Delay vs time and histogram of estimated delays with percentiles](../assets/images/delay_percentiles.svg)

The drift itself is recovered exactly; the residual is the filter group
delay — visible only because the noise-burst signals resolve single-sample
peaks.

## Reproduce

The generator lives in `scripts/gen_examples.py`; figures are committed
under `docs/assets/images/` and rebuilt only on demand. Common constants:

```python
FS = 48_000          # sampling rate for all examples
B_SEGMENTS = 20      # delay-vs-time scenario: 20 segments
B_JITTER_S = 0.030   # ... jittered by +/- 30 ms
B_BURST_S = 0.120    # 120 ms noise burst per segment
```

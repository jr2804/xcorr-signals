# ADR 0003 — Real Hilbert Envelope via realfft

**Date**: 2026-09-01
**Status**: Accepted

## Context

The reference implementation applies `np.abs(scipy.signal.hilbert(xcorr))`
as the envelope for oscillatory signals. The initial Rust port used `abs()`
as a placeholder, which is not an envelope: it is non-smooth and loses the
analytic-signal magnitude.

## Decision

`hilbert_env` computes the true analytic-signal magnitude
$\sqrt{x^2 + H(x)^2}$ with `realfft`: R2C transform, Hilbert spectrum
$-j \cdot \operatorname{sgn}(k) \cdot X[k]$, C2R back to $H(x)$.
`realfft`'s C2R is unnormalized, so the transform is divided by $N$.

## Consequences

- Envelope matches the scipy reference; exact unity envelope for periodic
  cosine probes (verified to 1e-9 in unit tests).
- `realfft` (already the skill-recommended real-input FFT crate) handles
  real transforms; ~2× faster than complex FFT for this step.
- The unnormalized-C2R gotcha is load-bearing; documented in HISTORY.md and
  the docstring to prevent regression.
- An extra FFT pair per channel when the envelope is enabled.

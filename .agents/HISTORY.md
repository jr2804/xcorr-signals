# AGENTS.md — HISTORY

Recorded decisions with git references. Read when relevant to current task.
Acts as simple long-term memory for the project.

## Format

| Date       | Decision   | Rationale   | Git ref          |
| ---------- | ---------- | ----------- | ---------------- |
| 2026-08-31 | Rust core as single cdylib crate at `src/xcorr_signals/` (g191-filter pattern), maturin build backend | Python package is primary artifact; Rust only accelerates xcorr DSP. Mirrors validated rust-pyo3-bindings skill architecture | (uncommitted) |
| 2026-08-31 | FFT xcorr uses circular-correlation lag remap (lag k at index k, lag -k at L-k) | Initial linear-layout extraction misplaced peaks; remap is correct for IFFT-based correlation | (uncommitted) |
| 2026-08-31 | Hilbert envelope: real Hilbert transform via realfft (H(x) = C2R(-j*sgn(k)*X[k]), env = sqrt(x²+H²)) replaces abs() approximation | abs() is not an envelope; realfft is the skill-recommended real-input FFT crate. Note: realfft C2R is unnormalized, divide by N | (uncommitted) |
| 2026-08-31 | xcorr test signals: noise bursts with lead/tail silence (not sine tones) | Periodic tones autocorrelate at every period — ambiguous peaks; noise bursts have one unambiguous peak, resolve 1-sample delays. Sine/cosine only kept for exact Hilbert-envelope math tests | (uncommitted) |
| 2026-08-31 | float32 audio accepted at binding boundary → converted to f64; single f64 core, f64 output | Generic f32/f64 core (ndarray+rustfft+realfft generics) not worth the churn; f64 accumulation is numerically more robust for correlation. Native f32 path possible later via num-traits generics if perf demands | (uncommitted) |

## Guidance

- Record decisions that would be costly to rediscover.
- Note false turns and why they were rejected.
- Link to relevant commits.
- Keep entries brief — enough to reconstruct reasoning.
- When this file grows too large, archive older entries to
  `.agents/history/` and leave a pointer here.

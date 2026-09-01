# ADR 0002 — Float32 Input, f64 Computation

**Date**: 2026-09-01
**Status**: Accepted

## Context

Audio is commonly stored as float32. The Rust core works on `f64`; float32
input must be supported without duplicating the DSP code. A fully generic
core (`num-traits::Float` through ndarray, rustfft, and realfft signatures)
was evaluated and rejected as not worth the churn.

## Decision

The PyO3 binding layer accepts float32 and float64 NumPy arrays (mixed
dtypes allowed between signal and reference) and converts to `f64` once at
the boundary. The core stays `f64`-only; all outputs are `float64`.

## Consequences

- Single DSP implementation — no generic code paths to test in parallel.
- f64 accumulation is numerically more robust for FFT-based correlation than
  float32 accumulation.
- One temporary f64 copy of float32 input (memory 2× input size).
- A native f32 core remains the upgrade path if throughput or memory demands
  it (recorded in HISTORY.md).

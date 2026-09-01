# ADR 0001 — Rust Core with PyO3 Bindings

**Date**: 2026-09-01
**Status**: Accepted

## Context

Cross-correlation of long audio signals is FFT-bound and too slow in pure
NumPy for interactive delay analysis on long recordings. The project brief
requires a Rust implementation.

## Decision

Single Rust crate (`xcorr_signals_core`) compiled as a `cdylib` extension
module `xcorr_signals._native`, exposed through PyO3/maturin. Python stays
the primary artifact: the package installs via pip, the CLI is Typer, and
all public types are NumPy arrays. Layout follows the single-crate default:
`xcorr.rs` holds the pure DSP, `pyo3_bindings.rs` is a thin adapter.

## Consequences

- One language for all per-sample math; predictable performance.
- Core testable without Python (`cargo test`); bindings stay thin.
- Contributors need a Rust toolchain (mise provides it); a second build
  system (Cargo) sits next to uv.
- Versioning: Cargo.toml keeps `version = "0.0.0"`; the release workflow
  rewrites it so the wheel matches the sdist produced by
  uv-dynamic-versioning.

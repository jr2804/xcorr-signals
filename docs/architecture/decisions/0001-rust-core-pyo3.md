# ADR 0001 — Rust Core with PyO3 Bindings

**Date**: 2026-09-01
**Status**: Accepted

## Context

Cross-correlation of long audio signals is FFT-bound and too slow in pure
NumPy for interactive delay analysis on long recordings. The project brief
requires a Rust implementation.

## Decision

Single Rust crate (`xcorr_signals_core`) compiled as a `cdylib` extension
module `xcorr_signals.xcorr_signals`, exposed through PyO3/maturin. Python stays
the primary artifact: the package installs via pip, the CLI is Typer, and
all public types are NumPy arrays. Layout follows the single-crate default:
`xcorr.rs` holds the pure DSP, `pyo3_bindings.rs` is a thin adapter.

## Consequences

- One language for all per-sample math; predictable performance.
- Core testable without Python (`cargo test`); bindings stay thin.
- Contributors need a Rust toolchain (mise provides it); a second build
  system (Cargo) sits next to uv.
- Versioning: Cargo.toml holds the release version; `release.yml` stamps it
  from the CalVer tag before `uv build` so the wheel matches the tagged
  source.

**Amendment (2026-11-27)**: the crate also emits an `rlib`, and the PyO3
bindings sit behind the `python` feature. Consumers using
`default-features = false` therefore get the pure-Rust core without a Python
dependency (GitHub issue #6).

**Amendment (2026-11-27)**: PyO3 is built with `abi3-py313`, so one
`cp313-abi3` wheel serves CPython 3.13 and newer. `release.yml` publishes
that wheel and the sdist to PyPI with Trusted Publishing on every `main`
push, unless the HEAD commit contains `[skip release]`.

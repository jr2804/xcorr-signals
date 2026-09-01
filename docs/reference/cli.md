---
title: CLI Reference
---

Entry point `xcorr-signals` (`xcorr_signals.cli.app:main`). Global option
`--version` / `-v` prints the package version.

## Commands

| Command | Purpose | Status |
| ------- | ------- | ------ |
| `default` | Welcome message | Implemented |
| `xcorr-cmd` | Cross-correlation of two signals | Stub |
| `delay-vs-time` | Mode 1: per-frame delays with reliability filtering | Stub |
| `delay-from-average` | Mode 2: single delay from averaged xcorr peak | Stub |

Stub commands parse their arguments and print the intended computation; WAV
I/O and core wiring are pending (see the Python API for working equivalents).

## Options

Options shared by the analysis commands:

| Option | Short | Type | Description |
| ------ | ----- | ---- | ----------- |
| `--input-file` | | path | Input WAV file (positional argument) |
| `--frame-size` | `-f` | int ≥ 1 | Frame size in samples |
| `--hop-size` | `-H` | int ≥ 1 | Hop size in samples |
| `--n-lags` | `-n` | int | Lag search window (± n_lags) |
| `--scaling` | `-s` | enum | `normalized`, `coeff`, `biased`, `unbiased`, `none` |
| `--reliability-threshold` | `-r` | float | Minimum peak for reliable frames |
| `--output-file` | `-o` | path | Output path; honors `XCORR_SIGNALS_OUTPUT_FILE` |

`--help` on any command prints the effective argument list.

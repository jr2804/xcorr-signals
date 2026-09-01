---
title: CLI Reference
---

Entry point `xcorr-signals` (`xcorr_signals.cli.app:cli`). Global option
`--version` / `-v` prints the package version.

The CLI covers the pipeline
**cross-correlation → estimate delay → compensate delay**:

| Command | Pipeline step | Output |
| ------- | ------------- | ------ |
| `xcorr` | 1. Cross-correlation lags/values | CSV per (lag, value, channel pair) |
| `delay-vs-time` | 2a. Per-frame delay estimates | CSV per (time, delay, peak, reliability) |
| `delay-from-average` | 2b. Single delay from averaged peak | CSV per (delay, channel pair) |
| `compensate-delay` | 3. Zero-pad test + reference to align | 2 WAV files + delay summary |

## Channel pairing

Every analysis command takes a test WAV (x) and a reference WAV (y) and
applies the pairing rule of `xcorr_signals.channels.channel_pairs`
(1-indexed channels):

- 1 test channel + 1 reference channel → single pair `(1, 1)`
- N test channels + 1 reference channel → all combinations
  `(1, 1), (2, 1), ..., (N, 1)`
- M test channels + M reference channels → pairwise `(1, 1), (2, 2), ...`
- any other channel count → error

## Commands

### `xcorr`

```bash
xcorr-signals xcorr TEST.wav REFERENCE.wav [-s scaling] [--hilbert-envelope] [-n LAGS] [-o OUT.csv]
```

Cross-correlation per channel pair. CSV columns:
`lag, value, test_channel, reference_channel`.

### `delay-vs-time`

```bash
xcorr-signals delay-vs-time TEST.wav REFERENCE.wav [-f FRAME] [-H HOP] [--hilbert-envelope] [-n LAGS] [-s scaling] [-r THRESHOLD] [-o OUT.csv]
```

Per-frame delay estimates (Mode 1). CSV columns:
`time_seconds, delay, peak, reliable, test_channel, reference_channel`.

### `delay-from-average`

```bash
xcorr-signals delay-from-average TEST.wav REFERENCE.wav [-f FRAME] [-H HOP] [--hilbert-envelope] [-n LAGS] [-s scaling] [-o OUT.csv]
```

Single delay from the averaged xcorr peak (Mode 2). CSV columns:
`delay, test_channel, reference_channel`.

### `compensate-delay`

```bash
xcorr-signals compensate-delay TEST.wav REFERENCE.wav [-d MAX_DELAY] [-n LAGS] [-s scaling] [-o PREFIX]
```

Estimates the delay from the strongest xcorr peak across all channel
pairs, then zero-pads test and reference so the pair is time-aligned
(mirrors `_compensate_signals` in the SQA preprocessor). Writes
`PREFIX_test_compensated.wav` and `PREFIX_reference_compensated.wav`
(default prefix: test file without extension) and prints the applied
delay.

## Options

| Option | Short | Type | Description |
| ------ | ----- | ---- | ----------- |
| `test_file` | | path | Test signal WAV (x), positional |
| `reference_file` | | path | Reference signal WAV (y), positional |
| `--frame-size` | `-f` | int ≥ 1 | Frame size in samples |
| `--hop-size` | `-H` | int ≥ 1 | Hop size in samples |
| `--n-lags` | `-n` | int | Lag search window (± n_lags) |
| `--scaling` | `-s` | enum | `normalized`, `coeff`, `biased`, `unbiased`, `none` |
| `--hilbert-envelope` | | flag | Hilbert envelope of the xcorr |
| `--reliability-threshold` | `-r` | float | Minimum peak for reliable frames |
| `--max-delay` | `-d` | float s | Delay search range for `compensate-delay` |
| `--output-file` | `-o` | path | CSV output; honors `XCORR_SIGNALS_OUTPUT_FILE` |
| `--output-prefix` | `-o` | str | WAV output prefix for `compensate-delay` |

`--help` on any command prints the effective argument list.

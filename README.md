# xcorr-signals

> Fast cross-correlation for estimating and compensating time delay between
> audio signal channels. A Rust DSP core exposed through a Python API and CLI.

<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="#"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776ab?logo=python"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"></a>
  <a href="https://github.com/jr2804/xcorr-signals/actions"><img alt="CI" src="https://github.com/jr2804/xcorr-signals/actions/workflows/ci.yml/badge.svg"></a>
</p>
<!-- markdownlint-enable MD033 -->

---

## What it does

`xcorr-signals` measures the time delay between a test audio signal and a
reference — a common task in acoustics, speech quality assessment, and
multi-channel recording alignment. It supports:

- **Single-delay** estimation (constant delay across the whole recording)
- **Delay-vs-time** tracking (per-frame delay for drifting channels)
- **Delay compensation** (zero-pad both signals to align them)
- **Multi-channel** pairing: 1×1, N×1, or M×M pairwise (1-indexed)

The heavy lifting (FFT cross-correlation, Hilbert envelope, scaling) is done
in Rust via PyO3/NumPy bindings; the Python layer provides a CLI and
NumPy-compatible API.

## Installation

```bash
# From PyPI (recommended)
pip install xcorr-signals

# Or with uv
uv add xcorr-signals

# Or from source
uv sync
uv run maturin develop
```

Requires **Python 3.13+** and a Rust toolchain (for source builds).

## Quick start

### Python API

```python
from xcorr_signals import xcorr, determine_delay_from_average_py
import numpy as np

fs = 48_000
n = fs  # 1 second of audio

# Create a test signal and a delayed reference
reference = np.random.default_rng(42).standard_normal(n)
test = np.zeros(n)
test[240:] = reference[:-240]  # 5 ms delay @ 48 kHz

# Estimate the delay
delay = determine_delay_from_average_py(
    test.reshape(-1, 1), reference,
    frame_size=n, hop_size=n, n_lags=1000, scaling="normalized"
)
print(f"Estimated delay: {delay} samples ({delay/fs*1000:.3f} ms)")
# → Estimated delay: 240 samples (5.000 ms)
```

### CLI

```bash
# Estimate a single delay
xcorr-signals delay-from-average test.wav reference.wav

# Track delay over time (per-frame)
xcorr-signals delay-vs-time test.wav reference.wav -f 4096 -H 2048 -o delays.csv

# Cross-correlation values for every lag
xcorr-signals xcorr test.wav reference.wav -o xcorr.csv

# Compensate (align) both signals
xcorr-signals compensate-delay test.wav reference.wav -o aligned_
# → aligned_test_compensated.wav
# → aligned_reference_compensated.wav
```

All commands accept multi-channel WAV files. Channel pairing rules:

| Channels | Pairing |
|----------|---------|
| 1 test + 1 ref | single pair `(1, 1)` |
| N test + 1 ref | all combinations `(1,1), (2,1), … (N,1)` |
| M test + M ref | pairwise `(1,1), (2,2), … (M,M)` |

## Environment variables

| Variable | Description |
|----------|-------------|
| `XCORR_SIGNALS_OUTPUT_FILE` | Default output file for CSV commands |

## Documentation

- **User guide**: [Delay estimation guide](https://jr2804.github.io/xcorr-signals/guides/delay-estimation/)
- **Concepts**: [Cross-correlation](https://jr2804.github.io/xcorr-signals/concepts/cross-correlation/), [Convolution](https://jr2804.github.io/xcorr-signals/concepts/convolution/), [Hilbert transform](https://jr2804.github.io/xcorr-signals/concepts/hilbert-transform/)
- **API reference**: [Python API](https://jr2804.github.io/xcorr-signals/reference/api/) · [CLI reference](https://jr2804.github.io/xcorr-signals/reference/cli/)
- **Full docs**: [https://jr2804.github.io/xcorr-signals/](https://jr2804.github.io/xcorr-signals/)

## Development

```bash
# Clone and set up
git clone https://github.com/jr2804/xcorr-signals.git
cd xcorr-signals
mise dev          # install deps + Rust toolchain

# Build Rust extension
mise run build-rust

# Run tests + quality checks
mise test         # pytest with coverage
mise lint         # ruff + ty + codespell
mise all          # test + lint + format in one pass

# Documentation
mise docs         # build static site
```

## CI/CD

| Workflow | Triggers | Jobs |
|----------|----------|------|
| **CI** (`ci.yml`) | push, PR to `main` | test matrix (3 OS × 3 Python versions) + lint + docs |
| **Release** (`release.yml`) | CalVer tag push | build platform wheels + sdist, publish to PyPI |

## Contributing

See [Contributing](https://jr2804.github.io/xcorr-signals/contributing/) and
[Code of Conduct](https://jr2804.github.io/xcorr-signals/code_of_conduct/).

## License

MIT — see [LICENSE](LICENSE).

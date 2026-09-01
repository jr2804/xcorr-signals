---
title: Quickstart
---

Install the package with its native Rust core:

```bash
uv add xcorr-signals
```

For development from a checkout, build the extension first, then run the test suite:

```bash
mise run dev          # uv sync --dev (installs maturin)
mise run build-rust   # maturin develop -> builds xcorr_signals._native
mise run test         # pytest with coverage
```

## First delay estimate

Generate a noise burst, degrade a copy, delay it by 5 ms, and recover the delay:

```python
import numpy as np
from xcorr_signals import xcorr

FS = 48_000  # Hz

rng = np.random.default_rng(42)
reference = rng.standard_normal(int(0.15 * FS))          # 150 ms noise burst

# test signal: soft-clip distortion + noise, delayed by 240 samples
delay = int(0.005 * FS)
test = np.roll(reference, delay)
test = 0.85 * np.tanh(5 * test) / np.tanh(5) + 0.02 * rng.standard_normal(test.size)

lags, values = xcorr(
    test.reshape(-1, 1), reference, hilbert_envelope=False, scaling="normalized"
)
print(f"delay = {lags[int(np.argmax(values))] / FS * 1000:.2f} ms")
```

Output:

```text
delay = 5.00 ms
```

`signals` is a `(samples, channels)` array and may be float32 or float64;
results are always float64.

## Command line

The same workflow works from the shell:

```bash
xcorr-signals delay-from-average test.wav reference.wav --frame-size 7200 --hop-size 7200
```

See the [CLI reference](../reference/cli.md) for all commands, and
[Examples](../examples/index.md) for degraded-signal scenarios with figures.

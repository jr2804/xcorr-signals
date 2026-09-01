---
title: Math Primer
---

The xcorr-signals pipeline rests on three classical signal-processing
concepts: **convolution**, **cross-correlation**, and the **Hilbert
transform**. Understanding how they interact makes every CLI flag and API
parameter predictable.

| Concept | What it does in the pipeline |
| ------- | ---------------------------- |
| **Convolution** | Models the acoustic path: $x(k) \rightarrow h(k-k_0) \rightarrow y(k)$.  The delay $k_0$ appears as a shifted impulse in $h$. |
| **Cross-correlation** | Measures similarity of two signals as a function of lag $\tau$.  The peak of the cross-correlation function (CCF) is the estimated delay. |
| **Hilbert transform** | Builds the **envelope** of the CCF (CCFHT), turning a noisy peak-finding problem into a cleaner zero-crossing problem (Hanus 2019). |

## Pages

- [Cross-correlation](cross-correlation.md) — definition, sliding dot product,
  scaling options (including the exact set shared with elephant/MATLAB), and
  FFT-based computation.
- [Convolution](convolution.md) — flip-and-shift, the LTI system model,
  relation to correlation, and why zero-padding matters.
- [Hilbert transform](hilbert-transform.md) — 90° phase shift, analytic signal,
  envelope, and the CCFHT zero-crossing method for time-delay estimation.

## References

- Wikipedia, *Cross-correlation* — [https://en.wikipedia.org/wiki/Cross-correlation](https://en.wikipedia.org/wiki/Cross-correlation)
- Wikipedia, *Convolution* — [https://en.wikipedia.org/wiki/Convolution](https://en.wikipedia.org/wiki/Convolution)
- Wikipedia, *Hilbert transform* — [https://en.wikipedia.org/wiki/Hilbert_transform](https://en.wikipedia.org/wiki/Hilbert_transform)
- Hanus, R. (2019). *Time delay estimation of random signals using cross-correlation with Hilbert Transform*. Measurement, 144, 67–74.
  DOI [10.1016/j.measurement.2019.07.014](https://doi.org/10.1016/j.measurement.2019.07.014)
- NeuralEnsemble/elephant — `cross_correlation_function` docs and source code:
  [elephant.readthedocs.io](https://elephant.readthedocs.io/en/latest/reference/_toctree/signal_processing/elephant.signal_processing.cross_correlation_function.html) and
  [GitHub source](https://github.com/NeuralEnsemble/elephant/blob/master/elephant/signal_processing.py)

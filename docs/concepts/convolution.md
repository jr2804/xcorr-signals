---
title: Convolution
---

Convolution is the mathematical description of a linear time-invariant (LTI)
system. In the audio-delay context it gives the model $x(k) \rightarrow
h(k-k_0) \rightarrow y(k)$, where a delayed copy of the input is produced by
convolving the original with a shifted impulse response $h$.

## Definition

For continuous signals

$$
(x * h)(t) \;=\; \int_{-\infty}^{\infty} x(\tau)\,h(t - \tau)\,d\tau
$$

For discrete sampled signals of length $N$

$$
(x * h)[n] \;=\; \sum_{k=0}^{N-1} x[k]\,h[n - k]
$$

The operation **flips** the second signal ($h$ is time-reversed) and then
slides it past the first signal, computing the area of the overlap at every
position. That flip is the only difference between convolution and
cross-correlation.

## Relation to cross-correlation

Cross-correlation is convolution without the flip:

$$
x \star h \;=\; \overline{x(-t)} * h(t)
$$

In words: *correlate* $x$ with $h$ = *convolve* the time-reversed conjugate of
$x$ with $h$. The peak of the cross-correlation therefore appears at the
negative of the lag that would align the flipped kernel in a convolution.

![Convolution flips the kernel; cross-correlation shifts without flipping](../assets/images/math_conv_vs_corr.svg)

## System model: delay as a shifted impulse

In an ideal acoustic path the output is the input delayed by $k_0$ samples:

$$
y[n] \;=\; x[n - k_0]
$$

This is the convolution of $x$ with a single impulse located at $k_0$:

$$
h[n] \;=\; \delta[n - k_0] \qquad \Rightarrow \qquad y \;=\; x * h
$$

In practice the channel also adds colour (reverberation, filtering), so $h$
becomes a short burst of energy centred on $k_0$. The cross-correlation peak
is still the best single-number estimate of $k_0$.

## FFT computation

Like correlation, convolution is computed efficiently via the FFT:

1. Zero-pad both signals to length $\ge N + M - 1$.
2. FFT both padded arrays.
3. Multiply the spectra point-wise.
4. Inverse-FFT.

The zero-padding prevents circular wrap-around and produces a **linear**
convolution result. `xcorr_signals` uses the same zero-padded FFT engine
for both operations.

## References

- Wikipedia, *Convolution* — [https://en.wikipedia.org/wiki/Convolution](https://en.wikipedia.org/wiki/Convolution)
- Wikipedia, *Cross-correlation* — [https://en.wikipedia.org/wiki/Cross-correlation](https://en.wikipedia.org/wiki/Cross-correlation)

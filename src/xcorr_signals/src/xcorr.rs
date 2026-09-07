// Cross-correlation core: zero-padded FFT correlation, scaling,
// real Hilbert envelope, and delay-estimation modes.
use ndarray::{ArrayView1, ArrayView2};
use realfft::{num_complex::Complex, RealFftPlanner};
use rustfft::FftPlanner;

use pyo3::pyclass;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[pyclass(eq, eq_int, module = "xcorr_signals")]
pub enum XCorrScaling {
    #[pyo3(name = "NORMALIZED")]
    Normalized,
    #[pyo3(name = "COEFF")]
    Coeff,
    #[pyo3(name = "BIASED")]
    Biased,
    #[pyo3(name = "UNBIASED")]
    Unbiased,
    #[pyo3(name = "NONE")]
    None,
}

#[derive(Debug, Clone)]
pub struct XCorrFrame {
    pub lags: Vec<f64>,
    pub values: Vec<f64>,
    pub peak_index: usize,
    pub peak_value: f64,
}

#[derive(Debug, Clone)]
pub struct XCorrResult {
    pub frames: Vec<XCorrFrame>,
    pub reliable_indices: Vec<usize>,
}

#[derive(Debug)]
pub enum XCorrError {
    EmptyInput,
    DimensionMismatch,
    InvalidLags(usize),
    InvalidFrame(usize),
    InvalidScaling(String),
}

impl std::fmt::Display for XCorrError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyInput => write!(f, "input signals must not be empty"),
            Self::DimensionMismatch => write!(f, "signals and reference must have equal length"),
            Self::InvalidLags(n) => write!(f, "n_lags must be a positive integer (got {n})"),
            Self::InvalidFrame(n) => write!(f, "frame_size and hop_size must be >= 1 (got {n})"),
            Self::InvalidScaling(s) => write!(f, "invalid scaling mode: {s}"),
        }
    }
}

fn zscore(x: &mut [f64]) {
    let n = x.len() as f64;
    let mean = x.iter().sum::<f64>() / n;
    let var = x.iter().map(|v| (v - mean) * (v - mean)).sum::<f64>() / n;
    let std = var.sqrt();
    if std < f64::EPSILON {
        x.fill(0.0);
    } else {
        for v in x.iter_mut() {
            *v = (*v - mean) / std;
        }
    }
}

fn hilbert(x: &[f64]) -> Vec<f64> {
    let n = x.len();
    let mut planner = RealFftPlanner::<f64>::new();
    let r2c = planner.plan_fft_forward(n);
    let c2r = planner.plan_fft_inverse(n);
    let mut spectrum = r2c.make_output_vec();
    let mut input = x.to_vec();
    r2c.process(&mut input, &mut spectrum).unwrap();
    for (k, bin) in spectrum.iter_mut().enumerate() {
        let sgn = if k == 0 || 2 * k == n { 0.0 } else { 1.0 };
        *bin *= Complex::new(0.0, -sgn);
    }
    let mut out = c2r.make_output_vec();
    c2r.process(&mut spectrum, &mut out).unwrap();
    let scale = 1.0 / n as f64;
    out.iter().map(|v| v * scale).collect()
}

pub fn hilbert_env(x: &[f64]) -> Vec<f64> {
    let h = hilbert(x);
    x.iter().zip(h).map(|(a, b)| (a * a + b * b).sqrt()).collect()
}

/// Zero-padded FFT cross-correlation: corr[k] = sum_n x[n] * y[n+k].
/// Output is centered: index i corresponds to lag i - tau0, where tau0 = n-1.
/// Length = 2*n - 1.
fn fft_xcorr(x: &[f64], y: &[f64]) -> Vec<f64> {
    let n = x.len();
    let fft_len = (2 * n).next_power_of_two();
    let tau0 = n - 1;
    let mut planner = FftPlanner::new();
    let fft = planner.plan_fft_forward(fft_len);

    let mut fx = vec![Complex::new(0.0, 0.0); fft_len];
    let mut fy = vec![Complex::new(0.0, 0.0); fft_len];
    for (i, v) in x.iter().enumerate() {
        fx[i] = Complex::new(*v, 0.0);
    }
    for (i, v) in y.iter().enumerate() {
        fy[i] = Complex::new(*v, 0.0);
    }
    fft.process(&mut fx);
    fft.process(&mut fy);

    for (a, b) in fx.iter_mut().zip(&fy) {
        *a *= b.conj();
    }

    let ifft = planner.plan_fft_inverse(fft_len);
    ifft.process(&mut fx);
    let scale = 1.0 / fft_len as f64;
    let raw: Vec<f64> = fx.iter().map(|c| c.re * scale).collect();

    // raw[0] = lag 0, raw[1] = lag 1, ..., raw[fft_len-1] = lag -1
    // Center into output: output[tau0 + lag] = raw[lag >= 0 ? lag : fft_len + lag]
    let mut out = vec![0.0f64; 2 * n - 1];
    for k in 0..=tau0 {
        out[tau0 + k] = raw[k];
    }
    for k in 1..=tau0 {
        out[tau0 - k] = raw[fft_len - k];
    }
    out
}

pub fn cross_correlation_function(
    signals: ArrayView2<f64>,
    reference: ArrayView1<f64>,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: XCorrScaling,
    zero_pad: bool,
) -> Result<Vec<XCorrFrame>, XCorrError> {
    let _ = zero_pad;
    let (nbr_samples, nbr_channels) = (signals.nrows(), signals.ncols());
    if nbr_samples == 0 || reference.is_empty() {
        return Err(XCorrError::EmptyInput);
    }
    // Unequal lengths: zero-pad the shorter side to the longer (issue #2).
    let n = nbr_samples.max(reference.len());
    if let Some(k) = n_lags {
        if k == 0 || k > n {
            return Err(XCorrError::InvalidLags(k));
        }
    }

    let xcorr_len = 2 * n - 1;
    let tau0 = n - 1;
    let n_lags = n_lags.unwrap_or(tau0).min(tau0);

    let mut ysig = reference.to_vec();
    ysig.resize(n, 0.0);
    zscore(&mut ysig);

    let mut frames = Vec::with_capacity(nbr_channels);
    for ch in signals.columns() {
        let mut xsig = ch.to_vec();
        xsig.resize(n, 0.0);
        zscore(&mut xsig);

        let mut raw = fft_xcorr(&xsig, &ysig);

        let norm = match scaling {
            XCorrScaling::Biased => Some(vec![nbr_samples as f64; xcorr_len]),
            XCorrScaling::Unbiased => {
                let tau: Vec<f64> = (0..xcorr_len).map(|i| (i as f64) - tau0 as f64).collect();
                Some(tau.iter().map(|t| (nbr_samples as f64) - t.abs()).collect())
            }
            XCorrScaling::Normalized | XCorrScaling::Coeff => {
                let nx = xsig.iter().map(|v| v * v).sum::<f64>();
                let ny = ysig.iter().map(|v| v * v).sum::<f64>();
                Some(vec![(nx * ny).sqrt(); xcorr_len])
            }
            XCorrScaling::None => None,
        };
        if let Some(norm) = norm {
            for (v, d) in raw.iter_mut().zip(norm) {
                if d != 0.0 {
                    *v /= d;
                }
            }
        }

        if hilbert_envelope {
            let env = hilbert_env(&raw);
            for (v, e) in raw.iter_mut().zip(env) {
                *v = e;
            }
        }

        // raw[i] corresponds to lag (i - tau0). Cut to window [-n_lags, +n_lags].
        let values: Vec<f64> = raw[tau0 - n_lags..=tau0 + n_lags].to_vec();
        let lags: Vec<f64> = (-(n_lags as i64)..=n_lags as i64).map(|t| t as f64).collect();
        let peak_index = values
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(n_lags);
        let peak_value = values[peak_index];

        frames.push(XCorrFrame { lags, values, peak_index, peak_value });
    }

    Ok(frames)
}

pub fn determine_delay_vs_time(
    signals: ArrayView2<f64>,
    reference: ArrayView1<f64>,
    frame_size: usize,
    hop_size: usize,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: XCorrScaling,
    reliability_threshold: f64,
) -> Result<Vec<XCorrResult>, XCorrError> {
    if frame_size == 0 || hop_size == 0 {
        return Err(XCorrError::InvalidFrame(0));
    }
    let n = signals.nrows();
    let n_ch = signals.ncols();
    let mut channels: Vec<XCorrResult> = (0..n_ch)
        .map(|_| XCorrResult { frames: Vec::new(), reliable_indices: Vec::new() })
        .collect();
    let mut start = 0;
    while start + frame_size <= n {
        let sig = signals.slice(ndarray::s![start..start + frame_size, ..]);
        let ref_ = reference.slice(ndarray::s![start..start + frame_size]);
        // One frame per channel: frames[c] is channel c's correlation.
        let frames = cross_correlation_function(
            sig, ref_, hilbert_envelope, n_lags, scaling, false,
        )?;
        for (c, frame) in frames.into_iter().enumerate() {
            let ch = &mut channels[c];
            if frame.peak_value >= reliability_threshold {
                ch.reliable_indices.push(ch.frames.len());
            }
            ch.frames.push(frame);
        }
        start += hop_size;
    }
    if channels.first().map_or(true, |c| c.frames.is_empty()) {
        return Err(XCorrError::InvalidFrame(frame_size));
    }
    Ok(channels)
}

pub fn determine_delay_from_average(
    signals: ArrayView2<f64>,
    reference: ArrayView1<f64>,
    frame_size: usize,
    hop_size: usize,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: XCorrScaling,
) -> Result<Vec<f64>, XCorrError> {
    let channels = determine_delay_vs_time(
        signals, reference, frame_size, hop_size,
        hilbert_envelope, n_lags, scaling, f64::NEG_INFINITY,
    )?;
    Ok(channels
        .iter()
        .map(|result| {
            let len = result.frames[0].values.len();
            let mut avg = vec![0.0f64; len];
            for f in &result.frames {
                for (a, v) in avg.iter_mut().zip(&f.values) {
                    *a += v;
                }
            }
            let inv = 1.0 / result.frames.len() as f64;
            avg.iter_mut().for_each(|v| *v *= inv);
            let peak_index = avg
                .iter()
                .enumerate()
                .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
                .map(|(i, _)| i)
                .unwrap_or(0);
            result.frames[0].lags[peak_index]
        })
        .collect())
}

pub(crate) struct XorShift64(u64);
impl XorShift64 {
    pub(crate) fn new(seed: u64) -> Self { Self(seed | 1) }
    pub(crate) fn next_u64(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        self.0 = x; x
    }
    pub(crate) fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64 * 2.0 - 1.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array2;

    fn noise_burst(n: usize, lead: usize, seed: u64) -> Vec<f64> {
        let mut rng = XorShift64::new(seed);
        let mut v = vec![0.0; n];
        for s in v.iter_mut().skip(lead) { *s = rng.next_f64(); }
        v
    }

    fn shifted_reference(sig: &[f64], delay: usize) -> Vec<f64> {
        // ref[k] = sig[k+delay] => test=sig, ref=shifted => peak at lag = delay
        let mut ref_ = vec![0.0; sig.len()];
        for k in 0..sig.len() - delay { ref_[k] = sig[k + delay]; }
        ref_
    }

    #[test]
    fn test_delay_detects_shifted_noise_burst() {
        let sig = noise_burst(128, 16, 42);
        let ref_ = shifted_reference(&sig, 2);
        let sig_arr = Array2::from_shape_vec((128, 1), sig.clone()).unwrap();
        let frames = cross_correlation_function(
            sig_arr.view(),
            ndarray::ArrayView1::from(&ref_),
            false, Some(16), XCorrScaling::Normalized, false,
        ).unwrap();
        assert_eq!(frames.len(), 1);
        let frame = &frames[0];
        assert!((frame.lags[frame.peak_index] - 2.0).abs() < 1e-9);
        assert!(frame.peak_value > 0.9);
    }

    #[test]
    fn test_hilbert_envelope_of_cosine_is_unity() {
        let n = 256;
        let x: Vec<f64> = (0..n).map(|i| (2.0 * std::f64::consts::PI * 7.0 * i as f64 / n as f64).cos()).collect();
        let env = hilbert_env(&x);
        let mid = &env[n / 4..3 * n / 4];
        let err = mid.iter().fold(0.0f64, |m, v| m.max((v - 1.0).abs()));
        assert!(err < 1e-9, "max envelope error {err}");
    }

    #[test]
    fn test_zero_delay_identity() {
        let sig = noise_burst(128, 16, 7);
        let sig_arr = Array2::from_shape_vec((128, 1), sig.clone()).unwrap();
        let frames = cross_correlation_function(
            sig_arr.view(),
            ndarray::ArrayView1::from(&sig),
            false, Some(16), XCorrScaling::Normalized, false,
        ).unwrap();
        let frame = &frames[0];
        assert!(frame.lags[frame.peak_index].abs() < 1e-9);
        assert!((frame.peak_value - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_delay_from_average_resolves_sub_period() {
        for delay in [1usize, 2, 3] {
            let sig = noise_burst(256, 32, 100 + delay as u64);
            let ref_ = shifted_reference(&sig, delay);
            let sig_arr = Array2::from_shape_vec((256, 1), sig.clone()).unwrap();
            let d = determine_delay_from_average(
                sig_arr.view(),
                ndarray::ArrayView1::from(&ref_),
                256, 256, false, Some(32), XCorrScaling::Normalized,
            ).unwrap();
            assert!((d[0] - delay as f64).abs() < 1e-9);
        }
    }

    #[test]
    fn test_dimension_mismatch_pads_shorter_side() {
        // Issue #2: unequal lengths are auto-padded with zeros.
        let sig = noise_burst(64, 8, 1);
        let other = noise_burst(32, 8, 2);
        let sig_arr = Array2::from_shape_vec((64, 1), sig).unwrap();
        let frames = cross_correlation_function(
            sig_arr.view(),
            ndarray::ArrayView1::from(&other),
            false, None, XCorrScaling::None, false,
        ).unwrap();
        assert_eq!(frames.len(), 1);
        assert_eq!(frames[0].values.len(), 2 * 64 - 1);
    }

    #[test]
    fn test_delay_vs_time_reliability() {
        let n = 512;
        let sig = noise_burst(n, 32, 9);
        let ref_ = shifted_reference(&sig, 5);
        let sig_arr = Array2::from_shape_vec((n, 1), sig.clone()).unwrap();
        let channels = determine_delay_vs_time(
            sig_arr.view(),
            ndarray::ArrayView1::from(&ref_),
            256, 256, false, Some(32), XCorrScaling::Normalized, 0.5,
        ).unwrap();
        assert_eq!(channels.len(), 1);
        assert_eq!(channels[0].frames.len(), 2);
        assert_eq!(channels[0].reliable_indices.len(), 2);
        for f in &channels[0].frames {
            assert!((f.lags[f.peak_index] - 5.0).abs() < 1e-9);
        }
    }
}


// PyO3 bindings: dtype dispatch (f32/f64) at the boundary, f64 core.
#![allow(clippy::useless_conversion)] // `?` on PyErr in PyResult fns triggers identity From

use ndarray::ArrayView1;
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::PyList;

use crate::{
    cross_correlation_function, determine_delay_from_average, determine_delay_vs_time,
    XCorrError, XCorrFrame, XCorrResult, XCorrScaling,
};

/// Extract an f64 2-D view from a NumPy array (float32 or float64).
fn to_f64_array2<'py>(
    any: &Bound<'py, PyAny>,
    py: Python<'py>,
) -> PyResult<(Vec<f64>, usize)> {
    if let Ok(arr) = any.extract::<PyReadonlyArray2<'py, f64>>() {
        let view = arr.as_array();
        return Ok((view.to_owned().into_raw_vec(), view.ncols()));
    }
    if let Ok(arr) = any.extract::<PyReadonlyArray2<'py, f32>>() {
        let view = arr.as_array();
        let data: Vec<f64> = view.iter().map(|v| *v as f64).collect();
        return Ok((data, view.ncols()));
    }
    // fall back: 1-D input promoted to a single channel
    if let Ok(arr) = any.extract::<PyReadonlyArray1<'py, f64>>() {
        return Ok((arr.as_array().to_owned().into_raw_vec(), 1));
    }
    if let Ok(arr) = any.extract::<PyReadonlyArray1<'py, f32>>() {
        return Ok((
            arr.as_array().iter().map(|v| *v as f64).collect(),
            1,
        ));
    }
    Err(PyTypeError::new_err(
        "signals must be a float32 or float64 NumPy array (samples, channels)",
    ))
}

/// Extract an f64 1-D view from a NumPy array (float32 or float64).
fn to_f64_array1<'py>(any: &Bound<'py, PyAny>) -> PyResult<Vec<f64>> {
    if let Ok(arr) = any.extract::<PyReadonlyArray1<'py, f64>>() {
        return Ok(arr.as_array().to_owned().into_raw_vec());
    }
    if let Ok(arr) = any.extract::<PyReadonlyArray1<'py, f32>>() {
        return Ok(arr.as_array().iter().map(|v| *v as f64).collect());
    }
    Err(PyTypeError::new_err(
        "reference must be a float32 or float64 NumPy array (samples,)",
    ))
}

fn parse_scaling(s: &str) -> PyResult<XCorrScaling> {
    match s {
        "normalized" | "coeff" => Ok(XCorrScaling::Normalized),
        "biased" => Ok(XCorrScaling::Biased),
        "unbiased" => Ok(XCorrScaling::Unbiased),
        "none" => Ok(XCorrScaling::None),
        other => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "invalid scaling mode: {other}"
        ))),
    }
}

fn map_err(e: XCorrError) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(e.to_string())
}

#[pyclass(skip_from_py_object)]
struct PyXCorrFrame {
    #[pyo3(get)]
    lags: Py<PyAny>,
    #[pyo3(get)]
    values: Py<PyAny>,
    #[pyo3(get)]
    peak_index: usize,
    #[pyo3(get)]
    peak_value: f64,
}

#[pyclass(skip_from_py_object)]
struct PyXCorrResult {
    #[pyo3(get)]
    frames: Py<PyAny>,
    #[pyo3(get)]
    reliable_indices: Py<PyAny>,
}

#[pyfunction]
#[pyo3(signature = (signals, reference, hilbert_envelope=false, n_lags=None, scaling="normalized", zero_pad=false))]
fn xcorr(
    py: Python<'_>,
    signals: Bound<'_, PyAny>,
    reference: Bound<'_, PyAny>,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: &str,
    zero_pad: bool,
) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
    let (data, ncols) = to_f64_array2(&signals, py)?;
    let ref_ = to_f64_array1(&reference)?;
    let arr = ndarray::Array2::from_shape_vec((data.len() / ncols, ncols), data)
        .map_err(|_| PyTypeError::new_err("ragged input"))?;
    let scaling = parse_scaling(scaling)?;
    let frame = cross_correlation_function(
        arr.view(),
        ArrayView1::from(&ref_),
        hilbert_envelope,
        n_lags,
        scaling,
        zero_pad,
    )
    .map_err(map_err)?;
    Ok((
        PyArray1::from_vec(py, frame.lags).into_any().unbind(),
        PyArray1::from_vec(py, frame.values).into_any().unbind(),
    ))
}

#[pyfunction]
#[pyo3(signature = (signals, reference, frame_size, hop_size, hilbert_envelope=false, n_lags=None, scaling="normalized", reliability_threshold=0.5))]
fn determine_delay_vs_time_py(
    py: Python<'_>,
    signals: Bound<'_, PyAny>,
    reference: Bound<'_, PyAny>,
    frame_size: usize,
    hop_size: usize,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: &str,
    reliability_threshold: f64,
) -> PyResult<PyXCorrResult> {
    let (data, ncols) = to_f64_array2(&signals, py)?;
    let ref_ = to_f64_array1(&reference)?;
    let arr = ndarray::Array2::from_shape_vec((data.len() / ncols, ncols), data)
        .map_err(|_| PyTypeError::new_err("ragged input"))?;
    let scaling = parse_scaling(scaling)?;
    let result: XCorrResult = determine_delay_vs_time(
        arr.view(),
        ArrayView1::from(&ref_),
        frame_size,
        hop_size,
        hilbert_envelope,
        n_lags,
        scaling,
        reliability_threshold,
    )
    .map_err(map_err)?;

    let frames: Vec<PyXCorrFrame> = result
        .frames
        .into_iter()
        .map(|f: XCorrFrame| PyXCorrFrame {
            lags: PyArray1::from_vec(py, f.lags).into_any().unbind(),
            values: PyArray1::from_vec(py, f.values).into_any().unbind(),
            peak_index: f.peak_index,
            peak_value: f.peak_value,
        })
        .collect();
    let frames_list = PyList::new(py, frames)?.into_any().unbind();
    let reliable = PyArray1::from_vec(
        py,
        result.reliable_indices.iter().map(|i| *i as i64).collect(),
    )
    .into_any()
    .unbind();
    Ok(PyXCorrResult { frames: frames_list, reliable_indices: reliable })
}

#[pyfunction]
#[pyo3(signature = (signals, reference, frame_size, hop_size, hilbert_envelope=false, n_lags=None, scaling="normalized"))]
fn determine_delay_from_average_py(
    py: Python<'_>,
    signals: Bound<'_, PyAny>,
    reference: Bound<'_, PyAny>,
    frame_size: usize,
    hop_size: usize,
    hilbert_envelope: bool,
    n_lags: Option<usize>,
    scaling: &str,
) -> PyResult<f64> {
    let (data, ncols) = to_f64_array2(&signals, py)?;
    let ref_ = to_f64_array1(&reference)?;
    let arr = ndarray::Array2::from_shape_vec((data.len() / ncols, ncols), data)
        .map_err(|_| PyTypeError::new_err("ragged input"))?;
    let scaling = parse_scaling(scaling)?;
    determine_delay_from_average(
        arr.view(),
        ArrayView1::from(&ref_),
        frame_size,
        hop_size,
        hilbert_envelope,
        n_lags,
        scaling,
    )
    .map_err(map_err)
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(xcorr, m)?)?;
    m.add_function(wrap_pyfunction!(determine_delay_vs_time_py, m)?)?;
    m.add_function(wrap_pyfunction!(determine_delay_from_average_py, m)?)?;
    m.add_class::<PyXCorrFrame>()?;
    m.add_class::<PyXCorrResult>()?;
    Ok(())
}

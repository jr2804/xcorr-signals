// Optional PyO3 layer: `default-features = false` builds a pure-Rust crate.
#[cfg(feature = "python")]
mod pyo3_bindings;
mod xcorr;

pub use xcorr::*;

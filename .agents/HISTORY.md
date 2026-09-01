# AGENTS.md — HISTORY

Recorded decisions with git references. Read when relevant to current task.
Acts as simple long-term memory for the project.

## Format

| Date       | Decision   | Rationale   | Git ref          |
| ---------- | ---------- | ----------- | ---------------- |
| 2026-08-31 | Rust core as single cdylib crate at `src/xcorr_signals/` (g191-filter pattern), maturin build backend | Python package is primary artifact; Rust only accelerates xcorr DSP. Mirrors validated rust-pyo3-bindings skill architecture | (uncommitted) |
| 2026-08-31 | FFT xcorr uses circular-correlation lag remap (lag k at index k, lag -k at L-k) | Initial linear-layout extraction misplaced peaks; remap is correct for IFFT-based correlation | (uncommitted) |
| 2026-08-31 | Hilbert envelope: real Hilbert transform via realfft (H(x) = C2R(-j*sgn(k)*X[k]), env = sqrt(x²+H²)) replaces abs() approximation | abs() is not an envelope; realfft is the skill-recommended real-input FFT crate. Note: realfft C2R is unnormalized, divide by N | (uncommitted) |
| 2026-08-31 | xcorr test signals: noise bursts with lead/tail silence (not sine tones) | Periodic tones autocorrelate at every period — ambiguous peaks; noise bursts have one unambiguous peak, resolve 1-sample delays. Sine/cosine only kept for exact Hilbert-envelope math tests | (uncommitted) |
| 2026-08-31 | float32 audio accepted at binding boundary → converted to f64; single f64 core, f64 output | Generic f32/f64 core (ndarray+rustfft+realfft generics) not worth the churn; f64 accumulation is numerically more robust for correlation. Native f32 path possible later via num-traits generics if perf demands | (uncommitted) |
| 2026-08-31 | Shared CLI args use Annotated-style `typer.Option` with NO positional default inside the OptionInfo; defaults live in command signatures (`frame_size: Annotated[int, FrameSizeArg] = 7200`) | Typer's `get_params_from_function` prepends an OptionInfo's `default` to its `param_decls` when reading Annotated metadata — `Option(7200, "--frame-size", ...)` puts the int 7200 into the decls and crashes with `'int' object has no attribute 'isidentifier'`. Only decl strings go in Annotated-position Options | 7b839ed |
| 2026-08-31 | Env-var override uses Typer's native `envvar=` on the Option, not `os.environ.get()` in the command body | User directive: must use Typer's integrated feature so `--output-file` flag and `XCORR_SIGNALS_OUTPUT_FILE` stay consistent with Typer docs/help | 7b839ed |
| 2026-08-31 | Group callback uses `invoke_without_command=True`; bare invocation prints help, `--version` exits | Without it, click group errors "Missing command" before processing the eager version option | 7b839ed |
| 2026-09-01 | Build backend is `maturin` (not hatchling); version comes from Cargo.toml, stamped by release.yml before `uv build` | uv-dynamic-versioning is a hatchling plugin — under the maturin backend it never runs, so wheels shipped 0.0.0 despite CalVer tags. Release workflow now sed-stamps the tag into Cargo.toml; CalVer minor is zero-stripped (2026.09.2 → 2026.9.2) because Cargo semver rejects leading zeros | 8ee6618, 46d2cd0 |
| 2026-09-01 | `tool.maturin exclude = ["**/target/**"]` | maturin packages the crate `target/` dir when building from an extracted sdist (no .gitignore there) → wheel balloons to GB and zip64 fails: "Large file option has not been set" | 0232a23 |

## Guidance

- Record decisions that would be costly to rediscover.
- Note false turns and why they were rejected.
- Link to relevant commits.
- Keep entries brief — enough to reconstruct reasoning.
- When this file grows too large, archive older entries to
  `.agents/history/` and leave a pointer here.

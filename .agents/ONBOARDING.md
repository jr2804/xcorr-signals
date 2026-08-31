# AGENTS.md — ONBOARDING

Read this when starting a new session. After first read, only revisit when
project structure or tooling changes significantly.

## Project

Fast cross-correlation for determining and compensating delay between audio signal channels, implemented in Rust. Full docs at `README.md` or `docs/`.

## Quick start

```bash
mise dev        # install dependencies (uv sync --dev)
mise build-rust # build Rust extension (maturin develop)
mise test       # run pytest with coverage
mise lint       # ruff + ty + codespell
mise format     # ruff format + isort + clean-sort
mise all        # test + lint + format in one pass
```

## Entry points (read these first)

| File / Section | Why |
| -------------- | --- |
| `AGENTS.md` | Root rail — rules + `.agents/` index |
| `.agents/POLICIES.md` | Boundaries, priorities, verification |
| `.agents/FILES.md` | Source-of-truth locations for this package |
| `pyproject.toml` | Dependencies, pytest config, maturin build |
| `src/xcorr_signals/Cargo.toml` | Rust crate manifest (single cdylib crate) |
| `src/xcorr_signals/src/` | Rust core: `xcorr.rs` (DSP), `pyo3_bindings.rs` (bindings) |
| `.copier-answers.yml` | Template answers (regenerated on `copier update`) |

## Layout

- **`src/xcorr_signals/`** — primary package source (src layout)
- **`src/xcorr_signals/src/`** — Rust core: `xcorr.rs` (xcorr/DSP algorithms), `pyo3_bindings.rs` (PyO3 bindings)
- **`src/xcorr_signals/Cargo.toml`** — Rust crate manifest (built as `xcorr_signals._native`)
- **`tests/`** — pytest suite (100% coverage gate)
- **`src/xcorr_signals/cli/`** — Typer CLI
- **`docs/`** — Zensical / MkDocs Material documentation
- **`.config/mise/`** — task runner config (`config.toml` + `conf.d/` fragments)

## Rust core dev loop

The Rust extension must be built before running tests that use it:

```bash
uv run maturin develop           # debug build into the venv
uv run maturin develop --release  # release build (for benchmarks)
```

Rust unit tests: `cargo test --lib` (run from `src/xcorr_signals/`).

## Where to dig deeper

- `docs/` — user-facing documentation
- `.agents/HISTORY.md` — past decisions and rationale
- Source-tree AGENTS.md files — local contracts for each area

## Available tools

If MCP dev-features are enabled (`include_mcp_tasks`), the following may be
available after running `mise run add-mcp-servers <agent>` and `mise run
add-skills`:

- **repowise** — architecture overview, risk, health scores, change-risk
- **codegraph** — symbol search, call graphs, dependency maps
- **grepai** — semantic code search by meaning, not text
- **bd / beads** — distributed issue tracker (if `tracking` skill category enabled)
- Various slop/dead-code detectors (see `.config/mise/conf.d/skills.toml`)

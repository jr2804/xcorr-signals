# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""CLI command implementations."""

from pathlib import Path
from typing import Annotated

import typer

from xcorr_signals.cli.args import (
    FrameSizeArg,
    HopSizeArg,
    InputFileArg,
    NLagsArg,
    OutputFileArg,
    ReliabilityArg,
    ScalingArg,
)


def default() -> None:
    """Welcome message."""
    typer.secho(
        "xcorr-signals — fast cross-correlation delay estimation (Rust core)",
        fg=typer.colors.CYAN,
    )


def xcorr_cmd() -> None:
    """Cross-correlation of two signals (stub until WAV I/O lands)."""
    typer.secho(
        "xcorr-cmd: WAV I/O pending; use xcorr_signals.xcorr from Python",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)


def delay_vs_time(
    input_file: Annotated[Path, InputFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    reliability_threshold: Annotated[float, ReliabilityArg] = 0.5,
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Per-frame delay estimates with reliability filtering (stub)."""
    typer.secho(
        f"delay-vs-time: WAV I/O pending ({input_file}, frame={frame_size}, "
        f"hop={hop_size}, n_lags={n_lags}, scaling={scaling}, "
        f"reliability={reliability_threshold}, out={output_file})",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)


def delay_from_average(
    input_file: Annotated[Path, InputFileArg],
    frame_size: Annotated[int, FrameSizeArg] = 7200,
    hop_size: Annotated[int, HopSizeArg] = 7200,
    n_lags: Annotated[int | None, NLagsArg] = None,
    scaling: Annotated[str, ScalingArg] = "normalized",
    output_file: Annotated[Path | None, OutputFileArg] = None,
) -> None:
    """Single delay from the averaged xcorr peak (stub)."""
    typer.secho(
        f"delay-from-average: WAV I/O pending ({input_file}, frame={frame_size}, hop={hop_size}, n_lags={n_lags}, scaling={scaling}, out={output_file})",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)

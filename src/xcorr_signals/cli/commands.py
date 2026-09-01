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
    get_output_file,
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
    frame_size: Annotated[int, FrameSizeArg],
    hop_size: Annotated[int, HopSizeArg],
    n_lags: Annotated[int | None, NLagsArg],
    scaling: Annotated[str, ScalingArg],
    reliability_threshold: Annotated[float, ReliabilityArg],
    output_file: Annotated[Path | None, OutputFileArg],
) -> None:
    """Per-frame delay estimates with reliability filtering (stub)."""
    out = get_output_file(output_file)
    typer.secho(
        f"delay-vs-time: WAV I/O pending ({input_file}, frame={frame_size}, "
        f"hop={hop_size}, n_lags={n_lags}, scaling={scaling}, "
        f"reliability={reliability_threshold}, out={out})",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)


def delay_from_average(
    input_file: Annotated[Path, InputFileArg],
    frame_size: Annotated[int, FrameSizeArg],
    hop_size: Annotated[int, HopSizeArg],
    n_lags: Annotated[int | None, NLagsArg],
    scaling: Annotated[str, ScalingArg],
    output_file: Annotated[Path | None, OutputFileArg],
) -> None:
    """Single delay from the averaged xcorr peak (stub)."""
    out = get_output_file(output_file)
    typer.secho(
        f"delay-from-average: WAV I/O pending ({input_file}, frame={frame_size}, hop={hop_size}, n_lags={n_lags}, scaling={scaling}, out={out})",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=2)

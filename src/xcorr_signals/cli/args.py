# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""CLI argument definitions."""

import os
from pathlib import Path

import typer

InputFileArg = typer.Argument(
    help="Input WAV file",
    exists=True,
    dir_okay=False,
    readable=True,
)

FrameSizeArg = typer.Option(
    7200,
    "--frame-size",
    "-f",
    help="Frame size in samples",
    min=1,
)

HopSizeArg = typer.Option(
    7200,
    "--hop-size",
    "-H",
    help="Hop size in samples",
    min=1,
)

NLagsArg = typer.Option(
    None,
    "--n-lags",
    "-n",
    help="Lag search window (+/- n_lags); full range if omitted",
    min=1,
)

ScalingArg = typer.Option(
    "normalized",
    "--scaling",
    "-s",
    help="xcorr scaling mode",
    case_sensitive=False,
)

ReliabilityArg = typer.Option(
    0.5,
    "--reliability-threshold",
    "-r",
    help="Minimum peak value for a frame to count as reliable",
    min=0.0,
    max=1.0,
)

OutputFileArg = typer.Option(
    None,
    "--output-file",
    "-o",
    help="Output file path (defaults to XCORR_SIGNALS_OUTPUT_FILE or stdout)",
)

EnvVarOutputFile = Path


def get_output_file(output_file: OutputFileArg) -> Path | None:

    if output_file is not None:
        return output_file
    env = os.environ.get("XCORR_SIGNALS_OUTPUT_FILE")
    return Path(env) if env else None

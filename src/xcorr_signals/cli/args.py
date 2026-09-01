# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""CLI argument definitions (Annotated-style OptionInfo).

NOTE: options carry only their parameter info — no positional default.
Typer's Annotated extraction prepends an OptionInfo's `default` to its
param_decls; a positional default like Option(7200, ...) then lands inside
the decls and crashes. Defaults live in the command signatures in
commands.py.
"""

from __future__ import annotations

import typer

TestFileArg = typer.Argument(
    help="Test signal WAV file (x)",
    exists=True,
    dir_okay=False,
    readable=True,
)

ReferenceFileArg = typer.Argument(
    help="Reference signal WAV file (y)",
    exists=True,
    dir_okay=False,
    readable=True,
)

FrameSizeArg = typer.Option(
    "--frame-size",
    "-f",
    help="Frame size in samples",
    min=1,
)

HopSizeArg = typer.Option(
    "--hop-size",
    "-H",
    help="Hop size in samples",
    min=1,
)

NLagsArg = typer.Option(
    "--n-lags",
    "-n",
    help="Lag search window (+/- n_lags); full range if omitted",
    min=1,
)

ScalingArg = typer.Option(
    "--scaling",
    "-s",
    help="xcorr scaling mode",
    case_sensitive=False,
)

HilbertArg = typer.Option(
    "--hilbert-envelope",
    help="Use the Hilbert envelope of the cross-correlation",
)

ReliabilityArg = typer.Option(
    "--reliability-threshold",
    "-r",
    help="Minimum peak value for a frame to count as reliable",
    min=0.0,
    max=1.0,
)

OutputFileArg = typer.Option(
    "--output-file",
    "-o",
    help="Output path (defaults to XCORR_SIGNALS_OUTPUT_FILE env var or stdout)",
    envvar="XCORR_SIGNALS_OUTPUT_FILE",
)

MaxDelayArg = typer.Option(
    "--max-delay",
    "-d",
    help="Maximum delay to search for, in seconds",
    min=0.0,
)

OutputPrefixArg = typer.Option(
    "--output-prefix",
    "-o",
    help="Prefix for compensated WAV files (default: derived from test file)",
)

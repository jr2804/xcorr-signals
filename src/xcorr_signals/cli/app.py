# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Typer application for xcorr-signals."""

from importlib import metadata
from typing import Annotated

import typer

from xcorr_signals.cli import commands

app = typer.Typer(
    name="xcorr-signals",
    help="Fast cross-correlation for audio delay estimation (Rust core).",
    no_args_is_help=True,
    add_completion=False,
)

try:
    _version = metadata.version("xcorr-signals")
except metadata.PackageNotFoundError:  # pragma: no cover
    _version = "0.0.0"


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show the version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Cross-correlation delay estimation with a Rust core."""
    if version:
        typer.echo(f"xcorr-signals {_version}")
        raise typer.Exit


app.command()(commands.default)
app.command(name="xcorr-cmd")(commands.xcorr_cmd)
app.command(name="delay-vs-time")(commands.delay_vs_time)
app.command(name="delay-from-average")(commands.delay_from_average)


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()

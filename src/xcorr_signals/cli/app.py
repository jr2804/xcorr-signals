# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes

"""Typer application for xcorr-signals."""

from importlib import metadata
from typing import Annotated

import typer

from xcorr_signals.cli import commands

app = typer.Typer(
    name="xcorr-signals",
    help="Cross-correlation, delay estimation and delay compensation (Rust core).",
    add_completion=False,
)

try:
    _version = metadata.version("xcorr-signals")
except metadata.PackageNotFoundError:  # pragma: no cover
    _version = "0.0.0"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


app.command(name="xcorr")(commands.xcorr_cmd)
app.command(name="delay-vs-time")(commands.delay_vs_time)
app.command(name="delay-from-average")(commands.delay_from_average)
app.command(name="compensate-delay")(commands.compensate_delay)


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()

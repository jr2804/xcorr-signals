"""Typer CLI app for Cross-correlation for audio signals."""

from __future__ import annotations

from importlib.metadata import version

import typer

# Version management
def _get_version() -> str:
    """Get application version from package metadata."""
    try:
        return version("xcorr_signals")
    except Exception:
        return "0.0.0"  # Fallback for development mode

app = typer.Typer(
    name="xcorr_signals",
    help="Fast cross-correlation for determining and compensating delay between audio signal channels, implemented in Rust.",
    add_completion=True,
    no_args_is_help=True,
)

@app.callback(invoke_without_command=True)
def _callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        is_eager=True,
    ),
) -> None:
    """Fast cross-correlation for determining and compensating delay between audio signal channels, implemented in Rust."""
    if version:
        typer.echo(_get_version())
        raise typer.Exit()


def main() -> None:
    """Entry point for the CLI application."""
    app()


# Import commands to register them with app
from xcorr_signals.cli import commands  # noqa: E402, F401

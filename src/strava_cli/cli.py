"""Main CLI entry point."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from strava_cli import __version__
from strava_cli.commands import (
    activities,
    athlete,
    auth,
    clubs,
    context,
    efforts,
    gear,
    routes,
    segments,
    upload,
)
from strava_cli.output import OutputFormat

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_AUTH_ERROR = 2


# Global state for format options
class State:
    """Global CLI state."""

    format: OutputFormat = OutputFormat.json
    fields: list[str] | None = None
    no_header: bool = False
    verbose: bool = False
    quiet: bool = False
    config_path: str | None = None
    profile: str | None = None


state = State()

app = typer.Typer(
    name="strava",
    help="Strava from your terminal. Pipe it, script it, automate it.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        print(f"strava-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format",
            envvar="STRAVA_FORMAT",
        ),
    ] = OutputFormat.json,
    fields: Annotated[
        str | None,
        typer.Option(
            "--fields",
            help="Comma-separated list of fields to include in output",
        ),
    ] = None,
    no_header: Annotated[
        bool,
        typer.Option(
            "--no-header",
            help="Omit header row in CSV/TSV output",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Verbose output to stderr",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress non-essential output",
        ),
    ] = False,
    config: Annotated[
        str | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to config file",
            envvar="STRAVA_CONFIG",
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="Named profile to use",
            envvar="STRAVA_PROFILE",
        ),
    ] = None,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    """Global options applied to all commands."""
    # Mutual exclusivity check
    if verbose and quiet:
        print("error: --verbose and --quiet are mutually exclusive", file=sys.stderr)
        raise typer.Exit(EXIT_ERROR)

    state.format = format
    state.fields = fields.split(",") if fields else None
    state.no_header = no_header
    state.verbose = verbose
    state.quiet = quiet
    state.config_path = config
    state.profile = profile


# Register subcommands
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(athlete.app, name="athlete", help="Athlete profile and stats")
app.add_typer(activities.app, name="activities", help="Activity management")
app.add_typer(segments.app, name="segments", help="Segment exploration")
app.add_typer(efforts.app, name="efforts", help="Segment efforts")
app.add_typer(routes.app, name="routes", help="Route management")
app.add_typer(clubs.app, name="clubs", help="Club information")
app.add_typer(gear.app, name="gear", help="Gear/equipment info")
app.add_typer(upload.app, name="upload", help="Upload activities")
app.add_typer(context.app, name="context", help="Aggregated context for LLMs")


def error(message: str, exit_code: int = EXIT_ERROR) -> None:
    """Print error message to stderr and exit."""
    print(f"error: {message}", file=sys.stderr)
    raise typer.Exit(exit_code)


def auth_error(message: str) -> None:
    """Print auth error message to stderr and exit."""
    error(message, EXIT_AUTH_ERROR)


if __name__ == "__main__":
    app()

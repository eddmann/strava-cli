"""Upload commands."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Annotated, Any

import typer

from strava_cli.client import get_client
from strava_cli.config import Config
from strava_cli.decorators import authenticated_command, emit_result
from strava_cli.exceptions import StravaCLIError

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def upload_file(
    ctx: typer.Context,
    file: Annotated[
        Path | None,
        typer.Argument(help="Activity file to upload"),
    ] = None,
    data_type: Annotated[
        str | None,
        typer.Option(
            "--data-type",
            "-t",
            help="File type: fit, fit.gz, gpx, gpx.gz, tcx, tcx.gz",
        ),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Activity name"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Activity description"),
    ] = None,
    sport_type: Annotated[
        str | None,
        typer.Option("--sport-type", "-s", help="Sport type override"),
    ] = None,
    trainer: Annotated[
        bool,
        typer.Option("--trainer", help="Mark as trainer/indoor"),
    ] = False,
    commute: Annotated[
        bool,
        typer.Option("--commute", help="Mark as commute"),
    ] = False,
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for processing to complete"),
    ] = False,
    external_id: Annotated[
        str | None,
        typer.Option("--external-id", help="External ID for the activity"),
    ] = None,
) -> None:
    """Upload an activity file.

    Supports FIT, GPX, and TCX files (optionally gzipped).

    Examples:
        strava upload activity.fit
        strava upload activity.gpx --data-type gpx --name "Morning Run"
        strava upload activity.fit.gz --wait
    """
    if ctx.invoked_subcommand is not None:
        return

    if file is None:
        raise typer.BadParameter("File argument is required")

    if not file.exists():
        print(f"error: File not found: {file}", file=sys.stderr)
        raise typer.Exit(1)

    # Auto-detect data type from extension if not provided
    if data_type is None:
        suffix = file.suffix.lower()
        if suffix == ".gz":
            # Check the part before .gz
            stem_suffix = Path(file.stem).suffix.lower()
            data_type = f"{stem_suffix[1:]}.gz" if stem_suffix else None
        else:
            data_type = suffix[1:] if suffix else None

    if data_type is None:
        print("error: Could not detect file type. Use --data-type", file=sys.stderr)
        raise typer.Exit(1)

    valid_types = {"fit", "fit.gz", "gpx", "gpx.gz", "tcx", "tcx.gz"}
    if data_type not in valid_types:
        valid_str = ", ".join(sorted(valid_types))
        print(f"error: Invalid data type '{data_type}'. Valid: {valid_str}", file=sys.stderr)
        raise typer.Exit(1)

    # Lazy import to avoid circular import (required for PyInstaller builds)
    from strava_cli import cli

    try:
        config = Config.load(cli.state.config_path)
        client = get_client(config, cli.state.profile)
    except StravaCLIError as e:
        print(f"error: {e.message}", file=sys.stderr)
        if e.hint and not cli.state.quiet:
            print(f"hint: {e.hint}", file=sys.stderr)
        raise typer.Exit(e.exit_code) from None

    upload_result = client.upload_activity(
        file_path=str(file),
        data_type=data_type,
        name=name,
        description=description,
        sport_type=sport_type,
        trainer=trainer,
        commute=commute,
        external_id=external_id,
    )

    if wait:
        # Poll for completion
        print("Waiting for processing...", file=sys.stderr)
        max_attempts = 60
        for _ in range(max_attempts):
            time.sleep(1)
            status = client.get_upload(upload_result.id)
            if hasattr(status, "activity_id") and status.activity_id:
                emit_result(status, f"Upload complete: activity {status.activity_id}")
                return
            if hasattr(status, "error") and status.error:
                print(f"error: Upload failed: {status.error}", file=sys.stderr)
                raise typer.Exit(1)

        print("error: Upload processing timeout", file=sys.stderr)
        raise typer.Exit(1)
    else:
        emit_result(upload_result, f"Upload started: ID {upload_result.id}")


@app.command("status")
@authenticated_command
def upload_status(
    client: Any,
    upload_id: Annotated[int, typer.Argument(help="Upload ID")],
) -> Any:
    """Check upload processing status.

    Examples:
        strava upload status 12345678
    """
    return client.get_upload(upload_id)

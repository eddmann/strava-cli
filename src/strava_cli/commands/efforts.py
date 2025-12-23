"""Segment effort commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command

app = typer.Typer(no_args_is_help=True)


@app.command("get")
@authenticated_command
def get_effort(
    client: Any,
    effort_id: Annotated[int, typer.Argument(help="Segment effort ID")],
) -> Any:
    """Get a segment effort by ID.

    Examples:
        strava efforts get 12345678901
    """
    return client.get_segment_effort(effort_id)


@app.command("list")
@authenticated_command
def list_efforts(
    client: Any,
    segment_id: Annotated[
        int,
        typer.Option("--segment-id", "-s", help="Segment ID"),
    ],
    start: Annotated[
        str | None,
        typer.Option(
            "--start",
            help="Start date ISO8601 (e.g., 2025-01-01)",
        ),
    ] = None,
    end: Annotated[
        str | None,
        typer.Option(
            "--end",
            help="End date ISO8601",
        ),
    ] = None,
) -> list:
    """List segment efforts for a segment.

    Examples:
        strava efforts list --segment-id 229781
        strava efforts list --segment-id 229781 --start 2025-01-01 --end 2025-12-31
    """
    return client.get_segment_efforts(
        segment_id=segment_id,
        start_date=start,
        end_date=end,
    )

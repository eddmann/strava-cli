"""Segment commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command, emit_output, emit_result, with_client

app = typer.Typer(no_args_is_help=True)


@app.command("get")
@authenticated_command
def get_segment(
    client: Any,
    segment_id: Annotated[int, typer.Argument(help="Segment ID")],
) -> Any:
    """Get a segment by ID.

    Examples:
        strava segments get 229781
    """
    return client.get_segment(segment_id)


@app.command("starred")
@authenticated_command
def starred_segments(
    client: Any,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Maximum number to return"),
    ] = None,
) -> list:
    """Get starred segments.

    Examples:
        strava segments starred
        strava segments starred --limit 10
    """
    return client.get_starred_segments(limit=limit)


@app.command("star")
@with_client
def star_segment(
    client: Any,
    segment_id: Annotated[int, typer.Argument(help="Segment ID")],
) -> None:
    """Star a segment.

    Examples:
        strava segments star 229781
    """
    segment = client.star_segment(segment_id, starred=True)
    emit_result(segment, f"Segment {segment_id} starred")


@app.command("unstar")
@with_client
def unstar_segment(
    client: Any,
    segment_id: Annotated[int, typer.Argument(help="Segment ID")],
) -> None:
    """Unstar a segment.

    Examples:
        strava segments unstar 229781
    """
    segment = client.star_segment(segment_id, starred=False)
    emit_result(segment, f"Segment {segment_id} unstarred")


@app.command("explore")
@with_client
def explore_segments(
    client: Any,
    bounds: Annotated[
        str,
        typer.Option(
            "--bounds",
            "-b",
            help="Bounding box: SW_LAT,SW_LNG,NE_LAT,NE_LNG",
        ),
    ],
    activity_type: Annotated[
        str | None,
        typer.Option(
            "--activity-type",
            "-t",
            help="Activity type filter (running, riding)",
        ),
    ] = None,
) -> None:
    """Explore segments in a geographic area.

    Examples:
        strava segments explore --bounds 37.7,-122.5,37.8,-122.4
        strava segments explore --bounds 37.7,-122.5,37.8,-122.4 --activity-type running
    """
    # Parse bounds
    try:
        sw_lat, sw_lng, ne_lat, ne_lng = map(float, bounds.split(","))
    except ValueError as e:
        raise typer.BadParameter("Bounds must be SW_LAT,SW_LNG,NE_LAT,NE_LNG") from e

    segments = client.explore_segments(
        bounds=(sw_lat, sw_lng, ne_lat, ne_lng),
        activity_type=activity_type,
    )
    emit_output(segments)

"""Route commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command, emit_output, emit_result, with_client

app = typer.Typer(no_args_is_help=True)


@app.command("list")
@authenticated_command
def list_routes(
    client: Any,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Maximum number to return"),
    ] = None,
) -> list:
    """List athlete's routes.

    Examples:
        strava routes list
        strava routes list --limit 10
    """
    return client.get_routes(limit=limit)


@app.command("get")
@authenticated_command
def get_route(
    client: Any,
    route_id: Annotated[int, typer.Argument(help="Route ID")],
) -> Any:
    """Get a route by ID.

    Examples:
        strava routes get 12345678
    """
    return client.get_route(route_id)


@app.command("export")
@with_client
def export_route(
    client: Any,
    route_id: Annotated[int, typer.Argument(help="Route ID")],
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Export format: gpx or tcx",
        ),
    ] = "gpx",
    output_file: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: stdout)",
        ),
    ] = None,
) -> None:
    """Export a route as GPX or TCX.

    Examples:
        strava routes export 12345678 --format gpx > route.gpx
        strava routes export 12345678 --format tcx -o route.tcx
    """
    import httpx

    format_lower = format.lower()
    if format_lower not in ("gpx", "tcx"):
        raise typer.BadParameter("Format must be 'gpx' or 'tcx'")

    url = f"https://www.strava.com/api/v3/routes/{route_id}/export_{format_lower}"

    with httpx.Client() as http_client:
        response = http_client.get(
            url,
            headers={"Authorization": f"Bearer {client.auth.access_token}"},
        )
        response.raise_for_status()
        content = response.text

    if output_file:
        with open(output_file, "w") as f:
            f.write(content)
        emit_result(
            {"file": output_file, "format": format_lower},
            f"Route exported to {output_file}",
        )
    else:
        print(content)


@app.command("streams")
@with_client
def get_route_streams(
    client: Any,
    route_id: Annotated[int, typer.Argument(help="Route ID")],
) -> None:
    """Get route streams (elevation, distance data).

    Examples:
        strava routes streams 12345678
    """
    streams = client.get_route_streams(route_id)

    # Convert streams to dict format
    stream_data = {}
    if hasattr(streams, "items"):
        for key, stream in streams.items():
            if hasattr(stream, "data"):
                stream_data[key] = stream.data
            else:
                stream_data[key] = stream
    else:
        stream_data = streams

    emit_output(stream_data)

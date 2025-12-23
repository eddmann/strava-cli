"""Activity commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command, emit_output, emit_result, with_client

app = typer.Typer(no_args_is_help=True)


@app.command("list")
@authenticated_command
def list_activities(
    client: Any,
    after: Annotated[
        str | None,
        typer.Option(
            "--after",
            "-a",
            help="Only activities after this ISO8601 date (e.g., 2025-01-01)",
        ),
    ] = None,
    before: Annotated[
        str | None,
        typer.Option(
            "--before",
            "-b",
            help="Only activities before this ISO8601 date",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-n",
            help="Maximum number of activities to return",
        ),
    ] = None,
) -> list:
    """List athlete activities.

    Returns activities in reverse chronological order.

    Examples:
        strava activities list --limit 10
        strava activities list --after 2025-01-01 | jq '.[].id'
    """
    return client.get_activities(
        before=before,
        after=after,
        limit=limit,
    )


@app.command("get")
@authenticated_command
def get_activity(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
    include_efforts: Annotated[
        bool,
        typer.Option(
            "--include-efforts",
            "-e",
            help="Include segment efforts in response",
        ),
    ] = False,
) -> Any:
    """Get a single activity by ID.

    Examples:
        strava activities get 12345678
        strava activities get 12345678 --include-efforts
    """
    return client.get_activity(activity_id, include_all_efforts=include_efforts)


@app.command("create")
@with_client
def create_activity(
    client: Any,
    name: Annotated[str, typer.Option("--name", "-n", help="Activity name")],
    sport_type: Annotated[
        str,
        typer.Option(
            "--sport-type",
            "-t",
            help="Sport type (Run, Ride, Swim, etc.)",
        ),
    ],
    start: Annotated[
        str,
        typer.Option(
            "--start",
            "-s",
            help="Start time in ISO8601 format (e.g., 2025-01-15T09:00:00)",
        ),
    ],
    elapsed: Annotated[
        int,
        typer.Option(
            "--elapsed",
            "-e",
            help="Elapsed time in seconds",
        ),
    ],
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Activity description"),
    ] = None,
    distance: Annotated[
        float | None,
        typer.Option("--distance", help="Distance in meters"),
    ] = None,
    trainer: Annotated[
        bool,
        typer.Option("--trainer", help="Mark as trainer/indoor activity"),
    ] = False,
    commute: Annotated[
        bool,
        typer.Option("--commute", help="Mark as commute"),
    ] = False,
) -> None:
    """Create a manual activity.

    Examples:
        strava activities create --name "Morning Run" --sport-type Run \\
            --start 2025-01-15T09:00:00 --elapsed 1800 --distance 5000
    """
    activity = client.create_activity(
        name=name,
        sport_type=sport_type,
        start_date_local=start,
        elapsed_time=elapsed,
        description=description,
        distance=distance,
        trainer=trainer,
        commute=commute,
    )
    emit_result(activity, f"Activity {activity.id} created: {name}")


@app.command("update")
@with_client
def update_activity(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
    name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="New activity name"),
    ] = None,
    sport_type: Annotated[
        str | None,
        typer.Option("--sport-type", "-t", help="New sport type"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="New description"),
    ] = None,
    trainer: Annotated[
        bool | None,
        typer.Option("--trainer/--no-trainer", help="Mark as trainer activity"),
    ] = None,
    commute: Annotated[
        bool | None,
        typer.Option("--commute/--no-commute", help="Mark as commute"),
    ] = None,
    gear_id: Annotated[
        str | None,
        typer.Option("--gear-id", "-g", help="Gear ID to associate"),
    ] = None,
) -> None:
    """Update an activity.

    Examples:
        strava activities update 12345678 --name "Evening Run"
        strava activities update 12345678 --description "Great workout"
    """
    activity = client.update_activity(
        activity_id=activity_id,
        name=name,
        sport_type=sport_type,
        description=description,
        trainer=trainer,
        commute=commute,
        gear_id=gear_id,
    )
    emit_result(activity, f"Activity {activity_id} updated")


@app.command("delete")
@with_client
def delete_activity(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete an activity.

    Examples:
        strava activities delete 12345678
        strava activities delete 12345678 --force
    """
    if not force:
        confirm = typer.confirm(f"Delete activity {activity_id}?")
        if not confirm:
            raise typer.Abort()

    client.delete_activity(activity_id)

    emit_result({"activity_id": activity_id}, f"Activity {activity_id} deleted")


@app.command("streams")
@with_client
def get_streams(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
    keys: Annotated[
        str | None,
        typer.Option(
            "--keys",
            "-k",
            help="Comma-separated stream types (time,distance,latlng,altitude,...)",
        ),
    ] = None,
) -> None:
    """Get activity streams (time series data).

    Examples:
        strava activities streams 12345678
        strava activities streams 12345678 --keys time,distance,heartrate
    """
    key_list = keys.split(",") if keys else None
    streams = client.get_activity_streams(activity_id, keys=key_list)

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


@app.command("laps")
@authenticated_command
def get_laps(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
) -> list:
    """Get activity laps.

    Examples:
        strava activities laps 12345678
    """
    return client.get_activity_laps(activity_id)


@app.command("zones")
@authenticated_command
def get_zones(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
) -> Any:
    """Get activity zones (heart rate, power distribution).

    Examples:
        strava activities zones 12345678
    """
    return client.get_activity_zones(activity_id)


@app.command("comments")
@authenticated_command
def get_comments(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
) -> list:
    """Get activity comments.

    Examples:
        strava activities comments 12345678
    """
    return client.get_activity_comments(activity_id)


@app.command("kudos")
@authenticated_command
def get_kudos(
    client: Any,
    activity_id: Annotated[int, typer.Argument(help="Activity ID")],
) -> list:
    """Get activity kudos (who gave kudos).

    Examples:
        strava activities kudos 12345678
    """
    return client.get_activity_kudos(activity_id)

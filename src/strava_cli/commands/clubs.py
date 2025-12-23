"""Club commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command

app = typer.Typer(no_args_is_help=True)


@app.command("list")
@authenticated_command
def list_clubs(client: Any) -> list:
    """List athlete's clubs.

    Examples:
        strava clubs list
        strava clubs list | jq '.[].name'
    """
    return client.get_athlete_clubs()


@app.command("get")
@authenticated_command
def get_club(
    client: Any,
    club_id: Annotated[int, typer.Argument(help="Club ID")],
) -> Any:
    """Get a club by ID.

    Examples:
        strava clubs get 12345
    """
    return client.get_club(club_id)


@app.command("members")
@authenticated_command
def get_members(
    client: Any,
    club_id: Annotated[int, typer.Argument(help="Club ID")],
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Maximum number to return"),
    ] = None,
) -> list:
    """Get club members.

    Examples:
        strava clubs members 12345
        strava clubs members 12345 --limit 50
    """
    return client.get_club_members(club_id, limit=limit)


@app.command("activities")
@authenticated_command
def get_club_activities(
    client: Any,
    club_id: Annotated[int, typer.Argument(help="Club ID")],
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-n", help="Maximum number to return"),
    ] = None,
) -> list:
    """Get recent club activities.

    Examples:
        strava clubs activities 12345
        strava clubs activities 12345 --limit 20
    """
    return client.get_club_activities(club_id, limit=limit)

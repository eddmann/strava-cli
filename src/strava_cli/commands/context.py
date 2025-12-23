"""Context command - aggregated data for LLM prompts."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from strava_cli.client import get_client
from strava_cli.config import Config
from strava_cli.decorators import emit_output
from strava_cli.exceptions import StravaCLIError
from strava_cli.output import serialize_object

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def context(
    ctx: typer.Context,
    activities_limit: Annotated[
        int,
        typer.Option(
            "--activities",
            "-a",
            help="Number of recent activities to include",
        ),
    ] = 5,
    include_clubs: Annotated[
        bool,
        typer.Option(
            "--clubs/--no-clubs",
            help="Include club memberships",
        ),
    ] = True,
    include_gear: Annotated[
        bool,
        typer.Option(
            "--gear/--no-gear",
            help="Include gear information",
        ),
    ] = True,
    focus: Annotated[
        str | None,
        typer.Option(
            "--focus",
            "-f",
            help="Focus area: activities, stats, gear, clubs (comma-separated)",
        ),
    ] = None,
) -> None:
    """Get aggregated context for LLM prompts.

    Returns athlete profile, stats, gear, clubs, and recent activities
    in a single call - optimized for LLM context windows.

    Examples:
        strava context
        strava context --activities 10
        strava context --focus stats,gear
        strava context --no-clubs --no-gear
    """
    if ctx.invoked_subcommand is not None:
        return

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

    # Parse focus areas
    focus_areas = set(focus.split(",")) if focus else None

    result = {}

    # Always include basic athlete info
    athlete = client.get_athlete()
    athlete_data = serialize_object(athlete)

    # Simplify athlete data for context
    result["athlete"] = {
        "id": athlete_data.get("id"),
        "firstname": athlete_data.get("firstname"),
        "lastname": athlete_data.get("lastname"),
        "city": athlete_data.get("city"),
        "country": athlete_data.get("country"),
        "sex": athlete_data.get("sex"),
        "premium": athlete_data.get("premium"),
        "created_at": athlete_data.get("created_at"),
        "measurement_preference": athlete_data.get("measurement_preference"),
        "ftp": athlete_data.get("ftp"),
        "weight": athlete_data.get("weight"),
    }

    # Include stats
    if focus_areas is None or "stats" in focus_areas:
        try:
            stats = client.get_athlete_stats(athlete.id)
            stats_data = serialize_object(stats)
            result["stats"] = stats_data
        except Exception:
            result["stats"] = None

    # Include gear from athlete profile
    if include_gear and (focus_areas is None or "gear" in focus_areas):
        gear_list = []
        if athlete_data.get("bikes"):
            for bike in athlete_data["bikes"]:
                gear_list.append(
                    {
                        "id": bike.get("id"),
                        "name": bike.get("name"),
                        "type": "bike",
                        "primary": bike.get("primary"),
                        "distance": bike.get("distance"),
                    }
                )
        if athlete_data.get("shoes"):
            for shoe in athlete_data["shoes"]:
                gear_list.append(
                    {
                        "id": shoe.get("id"),
                        "name": shoe.get("name"),
                        "type": "shoes",
                        "primary": shoe.get("primary"),
                        "distance": shoe.get("distance"),
                    }
                )
        result["gear"] = gear_list

    # Include clubs
    if include_clubs and (focus_areas is None or "clubs" in focus_areas):
        try:
            clubs = client.get_athlete_clubs()
            clubs_data = []
            for club in clubs:
                club_obj = serialize_object(club)
                clubs_data.append(
                    {
                        "id": club_obj.get("id"),
                        "name": club_obj.get("name"),
                        "member_count": club_obj.get("member_count"),
                        "sport_type": club_obj.get("sport_type"),
                    }
                )
            result["clubs"] = clubs_data
        except Exception:
            result["clubs"] = []

    # Include recent activities
    if focus_areas is None or "activities" in focus_areas:
        try:
            activities = client.get_activities(limit=activities_limit)
            activities_data = []
            for activity in activities:
                act_obj = serialize_object(activity)
                activities_data.append(
                    {
                        "id": act_obj.get("id"),
                        "name": act_obj.get("name"),
                        "sport_type": act_obj.get("sport_type"),
                        "distance": act_obj.get("distance"),
                        "moving_time": act_obj.get("moving_time"),
                        "total_elevation_gain": act_obj.get("total_elevation_gain"),
                        "start_date": act_obj.get("start_date"),
                        "average_heartrate": act_obj.get("average_heartrate"),
                        "average_watts": act_obj.get("average_watts"),
                    }
                )
            result["recent_activities"] = activities_data
        except Exception:
            result["recent_activities"] = []

    # Include scopes
    result["scopes"] = config.auth.scopes

    emit_output(result)

"""Athlete commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command, emit_output, with_client

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
@with_client
def athlete_profile(
    client: Any,
    ctx: typer.Context,
) -> None:
    """Get authenticated athlete profile.

    When called without a subcommand, returns the athlete profile.

    Examples:
        strava athlete
        strava athlete | jq '.id'
    """
    if ctx.invoked_subcommand is not None:
        return

    athlete = client.get_athlete()
    emit_output(athlete)


@app.command("stats")
@with_client
def stats(
    client: Any,
    athlete_id: Annotated[
        int | None,
        typer.Option(
            "--athlete-id",
            "-a",
            help="Athlete ID (defaults to authenticated athlete)",
        ),
    ] = None,
) -> None:
    """Get athlete statistics (YTD, all-time totals).

    Examples:
        strava athlete stats
        strava athlete stats | jq '.all_run_totals'
    """
    if athlete_id is None:
        athlete = client.get_athlete()
        athlete_id = athlete.id

    stats_data = client.get_athlete_stats(athlete_id)
    emit_output(stats_data)


@app.command("zones")
@authenticated_command
def zones(client: Any) -> Any:
    """Get athlete heart rate and power zones.

    Examples:
        strava athlete zones
        strava athlete zones | jq '.heart_rate'
    """
    return client.get_athlete_zones()

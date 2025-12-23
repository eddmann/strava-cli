"""Gear commands."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from strava_cli.decorators import authenticated_command

app = typer.Typer(no_args_is_help=True)


@app.command("get")
@authenticated_command
def get_gear(
    client: Any,
    gear_id: Annotated[str, typer.Argument(help="Gear ID (e.g., b12345678)")],
) -> Any:
    """Get gear/equipment details.

    Gear IDs start with 'b' for bikes or 'g' for shoes.

    Examples:
        strava gear get b12345678
        strava gear get g98765432
    """
    return client.get_gear(gear_id)

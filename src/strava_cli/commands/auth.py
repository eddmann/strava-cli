"""Authentication commands."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from strava_cli import auth as auth_helpers
from strava_cli.config import Config, get_client_credentials, get_config_path
from strava_cli.decorators import emit_result
from strava_cli.output import OutputFormat, output

app = typer.Typer(no_args_is_help=True)


@app.command("login")
def login(
    scopes: Annotated[
        str | None,
        typer.Option(
            "--scopes",
            "-s",
            help="Comma-separated OAuth scopes (default: read,read_all,activity:read,...)",
        ),
    ] = None,
    port: Annotated[
        int,
        typer.Option(
            "--port",
            help="Local port for OAuth callback",
        ),
    ] = 8000,
) -> None:
    """Authenticate with Strava via OAuth.

    Opens a browser window for authorization. Requires STRAVA_CLIENT_ID
    and STRAVA_CLIENT_SECRET environment variables.
    """
    scope_list = scopes.split(",") if scopes else None

    result = auth_helpers.interactive_login(scopes=scope_list, port=port)

    if result is None:
        raise typer.Exit(2)

    # Save to config
    config = Config.load()
    config.auth.access_token = result.access_token
    config.auth.refresh_token = result.refresh_token
    config.auth.expires_at = result.expires_at
    config.auth.athlete_id = result.athlete_id
    config.auth.scopes = result.scopes
    config.save()

    # Output result
    output_data = {
        "athlete_id": result.athlete_id,
        "expires_at": result.expires_at,
        "scopes": result.scopes,
        "config_path": str(get_config_path()),
    }
    emit_result(output_data, f"Logged in as athlete {result.athlete_id}")


@app.command("logout")
def logout(
    revoke: Annotated[
        bool,
        typer.Option(
            "--revoke",
            "-r",
            help="Revoke token on Strava server (not just local)",
        ),
    ] = False,
) -> None:
    """Log out and clear stored credentials.

    Use --revoke to also invalidate the token on Strava's servers.
    """
    config = Config.load()

    revoked = None
    if revoke and config.auth.access_token:
        revoked = auth_helpers.deauthorize(config.auth.access_token)

    config.clear_auth()
    config.save()

    if revoke:
        output_data = {"revoked": revoked}
        human_msg = "Logged out (token revoked)" if revoked else "Logged out (revoke failed)"
    else:
        output_data = {}
        human_msg = "Logged out"

    emit_result(output_data, human_msg)


@app.command("status")
def status(
    format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format"),
    ] = OutputFormat.json,
) -> None:
    """Show current authentication status."""
    config = Config.load()

    data = {
        "authenticated": config.auth.is_authenticated(),
        "athlete_id": config.auth.athlete_id,
        "expires_at": config.auth.expires_at,
        "expired": config.auth.is_expired() if config.auth.is_authenticated() else None,
        "scopes": config.auth.scopes,
        "config_path": str(get_config_path()),
    }

    # Check if credentials are configured
    client_id, client_secret = get_client_credentials()
    data["client_configured"] = bool(client_id and client_secret)

    output(data, format=format)


@app.command("refresh")
def refresh() -> None:
    """Force refresh the access token.

    Requires STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables.
    """
    config = Config.load()

    if not config.auth.refresh_token:
        print("error: No refresh token available. Run 'strava auth login' first.", file=sys.stderr)
        raise typer.Exit(2)

    client_id, client_secret = get_client_credentials()
    if not client_id or not client_secret:
        print(
            "error: STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables required",
            file=sys.stderr,
        )
        raise typer.Exit(2)

    try:
        result = auth_helpers.refresh_access_token(
            client_id,
            client_secret,
            config.auth.refresh_token,
        )

        # Update config
        config.auth.access_token = result.access_token
        config.auth.refresh_token = result.refresh_token
        config.auth.expires_at = result.expires_at
        config.save()

        emit_result(
            {"expires_at": result.expires_at},
            f"Token refreshed (expires {result.expires_at})",
        )

    except Exception as e:
        print(f"error: Token refresh failed: {e}", file=sys.stderr)
        raise typer.Exit(1) from None

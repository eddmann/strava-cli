"""CLI tests for strava-cli.

These tests exercise the CLI through its public interface (the command line).
We mock only at the HTTP boundary (stravalib.Client and httpx for OAuth).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from strava_cli import __version__
from strava_cli.cli import app


class TestVersion:
    """Tests for version display."""

    def test_version_flag(self, cli_runner: CliRunner) -> None:
        """--version shows the version number."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short_flag(self, cli_runner: CliRunner) -> None:
        """-V shows the version number."""
        result = cli_runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestHelp:
    """Tests for help output."""

    def test_help_shows_commands(self, cli_runner: CliRunner) -> None:
        """--help shows available commands."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "activities" in result.stdout
        assert "athlete" in result.stdout
        assert "auth" in result.stdout

    def test_subcommand_help(self, cli_runner: CliRunner) -> None:
        """Subcommand --help shows subcommand options."""
        result = cli_runner.invoke(app, ["activities", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout
        assert "get" in result.stdout


class TestAuth:
    """Tests for authentication commands."""

    def test_status_shows_authenticated(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
    ) -> None:
        """auth status shows authenticated state when tokens exist."""
        result = cli_runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["authenticated"] is True
        assert data["athlete_id"] == 12345

    def test_status_shows_not_authenticated(
        self,
        cli_runner: CliRunner,
        unauthenticated_config: Path,
    ) -> None:
        """auth status shows not authenticated when no tokens."""
        result = cli_runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["authenticated"] is False

    def test_logout_clears_tokens(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
    ) -> None:
        """auth logout clears authentication tokens."""
        result = cli_runner.invoke(app, ["auth", "logout"])
        assert result.exit_code == 0
        # JSON format outputs empty object, human format says "Logged out"
        assert result.stdout.strip() in ["{}", "Logged out"]

        # Verify tokens are cleared
        status_result = cli_runner.invoke(app, ["auth", "status"])
        data = json.loads(status_result.stdout)
        assert data["authenticated"] is False

    def test_refresh_without_token_fails(
        self,
        cli_runner: CliRunner,
        unauthenticated_config: Path,
    ) -> None:
        """auth refresh fails when no refresh token exists."""
        result = cli_runner.invoke(app, ["auth", "refresh"])
        assert result.exit_code == 2
        assert "No refresh token" in result.stderr

    def test_refresh_with_token(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        env_credentials: None,
        mock_httpx_oauth: MagicMock,
    ) -> None:
        """auth refresh updates tokens when valid refresh token exists."""
        result = cli_runner.invoke(app, ["auth", "refresh"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "expires_at" in data


class TestActivities:
    """Tests for activity commands."""

    def test_list_returns_activities(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities list returns activity data."""
        result = cli_runner.invoke(app, ["activities", "list"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Morning Run"

    def test_list_with_limit(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities list respects --limit option."""
        result = cli_runner.invoke(app, ["activities", "list", "--limit", "5"])
        assert result.exit_code == 0
        # Verify the limit was passed to the client
        mock_stravalib.get_activities.assert_called_once()
        call_kwargs = mock_stravalib.get_activities.call_args
        assert call_kwargs.kwargs.get("limit") == 5

    def test_list_with_format_csv(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities list outputs CSV format."""
        result = cli_runner.invoke(app, ["--format", "csv", "activities", "list"])
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 2  # Header + data
        # CSV should have comma-separated values
        assert "," in lines[0]

    def test_get_single_activity(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities get returns a single activity."""
        result = cli_runner.invoke(app, ["activities", "get", "123456789"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == 123456789
        assert data["name"] == "Morning Run"

    def test_create_activity(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities create creates a new activity."""
        result = cli_runner.invoke(
            app,
            [
                "activities",
                "create",
                "--name",
                "Test Run",
                "--sport-type",
                "Run",
                "--start",
                "2025-01-15T08:00:00",
                "--elapsed",
                "1800",
            ],
        )
        assert result.exit_code == 0
        mock_stravalib.create_activity.assert_called_once()

    def test_delete_activity_with_confirm(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """activities delete requires confirmation."""
        # Without --yes, it should prompt (and fail in non-interactive)
        result = cli_runner.invoke(app, ["activities", "delete", "123456789"], input="y\n")
        assert result.exit_code == 0
        mock_stravalib.delete_activity.assert_called_once_with(123456789)

    def test_unauthenticated_fails(
        self,
        cli_runner: CliRunner,
        unauthenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """Commands fail with exit code 2 when not authenticated."""
        result = cli_runner.invoke(app, ["activities", "list"])
        assert result.exit_code == 2
        assert "Not authenticated" in result.stderr


class TestAthlete:
    """Tests for athlete commands."""

    def test_profile(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """athlete (without subcommand) returns athlete data."""
        result = cli_runner.invoke(app, ["athlete"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == 12345
        assert data["firstname"] == "Test"

    def test_stats(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """athlete stats returns athlete statistics."""
        result = cli_runner.invoke(app, ["athlete", "stats"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "all_ride_totals" in data


class TestSegments:
    """Tests for segment commands."""

    def test_list_starred(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """segments starred lists starred segments."""
        result = cli_runner.invoke(app, ["segments", "starred"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_get_segment(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """segments get returns segment details."""
        result = cli_runner.invoke(app, ["segments", "get", "987654"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Test Climb"


class TestRoutes:
    """Tests for route commands."""

    def test_list_routes(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """routes list returns athlete routes."""
        result = cli_runner.invoke(app, ["routes", "list"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestClubs:
    """Tests for club commands."""

    def test_list_clubs(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """clubs list returns athlete clubs."""
        result = cli_runner.invoke(app, ["clubs", "list"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


class TestGear:
    """Tests for gear commands."""

    def test_get_gear(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """gear get returns gear details."""
        result = cli_runner.invoke(app, ["gear", "get", "b12345"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Road Bike"


class TestContext:
    """Tests for context command (LLM aggregation)."""

    def test_context_aggregates_data(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """context command aggregates athlete data."""
        result = cli_runner.invoke(app, ["context"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Should include athlete info
        assert "athlete" in data
        # Should include stats
        assert "stats" in data


class TestOutputFormats:
    """Tests for different output formats."""

    def test_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """JSON format outputs valid JSON."""
        result = cli_runner.invoke(app, ["--format", "json", "activities", "list"])
        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_jsonl_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """JSONL format outputs one JSON object per line."""
        result = cli_runner.invoke(app, ["--format", "jsonl", "activities", "list"])
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line:  # Skip empty lines
                json.loads(line)  # Should be valid JSON

    def test_tsv_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """TSV format uses tab separators."""
        result = cli_runner.invoke(app, ["--format", "tsv", "activities", "list"])
        assert result.exit_code == 0
        assert "\t" in result.stdout

    def test_fields_filter(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """--fields filters output to specified fields."""
        result = cli_runner.invoke(app, ["--fields", "id,name", "activities", "list"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        # Should only have id and name fields
        assert "id" in data[0]
        assert "name" in data[0]


class TestMutationDualOutput:
    """Tests for mutation command dual output (human vs machine formats)."""

    def test_create_activity_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """create activity with human format shows human message."""
        result = cli_runner.invoke(
            app,
            [
                "--format",
                "human",
                "activities",
                "create",
                "--name",
                "Test Run",
                "--sport-type",
                "Run",
                "--start",
                "2025-01-15T08:00:00",
                "--elapsed",
                "1800",
            ],
        )
        assert result.exit_code == 0
        # Human format should show a message, not JSON
        assert "created" in result.stdout.lower()
        assert "{" not in result.stdout  # Not JSON

    def test_create_activity_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """create activity with JSON format outputs full data."""
        result = cli_runner.invoke(
            app,
            [
                "--format",
                "json",
                "activities",
                "create",
                "--name",
                "Test Run",
                "--sport-type",
                "Run",
                "--start",
                "2025-01-15T08:00:00",
                "--elapsed",
                "1800",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "id" in data

    def test_delete_activity_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """delete activity with human format shows human message."""
        result = cli_runner.invoke(
            app,
            ["--format", "human", "activities", "delete", "123456789", "--force"],
        )
        assert result.exit_code == 0
        assert "deleted" in result.stdout.lower()
        assert "123456789" in result.stdout

    def test_delete_activity_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """delete activity with JSON format outputs structured data."""
        result = cli_runner.invoke(
            app,
            ["--format", "json", "activities", "delete", "123456789", "--force"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["activity_id"] == 123456789

    def test_star_segment_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """star segment with human format shows human message."""
        result = cli_runner.invoke(
            app,
            ["--format", "human", "segments", "star", "987654"],
        )
        assert result.exit_code == 0
        assert "starred" in result.stdout.lower()

    def test_star_segment_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """star segment with JSON format outputs full data."""
        result = cli_runner.invoke(
            app,
            ["--format", "json", "segments", "star", "987654"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "name" in data

    def test_unstar_segment_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """unstar segment with human format shows human message."""
        result = cli_runner.invoke(
            app,
            ["--format", "human", "segments", "unstar", "987654"],
        )
        assert result.exit_code == 0
        assert "unstarred" in result.stdout.lower()

    def test_unstar_segment_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """unstar segment with JSON format outputs full data."""
        result = cli_runner.invoke(
            app,
            ["--format", "json", "segments", "unstar", "987654"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "name" in data

    def test_update_activity_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """update activity with human format shows human message."""
        result = cli_runner.invoke(
            app,
            ["--format", "human", "activities", "update", "123456789", "--name", "Updated Run"],
        )
        assert result.exit_code == 0
        assert "updated" in result.stdout.lower()
        assert "123456789" in result.stdout

    def test_update_activity_json_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
        mock_stravalib: MagicMock,
    ) -> None:
        """update activity with JSON format outputs full data."""
        result = cli_runner.invoke(
            app,
            ["--format", "json", "activities", "update", "123456789", "--name", "Updated Run"],
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "id" in data

    def test_logout_human_format(
        self,
        cli_runner: CliRunner,
        authenticated_config: Path,
    ) -> None:
        """logout with human format shows human message."""
        result = cli_runner.invoke(
            app,
            ["--format", "human", "auth", "logout"],
        )
        assert result.exit_code == 0
        assert "logged out" in result.stdout.lower()


class TestConfigPermissions:
    """Tests for config file security."""

    def test_config_file_permissions(
        self,
        cli_runner: CliRunner,
        tmp_config_dir: Path,
        env_credentials: None,
        mock_httpx_oauth: MagicMock,
    ) -> None:
        """Config file is created with restrictive permissions."""
        with (
            patch("strava_cli.auth.webbrowser.open"),
            patch("strava_cli.auth.start_callback_server") as mock_server,
            patch("strava_cli.auth.OAuthCallbackHandler") as mock_handler,
        ):
            # Set up OAuth callback mock
            mock_handler.auth_code = "test_code"
            mock_handler.state = None  # Will be set by the test
            mock_handler.error = None

            # Make the server return immediately
            mock_srv = MagicMock()
            mock_server.return_value = mock_srv

            # We need to capture the state and return it
            def handle_request():
                # Get the state from the auth URL that was built
                mock_handler.state = mock_handler.state or "captured_state"

            mock_srv.handle_request = handle_request

        # Verify config directory and file have correct permissions after save
        from strava_cli.config import Config

        config = Config()
        config.auth.access_token = "test_token"
        config_file = tmp_config_dir / "config.toml"
        config.save(config_file)

        # Check permissions (0o600 = owner read/write only)
        mode = config_file.stat().st_mode
        assert (mode & 0o777) == 0o600

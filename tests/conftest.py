"""Shared test fixtures for strava-cli."""

from __future__ import annotations

import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def tmp_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary config directory using XDG_CONFIG_HOME."""
    config_dir = tmp_path / "strava-cli"
    config_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return config_dir


@pytest.fixture
def authenticated_config(tmp_config_dir: Path) -> Path:
    """Create a config file with valid authentication tokens."""
    config_file = tmp_config_dir / "config.toml"
    config_file.write_text("""[auth]
access_token = "test_access_token_12345"
refresh_token = "test_refresh_token_67890"
expires_at = 9999999999
athlete_id = 12345
scopes = ["read", "activity:read", "activity:write"]

[defaults]
format = "json"
limit = 30
""")
    return config_file


@pytest.fixture
def unauthenticated_config(tmp_config_dir: Path) -> Path:
    """Create a config file without authentication."""
    config_file = tmp_config_dir / "config.toml"
    config_file.write_text("""[auth]

[defaults]
format = "json"
limit = 30
""")
    return config_file


@pytest.fixture
def env_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up Strava API credentials in environment."""
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "test_secret_abc123")


class MockModel:
    """A simple mock object that serializes properly.

    Unlike MagicMock, this doesn't auto-create attributes, so the output
    serialization code can iterate over __dict__ correctly.
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def mock_stravalib() -> Generator[MagicMock, None, None]:
    """Mock stravalib.Client at the module boundary.

    This is our HTTP boundary - stravalib makes the actual API calls.
    We use MockModel objects that serialize properly via __dict__.
    """
    with patch("strava_cli.client.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Configure default return values for common methods
        mock_client.access_token = None

        # Athlete data
        mock_athlete = MockModel(
            id=12345,
            firstname="Test",
            lastname="User",
            city="San Francisco",
            country="United States",
            premium=True,
        )
        mock_client.get_athlete.return_value = mock_athlete

        # Athlete stats
        mock_stats = MockModel(
            all_ride_totals=MockModel(count=100, distance=5000000, moving_time=360000),
            all_run_totals=MockModel(count=50, distance=500000, moving_time=180000),
            ytd_ride_totals=MockModel(count=10, distance=500000, moving_time=36000),
            ytd_run_totals=MockModel(count=5, distance=50000, moving_time=18000),
        )
        mock_client.get_athlete_stats.return_value = mock_stats

        # Activities
        mock_activity = MockModel(
            id=123456789,
            name="Morning Run",
            type="Run",
            sport_type="Run",
            distance=5000.0,
            moving_time=1800,
            elapsed_time=1900,
            total_elevation_gain=50.0,
            start_date="2025-01-15T08:00:00Z",
            start_date_local="2025-01-15T08:00:00",
            average_speed=2.78,
            max_speed=3.5,
            average_heartrate=145,
            max_heartrate=165,
        )
        mock_client.get_activities.return_value = iter([mock_activity])
        mock_client.get_activity.return_value = mock_activity

        # Create activity returns the created activity
        mock_client.create_activity.return_value = mock_activity

        # Segments
        mock_segment = MockModel(
            id=987654,
            name="Test Climb",
            distance=2000.0,
            average_grade=5.0,
            maximum_grade=12.0,
            elevation_high=500.0,
            elevation_low=400.0,
        )
        mock_client.get_segment.return_value = mock_segment
        mock_client.get_starred_segments.return_value = iter([mock_segment])

        # Routes
        mock_route = MockModel(
            id=111222,
            name="Sunday Loop",
            distance=50000.0,
            elevation_gain=500.0,
        )
        mock_client.get_routes.return_value = iter([mock_route])
        mock_client.get_route.return_value = mock_route

        # Clubs
        mock_club = MockModel(
            id=555666,
            name="Test Cycling Club",
            member_count=100,
            city="San Francisco",
        )
        mock_client.get_athlete_clubs.return_value = iter([mock_club])
        mock_client.get_club.return_value = mock_club
        mock_client.get_club_members.return_value = iter([mock_athlete])
        mock_client.get_club_activities.return_value = iter([mock_activity])

        # Gear
        mock_gear = MockModel(
            id="b12345",
            name="Road Bike",
            distance=10000000.0,
            brand_name="Specialized",
            model_name="Tarmac",
        )
        mock_client.get_gear.return_value = mock_gear

        # Zones
        mock_zones = MockModel(
            heart_rate=MockModel(
                zones=[
                    MockModel(min=0, max=120),
                    MockModel(min=120, max=150),
                    MockModel(min=150, max=170),
                    MockModel(min=170, max=185),
                    MockModel(min=185, max=220),
                ]
            )
        )
        mock_client.get_athlete_zones.return_value = mock_zones

        yield mock_client


@pytest.fixture
def mock_httpx_oauth() -> Generator[MagicMock, None, None]:
    """Mock httpx calls for OAuth token exchange.

    This mocks the direct httpx calls in auth.py for OAuth flow.
    """
    with patch("strava_cli.auth.httpx.Client") as mock_httpx_class:
        mock_httpx = MagicMock()
        mock_httpx_class.return_value.__enter__ = MagicMock(return_value=mock_httpx)
        mock_httpx_class.return_value.__exit__ = MagicMock(return_value=False)

        # Default OAuth token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_at": int(time.time()) + 21600,  # 6 hours from now
            "athlete": {"id": 12345},
            "scope": "read,activity:read,activity:write",
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        yield mock_httpx

"""Client wrapper tests for strava-cli."""

from __future__ import annotations

from unittest.mock import patch

from strava_cli.client import StravaClient
from strava_cli.config import Config


def test_get_upload_fetches_upload_endpoint() -> None:
    """get_upload uses stravalib's upload endpoint protocol."""
    config = Config()
    config.auth.access_token = "test_access_token"
    config.auth.expires_at = 9999999999

    with patch("strava_cli.client.Client") as client_class:
        mock_client = client_class.return_value
        mock_client.protocol.get.return_value = {
            "id": 777888,
            "activity_id": None,
            "status": "Your activity is still being processed.",
            "error": None,
        }

        upload = StravaClient(config).get_upload(777888)

    mock_client.protocol.get.assert_called_once_with(
        "/uploads/{upload_id}",
        upload_id=777888,
        check_for_errors=False,
    )
    assert upload.upload_id == 777888
    assert upload.status == "Your activity is still being processed."


def test_get_upload_returns_error_status_without_raising() -> None:
    """get_upload lets callers decide how to present upload errors."""
    config = Config()
    config.auth.access_token = "test_access_token"
    config.auth.expires_at = 9999999999

    with patch("strava_cli.client.Client") as client_class:
        mock_client = client_class.return_value
        mock_client.protocol.get.return_value = {
            "id": 777888,
            "activity_id": None,
            "status": "There was an error processing your activity.",
            "error": "duplicate of activity 123",
        }

        upload = StravaClient(config).get_upload(777888)

    assert upload.upload_id == 777888
    assert upload.error == "duplicate of activity 123"

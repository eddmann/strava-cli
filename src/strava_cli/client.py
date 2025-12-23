"""Stravalib client wrapper with auto-refresh and error handling."""

from __future__ import annotations

from stravalib import Client
from stravalib.exc import AccessUnauthorized, RateLimitExceeded

from strava_cli.config import Config, get_client_credentials
from strava_cli.exceptions import (
    AuthenticationError,
    MissingCredentialsError,
    RateLimitError,
    TokenRefreshError,
)


class StravaClient:
    """Wrapper around stravalib Client with token management."""

    def __init__(self, config: Config, profile: str | None = None):
        """Initialize the Strava client.

        Args:
            config: Application configuration
            profile: Optional profile name to use
        """
        self.config = config
        self.profile = profile
        self.auth = config.get_profile(profile)
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create the stravalib Client."""
        if self._client is None:
            self._client = Client()
            if self.auth.access_token:
                self._client.access_token = self.auth.access_token
        return self._client

    def is_authenticated(self) -> bool:
        """Check if we have valid authentication."""
        return self.auth.is_authenticated()

    def ensure_authenticated(self) -> None:
        """Ensure we have valid authentication, refreshing if needed.

        Raises:
            AuthenticationError: If not authenticated
            TokenRefreshError: If token refresh fails
        """
        if not self.is_authenticated():
            raise AuthenticationError()

        # Check if token is expired and refresh if we can
        if self.auth.is_expired() and self.auth.refresh_token and not self.refresh_token():
            raise TokenRefreshError("Unable to refresh expired token")

    def refresh_token(self) -> bool:
        """Refresh the access token.

        Returns:
            True if successful, False otherwise

        Raises:
            MissingCredentialsError: If client credentials not configured
            TokenRefreshError: If no refresh token available
        """
        client_id, client_secret = get_client_credentials()
        if not client_id or not client_secret:
            raise MissingCredentialsError()

        if not self.auth.refresh_token:
            raise TokenRefreshError("No refresh token available")

        try:
            response = self.client.refresh_access_token(
                client_id=int(client_id),
                client_secret=client_secret,
                refresh_token=self.auth.refresh_token,
            )

            # Update auth config
            self.auth.access_token = response["access_token"]
            self.auth.refresh_token = response["refresh_token"]
            self.auth.expires_at = response["expires_at"]

            # Update client
            self._client = None  # Reset client to pick up new token

            # Save to config
            self.config.save()

            return True

        except Exception as e:
            raise TokenRefreshError(str(e)) from e

    def handle_rate_limit(self, exc: RateLimitExceeded) -> None:
        """Handle rate limit errors.

        Raises:
            RateLimitError: Always raised with info from the exception
        """
        # Extract retry-after if available from exception
        raise RateLimitError()

    def handle_unauthorized(self, exc: AccessUnauthorized) -> None:
        """Handle unauthorized errors.

        Raises:
            AuthenticationError: If token refresh fails or not available
        """
        # Try to refresh token
        if self.auth.refresh_token:
            try:
                self.refresh_token()
                return  # Caller should retry
            except Exception:
                pass  # Fall through to raise auth error

        raise AuthenticationError(
            "Unauthorized. Your token may have expired.",
            hint="Run 'strava auth login' to re-authenticate.",
        )

    # Activity methods
    def get_activity(self, activity_id: int, include_all_efforts: bool = False):
        """Get a single activity."""
        self.ensure_authenticated()
        return self.client.get_activity(activity_id, include_all_efforts=include_all_efforts)

    def get_activities(
        self,
        before: str | None = None,
        after: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ):
        """Get athlete activities."""
        self.ensure_authenticated()
        from datetime import datetime

        before_dt = datetime.fromisoformat(before) if before else None
        after_dt = datetime.fromisoformat(after) if after else None

        # stravalib returns a generator, convert to list
        activities = self.client.get_activities(
            before=before_dt,
            after=after_dt,
            limit=limit,
        )
        return list(activities)

    def create_activity(
        self,
        name: str,
        sport_type: str,
        start_date_local: str,
        elapsed_time: int,
        description: str | None = None,
        distance: float | None = None,
        trainer: bool = False,
        commute: bool = False,
    ):
        """Create a manual activity."""
        self.ensure_authenticated()
        from datetime import datetime

        return self.client.create_activity(
            name=name,
            sport_type=sport_type,
            start_date_local=datetime.fromisoformat(start_date_local),
            elapsed_time=elapsed_time,
            description=description,
            distance=distance,
            trainer=trainer,
            commute=commute,
        )

    def update_activity(
        self,
        activity_id: int,
        name: str | None = None,
        sport_type: str | None = None,
        description: str | None = None,
        trainer: bool | None = None,
        commute: bool | None = None,
        gear_id: str | None = None,
    ):
        """Update an activity."""
        self.ensure_authenticated()
        return self.client.update_activity(
            activity_id=activity_id,
            name=name,
            sport_type=sport_type,
            description=description,
            trainer=trainer,
            commute=commute,
            gear_id=gear_id,
        )

    def delete_activity(self, activity_id: int) -> None:
        """Delete an activity."""
        self.ensure_authenticated()
        self.client.delete_activity(activity_id)

    def get_activity_streams(
        self,
        activity_id: int,
        keys: list[str] | None = None,
    ):
        """Get activity streams."""
        self.ensure_authenticated()
        if keys is None:
            keys = [
                "time",
                "distance",
                "latlng",
                "altitude",
                "heartrate",
                "cadence",
                "watts",
                "temp",
                "moving",
                "grade_smooth",
            ]
        return self.client.get_activity_streams(activity_id, types=keys)

    def get_activity_laps(self, activity_id: int):
        """Get activity laps."""
        self.ensure_authenticated()
        return list(self.client.get_activity_laps(activity_id))

    def get_activity_zones(self, activity_id: int):
        """Get activity zones."""
        self.ensure_authenticated()
        return self.client.get_activity_zones(activity_id)

    def get_activity_comments(self, activity_id: int):
        """Get activity comments."""
        self.ensure_authenticated()
        return list(self.client.get_activity_comments(activity_id))

    def get_activity_kudos(self, activity_id: int):
        """Get activity kudos."""
        self.ensure_authenticated()
        return list(self.client.get_activity_kudos(activity_id))

    # Athlete methods
    def get_athlete(self):
        """Get authenticated athlete."""
        self.ensure_authenticated()
        return self.client.get_athlete()

    def get_athlete_stats(self, athlete_id: int):
        """Get athlete stats."""
        self.ensure_authenticated()
        return self.client.get_athlete_stats(athlete_id)

    def get_athlete_zones(self):
        """Get athlete zones."""
        self.ensure_authenticated()
        return self.client.get_athlete_zones()

    # Segment methods
    def get_segment(self, segment_id: int):
        """Get a segment."""
        self.ensure_authenticated()
        return self.client.get_segment(segment_id)

    def get_starred_segments(self, limit: int | None = None):
        """Get starred segments."""
        self.ensure_authenticated()
        return list(self.client.get_starred_segments(limit=limit))

    def star_segment(self, segment_id: int, starred: bool = True):
        """Star or unstar a segment."""
        self.ensure_authenticated()
        return self.client.star_segment(segment_id, starred=starred)

    def explore_segments(
        self,
        bounds: tuple[float, float, float, float],
        activity_type: str | None = None,
    ):
        """Explore segments in a bounding box."""
        self.ensure_authenticated()
        return self.client.explore_segments(bounds, activity_type=activity_type)

    # Segment efforts
    def get_segment_effort(self, effort_id: int):
        """Get a segment effort."""
        self.ensure_authenticated()
        return self.client.get_segment_effort(effort_id)

    def get_segment_efforts(
        self,
        segment_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        """Get segment efforts."""
        self.ensure_authenticated()
        from datetime import datetime

        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        return list(
            self.client.get_segment_efforts(segment_id, start_date_local=start, end_date_local=end)
        )

    # Route methods
    def get_routes(self, athlete_id: int | None = None, limit: int | None = None):
        """Get athlete routes."""
        self.ensure_authenticated()
        if athlete_id is None:
            athlete = self.get_athlete()
            athlete_id = athlete.id
        return list(self.client.get_routes(athlete_id=athlete_id, limit=limit))

    def get_route(self, route_id: int):
        """Get a route."""
        self.ensure_authenticated()
        return self.client.get_route(route_id)

    def get_route_streams(self, route_id: int):
        """Get route streams."""
        self.ensure_authenticated()
        return self.client.get_route_streams(route_id)

    # Club methods
    def get_athlete_clubs(self):
        """Get athlete clubs."""
        self.ensure_authenticated()
        return list(self.client.get_athlete_clubs())

    def get_club(self, club_id: int):
        """Get a club."""
        self.ensure_authenticated()
        return self.client.get_club(club_id)

    def get_club_members(self, club_id: int, limit: int | None = None):
        """Get club members."""
        self.ensure_authenticated()
        return list(self.client.get_club_members(club_id, limit=limit))

    def get_club_activities(self, club_id: int, limit: int | None = None):
        """Get club activities."""
        self.ensure_authenticated()
        return list(self.client.get_club_activities(club_id, limit=limit))

    # Gear methods
    def get_gear(self, gear_id: str):
        """Get gear details."""
        self.ensure_authenticated()
        return self.client.get_gear(gear_id)

    # Upload methods
    def upload_activity(
        self,
        file_path: str,
        data_type: str,
        name: str | None = None,
        description: str | None = None,
        sport_type: str | None = None,
        trainer: bool = False,
        commute: bool = False,
        external_id: str | None = None,
    ):
        """Upload an activity file."""
        self.ensure_authenticated()
        with open(file_path, "rb") as f:
            return self.client.upload_activity(
                activity_file=f,
                data_type=data_type,
                name=name,
                description=description,
                sport_type=sport_type,
                trainer=trainer,
                commute=commute,
                external_id=external_id,
            )

    def get_upload(self, upload_id: int):
        """Get upload status."""
        self.ensure_authenticated()
        return self.client.get_upload(upload_id)


def get_client(config: Config | None = None, profile: str | None = None) -> StravaClient:
    """Get a configured Strava client.

    Args:
        config: Optional config, loads default if not provided
        profile: Optional profile name

    Returns:
        Configured StravaClient
    """
    if config is None:
        config = Config.load()
    return StravaClient(config, profile)

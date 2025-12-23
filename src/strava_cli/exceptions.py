"""Custom exceptions for strava-cli."""

from __future__ import annotations


class StravaCLIError(Exception):
    """Base exception for all strava-cli errors.

    Attributes:
        message: Human-readable error message
        exit_code: Exit code to use (default: 1)
        hint: Optional hint for resolution
    """

    exit_code: int = 1

    def __init__(
        self,
        message: str,
        exit_code: int | None = None,
        hint: str | None = None,
    ) -> None:
        self.message = message
        if exit_code is not None:
            self.exit_code = exit_code
        self.hint = hint
        super().__init__(message)


class AuthenticationError(StravaCLIError):
    """Authentication required or failed.

    Exit code: 2 (standard for auth errors)
    """

    exit_code = 2

    def __init__(
        self,
        message: str = "Not authenticated. Run 'strava auth login' first.",
        hint: str | None = None,
    ) -> None:
        super().__init__(message, hint=hint)


class TokenExpiredError(AuthenticationError):
    """Access token has expired and could not be refreshed."""

    def __init__(self) -> None:
        super().__init__(
            "Access token expired and refresh failed.",
            hint="Run 'strava auth login' to re-authenticate.",
        )


class TokenRefreshError(AuthenticationError):
    """Failed to refresh access token."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Token refresh failed: {reason}",
            hint="Run 'strava auth login' to re-authenticate.",
        )


class ConfigurationError(StravaCLIError):
    """Configuration error (missing env vars, bad config file).

    Exit code: 2 (configuration is required to proceed)
    """

    exit_code = 2


class MissingCredentialsError(ConfigurationError):
    """Client credentials not configured."""

    def __init__(self) -> None:
        super().__init__(
            "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables required.",
            hint="See 'strava auth login --help' for setup instructions.",
        )


class RateLimitError(StravaCLIError):
    """Strava API rate limit exceeded.

    Exit code: 1 (transient error, retry later)
    """

    exit_code = 1

    def __init__(self, retry_after: int | None = None) -> None:
        msg = "Rate limit exceeded."
        if retry_after:
            msg += f" Retry after {retry_after} seconds."
        super().__init__(msg, hint="Wait and try again, or reduce request frequency.")
        self.retry_after = retry_after


class APIError(StravaCLIError):
    """General Strava API error.

    Exit code: 1
    """

    exit_code = 1

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(APIError):
    """Requested resource not found (404)."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(f"{resource} '{identifier}' not found.", status_code=404)


class ValidationError(StravaCLIError):
    """Input validation error.

    Exit code: 2 (user must fix input)
    """

    exit_code = 2


class FileError(StravaCLIError):
    """File operation error (not found, permission, etc.)."""

    exit_code = 1


class UploadError(StravaCLIError):
    """Activity upload failed."""

    exit_code = 1

    def __init__(self, message: str, upload_id: int | None = None) -> None:
        super().__init__(message)
        self.upload_id = upload_id

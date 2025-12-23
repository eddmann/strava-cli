"""OAuth authentication helpers."""

from __future__ import annotations

import http.server
import secrets
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass

import httpx

from strava_cli.config import Config, get_client_credentials, get_config_path

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"

DEFAULT_SCOPES = [
    "read",
    "read_all",
    "profile:read_all",
    "activity:read",
    "activity:read_all",
    "activity:write",
]


@dataclass
class AuthResult:
    """Result of OAuth authentication."""

    access_token: str
    refresh_token: str
    expires_at: int
    athlete_id: int
    scopes: list[str]


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    auth_code: str | None = None
    state: str | None = None
    error: str | None = None

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
        elif "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            OAuthCallbackHandler.state = params.get("state", [None])[0]

        # Send response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if OAuthCallbackHandler.error:
            html = f"""
            <html><body>
            <h1>Authentication Failed</h1>
            <p>Error: {OAuthCallbackHandler.error}</p>
            <p>You can close this window.</p>
            </body></html>
            """
        else:
            html = """
            <html><body>
            <h1>Authentication Successful</h1>
            <p>You can close this window and return to the terminal.</p>
            </body></html>
            """

        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def start_callback_server(port: int = 8000) -> socketserver.TCPServer:
    """Start a local server to receive the OAuth callback."""
    # Reset handler state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.state = None
    OAuthCallbackHandler.error = None

    server = socketserver.TCPServer(("localhost", port), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    return server


def build_auth_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str] | None = None,
) -> str:
    """Build the Strava authorization URL."""
    if scopes is None:
        scopes = DEFAULT_SCOPES

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": ",".join(scopes),
        "state": state,
    }

    return f"{STRAVA_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
) -> AuthResult:
    """Exchange authorization code for access token."""
    with httpx.Client() as client:
        response = client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()

    return AuthResult(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data["expires_at"],
        athlete_id=data["athlete"]["id"],
        scopes=data.get("scope", "").split(",") if data.get("scope") else [],
    )


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> AuthResult:
    """Refresh an expired access token."""
    with httpx.Client() as client:
        response = client.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()

    return AuthResult(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data["expires_at"],
        athlete_id=0,  # Not returned on refresh
        scopes=[],
    )


def deauthorize(access_token: str) -> bool:
    """Revoke access token."""
    try:
        with httpx.Client() as client:
            response = client.post(
                STRAVA_DEAUTH_URL,
                params={"access_token": access_token},
            )
            response.raise_for_status()
        return True
    except Exception:
        return False


def prompt_for_credentials() -> tuple[str, str] | None:
    """Prompt user for Strava API credentials with guided setup.

    Returns:
        Tuple of (client_id, client_secret) or None if cancelled
    """
    print("\nNo Strava API credentials found.", file=sys.stderr)
    print("\nTo authenticate, you need a Strava API application:", file=sys.stderr)
    print("  1. Go to https://www.strava.com/settings/api", file=sys.stderr)
    print("  2. Create an application", file=sys.stderr)
    print("  3. Set 'Authorization Callback Domain' to: localhost", file=sys.stderr)
    print("  4. Note your Client ID and Client Secret", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        client_id = input("Client ID: ").strip()
        if not client_id:
            print("error: Client ID is required", file=sys.stderr)
            return None

        client_secret = input("Client Secret: ").strip()
        if not client_secret:
            print("error: Client Secret is required", file=sys.stderr)
            return None

        return client_id, client_secret
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return None


def interactive_login(
    scopes: list[str] | None = None,
    port: int = 8000,
) -> AuthResult | None:
    """Perform interactive OAuth login flow.

    Opens browser for user authorization, starts local callback server.

    Args:
        scopes: OAuth scopes to request
        port: Port for callback server

    Returns:
        AuthResult if successful, None otherwise
    """
    config = Config.load()
    client_id, client_secret = get_client_credentials(config)

    if not client_id or not client_secret:
        result = prompt_for_credentials()
        if result is None:
            return None
        client_id, client_secret = result

        # Save credentials to config
        config.client_id = client_id
        config.client_secret = client_secret
        config.save()
        print(f"\nCredentials saved to {get_config_path()}", file=sys.stderr)

    redirect_uri = f"http://localhost:{port}/callback"
    state = secrets.token_urlsafe(16)

    auth_url = build_auth_url(client_id, redirect_uri, state, scopes)

    print("Opening browser for Strava authorization...", file=sys.stderr)
    print("\nIf browser doesn't open, visit:", file=sys.stderr)
    print(f"{auth_url}", file=sys.stderr)

    # Start callback server
    server = start_callback_server(port)

    # Open browser
    webbrowser.open(auth_url)

    # Wait for callback
    print("\nWaiting for authorization...", file=sys.stderr)

    def handle_request():
        server.handle_request()

    thread = threading.Thread(target=handle_request)
    thread.start()
    thread.join(timeout=120)

    server.server_close()

    if OAuthCallbackHandler.error:
        print(f"error: Authorization failed: {OAuthCallbackHandler.error}", file=sys.stderr)
        return None

    if not OAuthCallbackHandler.auth_code:
        print("error: No authorization code received (timeout)", file=sys.stderr)
        return None

    if OAuthCallbackHandler.state != state:
        print("error: State mismatch - possible CSRF attack", file=sys.stderr)
        return None

    print("Authorization code received, exchanging for token...", file=sys.stderr)

    try:
        result = exchange_code_for_token(
            client_id,
            client_secret,
            OAuthCallbackHandler.auth_code,
        )
        print("Authentication successful!", file=sys.stderr)
        return result
    except Exception as e:
        print(f"error: Token exchange failed: {e}", file=sys.stderr)
        return None

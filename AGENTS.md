# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

strava-cli provides Strava access from your terminal. Machine-readable output (JSON, JSONL, CSV, TSV, human tables).

## Development Commands

```bash
make install                        # Install dependencies
make run CMD="activities list"      # Run CLI command
make test                           # Run all tests
make test/test_cli.py::test_name    # Run single test
make lint                           # Check linting
make fmt                            # Format and auto-fix
make can-release                    # Full CI (lint + test)
```

## Architecture

```
src/strava_cli/
├── cli.py        # Main Typer app, global State singleton
├── client.py     # StravaClient wrapper with token refresh
├── config.py     # XDG config (~/.config/strava-cli/config.toml)
├── auth.py       # OAuth flow (local callback on port 8000)
├── output.py     # Serialization via serialize_object() using __dict__
├── decorators.py # @authenticated_command pattern
└── commands/     # Subcommand modules (activities, athlete, segments, etc.)
```

### Key Pattern

Commands use `@authenticated_command` which injects the client and auto-outputs the return value:

```python
@app.command("list")
@authenticated_command
def list_activities(client, limit: int = 30):
    return client.get_activities(limit=limit)  # Auto-serialized to JSON
```

Auth requires `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` env vars.

### Testing

Tests mock stravalib at HTTP boundary using `MockModel` (in `conftest.py`) since MagicMock doesn't serialize via `__dict__`. Key fixtures: `mock_stravalib`, `authenticated_config`, `cli_runner`.

### Exceptions

Custom hierarchy in `exceptions.py`. Exit codes: 2 = user action required, 1 = transient error.

### Data Units

All metric: distances (meters), times (seconds), speeds (m/s), elevation (meters), dates (ISO8601).

# Strava CLI

![Strava CLI](docs/heading.png)

Strava from your terminal. Pipe it, script it, automate it.

> Exploring CLI tools as skills for AI agents. [Background below](#background).

## Features

- All your Strava data — activities, stats, segments, routes, clubs, gear
- Script and automate — composable with jq, pipes, xargs, and standard Unix tools
- [AI agent ready](#ai-agent-integration) — install the skill for Claude, Cursor, and other assistants
- Flexible output — JSON for scripts, CSV for spreadsheets, tables for humans

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/eddmann/strava-cli/main/install.sh | sh
```

Downloads the pre-built binary for your platform (macOS/Linux) to `~/.local/bin`.

### Using uv/pipx

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install git+https://github.com/eddmann/strava-cli.git
```

### From Source

```bash
git clone https://github.com/eddmann/strava-cli
cd strava-cli
uv sync
uv run strava --help
```

## Quick Start

### 1. Authenticate

```bash
strava auth login
```

First time? You'll be guided to create a Strava API application:

1. Go to https://www.strava.com/settings/api
2. Create an application (set callback domain to `localhost`)
3. Enter your Client ID and Client Secret when prompted

Credentials and tokens are stored in `~/.config/strava-cli/config.toml`.

### 2. Use the CLI

```bash
# List recent activities
strava activities list --limit 10

# Get a specific activity
strava activities get 12345678

# Get your athlete profile
strava athlete

# Get your stats
strava athlete stats
```

## Command Reference

### Global Options

| Flag          | Short | Description                                                     |
| ------------- | ----- | --------------------------------------------------------------- |
| `--format`    | `-f`  | Output format: `json` (default), `jsonl`, `csv`, `tsv`, `human` |
| `--fields`    |       | Comma-separated list of fields to include                       |
| `--no-header` |       | Omit header row in CSV/TSV output                               |
| `--verbose`   | `-v`  | Verbose output to stderr                                        |
| `--quiet`     | `-q`  | Suppress non-essential output                                   |
| `--config`    | `-c`  | Path to config file                                             |
| `--profile`   | `-p`  | Named profile to use                                            |
| `--version`   | `-V`  | Show version and exit                                           |

### Context (LLM Helper)

```bash
strava context                      # Get full context: athlete, stats, gear, clubs, recent activities
strava context --activities 10      # Include more recent activities
strava context --focus stats,gear   # Only specific sections
strava context --no-clubs           # Exclude clubs
```

### Authentication

```bash
strava auth login          # OAuth browser flow
strava auth logout         # Clear stored credentials
strava auth logout --revoke  # Also revoke on Strava servers
strava auth status         # Show authentication status
strava auth refresh        # Force token refresh
```

### Activities

```bash
strava activities list [--after DATE] [--before DATE] [--limit N]
strava activities get <ID> [--include-efforts]
strava activities create --name NAME --sport-type TYPE --start ISO8601 --elapsed SECS
strava activities update <ID> [--name NAME] [--description DESC]
strava activities delete <ID> [--force]
strava activities streams <ID> [--keys time,distance,heartrate,...]
strava activities laps <ID>
strava activities zones <ID>
strava activities comments <ID>
strava activities kudos <ID>
```

### Athlete

```bash
strava athlete             # Get profile
strava athlete stats       # Get statistics
strava athlete zones       # Get HR/power zones
```

### Segments

```bash
strava segments get <ID>
strava segments starred [--limit N]
strava segments star <ID>
strava segments unstar <ID>
strava segments explore --bounds SW_LAT,SW_LNG,NE_LAT,NE_LNG [--activity-type running|riding]
```

### Segment Efforts

```bash
strava efforts get <ID>
strava efforts list --segment-id <ID> [--start DATE] [--end DATE]
```

### Routes

```bash
strava routes list [--limit N]
strava routes get <ID>
strava routes export <ID> --format gpx|tcx [-o FILE]
strava routes streams <ID>
```

### Clubs

```bash
strava clubs list
strava clubs get <ID>
strava clubs members <ID> [--limit N]
strava clubs activities <ID> [--limit N]
```

### Gear

```bash
strava gear get <GEAR_ID>   # e.g., b12345678 for bikes, g12345678 for shoes
```

### Upload

```bash
strava upload <FILE> [--data-type fit|gpx|tcx] [--name NAME] [--wait]
strava upload status <UPLOAD_ID>
```

## Composability

```bash
# Filter runs over 10km (distance in meters)
strava activities list | jq '.[] | select(.sport_type=="Run" and .distance > 10000)'

# Total distance this month in km
strava activities list --after 2025-12-01 | jq '[.[].distance] | add / 1000'

# Calculate pace for recent runs (min/km)
strava activities list --limit 5 | jq '.[] | select(.sport_type=="Run") | {name, pace: ((.moving_time/60) / (.distance/1000) | floor)}'
```

## Configuration

Config file location: `~/.config/strava-cli/config.toml`

```toml
[client]
id = "12345"
secret = "abc123..."

[auth]
access_token = "..."
refresh_token = "..."
expires_at = 1234567890
athlete_id = 12345
scopes = ["read", "activity:read_all", "activity:write"]

[defaults]
format = "json"
limit = 30

# Multiple profiles for different accounts
[profiles.work]
access_token = "..."
refresh_token = "..."
```

### Environment Variables

| Variable               | Description                              |
| ---------------------- | ---------------------------------------- |
| `STRAVA_CLIENT_ID`     | OAuth client ID (or use config file)     |
| `STRAVA_CLIENT_SECRET` | OAuth client secret (or use config file) |
| `STRAVA_ACCESS_TOKEN`  | Override access token                    |
| `STRAVA_REFRESH_TOKEN` | Override refresh token                   |
| `STRAVA_CONFIG`        | Config file path                         |
| `STRAVA_FORMAT`        | Default output format                    |
| `STRAVA_PROFILE`       | Default profile                          |

## AI Agent Integration

This CLI follows the [Agent Skills](https://agentskills.io/) standard — it works with Claude Code, Cursor, and other compatible AI agents. See [`SKILL.md`](SKILL.md) for the skill definition.

### Install Agent Skill

```bash
curl -fsSL https://raw.githubusercontent.com/eddmann/strava-cli/main/install-skill.sh | sh
```

Installs the skill to `~/.claude/skills/strava/` and `~/.cursor/skills/strava/`. Agents will auto-detect when you ask about Strava/fitness data.

## Development

```bash
git clone https://github.com/eddmann/strava-cli
cd strava-cli
make install                          # Install dependencies
make test                             # Run tests
make run CMD="activities list --limit 5"  # Run command
```

## Background

I recently built [strava-mcp](https://github.com/eddmann/strava-mcp), an MCP server for Strava. This got me thinking about alternative approaches to giving AI agents capabilities.

There's been a lot of discussion around the heavyweight nature of MCP. An alternative approach is to give agents [discoverable skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) via well-documented CLI tooling. Give an LLM a terminal and let it use composable CLI tools to build up functionality and solve problems — the Unix philosophy applied to AI agents.

This project is an exploration of [Claude Code Skills](https://simonwillison.net/2025/Oct/16/claude-skills/) and the emerging [Agent Skills](https://agentskills.io/) standard for AI-tool interoperability. The goal was to build a CLI that works seamlessly as both:

1. **A traditional Unix tool** — composable, pipe-friendly, machine-readable
2. **An AI agent skill** — structured output, comprehensive documentation, predictable behavior

Going forward, another approach worth exploring is going one step further than CLI and providing a [code library that agents can import and use directly](https://www.anthropic.com/engineering/code-execution-with-mcp).

## License

MIT

## Credits

Built on top of [stravalib](https://github.com/stravalib/stravalib).

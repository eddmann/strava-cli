---
name: strava
description: Query Strava fitness data including activities, athlete stats, segments, routes, clubs, and gear. Use when the user asks about cycling, running, swimming, workouts, training, or Strava data.
---

# Strava CLI Skill

Query and manage Strava data via the `strava` CLI.

## Prerequisites

- Install CLI: `curl -fsSL https://raw.githubusercontent.com/eddmann/strava-cli/main/install.sh | sh`
- Authenticate: `strava auth login` (requires `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`)

## Quick Context

Get aggregated athlete data in one call:

```bash
strava context                          # Full context: athlete, stats, gear, clubs, activities
strava context --activities 10          # More recent activities
strava context --focus stats,gear       # Specific sections only
```

## Commands

Run `strava --help` or `strava <command> --help` to discover all options.

### Activities

```bash
strava activities list [--after DATE] [--before DATE] [--limit N]
strava activities get <ID>
strava activities streams <ID> [--keys time,distance,heartrate,watts]
strava activities laps <ID>
strava activities zones <ID>
strava activities comments <ID>
strava activities kudos <ID>
```

### Athlete

```bash
strava athlete              # Profile
strava athlete stats        # YTD and all-time totals
strava athlete zones        # HR/power zones
```

### Segments & Efforts

```bash
strava segments get <ID>
strava segments starred
strava segments explore --bounds SW_LAT,SW_LNG,NE_LAT,NE_LNG
strava efforts get <ID>
strava efforts list --segment-id <ID>
```

### Routes, Clubs, Gear

```bash
strava routes list
strava routes get <ID>
strava routes streams <ID>
strava routes export <ID> --format gpx|tcx
strava clubs list
strava clubs get <ID>
strava clubs members <ID> [--limit N]
strava clubs activities <ID> [--limit N]
strava gear get <GEAR_ID>
```

## Data Units

| Field                     | Unit    |
| ------------------------- | ------- |
| distance                  | meters  |
| moving_time, elapsed_time | seconds |
| average_speed, max_speed  | m/s     |
| elevation                 | meters  |
| dates                     | ISO8601 |

## Common Patterns

```bash
# Recent activities
strava activities list --limit 10

# This month's activities
strava activities list --after 2025-12-01

# Filter with jq
strava activities list | jq '[.[] | select(.sport_type=="Run")]'

# Total distance
strava activities list | jq '[.[].distance] | add'
```

## Auth Status

```bash
strava auth status    # Check if authenticated
strava auth refresh   # Refresh token
strava auth logout    # Clear credentials
```

## Sport Types

Run, TrailRun, Walk, Hike, Ride, MountainBikeRide, GravelRide, EBikeRide, VirtualRide, VirtualRun, Swim, Workout, WeightTraining, Yoga, CrossFit, Rowing, Kayaking, Surf, Ski, Snowboard, IceSkate, Golf, Soccer, Tennis

## Exit Codes

- 0 = Success
- 1 = General error
- 2 = Auth error (run `strava auth login`)

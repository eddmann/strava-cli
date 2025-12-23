#!/bin/sh
set -e

REPO="eddmann/strava-cli"
SKILL_URL="https://raw.githubusercontent.com/${REPO}/main/SKILL.md"

echo "Installing strava-cli agent skill..."
echo ""

# Install for Claude Code
CLAUDE_DIR="${HOME}/.claude/skills/strava"
mkdir -p "$CLAUDE_DIR"
curl -fsSL "$SKILL_URL" -o "${CLAUDE_DIR}/SKILL.md"
echo "  Installed: ${CLAUDE_DIR}/SKILL.md"

# Install for Cursor
CURSOR_DIR="${HOME}/.cursor/skills/strava"
mkdir -p "$CURSOR_DIR"
curl -fsSL "$SKILL_URL" -o "${CURSOR_DIR}/SKILL.md"
echo "  Installed: ${CURSOR_DIR}/SKILL.md"

echo ""
echo "Agent skill installed for:"
echo "  - Claude Code"
echo "  - Cursor"
echo ""
echo "(Re-run this script to update)"
echo ""
echo "The skill will be auto-detected when you ask about Strava/fitness data."
echo ""
echo "Prerequisites:"
echo "  - strava-cli must be installed (curl -fsSL https://raw.githubusercontent.com/${REPO}/main/install.sh | sh)"
echo "  - Run 'strava auth login' to authenticate"

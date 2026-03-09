#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${CRONCTL_BOOTSTRAP_PYTHON:-3.11}"

cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it first: https://docs.astral.sh/uv/" >&2
  exit 1
fi

echo "==> Ensuring Python ${PYTHON_VERSION} is available"
uv python install "${PYTHON_VERSION}"

echo "==> Lockfile status"
if [ -f uv.lock ]; then
  echo "Using existing uv.lock"
else
  echo "uv.lock missing; generating one"
  uv lock --python "${PYTHON_VERSION}"
fi

echo "==> Syncing project with all extras"
uv sync --locked --all-extras --python "${PYTHON_VERSION}"

echo "==> Bootstrap complete"
echo "Next steps:"
echo "  uv run python -m cronctl init --non-interactive"
echo "  cp .mcp.json.example .mcp.json"
echo "  cp .claude/settings.cronctl.json.example ~/.claude/settings.json"

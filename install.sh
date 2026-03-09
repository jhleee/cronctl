#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${CRONCTL_INSTALL_REPO:-https://github.com/jhleee/cronctl.git}"
REPO_REF="${CRONCTL_INSTALL_REF:-main}"
INSTALL_ROOT="${CRONCTL_INSTALL_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/cronctl}"
REPO_DIR="${CRONCTL_INSTALL_REPO_DIR:-$INSTALL_ROOT/repo}"
PYTHON_VERSION="${CRONCTL_BOOTSTRAP_PYTHON:-3.11}"
AUTO_INIT="${CRONCTL_INSTALL_INIT:-1}"
COPY_MCP="${CRONCTL_INSTALL_COPY_MCP:-0}"
REGISTER_CLAUDE_MCP="${CRONCTL_INSTALL_REGISTER_CLAUDE_MCP:-0}"
SKILL_PATH="${CRONCTL_INSTALL_SKILL_PATH:-}"
AUTO_INSTALL_UV="${CRONCTL_INSTALL_UV:-1}"
UV_INSTALL_DIR="${CRONCTL_UV_INSTALL_DIR:-$HOME/.local/bin}"

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

is_true() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

ensure_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "$1 is required"
  fi
}

install_uv_if_missing() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi
  if ! is_true "$AUTO_INSTALL_UV"; then
    die "uv is required. Install it first or rerun with CRONCTL_INSTALL_UV=1."
  fi
  if ! command -v curl >/dev/null 2>&1; then
    die "uv is missing and curl is required to auto-install it."
  fi
  mkdir -p "$UV_INSTALL_DIR"
  log "Installing uv into $UV_INSTALL_DIR"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="$UV_INSTALL_DIR" sh
  export PATH="$UV_INSTALL_DIR:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    die "uv installation completed but the binary is still not on PATH."
  fi
}

clone_or_update_repo() {
  mkdir -p "$(dirname "$REPO_DIR")"
  if [ -d "$REPO_DIR/.git" ]; then
    local current_origin
    current_origin="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
    if [ -n "$current_origin" ] && [ "$current_origin" != "$REPO_URL" ]; then
      die "$REPO_DIR already points to $current_origin; expected $REPO_URL"
    fi
    if [ -n "$(git -C "$REPO_DIR" status --porcelain --untracked-files=no)" ]; then
      die "$REPO_DIR has uncommitted changes; refusing to overwrite the managed checkout."
    fi
    log "Updating checkout in $REPO_DIR"
    git -C "$REPO_DIR" fetch --depth 1 origin "$REPO_REF"
    git -C "$REPO_DIR" checkout --detach FETCH_HEAD >/dev/null 2>&1
  elif [ -e "$REPO_DIR" ]; then
    die "$REPO_DIR exists but is not a git checkout."
  else
    log "Cloning $REPO_URL into $REPO_DIR"
    git clone --branch "$REPO_REF" --depth 1 "$REPO_URL" "$REPO_DIR" >/dev/null
  fi
}

copy_mcp_template() {
  local target="$REPO_DIR/.mcp.json"
  if [ -e "$target" ]; then
    log "Leaving existing $target in place"
    return
  fi
  cp "$REPO_DIR/.mcp.json.example" "$target"
  log "Copied repo-local MCP template to $target"
}

run_init() {
  local init_args=(run python -m cronctl init --non-interactive)
  if [ -n "$SKILL_PATH" ]; then
    init_args+=(--skill-path "$SKILL_PATH")
  fi
  if is_true "$REGISTER_CLAUDE_MCP"; then
    init_args+=(--register-claude-mcp)
  fi
  (
    cd "$REPO_DIR"
    uv "${init_args[@]}"
  )
}

main() {
  ensure_command git
  install_uv_if_missing
  clone_or_update_repo

  log "Bootstrapping repository dependencies"
  CRONCTL_BOOTSTRAP_PYTHON="$PYTHON_VERSION" "$REPO_DIR/scripts/bootstrap.sh"

  log "Running doctor diagnostics"
  (
    cd "$REPO_DIR"
    uv run python -m cronctl --json doctor
  )

  if is_true "$AUTO_INIT"; then
    log "Initializing cronctl home"
    run_init
  else
    log "Skipping init because CRONCTL_INSTALL_INIT=$AUTO_INIT"
  fi

  if is_true "$COPY_MCP"; then
    copy_mcp_template
  fi

  cat <<EOF
==> Install complete
Repository: $REPO_DIR
Home: ${CRONCTL_HOME:-$HOME/.cronctl}

Next commands:
  cd "$REPO_DIR"
  uv run python -m cronctl add --id hello --schedule "* * * * *" --command "printf hello"
  uv run python -m cronctl exec hello
EOF
}

main "$@"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
INSTALL_ROOT="${AUTOLOOP_INSTALL_ROOT:-$HOME/.local/share/autoloop}"
BIN_DIR="${AUTOLOOP_BIN_DIR:-$HOME/.local/bin}"
VENV_DIR="$INSTALL_ROOT/venv"
LAUNCHER_PATH="$BIN_DIR/autoloop"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
CODEX_SKILLS_DIR="${CODEX_SKILLS_DIR:-$CODEX_HOME_DIR/skills}"
CODEX_AGENTS_SKILLS_DIR="${CODEX_AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
SKILL_NAME="autoloop"
SKILL_SOURCE_FILE="$REPO_ROOT/src/autoloop/skill/SKILL.md"
SKILL_DEST_DIR_PRIMARY="$CODEX_SKILLS_DIR/$SKILL_NAME"
SKILL_DEST_DIR_SECONDARY="$CODEX_AGENTS_SKILLS_DIR/$SKILL_NAME"

DRY_RUN=0
OVERWRITE=0
RECREATE_VENV=0
SKILL_TARGET="both"

declare -a CREATE_ITEMS=()
declare -a OVERWRITE_ITEMS=()
declare -a DELETE_ITEMS=()
declare -a SKIP_ITEMS=()
declare -a ADVISORIES=()
declare -a BLOCKERS=()
declare -a NEXT_STEPS=()
declare -a INSTALLED_SKILL_FILES=()

log() {
  printf '[autoloop-installer] %s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./install_autoloop.sh [options]

Options:
  --dry-run                  Print the install plan without changing files.
  --overwrite                Allow overwriting an existing launcher and skill files.
  --recreate-venv            Allow deleting and recreating an existing virtualenv.
  --skill-target TARGET      Install packaged skill to: both, codex, agents, or none.
  -h, --help                 Show this help text.

Notes:
  - Existing launcher and skill files are preserved unless --overwrite is passed.
  - Existing virtual environments are preserved unless --recreate-venv is passed.
  - Missing provider CLIs do not block installation; readiness is reported at the end.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "required command not found: $1"
  fi
}

append_unique() {
  local item="$1"
  shift
  local existing
  for existing in "$@"; do
    if [[ "$existing" == "$item" ]]; then
      return 0
    fi
  done
  return 1
}

add_create_item() {
  local item="$1"
  if ! append_unique "$item" "${CREATE_ITEMS[@]}"; then
    CREATE_ITEMS+=("$item")
  fi
}

add_skip_item() {
  local item="$1"
  if ! append_unique "$item" "${SKIP_ITEMS[@]}"; then
    SKIP_ITEMS+=("$item")
  fi
}

add_advisory() {
  local item="$1"
  if ! append_unique "$item" "${ADVISORIES[@]}"; then
    ADVISORIES+=("$item")
  fi
}

add_blocker() {
  local item="$1"
  if ! append_unique "$item" "${BLOCKERS[@]}"; then
    BLOCKERS+=("$item")
  fi
}

add_next_step() {
  local item="$1"
  if ! append_unique "$item" "${NEXT_STEPS[@]}"; then
    NEXT_STEPS+=("$item")
  fi
}

plan_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    add_create_item "directory: $path"
  fi
}

plan_file_write() {
  local path="$1"
  local label="$2"
  if [[ -e "$path" ]]; then
    if [[ "$OVERWRITE" == "1" ]]; then
      OVERWRITE_ITEMS+=("$label: $path")
    else
      add_blocker "$label already exists: $path (rerun with --overwrite)"
    fi
  else
    add_create_item "$label: $path"
  fi
}

plan_skill_install() {
  local target_label="$1"
  local target_root="$2"
  local skill_dir="$target_root/$SKILL_NAME"
  local skill_file="$skill_dir/SKILL.md"
  INSTALLED_SKILL_FILES+=("$skill_file")
  plan_dir "$target_root"
  plan_dir "$skill_dir"
  plan_file_write "$skill_file" "skill file ($target_label)"
}

run_or_echo() {
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  "$@"
}

write_launcher() {
  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi
  install -d "$BIN_DIR"
  cat > "$LAUNCHER_PATH" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
exec "$VENV_DIR/bin/autoloop" "\$@"
LAUNCHER
  chmod +x "$LAUNCHER_PATH"
}

print_section() {
  local heading="$1"
  shift
  local items=("$@")
  log "$heading"
  if [[ "${#items[@]}" -eq 0 ]]; then
    log "  - none"
    return 0
  fi
  local item
  for item in "${items[@]}"; do
    log "  - $item"
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --overwrite)
      OVERWRITE=1
      ;;
    --recreate-venv)
      RECREATE_VENV=1
      ;;
    --skill-target)
      shift
      [[ $# -gt 0 ]] || die "--skill-target requires one of: both, codex, agents, none"
      SKILL_TARGET="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
  shift
done

case "$SKILL_TARGET" in
  both|codex|agents|none)
    ;;
  *)
    die "invalid --skill-target value: $SKILL_TARGET"
    ;;
esac

require_cmd python3
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  die "python3 version must be 3.10 or higher."
fi

for required_path in pyproject.toml src/autoloop/main.py src/autoloop/loop_control.py src/autoloop/templates src/autoloop/skill/SKILL.md; do
  if [[ ! -e "$REPO_ROOT/$required_path" ]]; then
    die "expected $required_path in repository root: $REPO_ROOT"
  fi
done

HAS_CODEX=0
HAS_CLAUDE=0
HAS_GIT=0
PATH_READY=0
if command -v codex >/dev/null 2>&1; then
  HAS_CODEX=1
fi
if command -v claude >/dev/null 2>&1; then
  HAS_CLAUDE=1
fi
if command -v git >/dev/null 2>&1; then
  HAS_GIT=1
fi
if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
  PATH_READY=1
fi

plan_dir "$INSTALL_ROOT"
plan_dir "$BIN_DIR"

if [[ -e "$VENV_DIR" ]]; then
  if [[ "$RECREATE_VENV" == "1" ]]; then
    DELETE_ITEMS+=("existing virtualenv: $VENV_DIR")
    add_create_item "virtualenv: $VENV_DIR"
  else
    add_blocker "virtualenv already exists: $VENV_DIR (rerun with --recreate-venv)"
  fi
else
  add_create_item "virtualenv: $VENV_DIR"
fi

add_create_item "package install target: $VENV_DIR"
plan_file_write "$LAUNCHER_PATH" "launcher"

case "$SKILL_TARGET" in
  both)
    plan_skill_install "codex" "$CODEX_SKILLS_DIR"
    plan_skill_install "agents" "$CODEX_AGENTS_SKILLS_DIR"
    ;;
  codex)
    plan_skill_install "codex" "$CODEX_SKILLS_DIR"
    add_skip_item "agents skill target disabled (--skill-target=codex)"
    ;;
  agents)
    plan_skill_install "agents" "$CODEX_AGENTS_SKILLS_DIR"
    add_skip_item "codex skill target disabled (--skill-target=agents)"
    ;;
  none)
    add_skip_item "all skill installation disabled (--skill-target=none)"
    ;;
esac

if [[ "${AUTOLOOP_SKIP_PIP_UPGRADE:-0}" == "1" ]]; then
  add_skip_item "pip tooling upgrade skipped (AUTOLOOP_SKIP_PIP_UPGRADE=1)"
else
  add_create_item "pip tooling upgrade in $VENV_DIR"
fi

if [[ "${AUTOLOOP_SKIP_DEP_INSTALL:-0}" == "1" ]]; then
  add_skip_item "package dependency install skipped (AUTOLOOP_SKIP_DEP_INSTALL=1)"
else
  add_create_item "install package from $REPO_ROOT into $VENV_DIR"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  add_advisory "dry-run only; no files will be changed"
fi
if [[ "$HAS_CODEX" == "1" ]]; then
  add_advisory "Codex CLI detected on PATH"
else
  add_advisory "Codex CLI not found on PATH"
  add_next_step "Install the default provider CLI: npm i -g @openai/codex"
fi
if [[ "$HAS_CLAUDE" == "1" ]]; then
  add_advisory "Claude CLI detected on PATH"
else
  add_advisory "Claude CLI not found on PATH"
fi
add_next_step "Optional Claude path: set provider.name: claude in autoloop.yaml and verify credentials with: claude auth status"
if [[ "$HAS_GIT" == "1" ]]; then
  add_advisory "Git detected on PATH"
else
  add_advisory "Git not found on PATH; Autoloop can still run with --no-git"
  add_next_step "Optional git support: install git for checkpoints, or run Autoloop with --no-git"
fi
if [[ "$PATH_READY" == "1" ]]; then
  add_advisory "Launcher directory already present on PATH: $BIN_DIR"
else
  add_advisory "Launcher directory is not on PATH: $BIN_DIR"
  add_next_step "Add the launcher directory to PATH, for example: export PATH=\"$BIN_DIR:\$PATH\""
fi

READY=0
if [[ "$HAS_CODEX" == "1" && "$PATH_READY" == "1" ]]; then
  READY=1
fi

log "Pre-flight summary"
log "  - mode: $([[ "$DRY_RUN" == "1" ]] && printf 'dry-run' || printf 'install')"
log "  - overwrite existing launcher/skills: $([[ "$OVERWRITE" == "1" ]] && printf 'yes' || printf 'no')"
log "  - recreate existing virtualenv: $([[ "$RECREATE_VENV" == "1" ]] && printf 'yes' || printf 'no')"
log "  - skill target: $SKILL_TARGET"
print_section "Creates" "${CREATE_ITEMS[@]}"
print_section "Overwrites" "${OVERWRITE_ITEMS[@]}"
print_section "Deletes" "${DELETE_ITEMS[@]}"
print_section "Skips" "${SKIP_ITEMS[@]}"
print_section "Advisories" "${ADVISORIES[@]}"
print_section "Blockers" "${BLOCKERS[@]}"

if [[ "${#BLOCKERS[@]}" -gt 0 ]]; then
  log "Install plan blocked. Resolve the blockers and rerun."
  exit 1
fi

if [[ "$DRY_RUN" != "1" ]]; then
  log "Preparing directories"
  install -d "$INSTALL_ROOT" "$BIN_DIR"

  if [[ "$SKILL_TARGET" == "both" || "$SKILL_TARGET" == "codex" ]]; then
    log "Installing Autoloop skill to $SKILL_DEST_DIR_PRIMARY"
    install -d "$SKILL_DEST_DIR_PRIMARY"
    cp "$SKILL_SOURCE_FILE" "$SKILL_DEST_DIR_PRIMARY/SKILL.md"
  fi

  if [[ "$SKILL_TARGET" == "both" || "$SKILL_TARGET" == "agents" ]]; then
    log "Installing Autoloop skill to $SKILL_DEST_DIR_SECONDARY"
    install -d "$SKILL_DEST_DIR_SECONDARY"
    cp "$SKILL_SOURCE_FILE" "$SKILL_DEST_DIR_SECONDARY/SKILL.md"
  fi

  if [[ -e "$VENV_DIR" && "$RECREATE_VENV" == "1" ]]; then
    log "Removing existing virtual environment at $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi

  log "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"

  VENV_PYTHON="$VENV_DIR/bin/python"
  VENV_PIP="$VENV_DIR/bin/pip"

  if [[ "${AUTOLOOP_SKIP_PIP_UPGRADE:-0}" == "1" ]]; then
    log "Skipping pip tooling upgrade because AUTOLOOP_SKIP_PIP_UPGRADE=1"
  else
    log "Upgrading pip tooling (best-effort)"
    if ! "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel; then
      log "WARNING: pip tooling upgrade failed; continuing install."
    fi
  fi

  if [[ "${AUTOLOOP_SKIP_DEP_INSTALL:-0}" == "1" ]]; then
    log "Skipping package installation because AUTOLOOP_SKIP_DEP_INSTALL=1"
  else
    log "Installing Autoloop package into the virtual environment"
    "$VENV_PIP" install "$REPO_ROOT"
  fi

  log "Writing launcher to $LAUNCHER_PATH"
  write_launcher
fi

if [[ "$READY" == "1" ]]; then
  log "$([[ "$DRY_RUN" == "1" ]] && printf 'Predicted final status: installed and ready.' || printf 'Final status: installed and ready.')"
else
  log "$([[ "$DRY_RUN" == "1" ]] && printf 'Predicted final status: installed but not ready.' || printf 'Final status: installed but not ready.')"
fi

log "Next steps:"
log "  - Run: autoloop --help"
if [[ "$READY" == "1" ]]; then
  log "  - First run example: autoloop --workspace /path/to/repo --intent \"Describe the task here\""
else
  local_step=""
  for local_step in "${NEXT_STEPS[@]}"; do
    log "  - $local_step"
  done
fi

for skill_file in "${INSTALLED_SKILL_FILES[@]}"; do
  log "Skill target: $skill_file"
done
log "If your coding agent is already running, restart it to pick up updated skills."

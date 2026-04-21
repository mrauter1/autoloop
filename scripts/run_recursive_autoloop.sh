#!/usr/bin/env bash
set -euo pipefail

# Recursive Autoloop driver for framework evolution.
#
# What it does:
# 1) Creates one NEW workflow (not currently in the codebase) designed to improve SWE/architecture/research throughput.
# 2) In every subsequent cycle, forces analysis of 3 core framework improvements.
# 3) Implements the best next improvement through Autoloop plan/implement/test pairs.
#
# Requirements:
# - autoloop CLI installed and on PATH
# - run from repo root or pass --workspace

WORKSPACE="$(pwd)"
CYCLES="${CYCLES:-4}"          # total autoloop runs (>=2 recommended)
BASE_TASK_ID="${BASE_TASK_ID:-recursive-framework-evolution}"
STATE_DIR_NAME=".autoloop_recursive"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --cycles)
      CYCLES="$2"
      shift 2
      ;;
    --task-id-prefix)
      BASE_TASK_ID="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Usage: $0 [--workspace <path>] [--cycles <n>] [--task-id-prefix <slug>]" >&2
      exit 2
      ;;
  esac
done

if ! command -v autoloop >/dev/null 2>&1; then
  echo "FATAL: autoloop command not found in PATH." >&2
  exit 1
fi

if [[ ! -d "$WORKSPACE" ]]; then
  echo "FATAL: workspace does not exist: $WORKSPACE" >&2
  exit 1
fi

if ! [[ "$CYCLES" =~ ^[0-9]+$ ]] || [[ "$CYCLES" -lt 1 ]]; then
  echo "FATAL: --cycles must be a positive integer." >&2
  exit 1
fi

mkdir -p "$WORKSPACE/$STATE_DIR_NAME/tasks"

run_autoloop_cycle() {
  local cycle="$1"
  local task_id="${BASE_TASK_ID}-c${cycle}"
  local task_md="$WORKSPACE/$STATE_DIR_NAME/tasks/${task_id}.md"

  if [[ "$cycle" -eq 1 ]]; then
    cat > "$task_md" <<'TASK'
# Recursive Workflow Bootstrap (Cycle 1)

Goal: Add one **new workflow that does not exist yet** in this codebase and that materially improves recursive agentic software development.

Required workflow to add in this cycle:
- Workflow name: `architecture_research_board`

Purpose:
- Convert ambiguous product/engineering goals into decision-ready architecture options.
- Produce explicit trade-off analysis before implementation work starts.
- Improve recursive quality of future Autoloop runs by generating reusable specs/decision artifacts.

Minimum deliverables:
1. Workflow definition + invocation path in the current architecture.
2. Prompt/templates/artifacts for the new workflow.
3. Required artifacts explicitly declared and validated.
4. Tests/docs showing the workflow can be executed.

Constraints:
- Keep framework logic generic.
- Keep workflow-specific policy in workflow layer.
- Prefer structured machine-readable control outputs (JSON).
TASK
  else
    cat > "$task_md" <<TASK
# Recursive Framework Improvement (Cycle ${cycle})

Context:
- Continue improving this repository as a reusable workflow framework for multistep agentic LLM calls (Codex CLI / Claude Code).
- Read current architecture docs and existing code before changes.

Objectives for this cycle:
1. Identify exactly **3** core framework improvements that would significantly improve workflow power, reliability, or extensibility.
2. Evaluate those 3 options with explicit trade-offs.
3. Implement the best option fully in this cycle.
4. Update docs/tests accordingly.

Selection criteria:
- leverage across workflows
- implementation risk
- operational reliability
- developer ergonomics
- extensibility

Output requirements:
- Add/update a short decision record with the 3 candidates and the chosen one.
- Ensure code changes are complete and tested.
TASK
  fi

  echo
  echo "=== [Cycle ${cycle}/${CYCLES}] task_id=${task_id} ==="
  echo "Task file: $task_md"

  autoloop \
    --workspace "$WORKSPACE" \
    --task-id "$task_id" \
    --intent "$(cat "$task_md")" \
    --pairs plan,implement,test \
    --full-auto-answers \
    --git
}

cycle=1
while [[ "$cycle" -le "$CYCLES" ]]; do
  run_autoloop_cycle "$cycle"
  cycle=$((cycle + 1))
done

echo
echo "Recursive autoloop sequence finished."

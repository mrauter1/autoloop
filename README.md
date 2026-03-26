# Autoloop

Protocol-driven agent loops for shipping real code with less babysitting.

Autoloop is a stateful orchestration runtime for repository work. It runs plan, implement, and test producer/verifier pairs with durable state, resumable runs, phase scoping, provider-neutral sessions, and git-backed checkpoints.

## Requirements

- Python 3.10+
- One supported provider CLI:
  - `codex` for `provider.name: codex` (default)
  - `claude` for `provider.name: claude`, with local `claude auth status` already working
- `git` is optional when running with `--no-git`

## Install

Install from PyPI:

```bash
python3 -m pip install autoloop
autoloop --help
```

Install from this repository:

```bash
python3 -m pip install -e .
autoloop --help
python3 -m autoloop --help
```

Or use the bundled installer:

```bash
./install_autoloop.sh
```

The installer sets up Autoloop itself and the packaged skill, but it does not install provider CLIs for you. Install `codex` or `claude` separately based on the provider you plan to run.
Reruns are intentionally conservative: use `./install_autoloop.sh --dry-run` to preview changes, `--overwrite` to replace an existing launcher or skill file, `--recreate-venv` to replace an existing virtualenv, and `--skill-target both|codex|agents|none` to control where the packaged skill is installed.

## Quickstart

Put config in either:

- `~/.config/autoloop/autoloop.yaml` (or `$XDG_CONFIG_HOME/autoloop/autoloop.yaml`) for global defaults
- `/path/to/workspace/autoloop.yaml` for workspace-local overrides

Minimal Codex config:

```yaml
provider:
  name: codex
```

Minimal Claude config:

```yaml
provider:
  name: claude
```

First run:

```bash
autoloop --workspace /path/to/workspace --intent "Describe the task you want shipped"
```

Expected success artifacts under the workspace:

- `.autoloop/tasks/<task-id>/request.md`
- `.autoloop/tasks/<task-id>/runs/<run-id>/raw_phase_log.md`
- `.autoloop/tasks/<task-id>/runs/<run-id>/events.jsonl`

Useful follow-up commands:

```bash
autoloop --workspace /path/to/workspace --list-tasks
autoloop --workspace /path/to/workspace --task-id <task-id> --resume
```

Troubleshooting:

| Symptom | Fix |
| --- | --- |
| `codex` is missing for the default setup | Install Codex with `npm i -g @openai/codex`, or switch to `provider.name: claude` and verify `claude auth status`. |
| `autoloop` command is not found after running the installer | Add the installer bin directory to `PATH`, or run `python3 -m autoloop --help` from the repo checkout. |
| Autoloop is not picking up your config | Put exactly one `autoloop.yaml` or `autoloop.config` file in the global config directory or workspace root. |
| `git` is unavailable | Install `git`, or run Autoloop with `--no-git` if you do not need checkpoints. |

## Configuration

Autoloop reads configuration from these directories, in this order:

1. `$XDG_CONFIG_HOME/autoloop/` or `~/.config/autoloop/`
2. the selected workspace root passed to `--workspace`

Within each directory it looks for:

- `autoloop.yaml`
- `autoloop.config`
- legacy read-only fallback: `superloop.yaml`
- legacy read-only fallback: `superloop.config`

If more than one config file exists in the same directory, Autoloop fails fast instead of guessing.

Use the nested provider shape for new configs:

```yaml
provider:
  name: codex
  codex:
    model: gpt-5.4
    model_effort: null
  claude:
    model: null
    effort: null
    permission_strategy: inherit
runtime:
  pairs: plan,implement,test
  max_iterations: 15
  phase_mode: single
  intent_mode: preserve
  full_auto_answers: false
  no_git: false
```

Notes:

- Legacy flat Codex keys `provider.model` and `provider.model_effort` are still read for backward compatibility.
- `--model` and `--model-effort` are Codex-only CLI overrides.
- Claude defaults intentionally inherit the operator's existing Claude Code environment. Default Claude runs do not add strict mode, `--bare`, tool restriction flags, or `stream-json`.
- `runtime.full_auto_answers` now uses the active provider instead of being Codex-only.

## Runtime State

Fresh runs write state under `.autoloop/`.

For the first Autoloop release, resume and task listing can still read legacy `.superloop/` workspaces when no `.autoloop/` state exists for the requested task or run.

Session files now store provider-neutral `provider` and `session_id` fields. Legacy Codex session files that only contain `thread_id` remain load-compatible.

## Claude Validation

Maintainer live-validation steps for inherited-environment Claude repos and resume config-drift checks are recorded in [docs/claude_rollout_checklist.md](docs/claude_rollout_checklist.md).

## Skill

The packaged Autoloop skill lives at `src/autoloop/skill/SKILL.md`.

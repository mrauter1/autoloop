# Autoloop Improvement Plan

## Scope

Implement four user-facing changes in one coherent slice:
- harden `install_autoloop.sh` against silent overwrites and destructive reruns
- add a first-run quickstart to `README.md`
- make installer readiness outcomes explicit without blocking on missing provider CLIs
- remove the hidden `--no-no-git` parser branch while preserving existing `no_git` precedence

## Current State

- `install_autoloop.sh` always writes both skill targets, unconditionally `rm -rf`s the virtualenv, has no argument parsing, and only prints advisory provider CLI checks.
- `src/autoloop/main.py` already implements deterministic runtime precedence as builtins < global config < workspace config < CLI; the only git-flag UX defect is the hidden `--no-no-git` alias.
- `README.md` documents install and full configuration, but it does not contain a concise first-run path with expected artifacts, resume/list commands, or troubleshooting.

## Implementation Milestones

### 1. Harden installer mutation planning

- Add shell argument parsing to `install_autoloop.sh` for:
  - `--dry-run`
  - `--overwrite`
  - `--recreate-venv`
  - `--skill-target <both|codex|agents|none>`
- Compute the full mutation plan before any filesystem writes.
- Print a pre-flight summary that clearly distinguishes creates, overwrites, skips, deletions, and post-install advisories.
- Change default rerun behavior so existing install artifacts are not silently overwritten.
- Require `--recreate-venv` before deleting an existing venv, even when `--overwrite` is present.

### 2. Separate install success from readiness

- Keep provider CLI detection non-fatal.
- Emit one explicit final state:
  - `installed and ready`
  - `installed but not ready`
- Define readiness for installer messaging around the default first-run path the installer can honestly guarantee today:
  - `installed and ready` means installation succeeded and the default Codex-backed run path is usable without further provider setup.
  - `installed but not ready` means installation succeeded but the operator still needs provider setup before the default run path will work.
- Print exact next-step commands/messages for:
  - missing `codex` on the default path
  - opting into Claude instead of Codex (`provider.name: claude` plus `claude auth status`)
  - missing `git`
  - missing `PATH` exposure

### 3. Add README quickstart

- Add a concise quickstart section near install/configuration that includes:
  - where global and workspace `autoloop.yaml` files live
  - minimal Codex config
  - minimal Claude config
  - first run command
  - expected `.autoloop/` success artifacts
  - `--resume` and `--list-tasks` examples
  - a short troubleshooting table covering missing provider CLI/auth, config placement, and optional git
- Keep the existing detailed configuration section as the deeper reference instead of duplicating every option in quickstart.

### 4. Clean up git flag UX without changing precedence

- Remove the hidden `--no-no-git` argument from `build_arg_parser()`.
- Keep public `--git` and `--no-git` behavior unchanged.
- Do not change `_merge_runtime_config()` precedence rules.
- Update parser/config tests so they cover:
  - help output contains only the public flag pair
  - default CLI value remains `None`
  - `--git` overrides config `runtime.no_git: true`
  - `--no-git` overrides config `runtime.no_git: false`

### 5. Validate touched surfaces

- Add installer-focused regression coverage with subprocess-based tests that use temp directories and skip real dependency installation via existing env toggles.
- Re-run README/install-script resource tests and git/runtime precedence tests.

## Interface Definitions

### Installer contract

- `--dry-run`: print the same pre-flight plan and default-path readiness summary as a real install, but do not mutate the filesystem or run `pip`.
- `--overwrite`: allow replacing existing non-venv install artifacts selected by the plan (launcher, skill files/directories).
- `--recreate-venv`: explicitly authorize deleting and recreating an existing `$INSTALL_ROOT/venv`.
- `--skill-target <both|codex|agents|none>`: choose which packaged skill destinations are acted on; default remains `both` for backward compatibility.
- Existing env vars remain the path source of truth:
  - `AUTOLOOP_INSTALL_ROOT`
  - `AUTOLOOP_BIN_DIR`
  - `CODEX_HOME`
  - `CODEX_SKILLS_DIR`
  - `CODEX_AGENTS_SKILLS_DIR`

### Behavior boundaries

- Missing provider CLIs must never abort the installer.
- Readiness must not be based on “any supported provider present”; it must reflect the default Codex first-run path or clearly state the extra steps needed to switch providers.
- Missing `git` remains advisory because runtime `--no-git` support already exists.
- Removing `--no-no-git` is an intentional UX cleanup of an undocumented internal alias; no other CLI semantics should change.

## Compatibility Notes

- The installer becomes intentionally stricter on reruns. Existing installs may now require `--overwrite` and, separately, `--recreate-venv` to proceed. This is the requested safety change and should be documented in installer help/output.
- Default skill installation footprint stays aligned with current behavior (`both`) unless the operator narrows it.
- Because Autoloop currently defaults to Codex, the installer’s global ready/not-ready status should reflect Codex readiness for the out-of-the-box path. Claude remains supported, but the final output must tell Claude-only operators how to switch provider config and verify auth instead of claiming the default path is ready.
- Runtime config and CLI precedence for `no_git` remain unchanged.

## Regression Risks And Controls

| Risk | Why it matters | Control |
| --- | --- | --- |
| Dry-run output drifts from real execution | Users could approve a plan that the real installer does not follow | Drive both dry-run and real execution from the same computed mutation decisions |
| Installer becomes too strict or half-mutates on reruns | Existing users may be left with partial installs | Do all conflict detection before writes and fail before mutation when required flags are missing |
| Readiness messaging becomes misleading | The installer could claim the system is ready even when the default first run will fail | Base the final ready/not-ready state on the default Codex path and emit provider-specific next steps for optional Claude setup |
| Git flag cleanup changes runtime behavior | `no_git` precedence is already relied on by tests and existing users | Limit code change to parser wiring/help text and preserve `_merge_runtime_config()` behavior |
| README quickstart drifts from actual commands/artifacts | New users will follow it literally | Keep commands tied to current CLI/state layout and cover key README strings in tests where practical |

## Validation Plan

- Installer tests:
  - dry-run against empty temp install root
  - rerun against existing artifacts without `--overwrite` fails before mutation
  - existing venv requires `--recreate-venv`
  - skill target selection limits writes to requested destinations
  - final status wording distinguishes ready vs not ready for the default Codex path
  - environment with only `claude` installed reports `installed but not ready` and prints the Claude opt-in/config guidance
  - environment with `codex` installed reports `installed and ready`
- Runtime/parser tests:
  - targeted `tests/test_autoloop_observability.py` coverage for git flags and config precedence
- Docs/resource tests:
  - `tests/test_module_entrypoint.py`
  - `tests/test_resources.py`

## Rollout / Rollback

- Roll out as a single small change set so README, installer behavior, and tests land together.
- If installer regressions appear, first rollback the new shell flags and strict conflict gating while preserving doc-only improvements and parser test cleanup separately.
- Only restore `--no-no-git` if real external dependency evidence appears; otherwise keep the cleanup.

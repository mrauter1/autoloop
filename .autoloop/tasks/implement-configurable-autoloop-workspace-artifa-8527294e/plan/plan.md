# Configurable Workspace Artifact Tracking

## Goal
Add `track_autoloop_artifacts` as a runtime-level opt-out for auto-staging and auto-committing any repo-relative path under the resolved active task workspace root while leaving raw producer/verifier delta attribution and verifier scope behavior unchanged.

## Current Behavior Snapshot
- `RuntimeConfig` and CLI/config parsing currently have no artifact-tracking toggle.
- `tracked_autoloop_artifact_paths()` and `tracked_autoloop_paths()` currently exclude `runs/`, so baseline/final/task-scoped commits do not include run artifacts by default.
- Raw producer/verifier deltas are computed from git snapshots and then passed through `filter_volatile_task_run_paths()`, which currently removes `task_root_rel/runs/...`.
- Verifier scope checks use the raw verifier delta plus `verifier_exempt_runtime_artifact_paths()`; this path must stay unchanged for this feature.

## Required Interfaces
- `RuntimeConfig.track_autoloop_artifacts: bool = True`
- `RuntimeConfigOverride.track_autoloop_artifacts: Optional[bool]`
- Config file key: `runtime.track_autoloop_artifacts`
- CLI flags:
  - `--track-autoloop-artifacts`
  - `--no-track-autoloop-artifacts`
- New task-root helper:
  - classify repo-relative paths only from `task_root_rel`
  - `True` when the path equals `task_root_rel` or starts with `task_root_rel/`
- New commit-eligibility helper:
  - input: candidate paths, `task_root_rel`, `track_autoloop_artifacts`
  - behavior: pass through unchanged when tracking is enabled; drop every task-root path when disabled

## Implementation Plan
### Milestone 1: Runtime plumbing
- Extend runtime config dataclasses, config-file parsing, merge resolution, and CLI parsing with `track_autoloop_artifacts`, defaulting to `True`.
- Thread the resolved boolean through `main()` and `execute_pair_cycles()` so every git commit path decision can see the same run-level setting.
- Keep `--no-git` behavior unchanged apart from carrying the extra resolved field harmlessly.

### Milestone 2: Centralize commit eligibility and ignore handling
- Update tracked-path helpers so the active task workspace root includes `runs/` by default; do not keep a manual allow/deny list for task-root files.
- Add the task-root classifier plus commit-eligibility filter, and apply them only at auto-stage/auto-commit decision points.
- Extend the central commit helpers rather than scattering filtering across call sites so all existing flows are covered:
  - baseline tracked-artifact commits
  - pre-cycle tracked-artifact commits
  - clarification answer commits
  - producer delta commits
  - verifier completion / blocked / failure commits
  - pair completion and final run-artifact commits
- Add ignore-aware staging in the same helper layer:
  - never use force-add behavior
  - skip ignored untracked task-root paths with a warning
  - allow ignored-but-already-tracked task-root paths to stage under normal git semantics with a warning
  - no-op cleanly when filtering and ignored-path skipping leave nothing to commit
- Implement once-per-run-per-root warning suppression with a small in-memory cache shared across the run, keyed by active task root plus warning kind.

### Milestone 3: Preserve delta and verifier behavior while expanding tests
- Leave raw delta collection logic unchanged, including `filter_volatile_task_run_paths()` and snapshot/untracked baseline handling.
- Leave verifier scope checks and warnings wired to the raw verifier delta; do not switch them to the filtered commit-eligible set.
- Update existing tests that assert `runs/` is excluded from tracked autoloop paths or tracked-path commits.
- Add focused tests for:
  - runtime default/config/CLI resolution of `track_autoloop_artifacts`
  - tracked autoloop paths now including `runs/...`
  - opt-out removing all task-root paths from commit candidates while preserving non-task-root commit behavior
  - ignored untracked task-root paths being skipped with a single warning
  - ignored tracked task-root paths still staging with a single warning
  - raw producer/verifier delta behavior unchanged under both toggle values
  - verifier scope warnings still driven by raw deltas when tracking is disabled

## Affected Code Areas
- `src/autoloop/main.py`
  - runtime config dataclasses, parser, merge logic, arg parser
  - tracked-path helpers and new task-root classification/filter helpers
  - commit helper layer and its call sites in `main()` / `execute_pair_cycles()`
- `tests/test_autoloop_observability.py`
- `tests/test_phase_local_behavior.py`
- `tests/test_autoloop_git_tracking.py` or an equivalent git-focused test module for real ignore semantics

## Compatibility Notes
- Default git-enabled behavior changes only by newly including run-scoped artifacts under the active task root in tracked-path commits.
- The opt-out is explicit and additive; existing configs continue to resolve successfully without migration.
- Legacy `.superloop/...` workspaces are supported automatically if `task_root_rel` resolves there; no separate branching for legacy roots should be added.
- Already-tracked ignored files must not be de-indexed or otherwise “fixed”; the warning is informational only.

## Regression Controls
- Treat raw phase deltas as the source of truth for producer/verifier attribution and verifier scope checks.
- Apply the new toggle only in staging/commit eligibility code paths.
- Keep commit filtering centralized so future commit flows do not bypass the setting.
- Use tests that distinguish task-root paths from ordinary repo paths to prove the opt-out is narrow rather than global.

## Risk Register
- Risk: filtering is added at delta-generation time instead of commit time.
  - Control: keep delta helpers untouched and add dedicated tests that inspect raw deltas with tracking both on and off.
- Risk: one or more commit flows bypass the new filter.
  - Control: route all auto-stage/commit paths through the same helper interface and cover baseline/final/pair-cycle flows in tests.
- Risk: ignore handling regresses by turning ignored task-root files into fatal git errors.
  - Control: add real git tests around `.gitignore`, tracked-vs-untracked ignored files, and clean no-op behavior when nothing remains eligible.

## Validation
- Run the targeted test modules for observability, phase-local behavior, and git tracking.
- Prefer at least one real-repo git test for ignore semantics rather than only monkeypatched `run_git` coverage.

## Rollback
- Revert the runtime toggle plumbing and commit-helper filtering as one slice.
- Preserve any task workspace files already written; rollback should only remove the new auto-tracking behavior, not mutate workspace contents or git index state.

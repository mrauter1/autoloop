# Implementation Notes

- Task ID: retry-apply-pr-review-feedback-with-yaml-safe-pl-e652b5d6
- Pair: implement
- Phase ID: harden-track-autoloop-artifact-git-paths
- Phase Directory Key: harden-track-autoloop-artifact-git-paths
- Phase Title: Harden artifact staging path parsing and ignore detection
- Scope: phase-local producer artifact

## Files Changed

- `src/autoloop/main.py`
- `tests/test_autoloop_git_tracking.py`
- `tests/test_phase_local_behavior.py`
- `tests/test_autoloop_observability.py`

## Symbols Touched

- `normalize_repo_path()`
- `parse_status_entries()`
- `changed_paths()`
- `is_path_under_task_root()`
- `_tracked_ignored_paths()`
- `_resolve_stageable_commit_paths()`
- `try_commit_tracked_changes()`

## Checklist Mapping

- Milestone 1: switched commit-related status reads to `git status --porcelain -z`, added destination-path handling for rename or copy records, and kept line-mode normalization only as fallback parsing.
- Milestone 2: special-cased repo-root `"."` in `is_path_under_task_root()` and replaced per-path ignore or tracked probes with one batched `git ls-files -ci --exclude-standard -z` query over task-root stageable paths.
- Milestone 3: added regression coverage for spaced filenames, rename destination handling, repo-root `"."`, and legacy `.superloop` classification; updated the commit-failure observability stub for the `-z` status calls.

## Assumptions

- Commit-related callers are the intended scope for porcelain hardening, so line-based parsing remains fallback-only for existing tests or non-commit helpers that may still pass plain porcelain text.

## Preserved Invariants

- `_resolve_stageable_commit_paths()` still returns `Optional[List[str]]`.
- Ignored-untracked and ignored-tracked warnings remain once-per-root-per-kind via `warning_cache`.
- Delta attribution, verifier scope checks, no-git behavior, and `track_autoloop_artifacts` defaults were left unchanged.

## Intended Behavior Changes

- Repo-root task roots `"."` now classify repo-relative paths as in-scope while rejecting `../` traversal-style inputs.
- Commit staging and tracked-change detection now preserve raw repo-relative paths from porcelain `-z`, including quoted or special-character names and rename destinations.

## Known Non-Changes

- No changes to producer or verifier raw delta consumers.
- No changes to verifier scope exemptions or warning message text.
- No changes to planning artifacts or YAML serialization logic in this phase.

## Expected Side Effects

- Fewer git subprocesses when warning about ignored-but-tracked task-root paths.

## Validation Performed

- `pytest -q tests/test_autoloop_git_tracking.py`
- `pytest -q tests/test_phase_local_behavior.py`
- `pytest -q tests/test_autoloop_observability.py -k try_commit_tracked_changes_warns_and_returns_false_on_commit_failure`

## Deduplication / Centralization

- Centralized ignored tracked-path detection into `_tracked_ignored_paths()` so staging logic reuses one batched git query instead of duplicating per-path ignore and tracking probes.

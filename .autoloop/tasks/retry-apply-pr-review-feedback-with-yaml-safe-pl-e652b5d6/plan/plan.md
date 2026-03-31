# Plan

## Scope

Apply the validated PR review fixes for `track_autoloop_artifacts` in the existing git staging and commit helper flow without changing raw delta attribution, verifier scope evaluation, no-git behavior, or the default meaning of `track_autoloop_artifacts`.

## Review Triage

- Ignore/tracked performance concern: valid. `_resolve_stageable_commit_paths()` already batches one `git status --porcelain --ignored` call, but then falls back to per-path `git check-ignore` and `git ls-files` checks for task-root candidates. The plan should remove that subprocess-per-path pattern.
- Porcelain quoting/parsing concern: valid. `parse_status_entries()` currently slices line-oriented porcelain output and `normalize_repo_path()` only trims and splits `old -> new`, so quoted paths can be passed back into `git add` incorrectly.
- `is_path_under_task_root(path, ".")` edge case: valid. The current equality/prefix logic does not treat ordinary repo-relative paths as being under the repo root when `task_root_rel` is `"."`.
- Codex bot P1 unquoting warning: valid but not separate scope. It is the same parser correctness issue as the porcelain review item and should be fixed in the same helper refactor.

## Milestones

### 1. Harden git status parsing for commit-related flows

- Replace line-based porcelain parsing with a local helper that consumes `git status --porcelain -z` output and returns repo-relative `(status, path)` entries using the destination path for rename or copy records.
- Update every staging or tracked-change consumer that can feed parsed paths back into git commands or change detection:
  - `changed_paths()`
  - `_resolve_stageable_commit_paths()`
  - `try_commit_tracked_changes()`
- Preserve behavior for standard modified or untracked entries, ignored directory entries, and rename or copy entries without leaking quoted path tokens into later git calls.

### 2. Make task-root classification and ignore detection explicit

- Special-case `task_root_rel == "."` in `is_path_under_task_root()` so every repo-relative path is considered under the active root while keeping current equality or prefix behavior for normal `.autoloop/...` and legacy `.superloop/...` roots.
- Refactor ignored tracked-path detection inside `_resolve_stageable_commit_paths()` to reuse the initial status scan:
  - keep `status == "!!"` entries as the source of ignored-untracked warnings
  - narrow tracked-ignored detection to non-ignored task-root candidates already reported by status
  - batch ignore matching with a single git call over that narrowed set instead of per-path `check-ignore` and `ls-files` invocations
- Preserve once-per-run-per-root-per-kind warnings and the current `allow_fail` versus fatal error behavior.

### 3. Expand regression coverage around the touched helpers

- Add commit-flow coverage for filenames that require porcelain unquoting in staging or commit paths.
- Add `is_path_under_task_root()` coverage for:
  - repo root `.`
  - normal `.autoloop/tasks/<id>` roots
  - legacy `.superloop/tasks/<id>` roots
- Update ignore or tracked tests to confirm warning semantics still hold after the batching refactor.
- Keep existing `track_autoloop_artifacts` CLI or config coverage passing; only add observability-plumbing assertions if a touched helper path already belongs in that module.

## Interfaces And Files

- `src/autoloop/main.py`
  - keep `commit_paths()` and `try_commit_tracked_changes()` signatures unchanged
  - keep `_resolve_stageable_commit_paths()` returning `Optional[List[str]]`
  - confine parser and ignore-detection refactoring to local helpers in this module rather than adding a new abstraction layer
- `tests/test_autoloop_git_tracking.py`
  - primary coverage for staging behavior, ignored-untracked versus ignored-tracked warnings, and special-character filenames
- `tests/test_phase_local_behavior.py`
  - primary coverage for `is_path_under_task_root()` edge cases
- `tests/test_autoloop_observability.py`
  - keep current `track_autoloop_artifacts` plumbing expectations intact and only touch this module if existing assertions need adjustment

## Compatibility Notes

- No public CLI, config, or persisted artifact contract changes are planned.
- No migration is required.
- Legacy `.superloop` task roots remain supported through the same `task_root_rel` helper path; do not branch behavior on hardcoded state-root names.

## Regression Risks And Controls

- Rename or copy parsing risk: porcelain `-z` uses a different record layout than line mode. Mitigation is explicit helper coverage for rename or copy semantics and always staging the destination path.
- Ignored directory aggregation risk: `git status --ignored` may report a task-root directory entry instead of every leaf file. Mitigation is to keep ignored-untracked warnings keyed off any ignored task-root match rather than requiring leaf-level enumeration.
- Batched ignore-query risk: one failed batch git call could change warning behavior. Mitigation is to preserve the current fatal versus warning behavior through the existing `allow_fail` paths.
- Scope drift risk: commit filtering changes must not leak into producer or verifier raw delta logic or verifier scope checks. Mitigation is to leave snapshot or delta computation and verifier raw-delta consumers untouched.

## Validation

- Run focused tests for git tracking and phase-local helper behavior.
- Run adjacent observability or config tests that cover `track_autoloop_artifacts` plumbing if those expectations are touched.
- Confirm staging succeeds for a filename that plain porcelain would quote and that ignored warning behavior remains unchanged apart from the subprocess reduction.

## Rollback

- Revert only the parser and ignore-detection helper refactor in `src/autoloop/main.py` if the new status parsing proves unstable.
- Keep the test additions when rolling back implementation so the regression remains visible.

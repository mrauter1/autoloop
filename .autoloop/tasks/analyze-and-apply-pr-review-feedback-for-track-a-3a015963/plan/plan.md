# Plan

## Scope

Apply the in-scope PR review fixes for `track_autoloop_artifacts` in the existing git commit/filtering flow without changing delta attribution, verifier scope evaluation, no-git behavior, or the default meaning of `track_autoloop_artifacts`.

## Review Triage

- Ignore/tracked performance concern: valid. `_resolve_stageable_commit_paths()` currently narrows candidates with one `git status --porcelain --ignored` call, then may spawn `git check-ignore` and `git ls-files` once per candidate task-root path. The plan should remove that per-path subprocess pattern.
- Porcelain quoting/parsing concern: valid. `parse_status_entries()` currently slices line-oriented porcelain output and `normalize_repo_path()` only trims and splits `old -> new`, so quoted paths can reach `git add` and other path consumers incorrectly.
- `task_root_rel == "."` edge case: valid. `is_path_under_task_root(path, ".")` currently returns `False` for normal repo-relative paths because `"."/` is not a real prefix for those paths.
- Codex bot P1 unquoting warning: valid but not separate scope. It is the same correctness issue as the porcelain parsing review item and should be fixed by the same parser hardening.

## Milestones

### 1. Harden git status parsing in commit-related flows

- Replace line-based porcelain parsing with a local helper that consumes `git status --porcelain -z` output and returns repo-relative `(status, path)` entries using the destination path for rename/copy records.
- Update every staging/commit status consumer that can feed paths back into git commands or change detection:
  - `changed_paths()`
  - `_resolve_stageable_commit_paths()`
  - `try_commit_tracked_changes()`
- Preserve handling for standard modified/untracked entries, ignored directory entries, and rename/copy entries without introducing quoted path tokens.

### 2. Make task-root classification and ignore detection explicit

- Special-case `task_root_rel == "."` in `is_path_under_task_root()` so every repo-relative path is considered under the active root while keeping existing equality/prefix behavior for normal `.autoloop/...` and legacy `.superloop/...` roots.
- Refactor ignored tracked-path detection inside `_resolve_stageable_commit_paths()` to reuse the initial status scan:
  - keep `status == "!!"` entries as the source of ignored-untracked warnings
  - narrow tracked-ignored detection to non-`!!` task-root candidates already returned by status
  - batch ignore matching with one git call over that narrowed set instead of per-path `check-ignore`/`ls-files`
- Preserve once-per-run-per-root-per-kind warnings and current `allow_fail`/fatal behavior.

### 3. Expand regression coverage around the touched helpers

- Add commit-flow coverage for filenames that require porcelain unquoting in staging/commit paths.
- Add `is_path_under_task_root()` coverage for:
  - repo root (`"."`)
  - normal `.autoloop/tasks/<id>` roots
  - legacy `.superloop/tasks/<id>` roots
- Update ignore/tracked tests to confirm warnings still fire correctly after the batching refactor and that existing CLI/config plumbing behavior remains intact.

## Interfaces And Files

- `src/autoloop/main.py`
  - keep `commit_paths()` and `try_commit_tracked_changes()` signatures unchanged
  - keep `_resolve_stageable_commit_paths()` return contract unchanged (`Optional[List[str]]`)
  - confine the parsing/ignore refactor to local helpers in this module rather than introducing a new layer
- `tests/test_autoloop_git_tracking.py`
  - primary coverage for staging, ignored/untracked vs ignored/tracked warnings, and special-character filenames
- `tests/test_phase_local_behavior.py`
  - primary coverage for `is_path_under_task_root()` edge cases
- `tests/test_autoloop_observability.py`
  - retain existing CLI/config expectations; only add coverage here if a touched helper is already exercised naturally

## Compatibility Notes

- No public CLI, config, or persisted artifact contract changes are planned.
- No migration is required.
- Legacy `.superloop` task roots remain supported through the same `task_root_rel` helper path; do not branch behavior on hardcoded state-root names.

## Regression Risks And Controls

- Rename/copy parsing risk: `--porcelain -z` emits destination/source records differently from line mode; mitigation is explicit helper coverage for rename/copy semantics and use of the destination path when staging/checking deltas.
- Ignored directory aggregation risk: `git status --ignored` may report a task-root directory entry instead of leaf files for ignored untracked content; mitigation is to keep the ignored-untracked warning keyed off any `!!` task-root match, not individual files.
- Batched ignore-query risk: a failed batch git call could change warning behavior; mitigation is to preserve the current fatal vs warning behavior through the existing `allow_fail` flag paths.
- Scope drift risk: commit filtering changes must not leak into producer/verifier raw delta logic or verifier scope checks; mitigation is to leave snapshot/delta computation and verifier raw-delta consumers untouched.

## Validation

- Run focused tests for git tracking and task-root helpers.
- Run adjacent observability/config tests that cover the `track_autoloop_artifacts` plumbing.
- Confirm staging succeeds for a filename that plain porcelain would quote and that ignored warning behavior is unchanged apart from the subprocess reduction.

## Rollback

- Revert only the parser/helper refactor in `src/autoloop/main.py` if the new status parsing proves unstable.
- Keep test additions when rolling back implementation so the regression remains visible.

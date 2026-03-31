# Analyze and apply PR review feedback for track_autoloop_artifacts change

## Objective

Use review feedback to fix correctness/performance edge cases in the `track_autoloop_artifacts` implementation, applying only suggestions that are correct and in scope.

## Review items to evaluate

1. **Performance concern in ignored-tracked detection**
   - Current code computes `ignored_tracked_paths` by per-path calls to:
     - `git check-ignore --no-index -q -- <path>`
     - `git ls-files --error-unmatch -- <path>`
   - This can spawn many git processes and may be slow for large task roots.
   - Suggested direction: batch ignore detection and use existing status metadata for tracked/untracked classification.

2. **Porcelain path quoting/parsing correctness**
   - `git status --porcelain` may emit quoted paths for names containing spaces/special characters.
   - Current parsing may pass quoted path strings through to `git add`, causing pathspec failures.
   - Suggested direction: use robust parsing (`--porcelain -z`) and/or proper unquoting.

3. **Task-root helper edge case when `task_root_rel == "."`**
   - `is_path_under_task_root()` currently checks equality/prefix against `task_root_rel`.
   - If root is `.`, prefix checks may not behave as intended for repo-relative paths.
   - Suggested direction: make root handling explicit and robust.

4. **Codex bot P1: unquote porcelain paths before staging**
   - Validate whether this is a real crash path and fix accordingly.

## Required outcomes

### A. Correctness and applicability triage

- Explicitly validate each review suggestion against current behavior.
- Apply suggestions that are correct/in-scope.
- If any suggestion is not applicable, document why in implementation notes/feedback artifacts.

### B. Path parsing hardening

- Ensure status parsing used by commit staging handles paths with spaces/special characters correctly.
- Avoid regressions for renamed/copied paths and standard status lines.
- Ensure `commit_paths()` and related helpers stage the correct filesystem path strings.

### C. Task-root classification hardening

- Ensure `is_path_under_task_root()` behaves correctly for:
  - normal task roots like `.autoloop/tasks/<id>`
  - legacy roots like `.superloop/tasks/<id>`
  - edge case `task_root_rel == "."`

### D. Ignore/tracked detection efficiency

- Improve performance of ignored tracked-path detection to avoid per-path git subprocess explosion.
- Reuse already-available status information where possible.
- Preserve behavior:
  - ignored untracked task-root paths are skipped with warning
  - ignored but already tracked task-root paths may still commit and warn
  - warnings remain once-per-run-per-root-per-kind

### E. Behavioral invariants to preserve

Do not change:
- raw producer/verifier delta attribution logic
- verifier scope checks/warnings source (must remain raw deltas)
- no-git behavior
- default meaning of `track_autoloop_artifacts`

### F. Testing updates

Add/update tests to cover:
1. Porcelain path parsing for filenames with spaces/special characters in staging flow.
2. Root-case behavior of `is_path_under_task_root()` with `task_root_rel == "."`.
3. Ignore/tracked warning behavior remains correct after performance refactor.
4. No regression in existing `track_autoloop_artifacts` behavior and CLI/config plumbing.

## Acceptance criteria

1. Filenames requiring porcelain unquoting are staged/committed correctly (no pathspec failure due to quoted tokens).
2. `is_path_under_task_root(path, ".")` correctly treats repo-relative paths as under task root.
3. Ignore/tracked detection avoids unnecessary per-path subprocess churn while preserving semantics.
4. Existing behavior guarantees for commit filtering, delta attribution, and verifier scope remain intact.
5. Tests pass for the updated/added scenarios.

# Test Strategy

- Task ID: retry-apply-pr-review-feedback-with-yaml-safe-pl-e652b5d6
- Pair: test
- Phase ID: harden-track-autoloop-artifact-git-paths
- Phase Directory Key: harden-track-autoloop-artifact-git-paths
- Phase Title: Harden artifact staging path parsing and ignore detection
- Scope: phase-local producer artifact

## Behavior-to-Test Coverage Map

- AC-1 commit-path parsing:
  - real git staging path with spaces under the task root commits successfully
  - real git rename under the task root reports and commits the destination path
  - parser-level `parse_status_entries()` coverage now exercises NUL-delimited rename, copy, and embedded-newline path records deterministically
- AC-2 task-root classification:
  - repo-root `"."` treats repo-relative paths as in scope and rejects `../` traversal-style inputs
  - existing `.autoloop` and legacy `.superloop` task roots still classify descendants correctly
- AC-3 ignored warning semantics:
  - ignored untracked task-root paths are skipped with a single warning
  - ignored tracked task-root paths still warn once while allowing tracked updates to commit
  - external non-task-root changes still commit when ignored task-root files are present
- AC-4 adjacent plumbing:
  - best-effort final artifact commit path still warns and returns `False` on commit failure with the `-z` status calls

## Preserved Invariants Checked

- `changed_paths()` returns rename destinations rather than deleted source paths for commit-related status reads
- `commit_paths()` still limits commits to the requested path set
- warning text and once-per-root-per-kind behavior remain unchanged

## Edge Cases

- spaced filenames
- embedded newline filename parsing in porcelain `-z`
- repo-root `"."`
- legacy `.superloop` task root
- rename and copy status records

## Failure Paths

- ignored untracked task-root paths produce no commit when they are the only task-root candidates
- best-effort commit helper surfaces commit-hook failure as a warning and `False`

## Flake Risk / Stabilization

- git-behavior tests use temporary repositories with local user config and no network access
- parser-level copy coverage is string-based to avoid nondeterministic git copy-detection heuristics

## Known Gaps

- No end-to-end copy-detection repository test; copy handling is covered deterministically at the parser level because git copy reporting is heuristic-driven.

# Test Strategy

- Task ID: implement-configurable-autoloop-workspace-artifa-8527294e
- Pair: test
- Phase ID: workspace-artifact-tracking
- Phase Directory Key: workspace-artifact-tracking
- Phase Title: Configurable Workspace Artifact Tracking
- Scope: phase-local producer artifact

## Behavior To Coverage Map

- Runtime config / CLI plumbing:
  `tests/test_autoloop_observability.py`
  Covers default runtime resolution, config-file overrides, and `--track-autoloop-artifacts` / `--no-track-autoloop-artifacts`.
- Active task-root tracking defaults:
  `tests/test_autoloop_observability.py`, `tests/test_phase_local_behavior.py`, `tests/test_autoloop_git_tracking.py`
  Covers tracked-path helpers returning the active task root and default git commits including `runs/...`.
- Commit-eligibility opt-out:
  `tests/test_phase_local_behavior.py`, `tests/test_autoloop_git_tracking.py`, `tests/test_autoloop_observability.py`
  Covers task-root classification/filtering, non-task-root preservation, and disabled-artifact-tracking commit filtering during pair execution.
- Ignore semantics:
  `tests/test_autoloop_git_tracking.py`
  Covers ignored untracked task-root paths being skipped with warnings, mixed ignored-task-root plus external changes continuing successfully, ignored-but-tracked task-root paths still committing, and once-per-run warning suppression via a shared policy object.
- Preserved raw delta / verifier scope behavior:
  `tests/test_autoloop_observability.py`, `tests/test_phase_local_behavior.py`
  Covers `filter_volatile_task_run_paths()` remaining unchanged, producer/verifier raw delta behavior excluding `runs/...`, and verifier scope warnings still using raw deltas when artifact tracking is disabled.

## Preserved Invariants Checked

- `filter_volatile_task_run_paths()` still removes `task_root/runs/...` from raw producer/verifier deltas.
- `verifier_scope_violations()` still keys off raw verifier deltas and existing runtime-bookkeeping exemptions.
- No test normalizes force-add behavior or de-indexing of tracked ignored files.

## Edge Cases / Failure Paths

- Empty eligible commit set returns cleanly without a commit.
- Ignored untracked task-root artifacts warn without fatal git errors.
- Ignored untracked task-root artifacts do not block unrelated external-path commits in the same operation.
- Ignored tracked task-root artifacts still stage under normal git semantics and warn once.

## Flake Risk / Stabilization

- Git behavior is exercised through temporary local repositories only; no network, clocks, or parallel-process assumptions are used.
- Warning suppression assertions reuse a single `GitCommitPolicy` instance inside one test to keep the once-per-run cache deterministic.

## Known Gaps

- Resume-across-process warning suppression is not covered because the accepted implementation explicitly uses an in-memory per-run helper cache.

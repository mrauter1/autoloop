# Implementation Notes

- Task ID: implement-configurable-autoloop-workspace-artifa-8527294e
- Pair: implement
- Phase ID: workspace-artifact-tracking
- Phase Directory Key: workspace-artifact-tracking
- Phase Title: Configurable Workspace Artifact Tracking
- Scope: phase-local producer artifact

## Files Changed
- `src/autoloop/main.py`
- `tests/test_autoloop_observability.py`
- `tests/test_phase_local_behavior.py`
- `tests/test_autoloop_git_tracking.py`
- `.autoloop/tasks/implement-configurable-autoloop-workspace-artifa-8527294e/decisions.txt`

## Symbols Touched
- `RuntimeConfig`
- `RuntimeConfigOverride`
- `GitCommitPolicy`
- `parse_autoloop_config()`
- `_merge_runtime_config()`
- `build_arg_parser()`
- `tracked_autoloop_artifact_paths()`
- `tracked_autoloop_paths()`
- `is_path_under_task_root()`
- `filter_commit_eligible_paths()`
- `commit_paths()`
- `commit_tracked_changes()`
- `try_commit_tracked_changes()`
- `execute_pair_cycles()`
- `main()`

## Checklist Mapping
- Milestone 1 / AC-1: Added `track_autoloop_artifacts` to config parsing, merge resolution, CLI flags, and runtime propagation with a default of `true`.
- Milestone 2 / AC-2 / AC-3: Switched tracked artifact helpers to the active task-root prefix, added centralized commit-eligibility filtering, and added ignore-aware staging plus once-per-run warning suppression in the shared commit helper layer.
- Milestone 3 / AC-4: Left `filter_volatile_task_run_paths()` and verifier scope inputs unchanged; added tests proving raw delta filtering and verifier scope warnings still operate from the raw delta while commit eligibility can be disabled.

## Assumptions
- The shared in-memory warning cache is scoped to a single process/run by reusing one `GitCommitPolicy` instance across all git commit flows in `main()`.
- Using the active task-root prefix as the tracked artifact path is acceptable for pair-scoped tracked commits because commit-time eligibility filtering now enforces the opt-out uniformly by `task_root_rel`.

## Preserved Invariants
- Raw producer and verifier delta computation still uses phase snapshots plus `filter_volatile_task_run_paths()`.
- Verifier scope warnings still inspect raw verifier deltas and `verifier_exempt_runtime_artifact_paths()` only.
- Git ignore behavior never force-adds ignored paths.

## Intended Behavior Changes
- Git-enabled default tracking now treats the active task workspace root, including `runs/...`, as commit-eligible Autoloop artifacts.
- `--no-track-autoloop-artifacts` / `runtime.track_autoloop_artifacts=false` now strips every task-root path from auto-stage and auto-commit eligibility while preserving non-task-root deltas.
- Ignored untracked task-root paths now warn once and are skipped cleanly; ignored-but-tracked task-root paths warn once and may still commit under normal Git behavior.

## Known Non-Changes
- No changes to no-git execution beyond carrying the resolved runtime flag.
- No changes to verifier scope policy, runtime-bookkeeping exemptions, or raw delta attribution.
- No force-add, de-index, or ignore-rule rewriting behavior was added.

## Expected Side Effects
- Baseline, pre-cycle, question-answer, completion, failure, and finalize-run commits now all route through the same task-root filter and ignore-warning path.
- Existing tests that asserted `runs/` exclusion were updated to reflect full task-root tracking.

## Validation Performed
- `python -m py_compile src/autoloop/main.py`
- `python -m pytest tests/test_autoloop_observability.py tests/test_phase_local_behavior.py tests/test_autoloop_git_tracking.py`

## Centralization / Deduplication
- Centralized task-root eligibility filtering and ignore semantics in the shared commit helper layer so every auto-stage/commit flow inherits the same behavior instead of duplicating path filtering at each call site.

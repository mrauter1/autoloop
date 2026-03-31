# Implement configurable Autoloop workspace artifact tracking

## Objective

Implement a new runtime setting that controls whether Autoloop auto-stages and auto-commits its own task workspace artifacts.

Required outcome:

- In git-enabled mode, Autoloop workspace artifacts are tracked by default.
- Add an explicit opt-out that disables all auto-tracking of Autoloop workspace artifacts.
- Preserve existing per-phase delta attribution behavior regardless of the artifact-tracking setting.

## Scope definition

For this feature, **Autoloop workspace artifacts** means **every repo-relative path under the active task workspace root** for the current run.

Examples:

- `.autoloop/tasks/<task-id>/...`
- `.superloop/tasks/<task-id>/...` when operating on a legacy task workspace

Use the resolved active task workspace root (`task_root_rel`) as the only source of truth.

Do **not** special-case only specific files like `task.json`, `decisions.txt`, `runs/`, `raw_phase_log.md`, etc. The entire active task workspace root must be treated uniformly.

## Functional requirements

### 1. Add a new runtime setting

Add a runtime setting named:

- `track_autoloop_artifacts`

Default value:

- `true`

Support it in all runtime configuration surfaces:

- config file: `runtime.track_autoloop_artifacts`
- CLI:
  - `--track-autoloop-artifacts`
  - `--no-track-autoloop-artifacts`

### 2. Default behavior

When all of the following are true:

- git mode is enabled
- `track_autoloop_artifacts=true`

then Autoloop must auto-stage and auto-commit eligible paths under the active task workspace root, including run-scoped artifacts such as `runs/...`, subject to normal Git ignore semantics.

### 3. Opt-out behavior

When all of the following are true:

- git mode is enabled
- `track_autoloop_artifacts=false`

then Autoloop must **not** auto-stage or auto-commit any path under the active task workspace root.

This prohibition must apply uniformly to the entire active task workspace root.

Paths outside the active task workspace root must continue to behave normally and may still be auto-staged or auto-committed if they are part of producer/verifier deltas or other existing commit flows.

### 4. Delta behavior must remain unchanged

Do not change the logic that determines what changed during a producer or verifier phase.

Preserve the current per-phase delta attribution behavior, including:

- phase snapshot creation
- tracked-file delta comparison
- untracked-file baseline handling
- verifier raw delta attribution

This feature must affect **commit eligibility only**, not delta computation.

### 5. Verifier scope behavior must remain unchanged

Verifier scope checks and warnings must continue to operate on the **raw phase delta**, not on the filtered set of paths that are eligible for staging/commit.

The new artifact-tracking toggle must not change:

- what the verifier is considered to have touched
- how scope violations are detected
- whether scope warnings are emitted

### 6. Run artifacts must be included by default

Run-scoped artifacts under `runs/...` must no longer be treated as excluded or volatile for purposes of default artifact tracking.

When `track_autoloop_artifacts=true`, run-scoped artifacts should be eligible for auto-stage/auto-commit under the same rules as any other path under the active task workspace root.

When `track_autoloop_artifacts=false`, run-scoped artifacts must not be auto-staged or auto-committed.

## Git ignore semantics

Match normal Git semantics.

Rules:

1. Autoloop must never force-add ignored paths.
   - Do not use `git add -f`
   - Do not use any equivalent force behavior

2. If a path under the active task workspace root is **untracked** and ignored by Git exclude rules:
   - skip auto-staging that path
   - emit a warning
   - continue the run successfully

3. If a path under the active task workspace root is **already tracked by Git** and also matches ignore rules:
   - Autoloop may still auto-stage and auto-commit it under normal Git semantics
   - emit a warning explaining that ignore rules do not suppress updates to already-tracked files
   - continue the run successfully

4. Warnings must be clear and actionable.

5. Warnings should be emitted at most once per run per active task workspace root for each of these two cases:
   - ignored untracked Autoloop workspace paths are being skipped
   - ignored-but-already-tracked Autoloop workspace paths may still be committed

## Implementation requirements

### A. Runtime config plumbing

Add `track_autoloop_artifacts` to:

- `RuntimeConfig`
- `RuntimeConfigOverride`
- config parsing
- config merging
- CLI parsing
- runtime resolution
- any execution paths that need the resolved setting

Default must be `true`.

### B. Path classification

Add a helper that answers whether a repo-relative path belongs to the active Autoloop workspace root.

Use only the active `task_root_rel`.

Equivalent behavior:

- return true if `path` is equal to the active task root
- return true if `path` is under `task_root_rel/`
- otherwise return false

Do not classify paths using a manually maintained list of artifact filenames.

### C. Commit filtering

Add a helper that filters commit-eligible paths based on:

- the raw candidate path set
- the active task workspace root
- `track_autoloop_artifacts`

Required behavior:

- if `track_autoloop_artifacts=true`, keep all candidate paths
- if `track_autoloop_artifacts=false`, remove every path under the active task workspace root

This helper must be used consistently anywhere Autoloop decides what to auto-stage or auto-commit.

### D. Tracked artifact set

Update tracked artifact path helpers so that the active task workspace root includes run-scoped artifacts by default.

In practice, tracked-path helpers must no longer exclude `runs/`.

### E. Keep delta collection separate from commit filtering

Do not filter raw phase deltas at the moment they are computed.

Continue computing the same raw producer/verifier deltas as today.

Apply the new artifact-tracking filter only when deciding what paths are eligible to stage/commit.

### F. Commit flow coverage

Apply the new commit-eligibility rules consistently to all relevant Autoloop git commit flows, including:

- baseline tracked-artifact commits
- pre-cycle tracked-artifact commits
- clarification / question-answer related tracked-artifact commits
- producer delta commits
- verifier delta commits
- pair completion commits
- blocked commits
- failed commits
- final run-artifact commits

When the eligible path set is empty after filtering and/or skipping ignored paths, the commit helper should no-op cleanly.

### G. No special handling for legacy roots beyond the active task root

Do not hardcode separate behavior for `.autoloop` and `.superloop`.

The implementation must behave correctly based only on the active resolved task workspace root.

## Non-goals

Do not:

- redesign phase delta computation
- redesign verifier scope policy
- force ignored files into Git
- de-index or remove already-tracked files from Git
- change no-git mode behavior beyond plumbing the new flag through harmlessly

## Testing requirements

Update existing tests that assume run artifacts are excluded.

Add or update tests to cover the following:

### 1. Config and CLI

- default runtime resolution sets `track_autoloop_artifacts=true`
- config file override works
- `--track-autoloop-artifacts` works
- `--no-track-autoloop-artifacts` works

### 2. Default tracking behavior

- tracked Autoloop workspace paths include run-scoped artifacts under `runs/...`
- default git-enabled behavior auto-stages/auto-commits Autoloop workspace artifacts when they are not ignored

### 3. Opt-out behavior

- with `track_autoloop_artifacts=false`, no path under the active task workspace root is auto-staged or auto-committed
- non-Autoloop paths outside the active task workspace root still commit normally when they are part of deltas

### 4. Ignore semantics

- ignored untracked Autoloop workspace paths are skipped with a warning and do not cause fatal git errors
- ignored-but-already-tracked Autoloop workspace paths may still be committed and produce the correct warning
- warnings are not emitted repeatedly beyond the intended once-per-run-per-root behavior

### 5. Delta preservation

- raw producer/verifier delta behavior is unchanged when artifact tracking is enabled
- raw producer/verifier delta behavior is unchanged when artifact tracking is disabled

### 6. Verifier scope preservation

- verifier scope checks still use raw deltas
- disabling artifact tracking does not suppress legitimate verifier scope warnings

## Acceptance criteria

This change is complete only if all of the following are true:

1. In git-enabled mode, default behavior (`track_autoloop_artifacts=true`) auto-tracks Autoloop workspace artifacts under the active task workspace root, including `runs/...`, when they are not ignored.

2. In git-enabled mode with `track_autoloop_artifacts=false`, Autoloop never auto-stages or auto-commits any path under the active task workspace root.

3. If untracked Autoloop workspace paths are ignored by Git exclude rules, Autoloop skips them, warns, and continues successfully.

4. If already-tracked Autoloop workspace paths match ignore rules, Autoloop may still commit them under normal Git semantics and emits a warning explaining that behavior.

5. Producer/verifier delta attribution remains unchanged.

6. Verifier scope checks and warnings remain based on raw deltas and remain unchanged by the new setting.

7. Existing git-enabled workflows continue to work without regressions outside the new artifact-tracking behavior.

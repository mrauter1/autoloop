# Review Comment Applicability Plan

## Scope

Evaluate the three installer review comments about centralized `die()` handling, apply only any still-valid suggestion, and verify the touched behavior with focused installer and parser/resource checks.

## Verified Current State

- `install_autoloop.sh` already routes the `require_cmd` missing-command branch through `die()`.
- The Python version guard already fails through `die()`.
- The required repository path existence guard already fails through `die()`.
- Existing parser coverage already asserts the public git flag pair is `--git` / `--no-git` and rejects `--no-no-git`.
- Existing resource coverage already exercises packaged template and README resource expectations.

## Implementation Direction

### 1. Re-verify applicability before editing

- Reconfirm the three target installer branches in the current worktree before making any change.
- Treat each review comment as non-actionable if the branch already calls `die()` and there is no duplicated or inconsistent error path left to remove.
- Record that non-actionable outcome in implementation notes so the stale comments are explicitly closed out.

### 2. Limit code changes to real gaps only

- If verification still shows all three branches already use `die()`, do not edit `install_autoloop.sh`.
- Only make a minimal installer change if one of the reviewed branches no longer funnels through `die()` in the implementation turn.
- Do not broaden scope into unrelated installer refactors or error-message rewrites.

### 3. Validate requested regression surfaces

- Extend targeted installer coverage in `tests/test_installer.py` so validation executes the three reviewed failure paths, using the existing subprocess/env harness to prove each branch still terminates through `die()`:
  - missing `python3` / `require_cmd`
  - failing Python version guard
  - missing required repository path
- Keep the existing installer success/rerun/readiness coverage in the same test module.
- Run targeted parser/resource coverage that confirms:
  - `--git` and `--no-git` remain the only public git flags
  - `--no-no-git` is still rejected
  - packaged/resource expectations remain intact
- If no source change is needed, those branch-specific installer tests still run and are reported as the runtime evidence for leaving the review comments unapplied.

## Compatibility Notes

- Public CLI behavior must remain `--git` and `--no-git` only; no hidden `--no-no-git` option may be introduced or restored.
- Installer preflight and error behavior should remain unchanged when the review comments are already satisfied.
- A no-code-change outcome is acceptable and preferred if current behavior already matches the requested centralized error handling.

## Regression Risks And Controls

| Risk | Control |
| --- | --- |
| Applying a stale review comment creates churn without behavior change | Require branch-by-branch verification before editing and document non-actionable comments explicitly |
| Touching installer error paths regresses existing behavior | Keep edits local to the verified branch gap only, otherwise leave `install_autoloop.sh` unchanged |
| Non-actionable findings are closed without runtime evidence | Reuse the existing installer subprocess harness to execute each reviewed failure branch and assert the expected `die()`-driven failure |
| Validation misses the user-specified git-flag guardrail | Include targeted parser coverage that proves `--git` / `--no-git` remain correct and `--no-no-git` stays rejected |

## Validation Plan

- `pytest tests/test_installer.py -k 'require_cmd or version or required_path or installer'`
- `pytest tests/test_autoloop_observability.py -k git_flag`
- `pytest tests/test_resources.py`

## Rollout / Rollback

- Ship as one small slice.
- If an installer change is made and causes failures, revert only that local installer adjustment and keep the documented applicability findings.

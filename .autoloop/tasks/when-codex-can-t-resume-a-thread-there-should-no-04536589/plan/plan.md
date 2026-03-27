# Codex Resume Failure Recovery Plan

## Scope

Implement one localized runtime change: when Autoloop has a saved Codex thread id but `codex exec resume` cannot resume it, do not fatal immediately. Warn, record the recovery in the raw logs, clear the stale session id, and retry the same phase once as a fresh Codex thread with the normal bootstrap context.

## Current State

- Missing session files or missing stored thread ids already downgrade to a warning plus `session_recovery`, then proceed with a new conversation.
- `run_provider_phase()` currently builds its prompt once from the saved session state, calls `execute_provider_turn()`, and fatals on any `ProviderExecutionError`.
- For Codex, a failed resume is indistinguishable from any other provider failure at the caller level, so a stale thread id aborts the run even though the runtime already knows how to bootstrap a fresh thread.
- Fresh-thread bootstrap context already exists in `build_phase_preamble()` and `build_fresh_phase_bootstrap()` when `include_request_snapshot=True`.

## Implementation Milestones

### 1. Add Codex resume fallback in the phase-turn path

- Keep `execute_provider_turn()` as the low-level provider executor that reports command mode and raw output on failure.
- In `run_provider_phase()`, detect the narrow recovery case:
  - provider is `codex`
  - a stored `session_id` was present
  - `execute_provider_turn()` failed while `command_mode == "resume"`
- On that path only:
  - emit a warning explaining that the saved Codex thread could not be resumed and the phase is restarting in a new thread
  - append recovery details to both task and run raw logs
  - clear the saved session id/thread id in the phase session file before retrying
  - rebuild the prompt as a fresh-thread prompt, not the earlier resume prompt
  - retry the phase once with Codex start mode

### 2. Preserve the correct fresh-thread bootstrap contract

- Recompute `include_request_snapshot` after clearing the stale session id so the fallback retry includes the immutable request snapshot.
- For phased pairs, ensure the retry goes through the existing `is_fresh_phase_thread` path so the prompt contains:
  - authoritative clarifications to date
  - prior phase status lines
  - relevant prior phase artifact paths
  - the active phase execution contract
- Reuse the existing prompt-building helpers instead of adding a parallel bootstrap implementation.

### 3. Keep non-recoverable cases strict

- Do not change behavior for:
  - fresh-start Codex failures
  - Claude provider failures
  - provider mismatch checks in `ensure_session_provider_match()`
  - missing-session and missing-thread-id recovery, which already has dedicated handling
- If the fresh-thread retry also fails, keep the existing `provider_failure` fatal path.

### 4. Add regression coverage

- Add a targeted test where a saved Codex session exists, the first provider call fails in resume mode, and the second call succeeds in start mode.
- Assert that the fallback path:
  - warns instead of terminating
  - records a recovery entry in raw logs
  - writes the new thread id back to the session file
  - rebuilds the prompt with fresh-thread bootstrap content rather than reusing the resume prompt
- Add or extend a test proving non-resume Codex failures still fatal so the fallback does not mask unrelated provider errors.

## Interface Definitions

### Runtime behavior contract

- Trigger: only a Codex phase turn with an existing saved `session_id` that fails during resume.
- Operator-visible behavior: one warning, then one automatic retry in a new thread.
- Persistence behavior: the stale saved thread id is cleared before retry and replaced with the new thread id if the retry succeeds.
- Logging behavior:
  - keep `provider_failure` logging for unrecovered provider failures
  - add a recovery log entry for the downgraded resume failure so operators can distinguish thread-resume recovery from generic start-mode warnings

### Prompt contract during fallback

- The retry must be equivalent to starting the phase in a fresh thread on this turn.
- The retry must therefore include the normal request/bootstrap context and must not present itself as a resumed thread.

## Compatibility Notes

- This is a Codex-only behavior change. Claude resume failures remain fatal until there is an explicit product decision otherwise.
- Session-file schema does not change.
- Provider mismatch remains fatal; the new behavior only handles stale or invalid Codex thread ids under an otherwise valid Codex configuration.
- User-visible change is limited to a warning plus continued execution instead of a fatal abort when the saved Codex thread can no longer be resumed.

## Regression Risks And Controls

| Risk | Why it matters | Control |
| --- | --- | --- |
| Retrying with the old resume prompt | The new thread would miss request/bootstrap context and could drift from earlier turns | Rebuild prompt inputs after clearing `session_id`; do not reuse the original prompt payload |
| Fallback swallows unrelated provider failures | Real CLI or prompt errors could become harder to diagnose | Gate fallback on `provider == codex`, saved session present, and `command_mode == "resume"` only |
| Raw logs lose the original resume-failure evidence | Operators need to diagnose why a new thread was started | Record the warning and the failed resume raw output in a dedicated recovery entry before retry |
| Session state remains stale after fallback | Later phases could keep retrying the dead thread id | Persist cleared session state before retry, then persist the new thread id on success |

## Validation Plan

- Targeted runtime tests in `tests/test_autoloop_observability.py` for:
  - Codex resume failure falling back to start mode and succeeding
  - start-mode Codex failure still surfacing as fatal
- If the fallback test uses a phased pair, also assert the fresh-thread bootstrap markers already covered in `tests/test_phase_local_behavior.py` appear in the retried prompt.
- Run the touched test module(s) after implementation.

## Rollout / Rollback

- Roll out as one small runtime-and-tests change set.
- If regression appears, revert the fallback branch in `run_provider_phase()` first; no schema or artifact migration is required.

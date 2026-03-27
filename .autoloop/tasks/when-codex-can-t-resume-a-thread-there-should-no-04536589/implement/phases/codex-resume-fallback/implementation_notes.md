# Implementation Notes

- Task ID: when-codex-can-t-resume-a-thread-there-should-no-04536589
- Pair: implement
- Phase ID: codex-resume-fallback
- Phase Directory Key: codex-resume-fallback
- Phase Title: Recover from stale Codex thread resumes
- Scope: phase-local producer artifact

## Files Changed

- `src/autoloop/main.py`
- `tests/test_autoloop_observability.py`
- `.autoloop/tasks/when-codex-can-t-resume-a-thread-there-should-no-04536589/decisions.txt`

## Symbols Touched

- `run_provider_phase`

## Checklist Mapping

- Milestone 1: added Codex-only resume recovery in `run_provider_phase`.
- Milestone 2: retry prompt is rebuilt after clearing `session_id`, reusing existing fresh-thread bootstrap helpers.
- Milestone 3: preserved fatal handling for non-resume failures by leaving the existing `provider_failure` fatal path in place.
- Milestone 4: added targeted observability tests for recovered resume and preserved Codex start failure.

## Assumptions

- A recoverable stale-thread case is identified by `provider == "codex"`, a saved `session_id` being present, and `ProviderExecutionError.command_mode == "resume"`.

## Preserved Invariants

- Provider mismatch checks remain fatal.
- Claude failures still use the existing fatal path.
- Fresh-start Codex failures still log `provider_failure` and fatal immediately.
- Session file schema is unchanged.

## Intended Behavior Changes

- Stale Codex resume failures now emit a warning, append `session_recovery` details to both raw logs, clear stale session state, and retry once in start mode.

## Known Non-Changes

- Missing-session and missing-thread-id recovery behavior is unchanged.
- Cross-provider resume semantics are unchanged.
- Claude resume failures are unchanged.

## Expected Side Effects

- Phase raw logs now include the original failed resume raw output under `session_recovery` before the retry.
- Successful recovery overwrites the cleared session file with the new Codex thread id from the retried turn.

## Validation Performed

- `pytest -q tests/test_autoloop_observability.py -k 'stale_codex_resume or codex_start_failures_fatal or logs_claude_provider_failures_before_fatal or uses_claude_append_system_prompt_file_and_persists_metadata'`
- `pytest -q tests/test_phase_local_behavior.py -k 'fresh_phase_bootstrap or build_phase_prompt'`

## Deduplication / Centralization

- Prompt rebuilding stays inside `run_provider_phase` via a local helper so both the initial attempt and the fallback retry use the same prompt-construction path.

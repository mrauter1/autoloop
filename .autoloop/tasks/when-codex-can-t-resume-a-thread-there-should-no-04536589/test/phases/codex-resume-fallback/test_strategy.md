# Test Strategy

- Task ID: when-codex-can-t-resume-a-thread-there-should-no-04536589
- Pair: test
- Phase ID: codex-resume-fallback
- Phase Directory Key: codex-resume-fallback
- Phase Title: Recover from stale Codex thread resumes
- Scope: phase-local producer artifact

## Coverage Map

- Behavior covered: stale Codex resume failure downgrades to a warning, clears stale session state, retries once in start mode, and persists the replacement thread id on success.
  Test: `test_run_provider_phase_recovers_from_stale_codex_resume_with_fresh_phase_bootstrap`
- Behavior covered: fallback retry rebuilds the prompt as a fresh phase thread with immutable request/bootstrap context instead of reusing the resumed-thread prompt.
  Test: `test_run_provider_phase_recovers_from_stale_codex_resume_with_fresh_phase_bootstrap`
- Preserved invariant: fresh-start Codex provider failures remain fatal and continue to log `provider_failure` without `session_recovery`.
  Test: `test_run_provider_phase_keeps_codex_start_failures_fatal`
- Failure path covered: if the resume recovery retry also fails, runtime still fatals and logs both the recovery entry and the fatal retry failure.
  Test: `test_run_provider_phase_fatals_when_codex_resume_recovery_retry_fails`
- Adjacent contract check: phase-local fresh-thread bootstrap ordering and markers remain intact.
  Test command: `pytest -q tests/test_phase_local_behavior.py -k 'fresh_phase_bootstrap or build_phase_prompt'`

## Stabilization Notes

- All covered paths stub `execute_provider_turn`, `warn`, and `fatal` directly to avoid CLI, timing, or environment nondeterminism.
- Prompt-content assertions use explicit strings for request/bootstrap markers and raw-log entry names so failures point to contract drift rather than incidental output changes.

## Known Gaps

- Claude resume failures and provider mismatch cases rely on existing non-test-phase coverage and were not duplicated here because this phase is scoped to Codex-only recovery behavior.

# Test Author ↔ Test Auditor Feedback

- Task ID: autoloop-improvement-instructions-please-impleme-8508e533
- Pair: test
- Phase ID: ux-installer-docs-and-cli-hardening
- Phase Directory Key: ux-installer-docs-and-cli-hardening
- Phase Title: Harden installer UX, quickstart docs, and git flag behavior
- Scope: phase-local authoritative verifier artifact

- Added installer regression coverage for the explicit rerun success path (`--overwrite` + `--recreate-venv`) and for the not-ready PATH-remediation branch when Codex is present but the launcher directory is not on `PATH`. Updated `test_strategy.md` with the behavior-to-test map and stabilization notes.
- TST-001 | blocking | `tests/test_installer.py`: every installer test passes `--skill-target` explicitly (usually `codex` or `none`), so the suite never verifies the shared-decision/backward-compatible default that omitting the flag should still install to both Codex and Agents skill targets. A regression changing the default from `both` to `codex` or `none` would still leave the current suite green. Minimal fix: add one installer test that omits `--skill-target` and asserts both skill destinations are written on a successful install.
- Addressed TST-001 by adding `tests/test_installer.py::test_installer_defaults_to_both_skill_targets`, which omits `--skill-target` and asserts that both the Codex and Agents skill destinations are written on a successful install.
- Re-audit result: no remaining blocking or non-blocking findings. Verified the default-target regression test is present and reran `pytest -q tests/test_installer.py tests/test_autoloop_observability.py tests/test_resources.py tests/test_module_entrypoint.py` successfully (`120 passed`).

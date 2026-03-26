# Test Strategy

- Task ID: autoloop-improvement-instructions-please-impleme-8508e533
- Pair: test
- Phase ID: ux-installer-docs-and-cli-hardening
- Phase Directory Key: ux-installer-docs-and-cli-hardening
- Phase Title: Harden installer UX, quickstart docs, and git flag behavior
- Scope: phase-local producer artifact

## Behavior-to-test coverage map

- Installer planning and dry-run:
  `tests/test_installer.py::test_installer_dry_run_prints_preflight_without_mutation`
- Installer guarded failure paths:
  `tests/test_installer.py::test_installer_existing_launcher_and_skill_require_overwrite`
  `tests/test_installer.py::test_installer_existing_venv_requires_recreate_flag`
- Installer explicit rerun success path:
  `tests/test_installer.py::test_installer_overwrite_and_recreate_flags_allow_safe_rerun`
- Skill target selection:
  `tests/test_installer.py::test_installer_defaults_to_both_skill_targets`
  `tests/test_installer.py::test_installer_skill_target_selection_limits_writes`
  `tests/test_installer.py::test_installer_reports_path_remediation_when_codex_is_present_but_launcher_not_on_path`
- Installer readiness messaging:
  `tests/test_installer.py::test_installer_reports_installed_but_not_ready_for_claude_only_path`
  `tests/test_installer.py::test_installer_reports_installed_and_ready_for_default_codex_path`
  `tests/test_installer.py::test_installer_reports_path_remediation_when_codex_is_present_but_launcher_not_on_path`
- Git flag cleanup and precedence invariants:
  `tests/test_autoloop_observability.py::test_build_arg_parser_exposes_explicit_git_flag_pair`
  `tests/test_autoloop_observability.py::test_resolve_runtime_config_applies_global_local_and_cli_precedence`
- README quickstart/docs coverage:
  `tests/test_resources.py::test_readme_quickstart_covers_first_run_resume_and_troubleshooting`
  `tests/test_module_entrypoint.py`

## Preserved invariants checked

- Hidden `--no-no-git` support remains removed while `--git` and `--no-git` keep deterministic precedence.
- Missing provider CLIs stay non-fatal to installer execution.
- Default installer behavior still writes the packaged skill to both Codex and Agents targets when `--skill-target` is omitted.
- Default skill target can be narrowed without touching the unselected skill destination.

## Edge cases and failure paths

- Existing launcher/skill without `--overwrite`
- Existing virtualenv without `--recreate-venv`
- Codex present but launcher bin directory missing from `PATH`
- Claude-only environment reported as installed but not ready

## Flake risks and stabilization

- Installer tests run with isolated temp directories and a synthetic `PATH` so provider detection and filesystem mutations are deterministic.
- Dependency installation and pip upgrade are disabled with existing test-only env toggles to avoid network and packaging nondeterminism.

## Known gaps

- No direct assertion currently checks `--skill-target agents`; coverage now includes the backward-compatible default plus narrowed `codex` and `none` targets.

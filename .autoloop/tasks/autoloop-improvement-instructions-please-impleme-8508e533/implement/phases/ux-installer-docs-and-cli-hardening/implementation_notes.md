# Implementation Notes

- Task ID: autoloop-improvement-instructions-please-impleme-8508e533
- Pair: implement
- Phase ID: ux-installer-docs-and-cli-hardening
- Phase Directory Key: ux-installer-docs-and-cli-hardening
- Phase Title: Harden installer UX, quickstart docs, and git flag behavior
- Scope: phase-local producer artifact

## Files changed

- `install_autoloop.sh`
- `README.md`
- `src/autoloop/main.py`
- `tests/test_installer.py`
- `tests/test_autoloop_observability.py`
- `tests/test_resources.py`
- `../decisions.txt`

## Symbols touched

- `build_arg_parser`
- installer shell helpers and option parsing in `install_autoloop.sh`

## Checklist mapping

- Milestone 1: implemented installer preflight planning, dry-run mode, overwrite gating, separate venv recreation flag, and skill target selection
- Milestone 2: implemented explicit ready/not-ready final messaging and prerequisite next steps
- Milestone 3: added README quickstart, resume/list commands, artifact expectations, and troubleshooting table
- Milestone 4: removed hidden `--no-no-git` parser alias and preserved existing config precedence behavior
- Milestone 5: added installer and README regression coverage and ran targeted tests

## Assumptions

- Ready/not-ready messaging should reflect whether a first default Codex-backed `autoloop ...` command is usable immediately, so the launcher bin directory being absent from `PATH` is treated as not ready
- Installer overwrite safety should guard managed files/paths without deleting broader parent skill directories

## Preserved invariants

- Missing provider CLIs remain non-fatal for installation
- Default skill target remains both Codex and Agents locations for backward compatibility
- Runtime config precedence remains builtins < global config < workspace config < CLI
- Public git flags remain `--git` and `--no-git`

## Intended behavior changes

- Installer reruns now fail fast before mutation when managed artifacts already exist unless the required explicit flags are supplied
- Installer supports `--dry-run`, `--overwrite`, `--recreate-venv`, and `--skill-target`
- Installer prints a mutation summary before writes and ends with explicit ready/not-ready wording plus next-step remediation
- README now includes a concise first-run quickstart and troubleshooting guidance
- Hidden `--no-no-git` parsing support has been removed

## Known non-changes

- Installer still does not install provider CLIs
- Missing git remains advisory because `--no-git` continues to be supported
- Runtime behavior outside the git parser cleanup was not changed

## Expected side effects

- Existing installs may require extra explicit flags on rerun
- Operators with Codex installed but without the launcher bin directory on `PATH` now get a non-ready final status until PATH is fixed

## Validation performed

- `bash -n install_autoloop.sh`
- `./install_autoloop.sh --help`
- `pytest -q tests/test_installer.py tests/test_autoloop_observability.py tests/test_resources.py tests/test_module_entrypoint.py`

## Deduplication / centralization

- Installer dry-run/live behavior shares one preflight planning path so the reported plan and real mutation gating stay aligned

# Retry: apply PR review feedback with YAML-safe planning artifacts

The previous run failed because generated `phase_plan.yaml` included YAML-invalid backtick content in a plain scalar. Re-run this task and ensure planning artifacts are YAML-parseable.

## Main task

Analyze and apply review suggestions for the `track_autoloop_artifacts` feature:
- improve ignore/tracked detection performance in staging logic
- harden porcelain path parsing (quoted/special filenames)
- handle `is_path_under_task_root(path, ".")` robustly
- preserve delta/scope invariants
- add/update tests accordingly

## Important planning artifact constraint

When generating `phase_plan.yaml` criteria text, avoid unescaped backticks or any YAML-breaking characters in plain scalars. Use YAML-safe quoted strings where needed.

## Execution mode

Run full workflow with pairs: plan, implement, test.

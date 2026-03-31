from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import autoloop.main as autoloop

from autoloop.main import (
    GitCommitPolicy,
    changed_paths,
    changed_paths_from_snapshot,
    commit_paths,
    parse_status_entries,
    phase_snapshot_ref,
)


def init_temp_git_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="autoloop-test-"))
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Autoloop Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "autoloop-test@example.com"], cwd=root, check=True)
    return root


def commit_initial_file(root: Path, name: str = "tracked.txt", content: str = "init\n") -> Path:
    path = root / name
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return path


def last_commit_files(root: Path) -> set[str]:
    show = subprocess.run(
        ["git", "show", "--name-only", "--pretty=", "-z"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.split("\0")
    return {entry for entry in show if entry}


def test_dirty_file_edited_again_is_in_snapshot_delta():
    root = init_temp_git_repo()
    tracked = commit_initial_file(root)

    # Already dirty before snapshot
    tracked.write_text("init\nbefore\n", encoding="utf-8")
    snap = phase_snapshot_ref(root)

    # Edited again during phase
    tracked.write_text("init\nbefore\nafter\n", encoding="utf-8")
    delta = changed_paths_from_snapshot(root, snap)

    assert "tracked.txt" in delta


def test_new_untracked_file_after_baseline_is_in_delta():
    root = init_temp_git_repo()
    commit_initial_file(root)

    snap = phase_snapshot_ref(root)
    (root / "new_file.txt").write_text("new\n", encoding="utf-8")

    delta = changed_paths_from_snapshot(root, snap)
    assert "new_file.txt" in delta


def test_preexisting_untracked_file_is_not_reported_as_new_delta():
    root = init_temp_git_repo()
    commit_initial_file(root)

    # Exists before baseline snapshot
    (root / "already_untracked.txt").write_text("existing\n", encoding="utf-8")
    snap = phase_snapshot_ref(root)

    # Phase makes no new changes
    delta = changed_paths_from_snapshot(root, snap)
    assert "already_untracked.txt" not in delta


def test_commit_paths_commits_only_requested_paths():
    root = init_temp_git_repo()
    commit_initial_file(root)

    a = root / "a.txt"
    b = root / "b.txt"
    a.write_text("A\n", encoding="utf-8")
    b.write_text("B\n", encoding="utf-8")

    committed = commit_paths(root, "commit-a-only", ["a.txt"])
    assert committed is True

    committed_files = last_commit_files(root)

    assert "a.txt" in committed_files
    assert "b.txt" not in committed_files


def test_commit_paths_tracks_run_artifacts_under_task_root_by_default():
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    events_file = root / task_root / "runs" / "run-1" / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text('{"event_type":"run_started"}\n', encoding="utf-8")

    committed = commit_paths(
        root,
        "track-task-root",
        [f"{task_root}/"],
        git_commit_policy=GitCommitPolicy(task_root_rel=task_root),
    )

    assert committed is True
    assert f"{task_root}/runs/run-1/events.jsonl" in last_commit_files(root)


def test_commit_paths_opt_out_filters_task_root_but_keeps_external_paths():
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    feedback = root / task_root / "implement" / "phases" / "phase-1" / "feedback.md"
    feedback.parent.mkdir(parents=True, exist_ok=True)
    feedback.write_text("# feedback\n", encoding="utf-8")
    src_file = root / "src" / "feature.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("print('ok')\n", encoding="utf-8")

    committed = commit_paths(
        root,
        "opt-out",
        [f"{task_root}/", "src/feature.py"],
        git_commit_policy=GitCommitPolicy(task_root_rel=task_root, track_autoloop_artifacts=False),
    )

    assert committed is True
    committed_files = last_commit_files(root)
    assert "src/feature.py" in committed_files
    assert f"{task_root}/implement/phases/phase-1/feedback.md" not in committed_files


def test_commit_paths_skips_ignored_untracked_task_root_paths_with_single_warning(monkeypatch):
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    (root / ".gitignore").write_text(f"{task_root}/runs/\n", encoding="utf-8")
    ignored_file = root / task_root / "runs" / "run-1" / "events.jsonl"
    ignored_file.parent.mkdir(parents=True, exist_ok=True)
    ignored_file.write_text('{"event_type":"run_started"}\n', encoding="utf-8")

    warnings: list[str] = []
    monkeypatch.setattr(autoloop, "warn", lambda message: warnings.append(message))
    policy = GitCommitPolicy(task_root_rel=task_root)

    assert commit_paths(root, "ignored-untracked", [f"{task_root}/"], git_commit_policy=policy) is False
    assert commit_paths(root, "ignored-untracked-again", [f"{task_root}/"], git_commit_policy=policy) is False
    assert warnings == [
        (
            "Ignored untracked Autoloop workspace paths under "
            f"`{task_root}` were skipped during auto-stage. Remove the ignore rule or track those paths manually if they should be committed."
        )
    ]


def test_commit_paths_skips_ignored_untracked_task_root_paths_but_commits_external_changes(monkeypatch):
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    (root / ".gitignore").write_text(f"{task_root}/runs/\n", encoding="utf-8")
    ignored_file = root / task_root / "runs" / "run-1" / "events.jsonl"
    ignored_file.parent.mkdir(parents=True, exist_ok=True)
    ignored_file.write_text('{"event_type":"run_started"}\n', encoding="utf-8")

    src_file = root / "src" / "feature.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("print('ok')\n", encoding="utf-8")

    warnings: list[str] = []
    monkeypatch.setattr(autoloop, "warn", lambda message: warnings.append(message))

    committed = commit_paths(
        root,
        "ignored-untracked-with-external",
        [f"{task_root}/", "src/feature.py"],
        git_commit_policy=GitCommitPolicy(task_root_rel=task_root),
    )

    assert committed is True
    committed_files = last_commit_files(root)
    assert "src/feature.py" in committed_files
    assert f"{task_root}/runs/run-1/events.jsonl" not in committed_files
    assert warnings == [
        (
            "Ignored untracked Autoloop workspace paths under "
            f"`{task_root}` were skipped during auto-stage. Remove the ignore rule or track those paths manually if they should be committed."
        )
    ]


def test_commit_paths_warns_once_for_ignored_but_tracked_task_root_paths(monkeypatch):
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    tracked_file = root / task_root / "decisions.txt"
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_file.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", f"{task_root}/decisions.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "track-task-file"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    (root / ".gitignore").write_text(f"{task_root}/decisions.txt\n", encoding="utf-8")

    warnings: list[str] = []
    monkeypatch.setattr(autoloop, "warn", lambda message: warnings.append(message))
    policy = GitCommitPolicy(task_root_rel=task_root)

    tracked_file.write_text("first update\n", encoding="utf-8")
    assert commit_paths(root, "ignored-tracked-1", [f"{task_root}/"], git_commit_policy=policy) is True
    assert f"{task_root}/decisions.txt" in last_commit_files(root)

    tracked_file.write_text("second update\n", encoding="utf-8")
    assert commit_paths(root, "ignored-tracked-2", [f"{task_root}/"], git_commit_policy=policy) is True
    assert warnings == [
        (
            "Already-tracked Autoloop workspace paths under "
            f"`{task_root}` still match ignore rules. Git may continue auto-committing updates to those tracked paths until they are removed from the index."
        )
    ]


def test_commit_paths_stages_task_root_files_with_spaces_in_their_names():
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    artifact = root / task_root / "implement" / "phases" / "phase 1" / "notes with spaces.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# notes\n", encoding="utf-8")

    committed = commit_paths(
        root,
        "track-spaced-artifact",
        [f"{task_root}/"],
        git_commit_policy=GitCommitPolicy(task_root_rel=task_root),
    )

    assert committed is True
    assert f"{task_root}/implement/phases/phase 1/notes with spaces.md" in last_commit_files(root)


def test_changed_paths_and_commit_paths_use_rename_destination_paths():
    root = init_temp_git_repo()
    commit_initial_file(root)

    task_root = ".autoloop/tasks/task-1"
    original = root / task_root / "old name.txt"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", f"{task_root}/old name.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "add-task-file"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    subprocess.run(["git", "mv", f"{task_root}/old name.txt", f"{task_root}/new name.txt"], cwd=root, check=True)

    delta = changed_paths(root, tracked_paths=[f"{task_root}/"])

    assert f"{task_root}/new name.txt" in delta
    assert f"{task_root}/old name.txt" not in delta

    committed = commit_paths(
        root,
        "rename-task-file",
        [f"{task_root}/"],
        git_commit_policy=GitCommitPolicy(task_root_rel=task_root),
    )

    assert committed is True
    assert f"{task_root}/new name.txt" in last_commit_files(root)


def test_parse_status_entries_handles_nul_delimited_rename_copy_and_embedded_newlines():
    status_text = (
        "R  .autoloop/tasks/task-1/new name.txt\0"
        ".autoloop/tasks/task-1/old name.txt\0"
        "C  .autoloop/tasks/task-1/copied notes.txt\0"
        ".autoloop/tasks/task-1/source notes.txt\0"
        "?? .autoloop/tasks/task-1/notes\nwith newline.md\0"
    )

    assert parse_status_entries(status_text) == [
        ("R ", ".autoloop/tasks/task-1/new name.txt"),
        ("C ", ".autoloop/tasks/task-1/copied notes.txt"),
        ("??", ".autoloop/tasks/task-1/notes\nwith newline.md"),
    ]

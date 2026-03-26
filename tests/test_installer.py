from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "install_autoloop.sh"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def build_installer_env(
    tmp_path: Path,
    *,
    fake_codex: bool = False,
    fake_claude: bool = False,
    bin_on_path: bool = False,
) -> tuple[dict[str, str], Path, Path, Path, Path]:
    install_root = tmp_path / "install-root"
    bin_dir = tmp_path / "bin"
    home_dir = tmp_path / "home"
    codex_home = tmp_path / "codex-home"
    fake_path_dir = tmp_path / "fake-path"

    home_dir.mkdir()
    fake_path_dir.mkdir()

    if fake_codex:
        write_executable(fake_path_dir / "codex", "#!/usr/bin/env bash\nexit 0\n")
    if fake_claude:
        write_executable(fake_path_dir / "claude", "#!/usr/bin/env bash\nexit 0\n")

    path_entries = [str(fake_path_dir)]
    for command_name in ("bash", "python3", "install", "cp", "rm", "chmod", "mkdir"):
        command_path = shutil.which(command_name)
        if command_path is None:
            continue
        command_dir = str(Path(command_path).parent)
        if command_dir not in path_entries:
            path_entries.append(command_dir)
    if bin_on_path:
        path_entries.append(str(bin_dir))

    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home_dir),
            "PATH": os.pathsep.join(path_entries),
            "AUTOLOOP_INSTALL_ROOT": str(install_root),
            "AUTOLOOP_BIN_DIR": str(bin_dir),
            "CODEX_HOME": str(codex_home),
            "AUTOLOOP_SKIP_PIP_UPGRADE": "1",
            "AUTOLOOP_SKIP_DEP_INSTALL": "1",
        }
    )
    return env, install_root, bin_dir, codex_home, home_dir


def run_installer(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALLER), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_installer_dry_run_prints_preflight_without_mutation(tmp_path: Path):
    env, install_root, bin_dir, codex_home, home_dir = build_installer_env(tmp_path)

    result = run_installer(["--dry-run", "--skill-target", "codex"], env)

    assert result.returncode == 0, result.stderr
    assert "Pre-flight summary" in result.stdout
    assert "dry-run only; no files will be changed" in result.stdout
    assert "Predicted final status: installed but not ready." in result.stdout
    assert not install_root.exists()
    assert not (bin_dir / "autoloop").exists()
    assert not (codex_home / "skills" / "autoloop" / "SKILL.md").exists()
    assert not (home_dir / ".agents" / "skills" / "autoloop" / "SKILL.md").exists()


def test_installer_existing_launcher_and_skill_require_overwrite(tmp_path: Path):
    env, install_root, bin_dir, codex_home, _ = build_installer_env(tmp_path)
    launcher = bin_dir / "autoloop"
    skill_file = codex_home / "skills" / "autoloop" / "SKILL.md"

    skill_file.parent.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    launcher.write_text("old launcher\n", encoding="utf-8")
    skill_file.write_text("old skill\n", encoding="utf-8")

    result = run_installer(["--skill-target", "codex"], env)

    assert result.returncode == 1
    assert "--overwrite" in result.stdout
    assert launcher.read_text(encoding="utf-8") == "old launcher\n"
    assert skill_file.read_text(encoding="utf-8") == "old skill\n"
    assert not (install_root / "venv").exists()


def test_installer_existing_venv_requires_recreate_flag(tmp_path: Path):
    env, install_root, _, _, _ = build_installer_env(tmp_path)
    marker = install_root / "venv" / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("keep me\n", encoding="utf-8")

    result = run_installer(["--skill-target", "none"], env)

    assert result.returncode == 1
    assert "--recreate-venv" in result.stdout
    assert marker.read_text(encoding="utf-8") == "keep me\n"


def test_installer_overwrite_and_recreate_flags_allow_safe_rerun(tmp_path: Path):
    env, install_root, bin_dir, codex_home, home_dir = build_installer_env(tmp_path, fake_codex=True, bin_on_path=True)
    launcher = bin_dir / "autoloop"
    skill_file = codex_home / "skills" / "autoloop" / "SKILL.md"
    marker = install_root / "venv" / "marker.txt"
    expected_skill = (REPO_ROOT / "src" / "autoloop" / "skill" / "SKILL.md").read_text(encoding="utf-8")

    launcher.parent.mkdir(parents=True)
    skill_file.parent.mkdir(parents=True)
    marker.parent.mkdir(parents=True)
    launcher.write_text("old launcher\n", encoding="utf-8")
    skill_file.write_text("old skill\n", encoding="utf-8")
    marker.write_text("old venv\n", encoding="utf-8")

    result = run_installer(["--overwrite", "--recreate-venv", "--skill-target", "codex"], env)

    assert result.returncode == 0, result.stderr
    assert "Overwrites" in result.stdout
    assert "Deletes" in result.stdout
    assert "Final status: installed and ready." in result.stdout
    assert str(install_root / "venv") in launcher.read_text(encoding="utf-8")
    assert skill_file.read_text(encoding="utf-8") == expected_skill
    assert not marker.exists()
    assert not (home_dir / ".agents" / "skills" / "autoloop" / "SKILL.md").exists()


def test_installer_skill_target_selection_limits_writes(tmp_path: Path):
    env, install_root, bin_dir, codex_home, home_dir = build_installer_env(tmp_path)

    result = run_installer(["--skill-target", "codex"], env)

    assert result.returncode == 0, result.stderr
    assert (install_root / "venv" / "bin" / "python").exists()
    assert (bin_dir / "autoloop").exists()
    assert (codex_home / "skills" / "autoloop" / "SKILL.md").exists()
    assert not (home_dir / ".agents" / "skills" / "autoloop" / "SKILL.md").exists()


def test_installer_defaults_to_both_skill_targets(tmp_path: Path):
    env, _, _, codex_home, home_dir = build_installer_env(tmp_path)

    result = run_installer([], env)

    assert result.returncode == 0, result.stderr
    assert (codex_home / "skills" / "autoloop" / "SKILL.md").exists()
    assert (home_dir / ".agents" / "skills" / "autoloop" / "SKILL.md").exists()


def test_installer_reports_installed_but_not_ready_for_claude_only_path(tmp_path: Path):
    env, _, bin_dir, _, _ = build_installer_env(tmp_path, fake_claude=True, bin_on_path=True)
    bin_dir.mkdir(parents=True)

    result = run_installer(["--skill-target", "none"], env)

    assert result.returncode == 0, result.stderr
    assert "Final status: installed but not ready." in result.stdout
    assert "provider.name: claude" in result.stdout
    assert "claude auth status" in result.stdout
    assert "npm i -g @openai/codex" in result.stdout


def test_installer_reports_installed_and_ready_for_default_codex_path(tmp_path: Path):
    env, _, bin_dir, _, _ = build_installer_env(tmp_path, fake_codex=True, bin_on_path=True)
    bin_dir.mkdir(parents=True)

    result = run_installer(["--skill-target", "none"], env)

    assert result.returncode == 0, result.stderr
    assert "Final status: installed and ready." in result.stdout


def test_installer_reports_path_remediation_when_codex_is_present_but_launcher_not_on_path(tmp_path: Path):
    env, _, _, codex_home, home_dir = build_installer_env(tmp_path, fake_codex=True, bin_on_path=False)

    result = run_installer(["--skill-target", "none"], env)

    assert result.returncode == 0, result.stderr
    assert "Final status: installed but not ready." in result.stdout
    assert 'export PATH="' in result.stdout
    assert not (codex_home / "skills" / "autoloop" / "SKILL.md").exists()
    assert not (home_dir / ".agents" / "skills" / "autoloop" / "SKILL.md").exists()

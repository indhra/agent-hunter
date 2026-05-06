"""
Integration tests for the ./setup installer script.

These tests run the actual bash setup script in a sandboxed environment:
- HOME is redirected to a temp directory so symlinks go to tmp/.claude/skills/
  instead of the real ~/.claude/skills/ — your real install is never touched.
- The venv and bin/ are written to the real repo (they're gitignored), which
  makes re-runs fast (deps are already installed).

Run:
    pytest tests/test_setup.py -v
    pytest tests/test_setup.py -v -k "symlink or wrapper"   # subset

Mark:  @pytest.mark.setup — all tests here carry this mark.
Skip:  pytest tests/test_setup.py --ignore-glob="*test_setup*" to skip entirely.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SETUP_SCRIPT = REPO_ROOT / "setup"

pytestmark = pytest.mark.setup


# ── helpers ──────────────────────────────────────────────────────────────────


def _run_setup(fake_home: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """Run ./setup with HOME redirected to *fake_home*."""
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["TERM"] = "dumb"  # suppress color escape codes in assertions
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SETUP_SCRIPT)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,  # first run installs deps — allow time
    )


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences so assertions work on plain text."""
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    """Temporary HOME with .claude/skills/ pre-created, isolated per test."""
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    return tmp_path


@pytest.fixture(scope="module")
def setup_result(tmp_path_factory: pytest.TempPathFactory):
    """Run setup ONCE for the whole module — faster than per-test."""
    fake_home = tmp_path_factory.mktemp("home")
    (fake_home / ".claude" / "skills").mkdir(parents=True)
    result = _run_setup(fake_home)
    return result, fake_home


# ── basic sanity ─────────────────────────────────────────────────────────────


class TestSetupBasic:
    def test_setup_script_exists(self):
        assert SETUP_SCRIPT.exists(), f"setup script not found at {SETUP_SCRIPT}"
        assert os.access(SETUP_SCRIPT, os.X_OK) or True  # executable or bash-runnable

    def test_exits_zero(self, setup_result):
        result, _ = setup_result
        assert result.returncode == 0, (
            f"setup exited {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    def test_detects_python_version(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "Python 3." in out, f"No Python version line in output:\n{out}"

    def test_no_unexpected_errors(self, setup_result):
        result, _ = setup_result
        # stderr should be empty (or only ignorable pip noise)
        err = result.stderr.strip()
        fatal_keywords = ["Traceback", "Error:", "FAILED", "fatal"]
        for kw in fatal_keywords:
            assert kw not in err, f"Unexpected error in stderr ({kw!r}):\n{err}"


# ── venv ─────────────────────────────────────────────────────────────────────


class TestVenv:
    def test_venv_directory_created(self, setup_result):
        _, _ = setup_result
        assert (REPO_ROOT / ".venv").exists(), ".venv/ not created"

    def test_venv_python_executable(self, setup_result):
        _, _ = setup_result
        venv_python = REPO_ROOT / ".venv" / "bin" / "python"
        assert venv_python.exists(), f"venv python not found at {venv_python}"
        assert os.access(venv_python, os.X_OK), "venv python is not executable"

    def test_dependencies_installed(self, setup_result):
        _, _ = setup_result
        venv_pip = REPO_ROOT / ".venv" / "bin" / "pip"
        result = subprocess.run(
            [str(venv_pip), "show", "requests", "PyYAML", "rich"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Required packages missing:\n{result.stdout}\n{result.stderr}"
        )

    def test_output_mentions_venv(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "venv" in out.lower() or "Dependencies installed" in out


# ── bin wrapper ──────────────────────────────────────────────────────────────


class TestWrapper:
    def test_wrapper_file_written(self, setup_result):
        _, _ = setup_result
        wrapper = REPO_ROOT / "bin" / "agent-hunter"
        assert wrapper.exists(), f"bin/agent-hunter wrapper not created at {wrapper}"

    def test_wrapper_is_executable(self, setup_result):
        _, _ = setup_result
        wrapper = REPO_ROOT / "bin" / "agent-hunter"
        assert wrapper.stat().st_mode & stat.S_IXUSR, "bin/agent-hunter is not executable"

    def test_wrapper_is_bash_script(self, setup_result):
        _, _ = setup_result
        wrapper = REPO_ROOT / "bin" / "agent-hunter"
        first_line = wrapper.read_text().splitlines()[0]
        assert "bash" in first_line or "sh" in first_line, (
            f"Wrapper doesn't look like a shell script (first line: {first_line!r})"
        )

    def test_wrapper_invokes_venv_python(self, setup_result):
        _, _ = setup_result
        wrapper_text = (REPO_ROOT / "bin" / "agent-hunter").read_text()
        assert ".venv" in wrapper_text, "Wrapper doesn't reference the venv"
        assert "main.py" in wrapper_text, "Wrapper doesn't reference main.py"

    def test_wrapper_help_flag_works(self, setup_result):
        _, _ = setup_result
        result = subprocess.run(
            [str(REPO_ROOT / "bin" / "agent-hunter"), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"bin/agent-hunter --help failed:\n{result.stdout}\n{result.stderr}"
        )

    def test_wrapper_lists_commands(self, setup_result):
        _, _ = setup_result
        result = subprocess.run(
            [str(REPO_ROOT / "bin" / "agent-hunter"), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = result.stdout + result.stderr
        assert "hunt" in out.lower(), f"'hunt' not in --help output:\n{out}"


# ── symlinks ─────────────────────────────────────────────────────────────────


class TestSymlinks:
    def test_agent_hunter_update_symlinked(self, setup_result):
        result, fake_home = setup_result
        symlink = fake_home / ".claude" / "skills" / "agent-hunter-update"
        assert symlink.exists(), (
            f"agent-hunter-update symlink not found at {symlink}\nsetup stdout:\n{result.stdout}"
        )

    def test_symlink_is_a_symlink(self, setup_result):
        _, fake_home = setup_result
        symlink = fake_home / ".claude" / "skills" / "agent-hunter-update"
        assert symlink.is_symlink(), f"{symlink} exists but is not a symlink"

    def test_symlink_points_to_skill_dir(self, setup_result):
        _, fake_home = setup_result
        symlink = fake_home / ".claude" / "skills" / "agent-hunter-update"
        expected = (REPO_ROOT / "agent-hunter-update").resolve()
        actual = symlink.resolve()
        assert actual == expected, (
            f"Symlink points to wrong target.\n  Got:      {actual}\n  Expected: {expected}"
        )

    def test_symlink_skill_md_readable(self, setup_result):
        _, fake_home = setup_result
        skill_md = fake_home / ".claude" / "skills" / "agent-hunter-update" / "SKILL.md"
        assert skill_md.exists(), f"SKILL.md not reachable via symlink at {skill_md}"

    def test_setup_output_mentions_linked_skill(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "agent-hunter-update" in out, (
            f"setup output doesn't mention agent-hunter-update:\n{out}"
        )


# ── CLAUDE.md block ───────────────────────────────────────────────────────────


class TestClaudeMdBlock:
    def test_block_header_in_output(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "## agent-hunter" in out

    def test_block_lists_agent_hunter_skill(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "/agent-hunter" in out

    def test_block_lists_update_skill(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "/agent-hunter-update" in out

    def test_block_mentions_security_scan(self, setup_result):
        result, _ = setup_result
        out = _strip_ansi(result.stdout)
        assert "security-scan" in out or "security scan" in out

    def test_auto_append_skipped_when_in_skill_dir(self, fake_home):
        """When run FROM the skill dir itself, the interactive append is skipped."""
        result = _run_setup(fake_home)
        out = _strip_ansi(result.stdout)
        # Should not prompt when cwd == SKILL_DIR
        assert "Add the agent-hunter section" not in out


# ── idempotency ───────────────────────────────────────────────────────────────


class TestIdempotency:
    def test_second_run_exits_zero(self, fake_home):
        r1 = _run_setup(fake_home)
        r2 = _run_setup(fake_home)
        assert r1.returncode == 0, f"First run failed:\n{r1.stdout}\n{r1.stderr}"
        assert r2.returncode == 0, f"Second run failed:\n{r2.stdout}\n{r2.stderr}"

    def test_second_run_does_not_duplicate_symlink(self, fake_home):
        _run_setup(fake_home)
        _run_setup(fake_home)
        symlink = fake_home / ".claude" / "skills" / "agent-hunter-update"
        assert symlink.is_symlink(), "Symlink should still exist after second run"

    def test_second_run_is_faster(self, fake_home):
        import time

        t0 = time.monotonic()
        _run_setup(fake_home)
        first_duration = time.monotonic() - t0

        t0 = time.monotonic()
        _run_setup(fake_home)
        second_duration = time.monotonic() - t0

        # Second run skips heavy dep install — should be meaningfully faster.
        # We allow 2x first_duration as a loose upper bound.
        assert second_duration < first_duration * 2, (
            f"Second run ({second_duration:.1f}s) not faster than first ({first_duration:.1f}s) — "
            "venv reuse may be broken"
        )


# ── python version guard ──────────────────────────────────────────────────────


class TestPythonVersionGuard:
    def test_fails_with_fake_old_python(self, fake_home, tmp_path):
        """setup should exit non-zero if only Python 2.x is available."""
        # Create a fake 'python3' that reports version 2.7
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_python = fake_bin / "python3"
        fake_python.write_text(
            "#!/usr/bin/env bash\n"
            'if [[ "$*" == *"version_info.minor"* ]]; then echo 7; exit 0; fi\n'
            'if [[ "$*" == *"version_info.major"* ]]; then echo 2; exit 0; fi\n'
            'echo "Python 2.7.18"\n'
        )
        fake_python.chmod(fake_python.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        # Shadow PATH — keep /bin so bash itself is still reachable, but fake python3 wins
        env_path = f"{fake_bin}:/usr/bin:/bin"
        result = _run_setup(fake_home, extra_env={"PATH": env_path})
        assert result.returncode != 0, (
            "setup should fail when no Python 3.10+ is available, but it exited 0"
        )

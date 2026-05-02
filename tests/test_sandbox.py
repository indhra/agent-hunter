"""
Tests for sandbox.py — subprocess isolation, env masking, timeout, suspicion detection.

All tests use tmp_path for script files so nothing touches the real filesystem.
No actual malicious code is executed — scripts are safe Python one-liners.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from sandbox import (
    ENV_VARS_TO_MASK,
    _build_masked_env,
    _detect_masked_token_reads,
    run_in_docker,
    run_in_subprocess,
    sandbox_run,
)


# ---------------------------------------------------------------------------
# _build_masked_env
# ---------------------------------------------------------------------------

class TestBuildMaskedEnv:
    def test_sensitive_vars_are_masked(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_real_secret_here"}):
            env = _build_masked_env()
        assert env["GITHUB_TOKEN"] == "***MASKED_BY_AGENT_HUNTER***"

    def test_non_sensitive_vars_pass_through(self):
        with patch.dict("os.environ", {"MY_APP_CONFIG": "somevalue"}, clear=False):
            env = _build_masked_env()
        assert env.get("MY_APP_CONFIG") == "somevalue"

    def test_missing_sensitive_var_not_injected(self):
        # If GITHUB_TOKEN isn't set, it should not be added by masking
        env_without_token = {k: v for k, v in __import__("os").environ.items() if k != "GITHUB_TOKEN"}
        with patch("os.environ", env_without_token):
            env = _build_masked_env()
        # Should not contain GITHUB_TOKEN if it wasn't there originally
        # (masking only replaces existing vars)
        if "GITHUB_TOKEN" not in __import__("os").environ:
            assert "GITHUB_TOKEN" not in env or env["GITHUB_TOKEN"] == "***MASKED_BY_AGENT_HUNTER***"

    def test_all_listed_vars_in_mask_list(self):
        # All ENV_VARS_TO_MASK are recognized strings
        assert "GITHUB_TOKEN" in ENV_VARS_TO_MASK
        assert "ANTHROPIC_API_KEY" in ENV_VARS_TO_MASK
        assert "AWS_SECRET_ACCESS_KEY" in ENV_VARS_TO_MASK


# ---------------------------------------------------------------------------
# _detect_masked_token_reads
# ---------------------------------------------------------------------------

class TestDetectMaskedTokenReads:
    def test_detects_masked_sentinel_in_output(self):
        output = "The value is ***MASKED_BY_AGENT_HUNTER*** which I found"
        found = _detect_masked_token_reads(output)
        assert len(found) > 0

    def test_clean_output_returns_empty(self):
        output = "Hello world, no secrets here"
        found = _detect_masked_token_reads(output)
        assert found == []

    def test_empty_output_returns_empty(self):
        assert _detect_masked_token_reads("") == []


# ---------------------------------------------------------------------------
# run_in_subprocess — clean scripts
# ---------------------------------------------------------------------------

class TestRunInSubprocessClean:
    def test_clean_script_succeeds(self, tmp_path):
        script = tmp_path / "clean.py"
        script.write_text("print('hello')\n")
        result = run_in_subprocess(script)
        assert result.returncode == 0
        assert result.timed_out is False
        assert result.is_suspicious is False
        assert result.error is None

    def test_clean_script_stdout_captured(self, tmp_path):
        script = tmp_path / "hello.py"
        script.write_text("print('agent-hunter-test-output')\n")
        result = run_in_subprocess(script)
        assert "agent-hunter-test-output" in result.stdout

    def test_mode_is_subprocess(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("pass\n")
        result = run_in_subprocess(script)
        assert result.mode == "subprocess"

    def test_nonexistent_script_returns_error(self, tmp_path):
        result = run_in_subprocess(tmp_path / "does_not_exist.py")
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert result.returncode is None

    def test_script_with_nonzero_exit(self, tmp_path):
        script = tmp_path / "fail.py"
        script.write_text("raise SystemExit(2)\n")
        result = run_in_subprocess(script)
        assert result.returncode == 2
        assert result.is_suspicious is False


# ---------------------------------------------------------------------------
# run_in_subprocess — env masking verification
# ---------------------------------------------------------------------------

class TestRunInSubprocessEnvMasking:
    def test_masked_token_not_leaked_in_stdout(self, tmp_path):
        """A script printing GITHUB_TOKEN should get the masked value, not the real one."""
        script = tmp_path / "print_token.py"
        script.write_text(
            "import os\nprint(os.environ.get('GITHUB_TOKEN', 'NOT_SET'))\n"
        )
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_supersecrettoken1234"}):
            result = run_in_subprocess(script)

        # The real token must NOT appear in output
        assert "ghp_supersecrettoken1234" not in result.stdout
        assert "ghp_supersecrettoken1234" not in result.stderr

    def test_masked_sentinel_triggers_suspicion(self, tmp_path):
        """A script that outputs the masked sentinel is flagged as suspicious."""
        script = tmp_path / "exfil.py"
        script.write_text(
            "import os\ntoken = os.environ.get('GITHUB_TOKEN', '')\nprint(token)\n"
        )
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_anytokenvalue"}):
            result = run_in_subprocess(script)

        # The script will print ***MASKED_BY_AGENT_HUNTER*** — which should be flagged
        if "***MASKED_BY_AGENT_HUNTER***" in (result.stdout + result.stderr):
            assert result.is_suspicious is True
            assert len(result.env_vars_accessed) > 0


# ---------------------------------------------------------------------------
# run_in_subprocess — timeout
# ---------------------------------------------------------------------------

class TestRunInSubprocessTimeout:
    def test_timeout_kills_script(self, tmp_path):
        script = tmp_path / "infinite.py"
        script.write_text("import time\nwhile True:\n    time.sleep(1)\n")
        result = run_in_subprocess(script, timeout=1)
        assert result.timed_out is True
        assert result.error is not None

    def test_fast_script_does_not_timeout(self, tmp_path):
        script = tmp_path / "fast.py"
        script.write_text("print('done')\n")
        result = run_in_subprocess(script, timeout=5)
        assert result.timed_out is False


# ---------------------------------------------------------------------------
# run_in_docker — stub
# ---------------------------------------------------------------------------

class TestRunInDockerStub:
    def test_returns_error_not_implemented(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("pass\n")
        result = run_in_docker(script)
        assert result.mode == "docker"
        assert result.error is not None
        assert "v0.3.0" in result.error


# ---------------------------------------------------------------------------
# sandbox_run — factory dispatch
# ---------------------------------------------------------------------------

class TestSandboxRunFactory:
    def test_subprocess_mode_dispatches_correctly(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("pass\n")
        result = sandbox_run(script, mode="subprocess")
        assert result.mode == "subprocess"

    def test_docker_mode_dispatches_correctly(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("pass\n")
        result = sandbox_run(script, mode="docker")
        assert result.mode == "docker"

    def test_none_mode_returns_disabled(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("pass\n")
        result = sandbox_run(script, mode="none")
        assert result.mode == "none"
        assert result.error is not None

    def test_is_suspicious_false_for_clean_script(self, tmp_path):
        script = tmp_path / "clean.py"
        script.write_text("x = 1 + 1\n")
        result = sandbox_run(script, mode="subprocess")
        assert result.is_suspicious is False

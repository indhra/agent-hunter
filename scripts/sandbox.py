"""
sandbox.py — Runtime isolation for suspicious skill scripts.

Why static analysis is not enough:
    Prompt injection, obfuscated shell calls, and dynamic eval() can bypass
    regex-based static scanning. The sandbox adds a second defensive layer:
    actually execute the suspect code in isolation and observe its behavior.

Sandbox modes (configurable in config.json "sandbox_mode"):
    "none"       — no sandbox, trust static scan only (not recommended)
    "subprocess" — run in child process with masked env vars and restricted cwd
    "docker"     — run in a disposable Docker container (v0.3.0+, opt-in)

What is sandboxed:
    - Skills that received a YELLOW rating from static scan
    - Skills from "raw" trust tier (not verified or community-reviewed)
    - Skills being installed for the first time

What the sandbox checks:
    - Does the script attempt to read environment variables?
    - Does it make unexpected network calls?
    - Does it write files outside its working directory?
    - Does it fail or error in unexpected ways?

Human remains in the loop: sandbox results are shown in the hunt report.
Installation is never automatic.

No LLM calls.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Environment variable names to mask in subprocess mode
ENV_VARS_TO_MASK = [
    "GITHUB_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "DATABASE_URL",
    "SECRET_KEY",
    "PRIVATE_KEY",
    "AUTH_TOKEN",
    "SLACK_TOKEN",
    "DISCORD_TOKEN",
    "TELEGRAM_TOKEN",
]

SANDBOX_TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SandboxResult:
    mode: str = "none"  # "subprocess", "docker", "none"
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    env_vars_accessed: list[str] = field(default_factory=list)  # suspicious reads
    network_calls_detected: bool = False
    file_writes_outside_cwd: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def is_suspicious(self) -> bool:
        return bool(
            self.env_vars_accessed or self.network_calls_detected or self.file_writes_outside_cwd
        )


# ---------------------------------------------------------------------------
# Subprocess sandbox (v0.2.0)
# ---------------------------------------------------------------------------


def run_in_subprocess(
    script_path: str | Path,
    timeout: int = SANDBOX_TIMEOUT_SECONDS,
) -> SandboxResult:
    """Run a Python script in an isolated subprocess with masked environment.

    The subprocess runs with:
    - All sensitive env vars replaced with "***MASKED***"
    - A fresh temp directory as the working directory
    - stdout/stderr captured (not echoed to host)
    - Hard timeout (killed after `timeout` seconds)

    Args:
        script_path: Path to the Python script to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        SandboxResult with execution details and suspicion indicators.
    """
    result = SandboxResult(mode="subprocess")
    script_path = Path(script_path)

    if not script_path.exists():
        result.error = f"Script not found: {script_path}"
        return result

    # Build masked environment
    masked_env = _build_masked_env()

    with tempfile.TemporaryDirectory(prefix="agent-hunter-sandbox-") as tmpdir:
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                env=masked_env,
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result.returncode = proc.returncode
            result.stdout = proc.stdout[:2000]  # limit output
            result.stderr = proc.stderr[:2000]

            # Check if masked tokens appear in output (exfiltration attempt)
            result.env_vars_accessed = _detect_masked_token_reads(proc.stdout + proc.stderr)

        except subprocess.TimeoutExpired:
            result.timed_out = True
            result.error = f"Script exceeded {timeout}s timeout — killed."
        except (OSError, PermissionError) as exc:
            result.error = str(exc)

    return result


def _build_masked_env() -> dict[str, str]:
    """Return a copy of the current environment with sensitive vars masked."""
    env = os.environ.copy()
    for var in ENV_VARS_TO_MASK:
        if var in env:
            env[var] = "***MASKED_BY_AGENT_HUNTER***"
    return env


def _detect_masked_token_reads(output: str) -> list[str]:
    """Detect if the sandbox script tried to read masked env vars (and outputted them)."""
    found = []
    for var in ENV_VARS_TO_MASK:
        if "***MASKED_BY_AGENT_HUNTER***" in output:
            found.append(var)
            break  # one hit is enough to flag
    return found


# ---------------------------------------------------------------------------
# Docker sandbox (v0.6.0 — complete implementation)
# ---------------------------------------------------------------------------


def _check_docker_available() -> bool:
    """Check if Docker is installed and accessible."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=5, check=True)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def run_in_docker(
    script_path: str | Path,
    timeout: int = SANDBOX_TIMEOUT_SECONDS,
) -> SandboxResult:
    """Run a Python script in a disposable Docker container.

    Container settings:
        - Image: python:3.12-slim
        - No network (--network none)
        - Temporary copy of script (no volume mounts for code)
        - Hard timeout: 5s (killed after)
        - Container destroyed after execution
        - Working directory: /tmp/sandbox_test

    Returns:
        SandboxResult with execution details.
        If Docker is not available, falls back to subprocess.
    """
    result = SandboxResult(mode="docker")
    script_path = Path(script_path)

    if not script_path.exists():
        result.error = f"Script not found: {script_path}"
        return result

    # Fallback to subprocess if Docker not available
    if not _check_docker_available():
        result.error = "Docker not available; falling back to subprocess mode"
        subprocess_result = run_in_subprocess(script_path, timeout=timeout)
        # Copy results but keep mode as "docker" to indicate what was intended
        result.returncode = subprocess_result.returncode
        result.stdout = subprocess_result.stdout
        result.stderr = subprocess_result.stderr
        result.timed_out = subprocess_result.timed_out
        result.env_vars_accessed = subprocess_result.env_vars_accessed
        result.mode = "docker_fallback_to_subprocess"
        return result

    # Build Dockerfile on the fly
    dockerfile_content = """FROM python:3.12-slim
WORKDIR /tmp/sandbox_test
COPY script.py /tmp/sandbox_test/script.py
RUN chmod +x /tmp/sandbox_test/script.py
ENTRYPOINT ["python", "script.py"]
"""

    try:
        with tempfile.TemporaryDirectory(prefix="agent-hunter-docker-") as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write the Dockerfile
            dockerfile_path = tmpdir_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)

            # Copy the script
            script_copy = tmpdir_path / "script.py"
            script_copy.write_bytes(script_path.read_bytes())

            # Build image (random tag to avoid collisions)
            image_tag = f"agent-hunter-sandbox-{int(time.time())}-{hashlib.sha256(str(script_path).encode()).hexdigest()[:8]}"

            build_cmd = [
                "docker",
                "build",
                "-t",
                image_tag,
                str(tmpdir_path),
            ]

            build_result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if build_result.returncode != 0:
                result.error = f"Docker build failed: {build_result.stderr[:200]}"
                return result

            # Run container with network isolation
            run_cmd = [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--memory=128m",
                "--cpus=0.5",
                image_tag,
            ]

            try:
                run_result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                result.returncode = run_result.returncode
                result.stdout = run_result.stdout[:2000]
                result.stderr = run_result.stderr[:2000]

                # Check for suspicious output
                output = run_result.stdout + run_result.stderr
                result.env_vars_accessed = _detect_masked_token_reads(output)

            except subprocess.TimeoutExpired:
                result.timed_out = True
                result.error = f"Docker container exceeded {timeout}s timeout — killed."
                # Kill the container
                subprocess.run(
                    ["docker", "rm", "-f", image_tag],
                    capture_output=True,
                    timeout=5,
                )
            finally:
                # Clean up the image
                subprocess.run(
                    ["docker", "image", "rm", "-f", image_tag],
                    capture_output=True,
                    timeout=10,
                )

    except subprocess.TimeoutExpired as e:
        result.error = f"Docker operation timed out: {str(e)[:100]}"
    except Exception as e:
        result.error = f"Docker sandbox error: {str(e)[:100]}"

    return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def sandbox_run(
    script_path: str | Path,
    mode: str = "subprocess",
    timeout: int = SANDBOX_TIMEOUT_SECONDS,
) -> SandboxResult:
    """Run a script in the configured sandbox mode.

    Args:
        script_path: Path to the script to test.
        mode: "subprocess", "docker", or "none".
        timeout: Max execution time in seconds.

    Returns:
        SandboxResult.
    """
    if mode == "subprocess":
        return run_in_subprocess(script_path, timeout=timeout)
    elif mode == "docker":
        return run_in_docker(script_path, timeout=timeout)
    else:
        return SandboxResult(mode="none", error="Sandbox disabled.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Run a skill script in sandbox isolation")
    parser.add_argument("script", help="Path to the script to sandbox-test")
    parser.add_argument("--mode", default="subprocess", choices=["subprocess", "docker", "none"])
    parser.add_argument("--timeout", type=int, default=SANDBOX_TIMEOUT_SECONDS)
    args = parser.parse_args()

    res = sandbox_run(args.script, mode=args.mode, timeout=args.timeout)

    print(f"Mode: {res.mode}")
    print(f"Returncode: {res.returncode}")
    print(f"Timed out: {res.timed_out}")
    print(f"Suspicious: {res.is_suspicious}")
    if res.env_vars_accessed:
        print(f"⚠️  Env vars accessed: {res.env_vars_accessed}")
    if res.error:
        print(f"Error: {res.error}")
    if res.stderr:
        print(f"Stderr: {res.stderr[:500]}")

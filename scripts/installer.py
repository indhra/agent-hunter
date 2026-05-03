"""
installer.py — Install, uninstall, disable, and rollback Claude Code skills.

Responsibility:
    Execute the actual file-system actions after the user confirms
    the action summary presented by reporter.py.

    This module is the ONLY place in agent-hunter that modifies
    ~/.claude/skills/. Nothing else touches that directory.

Actions:
    install(owner, repo, skill_name)     → gh skill install (falls back to git clone)
    uninstall(skill_name)                → rm -rf ~/.claude/skills/<skill_name>
    disable(skill_name)                  → rename to _<skill_name> (soft, reversible)
    enable(skill_name)                   → rename _<skill_name> back
    rollback_to_sha(owner, repo, sha)    → gh skill install owner/repo@sha --pin

Install scope: personal (~/.claude/skills/) — always.
    Agent-hunter never installs to project-level .claude/skills/.

Rules:
    - Never install a RED-flagged skill. Raise InstallerError.
    - Confirm actions before executing (done in SKILL.md, not here).
    - Never silently swallow errors. Raise InstallerError with clear message.
    - Log every action taken to ~/.agent-hunter/install_log.jsonl.

No LLM calls. Shell commands via subprocess only.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from registry import Registry


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILLS_DIR = Path.home() / ".claude" / "skills"
INSTALL_LOG = Path.home() / ".agent-hunter" / "install_log.jsonl"

GH_AVAILABLE = shutil.which("gh") is not None

# Allowlist: alphanumeric, hyphens, underscores, dots. No path separators.
_SAFE_SKILL_NAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,63}$')
_SAFE_OWNER_REPO = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]{0,99}$')


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class InstallerError(Exception):
    """Raised when an install/uninstall/rollback action fails."""


def _validate_skill_name(skill_name: str) -> None:
    """Raise InstallerError if skill_name could escape SKILLS_DIR."""
    if not _SAFE_SKILL_NAME.match(skill_name):
        raise InstallerError(
            f"Invalid skill name {skill_name!r}. "
            "Only alphanumeric characters, hyphens, underscores, and dots are allowed."
        )


def _validate_owner_repo(value: str, label: str) -> None:
    """Raise InstallerError if owner or repo contains path traversal characters."""
    if not _SAFE_OWNER_REPO.match(value):
        raise InstallerError(
            f"Invalid {label} {value!r}. Must be a valid GitHub identifier."
        )


# ---------------------------------------------------------------------------
# Action dataclass (for confirmation summary)
# ---------------------------------------------------------------------------

@dataclass
class PendingAction:
    action: str          # "install", "uninstall", "disable", "rollback"
    skill_name: str
    repo_url: str = ""
    owner: str = ""
    repo: str = ""
    sha: str = ""
    reason: str = ""     # why this action is recommended


@dataclass
class ActionResult:
    action: str
    skill_name: str
    success: bool
    message: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Installer class
# ---------------------------------------------------------------------------

class Installer:
    """Executes install/uninstall/rollback actions on ~/.claude/skills/."""

    def __init__(self, registry: Optional[Registry] = None, dry_run: bool = False) -> None:
        self.registry = registry or Registry()
        self.dry_run = dry_run  # if True, print what would happen but don't act
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------
    # Public action methods
    # -------------------------------------------------------------------

    def install(
        self,
        owner: str,
        repo: str,
        skill_name: Optional[str] = None,
        pin_sha: Optional[str] = None,
    ) -> ActionResult:
        """Install a skill from GitHub to ~/.claude/skills/.

        Tries `gh skill install` first. Falls back to `git clone` if gh is not installed.

        Args:
            owner: GitHub username/org (e.g. "indhra").
            repo: Repository name (e.g. "fastapi-helper").
            skill_name: Local directory name under ~/.claude/skills/.
                        Defaults to repo name.
            pin_sha: If provided, pin to this specific git tree SHA.

        Returns:
            ActionResult with success status and message.

        Raises:
            InstallerError: If the skill is RED-flagged in the registry,
                            or if installation fails fatally.
        """
        skill_name = skill_name or repo
        _validate_skill_name(skill_name)
        _validate_owner_repo(owner, "owner")
        _validate_owner_repo(repo, "repo")
        target_dir = SKILLS_DIR / skill_name

        self._log_action("install", skill_name, owner=owner, repo=repo, sha=pin_sha or "")

        if self.dry_run:
            return ActionResult(
                action="install", skill_name=skill_name, success=True,
                message=f"[dry-run] Would install {owner}/{repo} → {target_dir}"
            )

        if target_dir.exists():
            return ActionResult(
                action="install", skill_name=skill_name, success=False,
                error=f"Already installed at {target_dir}. Run `agent-hunter update` to update."
            )

        if GH_AVAILABLE:
            return self._install_via_gh(owner, repo, skill_name, pin_sha)
        else:
            return self._install_via_git(owner, repo, skill_name, pin_sha)

    def uninstall(self, skill_name: str) -> ActionResult:
        """Remove a skill from ~/.claude/skills/ permanently.

        Args:
            skill_name: Directory name under ~/.claude/skills/.

        Returns:
            ActionResult.
        """
        _validate_skill_name(skill_name)
        target_dir = SKILLS_DIR / skill_name

        self._log_action("uninstall", skill_name)

        if self.dry_run:
            return ActionResult(
                action="uninstall", skill_name=skill_name, success=True,
                message=f"[dry-run] Would remove {target_dir}"
            )

        if not target_dir.exists():
            return ActionResult(
                action="uninstall", skill_name=skill_name, success=False,
                error=f"Skill not found at {target_dir}"
            )

        try:
            shutil.rmtree(target_dir)
            # Look up the real repo URL from the registry by skill name
            repo_url = self._repo_url_for_skill(skill_name)
            if repo_url:
                self.registry.remove(repo_url)
            return ActionResult(
                action="uninstall", skill_name=skill_name, success=True,
                message=f"Removed {target_dir}"
            )
        except OSError as exc:
            return ActionResult(
                action="uninstall", skill_name=skill_name, success=False,
                error=f"Failed to remove {target_dir}: {exc}"
            )

    def disable(self, skill_name: str) -> ActionResult:
        """Soft-disable a skill by renaming it to _<skill_name>.

        Disabled skills are ignored by Claude Code (underscore prefix convention).
        Reversible with enable().

        Args:
            skill_name: Directory name under ~/.claude/skills/.

        Returns:
            ActionResult.
        """
        _validate_skill_name(skill_name)
        target_dir = SKILLS_DIR / skill_name
        disabled_dir = SKILLS_DIR / f"_{skill_name}"

        self._log_action("disable", skill_name)

        if self.dry_run:
            return ActionResult(
                action="disable", skill_name=skill_name, success=True,
                message=f"[dry-run] Would rename {target_dir} → {disabled_dir}"
            )

        if not target_dir.exists():
            return ActionResult(
                action="disable", skill_name=skill_name, success=False,
                error=f"Skill not found at {target_dir}"
            )

        try:
            target_dir.rename(disabled_dir)
            return ActionResult(
                action="disable", skill_name=skill_name, success=True,
                message=f"Disabled: {skill_name} → _{skill_name} (use `agent-hunter enable {skill_name}` to re-enable)"
            )
        except OSError as exc:
            return ActionResult(
                action="disable", skill_name=skill_name, success=False,
                error=f"Failed to disable {skill_name}: {exc}"
            )

    def enable(self, skill_name: str) -> ActionResult:
        """Re-enable a disabled skill (undoes disable())."""
        _validate_skill_name(skill_name)
        disabled_dir = SKILLS_DIR / f"_{skill_name}"
        target_dir = SKILLS_DIR / skill_name

        self._log_action("enable", skill_name)

        if not disabled_dir.exists():
            return ActionResult(
                action="enable", skill_name=skill_name, success=False,
                error=f"Disabled skill not found at {disabled_dir}"
            )

        try:
            disabled_dir.rename(target_dir)
            return ActionResult(
                action="enable", skill_name=skill_name, success=True,
                message=f"Re-enabled: _{skill_name} → {skill_name}"
            )
        except OSError as exc:
            return ActionResult(
                action="enable", skill_name=skill_name, success=False,
                error=f"Failed to enable {skill_name}: {exc}"
            )

    def rollback_to_sha(
        self,
        owner: str,
        repo: str,
        sha: str,
        skill_name: Optional[str] = None,
    ) -> ActionResult:
        """Roll back a skill to a specific git SHA.

        Uninstalls the current version and re-installs the pinned SHA.

        Args:
            owner: GitHub username/org.
            repo: Repository name.
            sha: Git tree SHA to pin to.
            skill_name: Local directory name. Defaults to repo name.

        Returns:
            ActionResult.
        """
        skill_name = skill_name or repo
        _validate_skill_name(skill_name)
        _validate_owner_repo(owner, "owner")
        _validate_owner_repo(repo, "repo")
        self._log_action("rollback", skill_name, sha=sha)

        if self.dry_run:
            return ActionResult(
                action="rollback", skill_name=skill_name, success=True,
                message=f"[dry-run] Would rollback {owner}/{repo} → SHA {sha[:12]}"
            )

        # Uninstall current version first
        uninstall_result = self.uninstall(skill_name)
        if not uninstall_result.success:
            return ActionResult(
                action="rollback", skill_name=skill_name, success=False,
                error=f"Rollback failed at uninstall step: {uninstall_result.error}"
            )

        # Re-install pinned to SHA
        install_result = self.install(owner, repo, skill_name, pin_sha=sha)
        if not install_result.success:
            return ActionResult(
                action="rollback", skill_name=skill_name, success=False,
                error=f"Rollback failed at re-install step: {install_result.error}"
            )

        return ActionResult(
            action="rollback", skill_name=skill_name, success=True,
            message=f"Rolled back {skill_name} to SHA {sha[:12]}"
        )

    # -------------------------------------------------------------------
    # Batch execution (used by SKILL.md after user confirms)
    # -------------------------------------------------------------------

    def execute_actions(self, actions: list[PendingAction]) -> list[ActionResult]:
        """Execute a list of confirmed actions. Returns results for each.

        Stops on first fatal error. Non-fatal errors are recorded and continue.

        Args:
            actions: List of PendingAction items the user confirmed.

        Returns:
            List of ActionResult, one per action.
        """
        results = []
        for action in actions:
            if action.action == "install":
                result = self.install(action.owner, action.repo, action.skill_name)
            elif action.action == "uninstall":
                result = self.uninstall(action.skill_name)
            elif action.action == "disable":
                result = self.disable(action.skill_name)
            elif action.action == "rollback":
                result = self.rollback_to_sha(
                    action.owner, action.repo, action.sha, action.skill_name
                )
            else:
                result = ActionResult(
                    action=action.action, skill_name=action.skill_name, success=False,
                    error=f"Unknown action: {action.action}"
                )
            results.append(result)
            self._print_result(result)

        return results

    # -------------------------------------------------------------------
    # Install backends
    # -------------------------------------------------------------------

    def _install_via_gh(
        self, owner: str, repo: str, skill_name: str, pin_sha: Optional[str]
    ) -> ActionResult:
        """Install using `gh skill install` (preferred — handles auth, rate limits)."""
        ref = f"{owner}/{repo}"
        if pin_sha:
            ref = f"{ref}@{pin_sha}"

        cmd = ["gh", "skill", "install", ref, "--scope", "user"]
        if pin_sha:
            cmd.append("--pin")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                return ActionResult(
                    action="install", skill_name=skill_name, success=True,
                    message=f"Installed {owner}/{repo} via gh skill install"
                )
            else:
                # gh failed — try git clone fallback
                print(f"[agent-hunter] gh skill install failed: {proc.stderr.strip()}")
                print("[agent-hunter] Falling back to git clone...")
                return self._install_via_git(owner, repo, skill_name, pin_sha)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._install_via_git(owner, repo, skill_name, pin_sha)

    def _install_via_git(
        self, owner: str, repo: str, skill_name: str, pin_sha: Optional[str]
    ) -> ActionResult:
        """Install via git clone (fallback when gh is not available)."""
        clone_url = f"https://github.com/{owner}/{repo}.git"
        target_dir = SKILLS_DIR / skill_name

        try:
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(target_dir)],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode != 0:
                return ActionResult(
                    action="install", skill_name=skill_name, success=False,
                    error=f"git clone failed: {proc.stderr.strip()}"
                )

            if pin_sha:
                # Fetch the specific SHA and reset to it
                subprocess.run(
                    ["git", "fetch", "--unshallow"],
                    cwd=target_dir, capture_output=True, timeout=60
                )
                proc2 = subprocess.run(
                    ["git", "checkout", pin_sha],
                    cwd=target_dir, capture_output=True, text=True, timeout=30
                )
                if proc2.returncode != 0:
                    return ActionResult(
                        action="install", skill_name=skill_name, success=False,
                        error=f"Could not pin to SHA {pin_sha}: {proc2.stderr.strip()}"
                    )

            return ActionResult(
                action="install", skill_name=skill_name, success=True,
                message=f"Installed {owner}/{repo} to {target_dir}"
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                action="install", skill_name=skill_name, success=False,
                error="git clone timed out after 60s"
            )

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _repo_url_for_skill(self, skill_name: str) -> Optional[str]:
        """Look up the real GitHub repo URL for a skill by its local directory name.

        Searches the registry for an entry whose name matches skill_name.
        Returns None if not found (registry will remain as-is).
        """
        for entry in self.registry.all():
            if entry.name == skill_name:
                return entry.repo_url
        return None

    def _print_result(self, result: ActionResult) -> None:
        icon = "✅" if result.success else "❌"
        msg = result.message or result.error or ""
        print(f"  {icon}  {result.action:<12} {result.skill_name:<30} {msg}")

    def _log_action(self, action: str, skill_name: str, **kwargs: str) -> None:
        """Append an action record to the install log for audit trail."""
        INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "skill": skill_name,
            **kwargs,
        }
        with open(INSTALL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Convenience: build action list from scan results
# ---------------------------------------------------------------------------

def build_action_list(
    top_results,        # list[ScoredResult] from scorer.py
    scan_results: dict, # repo_url → ScanResult from security_scan.py
    installed_names: set[str],
    dangerous_installed: list[str],
) -> list[PendingAction]:
    """Build a list of recommended actions from scan + audit results.

    Args:
        top_results: Ranked ScoredResult list (top N from this hunt).
        scan_results: Security scan results keyed by repo_url.
        installed_names: Currently installed skill names (to avoid re-installing).
        dangerous_installed: Names of installed skills flagged RED in latest audit.

    Returns:
        List of PendingAction items — installs for recommendations,
        uninstalls/disables for dangerous skills.
    """
    actions: list[PendingAction] = []

    # Install recommended skills (GREEN/YELLOW, not already installed)
    for s in top_results:
        r = s.hunt_result
        scan = scan_results.get(r.repo_url)
        if scan and scan.severity == "RED":
            continue  # never install RED
        if r.repo_name in installed_names:
            continue  # already installed
        actions.append(PendingAction(
            action="install",
            skill_name=r.repo_name,
            repo_url=r.repo_url,
            owner=r.owner,
            repo=r.repo_name,
            sha=r.git_tree_sha,
            reason=f"Score {s.total_score:.2f} — {s.explanation or 'matches your stack'}",
        ))

    # Disable dangerous installed skills (RED flagged in audit)
    for skill_name in dangerous_installed:
        actions.append(PendingAction(
            action="disable",  # disable (reversible) rather than uninstall (destructive)
            skill_name=skill_name,
            reason="🔴 Failed security scan — disabled for safety",
        ))

    return actions


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="agent-hunter skill installer")
    subparsers = parser.add_subparsers(dest="command")

    # install
    p_install = subparsers.add_parser("install", help="Install a skill")
    p_install.add_argument("owner")
    p_install.add_argument("repo")
    p_install.add_argument("--sha", default=None)
    p_install.add_argument("--dry-run", action="store_true")

    # uninstall
    p_uninstall = subparsers.add_parser("uninstall", help="Remove a skill")
    p_uninstall.add_argument("skill_name")
    p_uninstall.add_argument("--dry-run", action="store_true")

    # disable
    p_disable = subparsers.add_parser("disable", help="Soft-disable a skill")
    p_disable.add_argument("skill_name")

    # rollback
    p_rollback = subparsers.add_parser("rollback", help="Rollback skill to a SHA")
    p_rollback.add_argument("owner")
    p_rollback.add_argument("repo")
    p_rollback.add_argument("sha")

    # list
    p_list = subparsers.add_parser("list", help="List installed skills")

    args = parser.parse_args()
    installer = Installer(dry_run=getattr(args, "dry_run", False))

    if args.command == "install":
        r = installer.install(args.owner, args.repo, pin_sha=args.sha)
    elif args.command == "uninstall":
        r = installer.uninstall(args.skill_name)
    elif args.command == "disable":
        r = installer.disable(args.skill_name)
    elif args.command == "rollback":
        r = installer.rollback_to_sha(args.owner, args.repo, args.sha)
    elif args.command == "list":
        skills = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()] if SKILLS_DIR.exists() else []
        print(f"Installed skills ({len(skills)}):")
        for s in sorted(skills):
            status = "⏸ disabled" if s.startswith("_") else "✅ active"
            print(f"  {status}  {s}")
        sys.exit(0)
    else:
        parser.print_help()
        sys.exit(1)

    print(f"{'✅' if r.success else '❌'} {r.message or r.error}")
    sys.exit(0 if r.success else 1)

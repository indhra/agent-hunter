"""
test_installer.py — Tests for installer.py.

All tests use tmp_path and mock registries — no real ~/.claude/skills/ is touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts/ to import path (same pattern as other test files)
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from installer import (  # noqa: E402
    Installer,
    build_action_list,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_installer(tmp_path: Path, dry_run: bool = False) -> tuple[Installer, MagicMock]:
    """Return an Installer using tmp_path as SKILLS_DIR, plus a mock registry."""
    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    installer = Installer(registry=mock_registry, dry_run=dry_run)
    installer.__class__  # ensure class is accessible

    # Patch SKILLS_DIR so nothing touches ~/.claude/skills/
    with patch("installer.SKILLS_DIR", tmp_path):
        installer._skills_dir = tmp_path
    # We'll patch at the module level in individual tests
    return installer, mock_registry


# ---------------------------------------------------------------------------
# dry_run=True — no filesystem changes
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_install_dry_run_returns_success_without_touching_fs(self, tmp_path):
        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry, dry_run=True)

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.install("owner", "myrepo")

        assert result.success is True
        assert "[dry-run]" in result.message
        assert not (tmp_path / "myrepo").exists()

    def test_uninstall_dry_run_returns_success_without_removing(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry, dry_run=True)

        # Create the skill dir so a real uninstall would have found it
        (tmp_path / "myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.uninstall("myrepo")

        assert result.success is True
        assert "[dry-run]" in result.message
        assert (tmp_path / "myrepo").exists()  # not removed in dry_run

    def test_disable_dry_run_returns_success(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry, dry_run=True)
        (tmp_path / "myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.disable("myrepo")

        assert result.success is True
        assert "[dry-run]" in result.message
        assert (tmp_path / "myrepo").exists()  # not renamed


# ---------------------------------------------------------------------------
# install()
# ---------------------------------------------------------------------------


class TestInstall:
    def test_install_already_installed_returns_failure(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "myrepo").mkdir()  # simulate already installed

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.install("owner", "myrepo")

        assert result.success is False
        assert "Already installed" in (result.error or "")

    def test_install_via_git_success(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        def fake_clone(*args, **kwargs):
            # Simulate git clone creating the target directory
            target = tmp_path / "myrepo"
            target.mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0, stderr="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.GH_AVAILABLE", False),
            patch("installer.subprocess.run", side_effect=fake_clone),
        ):
            result = installer.install("owner", "myrepo")

        assert result.success is True
        assert "myrepo" in result.message

    def test_install_via_git_failure_returns_error(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.GH_AVAILABLE", False),
            patch(
                "installer.subprocess.run", return_value=MagicMock(returncode=1, stderr="not found")
            ),
        ):
            result = installer.install("owner", "missingrepo")

        assert result.success is False
        assert result.error is not None


# ---------------------------------------------------------------------------
# uninstall()
# ---------------------------------------------------------------------------


class TestUninstall:
    def test_uninstall_removes_directory(self, tmp_path):
        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry)
        skill_dir = tmp_path / "myrepo"
        skill_dir.mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.uninstall("myrepo")

        assert result.success is True
        assert not skill_dir.exists()

    def test_uninstall_not_found_returns_failure(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.uninstall("nonexistent")

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    def test_uninstall_calls_registry_remove_with_real_url(self, tmp_path):
        """D5 regression: registry.remove() must be called with the actual repo URL."""
        from registry import RegistryEntry

        entry = RegistryEntry(
            name="myrepo",
            repo_url="https://github.com/owner/myrepo",
            install_path="~/.claude/skills/myrepo",
            trust_tier="raw",
        )
        mock_registry = MagicMock()
        mock_registry.all.return_value = [entry]

        installer = Installer(registry=mock_registry)
        (tmp_path / "myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.uninstall("myrepo")

        assert result.success is True
        # Must be called with the real URL, NOT "https://github.com/myrepo"
        mock_registry.remove.assert_called_once_with("https://github.com/owner/myrepo")

    def test_uninstall_unknown_skill_skips_registry_remove(self, tmp_path):
        """If skill not in registry (e.g. manually installed), remove() should not be called."""
        mock_registry = MagicMock()
        mock_registry.all.return_value = []  # no matching entry

        installer = Installer(registry=mock_registry)
        (tmp_path / "orphan-skill").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.uninstall("orphan-skill")

        assert result.success is True
        mock_registry.remove.assert_not_called()


# ---------------------------------------------------------------------------
# disable() / enable()
# ---------------------------------------------------------------------------


class TestDisableEnable:
    def test_disable_renames_to_underscore(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.disable("myrepo")

        assert result.success is True
        assert not (tmp_path / "myrepo").exists()
        assert (tmp_path / "_myrepo").exists()

    def test_disable_not_found_returns_failure(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.disable("nonexistent")

        assert result.success is False

    def test_enable_renames_back(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "_myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.enable("myrepo")

        assert result.success is True
        assert (tmp_path / "myrepo").exists()
        assert not (tmp_path / "_myrepo").exists()

    def test_enable_not_disabled_returns_failure(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.enable("nonexistent")

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    def test_disable_then_enable_roundtrip(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "myrepo").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            r1 = installer.disable("myrepo")
            r2 = installer.enable("myrepo")

        assert r1.success is True
        assert r2.success is True
        assert (tmp_path / "myrepo").exists()
        assert not (tmp_path / "_myrepo").exists()


# ---------------------------------------------------------------------------
# build_action_list()
# ---------------------------------------------------------------------------


class TestBuildActionList:
    def _make_scored_result(self, repo_name: str, repo_url: str, severity: str = "GREEN"):
        from security_scan import ScanResult
        from scorer import ScoredResult
        from hunter import HuntResult

        hunt = HuntResult(
            name=repo_name,
            repo_url=repo_url,
            raw_url=repo_url,
            owner="owner",
            repo_name=repo_name,
            description="A test skill",
            stars=100,
            result_type="skill",
        )
        scored = ScoredResult(hunt_result=hunt, skill_metadata=None)
        scored.total_score = 0.75
        scan = ScanResult(severity=severity)
        return scored, scan

    def test_excludes_red_results(self):
        s, scan = self._make_scored_result("badrepo", "https://github.com/o/badrepo", "RED")
        scan_results = {s.hunt_result.repo_url: scan}

        actions = build_action_list([s], scan_results, set(), [])

        assert len(actions) == 0

    def test_excludes_already_installed(self):
        s, scan = self._make_scored_result("myrepo", "https://github.com/o/myrepo")
        scan_results = {s.hunt_result.repo_url: scan}

        actions = build_action_list([s], scan_results, {"myrepo"}, [])

        assert len(actions) == 0

    def test_includes_green_not_installed(self):
        s, scan = self._make_scored_result("newrepo", "https://github.com/o/newrepo")
        scan_results = {s.hunt_result.repo_url: scan}

        actions = build_action_list([s], scan_results, set(), [])

        assert len(actions) == 1
        assert actions[0].action == "install"
        assert actions[0].skill_name == "newrepo"

    def test_disables_dangerous_installed(self):
        actions = build_action_list([], {}, set(), ["evil-skill"])

        assert len(actions) == 1
        assert actions[0].action == "disable"
        assert actions[0].skill_name == "evil-skill"

    def test_mixed_results(self):
        green, green_scan = self._make_scored_result("good", "https://github.com/o/good", "GREEN")
        red, red_scan = self._make_scored_result("bad", "https://github.com/o/bad", "RED")
        scan_results = {
            green.hunt_result.repo_url: green_scan,
            red.hunt_result.repo_url: red_scan,
        }

        actions = build_action_list([green, red], scan_results, set(), ["dangerous-old"])

        install_actions = [a for a in actions if a.action == "install"]
        disable_actions = [a for a in actions if a.action == "disable"]
        assert len(install_actions) == 1
        assert install_actions[0].skill_name == "good"
        assert len(disable_actions) == 1
        assert disable_actions[0].skill_name == "dangerous-old"

    # ---- Issue #6 defensive guard ------------------------------------------

    def _make_malformed_result(self):
        """A ScoredResult whose HuntResult has empty owner/repo_name.
        Simulates the upstream bug where npm/curated didn't populate fields.
        """
        from security_scan import ScanResult
        from scorer import ScoredResult
        from hunter import HuntResult

        hunt = HuntResult(
            name="@bad/pkg",
            repo_url="git+https://example.invalid/foo",
            raw_url="",
            owner="",  # ← the bug condition
            repo_name="",  # ← the bug condition
            description="malformed",
            stars=0,
            result_type="mcp_npm",
        )
        scored = ScoredResult(hunt_result=hunt, skill_metadata=None)
        scored.total_score = 0.30
        return scored, ScanResult(severity="GREEN")

    def test_skips_actions_with_empty_owner(self, capsys):
        """Issue #6: never emit an install action with empty owner."""
        s, scan = self._make_malformed_result()
        scan_results = {s.hunt_result.repo_url: scan}

        actions = build_action_list([s], scan_results, set(), [])

        # No install action should be emitted for the malformed candidate.
        install_actions = [a for a in actions if a.action == "install"]
        assert install_actions == []

        # And a count of skipped candidates is surfaced to the user.
        out = capsys.readouterr().out
        assert "Skipped 1" in out

    def test_skips_actions_with_empty_repo_name(self, capsys):
        """Owner present but repo_name empty is also rejected."""
        from security_scan import ScanResult
        from scorer import ScoredResult
        from hunter import HuntResult

        hunt = HuntResult(
            name="x",
            repo_url="https://github.com/owner/",
            owner="owner",
            repo_name="",  # ← empty
            description="malformed",
            stars=0,
        )
        scored = ScoredResult(hunt_result=hunt, skill_metadata=None)
        scored.total_score = 0.30
        actions = build_action_list(
            [scored], {hunt.repo_url: ScanResult(severity="GREEN")}, set(), []
        )

        assert [a for a in actions if a.action == "install"] == []
        assert "Skipped 1" in capsys.readouterr().out

    def test_mixed_malformed_and_valid(self, capsys):
        """Valid candidates still flow through; only malformed are dropped."""
        valid, valid_scan = self._make_scored_result("good", "https://github.com/o/good", "GREEN")
        bad, bad_scan = self._make_malformed_result()
        scan_results = {
            valid.hunt_result.repo_url: valid_scan,
            bad.hunt_result.repo_url: bad_scan,
        }

        actions = build_action_list([valid, bad], scan_results, set(), [])

        install_actions = [a for a in actions if a.action == "install"]
        assert len(install_actions) == 1
        assert install_actions[0].skill_name == "good"
        assert install_actions[0].owner == "owner"
        assert "Skipped 1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# rollback_to_sha()
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_dry_run(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry, dry_run=True)

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.rollback_to_sha("owner", "myrepo", "abc123def")

        assert result.success is True
        assert "[dry-run]" in result.message

    def test_rollback_uninstall_failure(self, tmp_path):
        """If uninstall fails, rollback should fail immediately."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            # No skill dir exists, so uninstall will fail
            result = installer.rollback_to_sha("owner", "myrepo", "abc123def")

        assert result.success is False
        assert "uninstall" in (result.error or "").lower()

    def test_rollback_orchestrates_uninstall_then_install(self, tmp_path):
        """Rollback should uninstall current version, then install pinned SHA."""
        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry)

        # Pre-create the skill dir
        skill_dir = tmp_path / "myrepo"
        skill_dir.mkdir()

        def fake_subprocess(*args, **kwargs):
            # Simulate git clone + checkout
            target = kwargs.get("cwd") or (tmp_path / "myrepo")
            Path(target).mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0, stderr="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.GH_AVAILABLE", False),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
        ):
            result = installer.rollback_to_sha("owner", "myrepo", "abc123def", "myrepo")

        # Should succeed
        assert result.success is True
        assert "Rolled back" in result.message


# ---------------------------------------------------------------------------
# _install_via_gh()
# ---------------------------------------------------------------------------


class TestInstallViaGh:
    def test_install_via_gh_success(self, tmp_path):
        """gh skill install succeeds."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        skill_dir = tmp_path / "myrepo"
        skill_dir.mkdir()  # simulate that install created it

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", return_value=MagicMock(returncode=0, stderr="")),
        ):
            result = installer._install_via_gh("owner", "myrepo", "myrepo", None)

        assert result.success is True
        assert "gh skill install" in result.message

    def test_install_via_gh_fallback_on_failure(self, tmp_path):
        """gh skill install fails → fallback to git clone."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        call_count = [0]

        def fake_subprocess(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # gh skill install fails
                return MagicMock(returncode=1, stderr="gh not configured")
            else:  # git clone succeeds
                skill_dir = tmp_path / "myrepo"
                skill_dir.mkdir(parents=True, exist_ok=True)
                return MagicMock(returncode=0, stderr="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
        ):
            result = installer._install_via_gh("owner", "myrepo", "myrepo", None)

        # Should succeed via fallback
        assert result.success is True

    def test_install_via_gh_with_pin_sha(self, tmp_path):
        """gh skill install with --pin flag."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        skill_dir = tmp_path / "myrepo"
        skill_dir.mkdir()

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch(
                "installer.subprocess.run", return_value=MagicMock(returncode=0, stderr="")
            ) as mock_run,
        ):
            result = installer._install_via_gh("owner", "myrepo", "myrepo", "abc123")

        assert result.success is True
        # Should have called subprocess with --pin flag
        calls = mock_run.call_args_list
        assert len(calls) > 0
        call_args = str(calls[0])
        assert "pin" in call_args.lower() or "abc123" in call_args


# ---------------------------------------------------------------------------
# _install_via_git() with pin_sha
# ---------------------------------------------------------------------------


class TestInstallViaGitWithPin:
    def test_install_via_git_with_pin_sha_success(self, tmp_path):
        """git clone with checkout to specific SHA."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        call_count = [0]

        def fake_subprocess(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # git clone
                skill_dir = tmp_path / "myrepo"
                skill_dir.mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0, stderr="", stdout="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
        ):
            result = installer._install_via_git("owner", "myrepo", "myrepo", "abc123def")

        assert result.success is True
        # Should have called git clone, fetch --unshallow, and checkout
        assert call_count[0] >= 3

    def test_install_via_git_pin_sha_checkout_fails(self, tmp_path):
        """git checkout to SHA fails."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        call_count = [0]

        def fake_subprocess(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # git clone
                skill_dir = tmp_path / "myrepo"
                skill_dir.mkdir(parents=True, exist_ok=True)
                return MagicMock(returncode=0, stderr="")
            elif call_count[0] == 2:  # fetch --unshallow
                return MagicMock(returncode=0, stderr="")
            else:  # git checkout — FAILS
                return MagicMock(returncode=1, stderr="SHA not found")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
        ):
            result = installer._install_via_git("owner", "myrepo", "myrepo", "badsha")

        assert result.success is False
        assert "SHA not found" in (result.error or "")

    def test_install_via_git_clone_timeout(self, tmp_path):
        """git clone times out."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 60)),
        ):
            result = installer._install_via_git("owner", "myrepo", "myrepo", None)

        assert result.success is False
        assert "timed out" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# execute_actions()
# ---------------------------------------------------------------------------


class TestExecuteActions:
    def test_execute_actions_empty_list(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            results = installer.execute_actions([])

        assert len(results) == 0

    def test_execute_actions_install_and_disable(self, tmp_path):
        """Execute a mix of install and disable actions."""
        from installer import PendingAction

        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry)

        # Create a disabled skill
        (tmp_path / "evil-skill").mkdir()

        actions = [
            PendingAction(action="disable", skill_name="evil-skill"),
        ]

        def fake_subprocess(*args, **kwargs):
            # For installs, simulate dir creation
            return MagicMock(returncode=0, stderr="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
            patch("installer.GH_AVAILABLE", False),
        ):
            results = installer.execute_actions(actions)

        assert len(results) == 1
        assert results[0].action == "disable"
        assert results[0].success is True

    def test_execute_actions_continues_on_non_fatal_error(self, tmp_path):
        """execute_actions should continue after a failure."""
        from installer import PendingAction

        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry)

        actions = [
            PendingAction(action="disable", skill_name="nonexistent-skill"),  # will fail
            PendingAction(action="disable", skill_name="also-missing"),  # will also fail
        ]

        with patch("installer.SKILLS_DIR", tmp_path):
            results = installer.execute_actions(actions)

        # Should have 2 results (both failed, but both attempted)
        assert len(results) == 2
        assert all(not r.success for r in results)

    def test_execute_actions_unknown_action_type(self, tmp_path):
        """execute_actions handles unknown action types gracefully."""
        from installer import PendingAction

        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        actions = [
            PendingAction(action="unknown-action", skill_name="skill"),
        ]

        with patch("installer.SKILLS_DIR", tmp_path):
            results = installer.execute_actions(actions)

        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown action" in (results[0].error or "")


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------


class TestValidation:
    def test_validate_skill_name_valid(self):
        from installer import _validate_skill_name

        # Should not raise
        _validate_skill_name("my-skill")
        _validate_skill_name("MySkill")
        _validate_skill_name("skill.v1")
        _validate_skill_name("skill_name")

    def test_validate_skill_name_invalid_path_traversal(self):
        from installer import _validate_skill_name, InstallerError

        # Path traversal attempts should fail
        with pytest.raises(InstallerError):
            _validate_skill_name("../../../etc/passwd")

    def test_validate_skill_name_invalid_special_chars(self):
        from installer import _validate_skill_name, InstallerError

        with pytest.raises(InstallerError):
            _validate_skill_name("skill$name")
        with pytest.raises(InstallerError):
            _validate_skill_name("skill@name")
        with pytest.raises(InstallerError):
            _validate_skill_name("skill/name")

    def test_validate_owner_repo_valid(self):
        from installer import _validate_owner_repo

        # Should not raise
        _validate_owner_repo("indhra", "owner")
        _validate_owner_repo("my-org", "owner")
        _validate_owner_repo("fastapi-helper", "repo")

    def test_validate_owner_repo_invalid(self):
        from installer import _validate_owner_repo, InstallerError

        with pytest.raises(InstallerError):
            _validate_owner_repo("../evil", "owner")
        with pytest.raises(InstallerError):
            _validate_owner_repo("bad@name", "repo")

    def test_validate_owner_repo_too_long(self):
        from installer import _validate_owner_repo, InstallerError

        # Max length is 100 characters
        long_name = "a" * 101
        with pytest.raises(InstallerError):
            _validate_owner_repo(long_name, "owner")


# ---------------------------------------------------------------------------
# _repo_url_for_skill()
# ---------------------------------------------------------------------------


class TestRepoUrlForSkill:
    def test_repo_url_found(self):
        from registry import RegistryEntry

        entry = RegistryEntry(
            name="myskill",
            repo_url="https://github.com/owner/myskill",
            install_path="~/.claude/skills/myskill",
            trust_tier="raw",
        )
        mock_registry = MagicMock()
        mock_registry.all.return_value = [entry]

        installer = Installer(registry=mock_registry)
        url = installer._repo_url_for_skill("myskill")

        assert url == "https://github.com/owner/myskill"

    def test_repo_url_not_found(self):
        mock_registry = MagicMock()
        mock_registry.all.return_value = []

        installer = Installer(registry=mock_registry)
        url = installer._repo_url_for_skill("unknown")

        assert url is None


# ---------------------------------------------------------------------------
# _log_action()
# ---------------------------------------------------------------------------


class TestLogAction:
    def test_log_action_creates_entry(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.INSTALL_LOG", tmp_path / "install_log.jsonl"):
            installer._log_action("install", "test-skill", owner="owner", repo="repo")

        # Check that the log file was created
        log_file = tmp_path / "install_log.jsonl"
        assert log_file.exists()

        # Parse the logged JSON
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = __import__("json").loads(lines[0])
        assert entry["action"] == "install"
        assert entry["skill"] == "test-skill"
        assert entry["owner"] == "owner"

    def test_log_action_appends(self, tmp_path):
        """Multiple log_action calls should append."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.INSTALL_LOG", tmp_path / "install_log.jsonl"):
            installer._log_action("install", "skill1")
            installer._log_action("disable", "skill2")

        log_file = tmp_path / "install_log.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Error edge cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_install_invalid_owner(self, tmp_path):
        from installer import InstallerError

        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            with pytest.raises(InstallerError):
                installer.install("../evil", "repo")

    def test_install_invalid_repo(self, tmp_path):
        from installer import InstallerError

        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path):
            with pytest.raises(InstallerError):
                installer.install("owner", "repo/../../evil")

    def test_disable_then_disable_again_fails(self, tmp_path):
        """Disabling an already-disabled skill should fail."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "_myskill").mkdir()

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.disable("myskill")

        assert result.success is False
        assert "not found" in (result.error or "").lower()

    def test_enable_when_not_disabled_fails(self, tmp_path):
        """Enabling a normal (not disabled) skill should fail."""
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)
        (tmp_path / "myskill").mkdir()  # normal, not disabled

        with patch("installer.SKILLS_DIR", tmp_path):
            result = installer.enable("myskill")

        assert result.success is False


# ---------------------------------------------------------------------------
# Integration: full workflow
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_install_disable_enable_workflow(self, tmp_path):
        """Full workflow: install → disable → enable."""
        mock_registry = MagicMock()
        mock_registry.all.return_value = []
        installer = Installer(registry=mock_registry)

        def fake_subprocess(*args, **kwargs):
            target = tmp_path / "my-skill"
            target.mkdir(parents=True, exist_ok=True)
            return MagicMock(returncode=0, stderr="")

        with (
            patch("installer.SKILLS_DIR", tmp_path),
            patch("installer.GH_AVAILABLE", False),
            patch("installer.subprocess.run", side_effect=fake_subprocess),
        ):
            # Install
            r1 = installer.install("owner", "my-skill")
            assert r1.success is True
            assert (tmp_path / "my-skill").exists()

            # Disable
            r2 = installer.disable("my-skill")
            assert r2.success is True
            assert (tmp_path / "_my-skill").exists()
            assert not (tmp_path / "my-skill").exists()

            # Enable
            r3 = installer.enable("my-skill")
            assert r3.success is True
            assert (tmp_path / "my-skill").exists()
            assert not (tmp_path / "_my-skill").exists()

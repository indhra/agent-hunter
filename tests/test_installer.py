"""
test_installer.py — Tests for installer.py.

All tests use tmp_path and mock registries — no real ~/.claude/skills/ is touched.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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

        with patch("installer.SKILLS_DIR", tmp_path), \
             patch("installer.GH_AVAILABLE", False), \
             patch("installer.subprocess.run", side_effect=fake_clone):
            result = installer.install("owner", "myrepo")

        assert result.success is True
        assert "myrepo" in result.message

    def test_install_via_git_failure_returns_error(self, tmp_path):
        mock_registry = MagicMock()
        installer = Installer(registry=mock_registry)

        with patch("installer.SKILLS_DIR", tmp_path), \
             patch("installer.GH_AVAILABLE", False), \
             patch("installer.subprocess.run",
                   return_value=MagicMock(returncode=1, stderr="not found")):
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

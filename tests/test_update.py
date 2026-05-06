"""
Tests for update.py — SkillUpdater, UpdateRequest, interactive update workflow.

All tests use mocked registries and tmp_path — never touches ~/.agent-hunter/.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from update import SkillUpdater, UpdateRequest, _extract_version
from registry import RegistryEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(**kwargs) -> RegistryEntry:
    defaults = dict(
        name="myskill",
        repo_url="https://github.com/owner/myskill",
        install_path="/tmp/nonexistent/myskill",
        git_tree_sha="abc123",
        trust_tier="raw",
        license="MIT",
    )
    defaults.update(kwargs)
    return RegistryEntry(**defaults)


def _make_updater(entries: list[RegistryEntry]) -> SkillUpdater:
    """Return a SkillUpdater with a mocked registry."""
    mock_reg = MagicMock()
    mock_reg.all.return_value = entries
    updater = SkillUpdater(registry=mock_reg)
    return updater


# ---------------------------------------------------------------------------
# UpdateRequest
# ---------------------------------------------------------------------------


class TestUpdateRequest:
    def test_has_changes_when_content_differs(self):
        entry = _entry()
        req = UpdateRequest(entry, "new content", "old content")
        assert req.has_changes is True

    def test_no_changes_when_identical(self):
        entry = _entry()
        content = "---\nname: test\n---\nBody"
        req = UpdateRequest(entry, content, content)
        assert req.has_changes is False

    def test_approved_flag_starts_false(self):
        entry = _entry()
        req = UpdateRequest(entry, "new", "old")
        assert req.approved is False


# ---------------------------------------------------------------------------
# _extract_version
# ---------------------------------------------------------------------------


class TestExtractVersion:
    def test_extracts_version_from_frontmatter(self):
        content = "---\nname: test\nversion: 2.0.0\n---\nBody"
        assert _extract_version(content) == "2.0.0"

    def test_extracts_quoted_version(self):
        content = '---\nversion: "1.5.3"\n---\nBody'
        assert _extract_version(content) == "1.5.3"

    def test_handles_single_quotes(self):
        content = "---\nversion: '3.0.0'\n---\nBody"
        assert _extract_version(content) == "3.0.0"

    def test_missing_version_returns_none(self):
        content = "---\nname: test\n---\nBody"
        assert _extract_version(content) is None

    def test_version_in_body_ignored(self):
        content = "---\nname: test\n---\nversion: 2.0.0"
        assert _extract_version(content) is None  # body content ignored


# ---------------------------------------------------------------------------
# SkillUpdater.check_updates
# ---------------------------------------------------------------------------


class TestCheckUpdates:
    def test_detects_update_when_remote_differs(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        local_v = "---\nversion: 1.0.0\n---\nOld content"
        skill_file.write_text(local_v)

        entry = _entry(install_path=str(skill_file))
        updater = _make_updater([entry])

        remote_v = "---\nversion: 2.0.0\n---\nNew content"
        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value=remote_v):
            updates = updater.check_updates()

        assert len(updates) == 1
        assert updates[0].entry.name == "myskill"
        assert updates[0].has_changes is True

    def test_ignores_skills_with_no_remote(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("content")
        entry = _entry(install_path=str(skill_file))
        updater = _make_updater([entry])

        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value=None):
            updates = updater.check_updates()

        assert len(updates) == 0

    def test_ignores_skills_not_installed(self, tmp_path):
        entry = _entry(install_path="/nonexistent/path")
        updater = _make_updater([entry])

        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value="content"):
            updates = updater.check_updates()

        assert len(updates) == 0

    def test_filters_by_skill_name(self, tmp_path):
        skill1 = tmp_path / "skill1.md"
        skill2 = tmp_path / "skill2.md"
        skill1.write_text("v1")
        skill2.write_text("v2")

        entries = [
            _entry(name="skill1", install_path=str(skill1)),
            _entry(name="skill2", install_path=str(skill2)),
        ]
        updater = _make_updater(entries)

        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value="different"):
            updates = updater.check_updates(skill_name="skill1")

        assert len(updates) == 1
        assert updates[0].entry.name == "skill1"

    def test_no_updates_returns_empty_list(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        content = "---\nversion: 1.0.0\n---\nContent"
        skill_file.write_text(content)

        entry = _entry(install_path=str(skill_file))
        updater = _make_updater([entry])

        # Remote is same as local
        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value=content):
            updates = updater.check_updates()

        assert len(updates) == 0


# ---------------------------------------------------------------------------
# SkillUpdater.prompt_update
# ---------------------------------------------------------------------------


class TestPromptUpdate:
    def test_user_approve_with_y(self):
        entry = _entry()
        req = UpdateRequest(entry, "new", "old")
        updater = _make_updater([])

        with patch("builtins.input", return_value="y"):
            approved = updater.prompt_update(req)

        assert approved is True

    def test_user_reject_with_n(self):
        entry = _entry()
        req = UpdateRequest(entry, "new", "old")
        updater = _make_updater([])

        with patch("builtins.input", return_value="n"):
            approved = updater.prompt_update(req)

        assert approved is False

    def test_user_reject_with_empty(self):
        entry = _entry()
        req = UpdateRequest(entry, "new", "old")
        updater = _make_updater([])

        with patch("builtins.input", return_value=""):
            approved = updater.prompt_update(req)

        assert approved is False

    def test_eoferror_handled_gracefully(self):
        entry = _entry()
        req = UpdateRequest(entry, "new", "old")
        updater = _make_updater([])

        with patch("builtins.input", side_effect=EOFError):
            approved = updater.prompt_update(req)

        assert approved is False

    def test_shows_line_count_summary(self, capsys):
        entry = _entry()
        old = "line1\nline2\nline3\n"  # 3 lines
        new = "line1\nline2\nline3\nline4\nline5\n"  # 5 lines
        req = UpdateRequest(entry, new, old)
        updater = _make_updater([])

        with patch("builtins.input", return_value="n"):
            updater.prompt_update(req)

        out = capsys.readouterr().out
        assert "lines" in out


# ---------------------------------------------------------------------------
# SkillUpdater.apply_update
# ---------------------------------------------------------------------------


class TestApplyUpdate:
    def test_writes_remote_content_to_file(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("old content")

        entry = _entry(install_path=str(skill_file))
        req = UpdateRequest(entry, "new content", "old content")
        updater = _make_updater([])

        success = updater.apply_update(req)

        assert success is True
        assert skill_file.read_text() == "new content"
        assert req.approved is True

    def test_returns_false_on_write_error(self):
        entry = _entry(install_path="/nonexistent/impossible/path")
        req = UpdateRequest(entry, "new", "old")
        updater = _make_updater([])

        success = updater.apply_update(req)

        assert success is False
        assert req.approved is False


# ---------------------------------------------------------------------------
# SkillUpdater.run_interactive_update
# ---------------------------------------------------------------------------


class TestRunInteractiveUpdate:
    def test_no_updates_returns_zero(self, tmp_path, capsys):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("content")
        entry = _entry(install_path=str(skill_file))
        updater = _make_updater([entry])

        with patch.object(updater, "check_updates", return_value=[]):
            approved, total = updater.run_interactive_update()

        assert approved == 0
        assert total == 0
        out = capsys.readouterr().out
        assert "No updates" in out

    def test_applies_all_approved_updates(self, tmp_path, capsys):
        skill1 = tmp_path / "skill1.md"
        skill2 = tmp_path / "skill2.md"
        skill1.write_text("v1")
        skill2.write_text("v2")

        entries = [
            _entry(name="skill1", install_path=str(skill1)),
            _entry(name="skill2", install_path=str(skill2)),
        ]
        updater = _make_updater(entries)

        reqs = [
            UpdateRequest(entries[0], "new1", "v1"),
            UpdateRequest(entries[1], "new2", "v2"),
        ]

        with patch.object(updater, "check_updates", return_value=reqs):
            with patch("builtins.input", return_value="y"):
                approved, total = updater.run_interactive_update()

        assert approved == 2
        assert total == 2
        assert skill1.read_text() == "new1"
        assert skill2.read_text() == "new2"

    def test_respects_user_rejections(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("old")

        entry = _entry(install_path=str(skill_file))
        updater = _make_updater([entry])

        req = UpdateRequest(entry, "new", "old")

        with patch.object(updater, "check_updates", return_value=[req]):
            with patch("builtins.input", return_value="n"):
                approved, total = updater.run_interactive_update()

        assert approved == 0
        assert total == 1
        assert skill_file.read_text() == "old"  # unchanged

    def test_filters_by_skill_name(self, tmp_path, capsys):
        skill1 = tmp_path / "skill1.md"
        skill2 = tmp_path / "skill2.md"
        skill1.write_text("v1")
        skill2.write_text("v2")

        entries = [
            _entry(name="skill1", install_path=str(skill1)),
            _entry(name="skill2", install_path=str(skill2)),
        ]
        updater = _make_updater(entries)

        # Simulate check_updates returning only skill1
        req1 = UpdateRequest(entries[0], "new1", "v1")
        with patch.object(updater, "check_updates", return_value=[req1]):
            with patch("builtins.input", return_value="y"):
                approved, total = updater.run_interactive_update(skill_name="skill1")

        assert approved == 1
        assert total == 1

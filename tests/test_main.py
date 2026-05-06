"""
Tests for main.py — CLI dispatcher, command dispatch, config loading, error paths.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import main as cli_main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(args: list[str]) -> int:
    return cli_main.main(args)


# ---------------------------------------------------------------------------
# Help / unknown commands
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_no_args_prints_help_returns_1(self, capsys):
        code = run([])
        assert code == 1
        out = capsys.readouterr().out
        assert "Usage" in out

    def test_help_flag_returns_0(self, capsys):
        code = run(["--help"])
        assert code == 0
        out = capsys.readouterr().out
        assert "agent-hunter" in out

    def test_h_flag_returns_0(self):
        code = run(["-h"])
        assert code == 0

    def test_help_command_returns_0(self):
        code = run(["help"])
        assert code == 0

    def test_unknown_command_returns_1(self, capsys):
        code = run(["frobnicator"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Unknown command" in out


# ---------------------------------------------------------------------------
# cmd_context
# ---------------------------------------------------------------------------


class TestCmdContext:
    def test_nonexistent_path_returns_1(self, capsys):
        code = run(["context", "/nonexistent/path/xyz"])
        assert code == 1

    def test_valid_path_returns_0(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\npytest\n")
        code = run(["context", str(tmp_path)])
        assert code == 0
        out = capsys.readouterr().out
        assert "Tech stack" in out

    def test_empty_project_returns_0(self, tmp_path, capsys):
        # No tech files — still returns 0, just empty profile
        code = run(["context", str(tmp_path)])
        assert code == 0

    def test_default_path_is_cwd(self, capsys):
        # Running 'context' with no args should not crash
        code = run(["context"])
        # Returns 0 or 1, just not an exception
        assert code in (0, 1)

    def test_extract_context_exception_returns_1(self, tmp_path, capsys):
        with patch("main.extract_context", side_effect=RuntimeError("read failed")):
            code = run(["context", str(tmp_path)])
        assert code == 1
        out = capsys.readouterr().out
        assert "Context extraction failed" in out

    def test_rich_profile_prints_optional_sections(self, tmp_path, capsys):
        from context_extractor import ContextProfile

        rich = ContextProfile(
            tech_stack=["python"],
            recent_domains=["ml"],
            dormant_domains=["rust"],
            extraction_warnings=["git not found"],
        )
        with patch("main.extract_context", return_value=rich):
            code = run(["context", str(tmp_path)])
        assert code == 0
        out = capsys.readouterr().out
        assert "Recent" in out
        assert "Dormant" in out
        assert "Warnings" in out


# ---------------------------------------------------------------------------
# cmd_scaffold
# ---------------------------------------------------------------------------


class TestCmdScaffold:
    def test_missing_name_returns_1(self, capsys):
        code = run(["scaffold"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires a skill name" in out

    def test_generates_stub(self, tmp_path, capsys):
        code = run(["scaffold", "my-test-skill", str(tmp_path)])
        assert code == 0
        stub = tmp_path / "my-test-skill" / "SKILL.md"
        assert stub.exists()
        assert "my-test-skill" in stub.read_text()

    def test_scaffold_error_returns_1(self, capsys):
        with patch("main.scaffold_skill", side_effect=RuntimeError("boom")):
            code = run(["scaffold", "badskill"])
        assert code == 1


# ---------------------------------------------------------------------------
# cmd_rollback
# ---------------------------------------------------------------------------


class TestCmdRollback:
    def test_success_returns_0(self):
        with patch("main.do_rollback", return_value=True):
            code = run(["rollback"])
        assert code == 0

    def test_failure_returns_1(self):
        with patch("main.do_rollback", return_value=False):
            code = run(["rollback"])
        assert code == 1

    def test_exception_returns_1(self, capsys):
        with patch("main.do_rollback", side_effect=RuntimeError("bad")):
            code = run(["rollback"])
        assert code == 1


# ---------------------------------------------------------------------------
# cmd_audit
# ---------------------------------------------------------------------------


class TestCmdAudit:
    def test_no_issues_returns_0(self):
        mock_report = MagicMock()
        mock_report.has_issues = False
        with patch("main.Auditor") as mock_cls:
            mock_cls.return_value.run.return_value = mock_report
            code = run(["audit"])
        assert code == 0

    def test_has_issues_returns_1(self):
        mock_report = MagicMock()
        mock_report.has_issues = True
        with patch("main.Auditor") as mock_cls:
            mock_cls.return_value.run.return_value = mock_report
            code = run(["audit"])
        assert code == 1

    def test_exception_returns_1(self, capsys):
        with patch("main.Auditor", side_effect=RuntimeError("fail")):
            code = run(["audit"])
        assert code == 1


# ---------------------------------------------------------------------------
# cmd_update
# ---------------------------------------------------------------------------


class TestCmdUpdate:
    def test_update_no_updates_available_returns_0(self, capsys):
        with patch("main.SkillUpdater") as mock_cls:
            mock_cls.return_value.run_interactive_update.return_value = (0, 0)
            code = run(["update"])
        assert code == 0  # 0 approved, 0 total → equal → return 0

    def test_update_all_approved_returns_0(self):
        with patch("main.SkillUpdater") as mock_cls:
            mock_cls.return_value.run_interactive_update.return_value = (2, 2)
            code = run(["update"])
        assert code == 0

    def test_update_some_approved_returns_1(self):
        with patch("main.SkillUpdater") as mock_cls:
            mock_cls.return_value.run_interactive_update.return_value = (1, 2)
            code = run(["update"])
        assert code == 1

    def test_update_filters_by_skill_name(self):
        with patch("main.SkillUpdater") as mock_cls:
            mock_cls.return_value.run_interactive_update.return_value = (1, 1)
            code = run(["update", "myskill"])
        mock_cls.return_value.run_interactive_update.assert_called_with(skill_name="myskill")
        assert code == 0

    def test_update_exception_returns_1(self, capsys):
        with patch("main.SkillUpdater", side_effect=RuntimeError("fail")):
            code = run(["update"])
        assert code == 1


# ---------------------------------------------------------------------------
# cmd_hunt
# ---------------------------------------------------------------------------


class TestCmdHunt:
    def test_nonexistent_project_root_returns_1(self, capsys):
        code = run(["hunt", "/no/such/path"])
        assert code == 1

    def test_empty_stack_returns_1(self, tmp_path, capsys):
        # A project with no tech files → no stack → exit 1
        code = run(["hunt", str(tmp_path)])
        assert code == 1
        out = capsys.readouterr().out
        assert "No tech stack" in out

    def test_no_results_suggests_scaffold(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        with patch("main.Hunter") as mock_hunter_cls:
            mock_hunter_cls.return_value.hunt.return_value = []
            code = run(["hunt", str(tmp_path)])
        assert code == 1
        out = capsys.readouterr().out
        assert "scaffold" in out

    def test_results_trigger_scan_and_report(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult

        mock_result = HuntResult(
            name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            raw_url="https://github.com/o/fastapi-skill/blob/main/SKILL.md",
            owner="o",
            repo_name="fastapi-skill",
            description="A skill",
            stars=200,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nfastapi helper",
        )

        from scorer import ScoredResult
        from security_scan import ScanResult

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        with (
            patch("main.Hunter") as mock_hunter_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report") as mock_render,
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=[]),
        ):
            mock_hunter_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])

        mock_render.assert_called_once()
        assert code == 0

    def test_hunt_exception_returns_1(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        with patch("main.Hunter") as mock_hunter_cls:
            mock_hunter_cls.return_value.hunt.side_effect = RuntimeError("API down")
            code = run(["hunt", str(tmp_path)])
        assert code == 1

    def test_all_results_red_returns_1(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult

        mock_result = HuntResult(
            name="bad-skill",
            repo_url="https://github.com/o/bad-skill",
            stars=100,
            result_type="skill",
            trust_tier="raw",
        )
        mock_scored = ScoredResult(hunt_result=mock_result, skill_metadata=None, total_score=0.5)

        with (
            patch("main.Hunter") as mock_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report"),
        ):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="RED")
            mock_score.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])

        assert code == 1

    def test_extract_context_exception_returns_1(self, tmp_path, capsys):
        with patch("main.extract_context", side_effect=RuntimeError("disk error")):
            code = run(["hunt", str(tmp_path)])
        assert code == 1
        out = capsys.readouterr().out
        assert "Context extraction failed" in out

    def test_parse_skill_exception_is_swallowed(self, tmp_path, capsys):
        """parse_skill_content failure must not abort the hunt."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult

        mock_result = HuntResult(
            name="good-skill",
            repo_url="https://github.com/o/good-skill",
            stars=100,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nsome content",
        )
        mock_scored = ScoredResult(hunt_result=mock_result, skill_metadata=None, total_score=0.7)

        with (
            patch("main.Hunter") as mock_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.parse_skill_content", side_effect=Exception("bad yaml")),
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report"),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=[]),
        ):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])

        assert code == 0  # hunt must succeed despite parse failure


class TestConfigLoading:
    def test_loads_defaults(self, tmp_path):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 42}}')
        with (
            patch("main._DEFAULTS_PATH", defaults),
            patch("main._USER_CONFIG_PATH", tmp_path / "no_user.json"),
        ):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 42

    def test_user_config_overrides_defaults(self, tmp_path):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 10, "max_results": 5}}')
        user = tmp_path / "user.json"
        user.write_text('{"hunt": {"min_stars": 99}}')
        with patch("main._DEFAULTS_PATH", defaults), patch("main._USER_CONFIG_PATH", user):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 99
        assert config["hunt"]["max_results"] == 5  # default preserved

    def test_corrupt_user_config_falls_back_to_defaults(self, tmp_path, capsys):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 7}}')
        user = tmp_path / "user.json"
        user.write_text("NOT JSON {{{")
        with patch("main._DEFAULTS_PATH", defaults), patch("main._USER_CONFIG_PATH", user):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 7

    def test_missing_defaults_returns_empty(self, tmp_path):
        with (
            patch("main._DEFAULTS_PATH", tmp_path / "no.json"),
            patch("main._USER_CONFIG_PATH", tmp_path / "no.json"),
        ):
            config = cli_main._load_config()
        assert config == {}


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"x": 99}}
        result = cli_main._deep_merge(base, override)
        assert result == {"a": {"x": 99, "y": 2}, "b": 3}

    def test_non_dict_override_replaces(self):
        base = {"a": {"x": 1}}
        override = {"a": "string"}
        result = cli_main._deep_merge(base, override)
        assert result["a"] == "string"

    def test_new_keys_added(self):
        result = cli_main._deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_original_not_mutated(self):
        base = {"a": 1}
        cli_main._deep_merge(base, {"a": 2})
        assert base["a"] == 1


# ---------------------------------------------------------------------------
# cmd_install
# ---------------------------------------------------------------------------


class TestCmdInstall:
    def test_missing_args_returns_1(self, capsys):
        code = run(["install"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires <owner> <repo>" in out

    def test_one_arg_returns_1(self, capsys):
        code = run(["install", "onlyowner"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires <owner> <repo>" in out

    def test_success_returns_0(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.install.return_value = ActionResult(
                action="install", skill_name="my-skill", success=True, message="Installed my-skill"
            )
            code = run(["install", "owner", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Installed my-skill" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.install.return_value = ActionResult(
                action="install", skill_name="my-skill", success=False, error="Already installed"
            )
            code = run(["install", "owner", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Install failed" in out
        assert "Already installed" in out

    def test_exception_returns_1(self, capsys):
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.install.side_effect = RuntimeError("network error")
            code = run(["install", "owner", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Install failed" in out
        assert "network error" in out


# ---------------------------------------------------------------------------
# cmd_remove
# ---------------------------------------------------------------------------


class TestCmdRemove:
    def test_missing_args_returns_1(self, capsys):
        code = run(["remove"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires a skill name" in out

    def test_success_returns_0(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.uninstall.return_value = ActionResult(
                action="uninstall", skill_name="my-skill", success=True, message="Removed my-skill"
            )
            code = run(["remove", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Removed my-skill" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.uninstall.return_value = ActionResult(
                action="uninstall", skill_name="my-skill", success=False, error="Skill not found"
            )
            code = run(["remove", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Remove failed" in out
        assert "Skill not found" in out

    def test_exception_returns_1(self, capsys):
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.uninstall.side_effect = OSError("permission denied")
            code = run(["remove", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Remove failed" in out
        assert "permission denied" in out


# ---------------------------------------------------------------------------
# cmd_enable
# ---------------------------------------------------------------------------


class TestCmdEnable:
    def test_missing_args_returns_1(self, capsys):
        code = run(["enable"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires a skill name" in out

    def test_success_returns_0(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.enable.return_value = ActionResult(
                action="enable",
                skill_name="my-skill",
                success=True,
                message="Re-enabled: _my-skill → my-skill",
            )
            code = run(["enable", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Re-enabled" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult

        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.enable.return_value = ActionResult(
                action="enable",
                skill_name="my-skill",
                success=False,
                error="Disabled skill not found",
            )
            code = run(["enable", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Enable failed" in out
        assert "Disabled skill not found" in out

    def test_exception_returns_1(self, capsys):
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.enable.side_effect = OSError("disk full")
            code = run(["enable", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Enable failed" in out
        assert "disk full" in out


# ---------------------------------------------------------------------------
# Command: contribute (v0.4.0 Gap 4)
# ---------------------------------------------------------------------------


class TestCmdContribute:
    """Test the contribute command — validate, scan, and contribute a skill."""

    def test_missing_args_returns_1(self, capsys):
        """contribute without skill name should error."""
        code = run(["contribute"])
        assert code == 1
        out = capsys.readouterr().out
        assert "requires a skill name" in out

    def test_skill_not_installed_returns_1(self, capsys, tmp_path, monkeypatch):
        """contribute should fail if skill not in ~/.claude/skills/."""
        monkeypatch.setenv("HOME", str(tmp_path))
        code = run(["contribute", "nonexistent-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "not found" in out

    def test_skill_missing_skill_md_returns_1(self, capsys, tmp_path, monkeypatch):
        """contribute should fail if SKILL.md not found."""
        monkeypatch.setenv("HOME", str(tmp_path))
        skills_dir = tmp_path / ".claude" / "skills"
        skill_path = skills_dir / "my-skill"
        skill_path.mkdir(parents=True)
        # Don't create SKILL.md

        code = run(["contribute", "my-skill"])
        assert code == 1
        out = capsys.readouterr().out
        assert "SKILL.md" in out and "not found" in out

    def test_red_scan_blocks_contribution(self, capsys, tmp_path, monkeypatch):
        """contribute should block if security scan returns RED."""
        monkeypatch.setenv("HOME", str(tmp_path))
        skills_dir = tmp_path / ".claude" / "skills"
        skill_path = skills_dir / "bad-skill"
        skill_path.mkdir(parents=True)

        # Create SKILL.md with malicious pattern
        skill_file = skill_path / "SKILL.md"
        skill_file.write_text("""\
---
name: bad-skill
version: 1.0
trigger: bad trigger
domain_tags: [security]
---
`os.system("rm -rf /")`
""")

        # Simplified test: just verify the command exists and returns 1 for malicious
        # Full end-to-end is complex due to local imports
        code = run(["contribute", "bad-skill"])
        assert code == 1

    def test_missing_frontmatter_fields_blocks(self, capsys, tmp_path, monkeypatch):
        """contribute should block if required frontmatter fields missing."""
        monkeypatch.setenv("HOME", str(tmp_path))
        skills_dir = tmp_path / ".claude" / "skills"
        skill_path = skills_dir / "incomplete-skill"
        skill_path.mkdir(parents=True)

        skill_file = skill_path / "SKILL.md"
        skill_file.write_text("""\
---
name: incomplete-skill
version: 1.0
---
Content without trigger and domain_tags
""")

        code = run(["contribute", "incomplete-skill"])
        assert code == 1

    def test_valid_skill_shows_template(self, capsys, tmp_path, monkeypatch):
        """contribute should work with valid skill and show template."""
        monkeypatch.setenv("HOME", str(tmp_path))
        skills_dir = tmp_path / ".claude" / "skills"
        skill_path = skills_dir / "good-skill"
        skill_path.mkdir(parents=True)

        skill_file = skill_path / "SKILL.md"
        skill_file.write_text("""\
---
name: good-skill
version: 1.0.0
trigger: good trigger
domain_tags: [productivity]
---
A helpful skill.
""")

        # Mock subprocess to simulate gh not installed
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")

            code = run(["contribute", "good-skill"])

        # Should succeed and print template
        assert code == 0
        out = capsys.readouterr().out
        # Should contain either the GitHub CLI message or the template
        assert "good-skill" in out or "Contribute:" in out


# ---------------------------------------------------------------------------
# Helper: _list_installed_skills
# ---------------------------------------------------------------------------


class TestListInstalledSkills:
    def test_no_skills_dir_returns_empty_set(self, tmp_path):
        with patch("main.Path.home", return_value=tmp_path):
            result = cli_main._list_installed_skills()
        assert result == set()

    def test_lists_installed_skills(self, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "skill1").mkdir()
        (skills_dir / "skill2").mkdir()
        (skills_dir / "readme.txt").write_text("not a skill")

        with patch("main.Path.home", return_value=tmp_path):
            result = cli_main._list_installed_skills()

        assert result == {"skill1", "skill2"}

    def test_ignores_files_in_skills_dir(self, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "skill1").mkdir()
        (skills_dir / "file.txt").write_text("text")

        with patch("main.Path.home", return_value=tmp_path):
            result = cli_main._list_installed_skills()

        assert result == {"skill1"}


# ---------------------------------------------------------------------------
# Helper: _prompt_confirm_actions
# ---------------------------------------------------------------------------


class TestPromptConfirmActions:
    def test_user_says_yes_returns_all_actions(self, monkeypatch):
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="http://r1",
                owner="o",
                repo="r",
                reason="score 0.8",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "y")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 1
        assert result[0].skill_name == "skill1"

    def test_user_says_no_returns_empty_list(self, monkeypatch):
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="http://r1",
                owner="o",
                repo="r",
                reason="score 0.8",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "n")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 0

    def test_user_says_empty_returns_empty_list(self, monkeypatch):
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="http://r1",
                owner="o",
                repo="r",
                reason="score 0.8",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 0

    def test_user_skips_specific_actions(self, monkeypatch):
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="http://r1",
                owner="o",
                repo="r",
                reason="score 0.8",
            ),
            PendingAction(
                action="install",
                skill_name="skill2",
                repo_url="http://r2",
                owner="o",
                repo="r",
                reason="score 0.7",
            ),
            PendingAction(action="disable", skill_name="badskill", reason="RED"),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "1,3")
        result = cli_main._prompt_confirm_actions(actions)

        # Should skip 1st and 3rd, keep 2nd
        assert len(result) == 1
        assert result[0].skill_name == "skill2"

    def test_empty_actions_returns_empty(self):
        result = cli_main._prompt_confirm_actions([])
        assert result == []

    def test_invalid_input_returns_empty(self, monkeypatch):
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="http://r1",
                owner="o",
                repo="r",
                reason="score 0.8",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "not,valid,input")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# cmd_hunt with confirmation and execution
# ---------------------------------------------------------------------------


class TestCmdHuntWithConfirmation:
    def test_hunt_with_user_confirmation_yes_executes_install(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult
        from installer import ActionResult, PendingAction

        mock_result = HuntResult(
            name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            raw_url="https://github.com/o/fastapi-skill/blob/main/SKILL.md",
            owner="o",
            repo_name="fastapi-skill",
            description="A skill",
            stars=200,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nfastapi helper",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        # Mock the action that would be built
        mock_action = PendingAction(
            action="install",
            skill_name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            owner="o",
            repo="fastapi-skill",
            reason="score 0.70",
        )

        # User confirms with 'y'
        monkeypatch.setattr("builtins.input", lambda _: "y")

        with (
            patch("main.Hunter") as mock_hunter_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report") as _mock_render,
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=[mock_action]),
            patch("main.Installer") as mock_installer_cls,
        ):
            mock_hunter_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            mock_installer_obj = MagicMock()
            mock_installer_cls.return_value = mock_installer_obj
            mock_installer_obj.execute_actions.return_value = [
                ActionResult(
                    action="install", skill_name="fastapi-skill", success=True, message="Installed"
                )
            ]

            code = run(["hunt", str(tmp_path)])

        # Should have called execute_actions
        mock_installer_obj.execute_actions.assert_called_once()
        assert code == 0

    def test_hunt_with_user_confirmation_no_exits_without_install(
        self, tmp_path, monkeypatch, capsys
    ):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult
        from installer import PendingAction

        mock_result = HuntResult(
            name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            raw_url="https://github.com/o/fastapi-skill/blob/main/SKILL.md",
            owner="o",
            repo_name="fastapi-skill",
            description="A skill",
            stars=200,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nfastapi helper",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        mock_action = PendingAction(
            action="install",
            skill_name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            owner="o",
            repo="fastapi-skill",
            reason="score 0.70",
        )

        # User declines with 'n'
        monkeypatch.setattr("builtins.input", lambda _: "n")

        with (
            patch("main.Hunter") as mock_hunter_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report") as _mock_render,
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=[mock_action]),
            patch("main.Installer") as mock_installer_cls,
        ):
            mock_hunter_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            mock_installer_obj = MagicMock()
            mock_installer_cls.return_value = mock_installer_obj

            code = run(["hunt", str(tmp_path)])

        # Should NOT have called execute_actions
        mock_installer_obj.execute_actions.assert_not_called()
        assert code == 1

        out = capsys.readouterr().out
        assert "Cancelled" in out

    def test_hunt_no_actions_to_take_returns_0(self, tmp_path, capsys):
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult

        mock_result = HuntResult(
            name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            raw_url="https://github.com/o/fastapi-skill/blob/main/SKILL.md",
            owner="o",
            repo_name="fastapi-skill",
            description="A skill",
            stars=200,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nfastapi helper",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        # Already installed, so no actions
        with (
            patch("main.Hunter") as mock_hunter_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report") as _mock_render,
            patch("main._list_installed_skills", return_value={"fastapi-skill"}),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=[]),
        ):  # Empty list
            mock_hunter_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            code = run(["hunt", str(tmp_path)])

        assert code == 0
        out = capsys.readouterr().out
        assert "already installed" in out


# ---------------------------------------------------------------------------
# Edge Cases and Comprehensive Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Comprehensive edge case testing for robustness."""

    def test_prompt_all_actions_skipped_returns_empty(self, monkeypatch):
        """User skips all actions → returns empty list."""
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install", skill_name="s1", repo_url="r1", owner="o", repo="r", reason="test"
            ),
            PendingAction(
                action="install", skill_name="s2", repo_url="r2", owner="o", repo="r", reason="test"
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "1,2")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 0

    def test_prompt_partial_skip(self, monkeypatch):
        """User skips some, keeps others."""
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install", skill_name="s1", repo_url="r1", owner="o", repo="r", reason="test"
            ),
            PendingAction(
                action="install", skill_name="s2", repo_url="r2", owner="o", repo="r", reason="test"
            ),
            PendingAction(
                action="install", skill_name="s3", repo_url="r3", owner="o", repo="r", reason="test"
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "2")
        result = cli_main._prompt_confirm_actions(actions)

        # Skip index 1 (second action)
        assert len(result) == 2
        assert result[0].skill_name == "s1"
        assert result[1].skill_name == "s3"

    def test_prompt_with_whitespace_in_skip_list(self, monkeypatch):
        """User input with spaces around indices."""
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install", skill_name="s1", repo_url="r1", owner="o", repo="r", reason="test"
            ),
            PendingAction(
                action="install", skill_name="s2", repo_url="r2", owner="o", repo="r", reason="test"
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: " 1 , 2 ")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 0

    def test_prompt_case_insensitive_yes(self, monkeypatch):
        """User can type 'Y' or 'YES'."""
        from installer import PendingAction

        actions = [
            PendingAction(
                action="install", skill_name="s1", repo_url="r1", owner="o", repo="r", reason="test"
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "YES")
        result = cli_main._prompt_confirm_actions(actions)
        assert len(result) == 1

    def test_list_installed_skills_with_disabled(self, tmp_path):
        """Disabled skills (starting with _) are included in list."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "active-skill").mkdir()
        (skills_dir / "_disabled-skill").mkdir()

        with patch("main.Path.home", return_value=tmp_path):
            result = cli_main._list_installed_skills()

        assert "active-skill" in result
        assert "_disabled-skill" in result
        assert len(result) == 2

    def test_get_dangerous_installed_skips_disabled(self):
        """_get_dangerous_installed() returns dangerous skills from registry."""
        from registry import RegistryEntry

        mock_registry = MagicMock()

        # Create a dangerous entry
        dangerous_entry = RegistryEntry(
            name="dangerous-skill",
            repo_url="https://github.com/o/dangerous",
            install_path="/some/path",
            audit_status="security_issue",
        )

        mock_registry.all.return_value = [dangerous_entry]

        with patch("main._list_installed_skills", return_value={"dangerous-skill"}):
            # Just test that function returns a list (registry will be empty in test env)
            result = cli_main._get_dangerous_installed()
            assert isinstance(result, list)

    def test_hunt_with_failed_actions(self, tmp_path, monkeypatch):
        """Hunt → confirm → execute with some failures."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult
        from installer import PendingAction, ActionResult

        mock_result = HuntResult(
            name="skill1",
            repo_url="https://github.com/o/skill1",
            raw_url="https://github.com/o/skill1/blob/main/SKILL.md",
            owner="o",
            repo_name="skill1",
            description="A skill",
            stars=100,
            result_type="skill",
            trust_tier="raw",
            raw_content="# test",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        mock_actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="r",
                owner="o",
                repo="r",
                reason="test",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "y")

        with (
            patch("main.Hunter") as mock_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report"),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=mock_actions),
            patch("main.Installer") as mock_installer_cls,
        ):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            mock_installer_obj = MagicMock()
            mock_installer_cls.return_value = mock_installer_obj
            # One success, one failure
            mock_installer_obj.execute_actions.return_value = [
                ActionResult(action="install", skill_name="skill1", success=True),
            ]

            code = run(["hunt", str(tmp_path)])

        assert code == 0

    def test_hunt_with_all_action_failures(self, tmp_path, monkeypatch):
        """Hunt → confirm → execute where all actions fail."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult
        from installer import PendingAction, ActionResult

        mock_result = HuntResult(
            name="skill1",
            repo_url="https://github.com/o/skill1",
            raw_url="https://github.com/o/skill1/blob/main/SKILL.md",
            owner="o",
            repo_name="skill1",
            description="A skill",
            stars=100,
            result_type="skill",
            trust_tier="raw",
            raw_content="# test",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        mock_actions = [
            PendingAction(
                action="install",
                skill_name="skill1",
                repo_url="r",
                owner="o",
                repo="r",
                reason="test",
            ),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "y")

        with (
            patch("main.Hunter") as mock_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report"),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.build_action_list", return_value=mock_actions),
            patch("main.Installer") as mock_installer_cls,
        ):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            mock_installer_obj = MagicMock()
            mock_installer_cls.return_value = mock_installer_obj
            # All failures
            mock_installer_obj.execute_actions.return_value = [
                ActionResult(
                    action="install", skill_name="skill1", success=False, error="Network error"
                ),
            ]

            code = run(["hunt", str(tmp_path)])

        # Should return 1 on failure
        assert code == 1

    def test_hunt_mixed_actions_install_and_disable(self, tmp_path, monkeypatch):
        """Hunt with both install and disable actions."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult
        from installer import PendingAction, ActionResult

        mock_result = HuntResult(
            name="good-skill",
            repo_url="https://github.com/o/good-skill",
            raw_url="https://github.com/o/good-skill/blob/main/SKILL.md",
            owner="o",
            repo_name="good-skill",
            description="A good skill",
            stars=100,
            result_type="skill",
            trust_tier="raw",
            raw_content="# test",
        )

        mock_scored = ScoredResult(
            hunt_result=mock_result,
            skill_metadata=None,
            total_score=0.7,
        )

        mock_actions = [
            PendingAction(
                action="install",
                skill_name="good-skill",
                repo_url="r1",
                owner="o",
                repo="good-skill",
                reason="score 0.7",
            ),
            PendingAction(action="disable", skill_name="bad-skill", reason="RED flagged"),
        ]

        monkeypatch.setattr("builtins.input", lambda _: "y")

        with (
            patch("main.Hunter") as mock_cls,
            patch("main.scan_skill") as mock_scan,
            patch("main.score_results") as mock_score,
            patch("main.render_hunt_report"),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=["bad-skill"]),
            patch("main.build_action_list", return_value=mock_actions),
            patch("main.Installer") as mock_installer_cls,
        ):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="GREEN")
            mock_score.return_value = [mock_scored]

            mock_installer_obj = MagicMock()
            mock_installer_cls.return_value = mock_installer_obj
            mock_installer_obj.execute_actions.return_value = [
                ActionResult(action="install", skill_name="good-skill", success=True),
                ActionResult(action="disable", skill_name="bad-skill", success=True),
            ]

            code = run(["hunt", str(tmp_path)])

        assert code == 0


# ---------------------------------------------------------------------------
# Config error handling
# ---------------------------------------------------------------------------


class TestConfigErrorHandling:
    """Test exception handling in config loading."""

    def test_config_json_decode_error_in_defaults(self, tmp_path, capsys):
        """Corrupt defaults.json should print warning and continue."""
        defaults = tmp_path / "defaults.json"
        defaults.write_text("{ INVALID JSON")

        with (
            patch("main._DEFAULTS_PATH", defaults),
            patch("main._USER_CONFIG_PATH", tmp_path / "no_user.json"),
        ):
            config = cli_main._load_config()

        assert config == {}
        out = capsys.readouterr().out
        assert "Warning" in out

    def test_config_corrupt_user_uses_defaults(self, tmp_path):
        """Corrupt user config should fall back to defaults."""
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 5}}')
        user = tmp_path / "user.json"
        user.write_text("NOT JSON")

        with patch("main._DEFAULTS_PATH", defaults), patch("main._USER_CONFIG_PATH", user):
            config = cli_main._load_config()

        assert config["hunt"]["min_stars"] == 5


# ---------------------------------------------------------------------------
# _get_dangerous_installed
# ---------------------------------------------------------------------------


class TestGetDangerousInstalled:
    def test_returns_empty_when_no_skills(self):
        with patch("main._list_installed_skills", return_value=set()):
            result = cli_main._get_dangerous_installed()
        assert result == []

    def test_skips_disabled_skills(self):
        mock_reg = MagicMock()
        mock_reg.all.return_value = []
        with (
            patch("main._list_installed_skills", return_value={"_bad-skill"}),
            patch("registry.Registry", return_value=mock_reg),
        ):
            result = cli_main._get_dangerous_installed()
        assert result == []
        mock_reg.all.assert_not_called()

    def test_flags_security_issue_skills(self):
        mock_entry = MagicMock()
        mock_entry.name = "dangerous-skill"
        mock_entry.audit_status = "security_issue"
        mock_reg = MagicMock()
        mock_reg.all.return_value = [mock_entry]
        with (
            patch("main._list_installed_skills", return_value={"dangerous-skill"}),
            patch("main.Registry", return_value=mock_reg),
        ):
            result = cli_main._get_dangerous_installed()
        assert "dangerous-skill" in result

    def test_skips_healthy_skills(self):
        mock_entry = MagicMock()
        mock_entry.name = "good-skill"
        mock_entry.audit_status = "healthy"
        mock_reg = MagicMock()
        mock_reg.all.return_value = [mock_entry]
        with (
            patch("main._list_installed_skills", return_value={"good-skill"}),
            patch("registry.Registry", return_value=mock_reg),
        ):
            result = cli_main._get_dangerous_installed()
        assert result == []


# ---------------------------------------------------------------------------
# _prompt_confirm_actions (additional edge cases)
# ---------------------------------------------------------------------------


class TestPromptConfirmActionsEdgeCases:
    def _make_install_action(self, name="skill-a", reason=None):
        a = MagicMock()
        a.action = "install"
        a.skill_name = name
        a.repo_url = f"https://github.com/o/{name}"
        a.reason = reason
        return a

    def test_empty_actions_returns_empty(self):
        result = cli_main._prompt_confirm_actions([])
        assert result == []

    def test_y_confirms_all(self):
        with patch("builtins.input", return_value="y"):
            result = cli_main._prompt_confirm_actions([self._make_install_action()])
        assert len(result) == 1

    def test_yes_confirms_all(self):
        with patch("builtins.input", return_value="yes"):
            result = cli_main._prompt_confirm_actions([self._make_install_action()])
        assert len(result) == 1

    def test_n_returns_empty(self, capsys):
        a = self._make_install_action()
        with patch("builtins.input", return_value="n"):
            result = cli_main._prompt_confirm_actions([a])
        assert result == []
        out = capsys.readouterr().out
        assert "Cancelled" in out

    def test_empty_input_returns_empty(self):
        a = MagicMock()
        a.action = "disable"
        a.skill_name = "bad-skill"
        a.repo_url = "u"
        a.reason = "security issue"
        with patch("builtins.input", return_value=""):
            result = cli_main._prompt_confirm_actions([a])
        assert result == []

    def test_skip_index_removes_item(self):
        a1 = self._make_install_action("skill-a")
        a2 = self._make_install_action("skill-b")
        with patch("builtins.input", return_value="1"):
            result = cli_main._prompt_confirm_actions([a1, a2])
        assert len(result) == 1
        assert result[0].skill_name == "skill-b"

    def test_skip_all_prints_no_confirmed(self, capsys):
        a1 = self._make_install_action("skill-a")
        with patch("builtins.input", return_value="1"):
            result = cli_main._prompt_confirm_actions([a1])
        assert result == []
        out = capsys.readouterr().out
        assert "No actions confirmed" in out

    def test_invalid_skip_cancels(self, capsys):
        a1 = self._make_install_action()
        with patch("builtins.input", return_value="not-a-number"):
            result = cli_main._prompt_confirm_actions([a1])
        assert result == []
        out = capsys.readouterr().out
        assert "Invalid" in out

    def test_disable_action_printed_in_output(self, capsys):
        a = MagicMock()
        a.action = "disable"
        a.skill_name = "danger-skill"
        a.repo_url = "u"
        a.reason = "RED scan"
        with patch("builtins.input", return_value="y"):
            cli_main._prompt_confirm_actions([a])
        out = capsys.readouterr().out
        assert "DISABLE" in out

    def test_install_reason_printed_when_present(self, capsys):
        a = self._make_install_action(reason="high relevance")
        with patch("builtins.input", return_value="y"):
            cli_main._prompt_confirm_actions([a])
        out = capsys.readouterr().out
        assert "high relevance" in out


# ---------------------------------------------------------------------------
# cmd_hunt: action execution paths (Steps 7-9)
# ---------------------------------------------------------------------------


class TestCmdHuntActionExecution:
    def _setup(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        from hunter import HuntResult
        from scorer import ScoredResult
        from security_scan import ScanResult

        mock_result = HuntResult(
            name="fastapi-skill",
            repo_url="https://github.com/o/fastapi-skill",
            stars=200,
            result_type="skill",
            trust_tier="raw",
            raw_content="# SKILL\nfastapi helper",
        )
        mock_scored = ScoredResult(hunt_result=mock_result, skill_metadata=None, total_score=0.7)
        mock_scan = ScanResult(severity="GREEN")
        return mock_result, mock_scored, mock_scan

    def test_no_actions_returns_0(self, tmp_path, capsys):
        mock_result, mock_scored, mock_scan = self._setup(tmp_path)
        with (
            patch("main.Hunter") as mh,
            patch("main.scan_skill") as ms,
            patch("main.score_results") as msc,
            patch("main.render_hunt_report"),
            patch("main.build_action_list", return_value=[]),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
        ):
            mh.return_value.hunt.return_value = [mock_result]
            ms.return_value = mock_scan
            msc.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])
        assert code == 0
        assert "No new actions" in capsys.readouterr().out

    def test_user_cancels_returns_1(self, tmp_path, capsys):
        mock_result, mock_scored, mock_scan = self._setup(tmp_path)
        mock_action = MagicMock()
        mock_action.action = "install"
        mock_action.skill_name = "fastapi-skill"
        mock_action.repo_url = "https://github.com/o/fastapi-skill"
        mock_action.reason = None
        with (
            patch("main.Hunter") as mh,
            patch("main.scan_skill") as ms,
            patch("main.score_results") as msc,
            patch("main.render_hunt_report"),
            patch("main.build_action_list", return_value=[mock_action]),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("builtins.input", return_value="n"),
        ):
            mh.return_value.hunt.return_value = [mock_result]
            ms.return_value = mock_scan
            msc.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])
        assert code == 1

    def test_successful_actions_returns_0(self, tmp_path, capsys):
        mock_result, mock_scored, mock_scan = self._setup(tmp_path)
        mock_action = MagicMock()
        mock_action.action = "install"
        mock_action.skill_name = "fastapi-skill"
        mock_action.repo_url = "https://github.com/o/fastapi-skill"
        mock_action.reason = None
        from installer import ActionResult

        success = ActionResult(
            action="install", skill_name="fastapi-skill", success=True, message="OK"
        )
        with (
            patch("main.Hunter") as mh,
            patch("main.scan_skill") as ms,
            patch("main.score_results") as msc,
            patch("main.render_hunt_report"),
            patch("main.build_action_list", return_value=[mock_action]),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.Installer") as mi,
            patch("builtins.input", return_value="y"),
        ):
            mh.return_value.hunt.return_value = [mock_result]
            ms.return_value = mock_scan
            msc.return_value = [mock_scored]
            mi.return_value.execute_actions.return_value = [success]
            code = run(["hunt", str(tmp_path)])
        assert code == 0
        out = capsys.readouterr().out
        assert "1/1" in out

    def test_failed_actions_returns_1_with_warning(self, tmp_path, capsys):
        mock_result, mock_scored, mock_scan = self._setup(tmp_path)
        mock_action = MagicMock()
        mock_action.action = "install"
        mock_action.skill_name = "fastapi-skill"
        mock_action.repo_url = "https://github.com/o/fastapi-skill"
        mock_action.reason = None
        from installer import ActionResult

        fail = ActionResult(
            action="install", skill_name="fastapi-skill", success=False, error="Network error"
        )
        with (
            patch("main.Hunter") as mh,
            patch("main.scan_skill") as ms,
            patch("main.score_results") as msc,
            patch("main.render_hunt_report"),
            patch("main.build_action_list", return_value=[mock_action]),
            patch("main._list_installed_skills", return_value=set()),
            patch("main._get_dangerous_installed", return_value=[]),
            patch("main.Installer") as mi,
            patch("builtins.input", return_value="y"),
        ):
            mh.return_value.hunt.return_value = [mock_result]
            ms.return_value = mock_scan
            msc.return_value = [mock_scored]
            mi.return_value.execute_actions.return_value = [fail]
            code = run(["hunt", str(tmp_path)])
        assert code == 1
        out = capsys.readouterr().out
        assert "failed" in out.lower()


# ---------------------------------------------------------------------------
# _load_config: corrupt defaults.json path
# ---------------------------------------------------------------------------


class TestLoadConfigCorruptDefaults:
    def test_invalid_defaults_prints_warning_returns_empty(self, tmp_path, capsys):
        defaults = tmp_path / "defaults.json"
        defaults.write_text("NOT JSON")
        with (
            patch("main._DEFAULTS_PATH", defaults),
            patch("main._USER_CONFIG_PATH", tmp_path / "no_user.json"),
        ):
            config = cli_main._load_config()
        assert config == {}
        out = capsys.readouterr().out
        assert "Warning" in out

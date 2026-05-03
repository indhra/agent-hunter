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

        with patch("main.Hunter") as mock_hunter_cls, \
             patch("main.scan_skill") as mock_scan, \
             patch("main.score_results") as mock_score, \
             patch("main.render_hunt_report") as mock_render:
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

        with patch("main.Hunter") as mock_cls, \
             patch("main.scan_skill") as mock_scan, \
             patch("main.score_results") as mock_score, \
             patch("main.render_hunt_report"):
            mock_cls.return_value.hunt.return_value = [mock_result]
            mock_scan.return_value = ScanResult(severity="RED")
            mock_score.return_value = [mock_scored]
            code = run(["hunt", str(tmp_path)])

        assert code == 1


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_loads_defaults(self, tmp_path):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 42}}')
        with patch("main._DEFAULTS_PATH", defaults), \
             patch("main._USER_CONFIG_PATH", tmp_path / "no_user.json"):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 42

    def test_user_config_overrides_defaults(self, tmp_path):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 10, "max_results": 5}}')
        user = tmp_path / "user.json"
        user.write_text('{"hunt": {"min_stars": 99}}')
        with patch("main._DEFAULTS_PATH", defaults), \
             patch("main._USER_CONFIG_PATH", user):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 99
        assert config["hunt"]["max_results"] == 5  # default preserved

    def test_corrupt_user_config_falls_back_to_defaults(self, tmp_path, capsys):
        defaults = tmp_path / "defaults.json"
        defaults.write_text('{"hunt": {"min_stars": 7}}')
        user = tmp_path / "user.json"
        user.write_text("NOT JSON {{{")
        with patch("main._DEFAULTS_PATH", defaults), \
             patch("main._USER_CONFIG_PATH", user):
            config = cli_main._load_config()
        assert config["hunt"]["min_stars"] == 7

    def test_missing_defaults_returns_empty(self, tmp_path):
        with patch("main._DEFAULTS_PATH", tmp_path / "no.json"), \
             patch("main._USER_CONFIG_PATH", tmp_path / "no.json"):
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
                action="install", skill_name="my-skill", success=True,
                message="Installed my-skill"
            )
            code = run(["install", "owner", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Installed my-skill" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.install.return_value = ActionResult(
                action="install", skill_name="my-skill", success=False,
                error="Already installed"
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
                action="uninstall", skill_name="my-skill", success=True,
                message="Removed my-skill"
            )
            code = run(["remove", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Removed my-skill" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.uninstall.return_value = ActionResult(
                action="uninstall", skill_name="my-skill", success=False,
                error="Skill not found"
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
                action="enable", skill_name="my-skill", success=True,
                message="Re-enabled: _my-skill → my-skill"
            )
            code = run(["enable", "my-skill"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Re-enabled" in out

    def test_failure_returns_1(self, capsys):
        from installer import ActionResult
        with patch("main.Installer") as mock_cls:
            mock_cls.return_value.enable.return_value = ActionResult(
                action="enable", skill_name="my-skill", success=False,
                error="Disabled skill not found"
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

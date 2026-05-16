"""Tests for context_extractor.py."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context_extractor import (
    extract_context,
    TECH_ALLOWLIST,
    SkillUsage,
    _extract_session_skills,
    _extract_from_git_log,
    _infer_domain_tags,
)


class TestSignalExtraction:
    def test_extracts_fastapi_from_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi==0.110.0\nuvicorn\n")
        profile = extract_context(tmp_path)
        assert "fastapi" in profile.tech_stack

    def test_extracts_react_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"dependencies": {"react": "18.0.0"}}')
        profile = extract_context(tmp_path)
        assert "react" in profile.tech_stack

    def test_no_private_paths_in_tech_stack(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n/usr/local/myproject\n")
        profile = extract_context(tmp_path)
        # Private paths should not appear
        for signal in profile.tech_stack:
            assert "/" not in signal
            assert signal in TECH_ALLOWLIST

    def test_signals_are_lowercase(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("FastAPI\nDjango\n")
        profile = extract_context(tmp_path)
        for signal in profile.tech_stack:
            assert signal == signal.lower()

    def test_domain_tags_inferred(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\npostgresql\n")
        profile = extract_context(tmp_path)
        assert "backend" in profile.domain_tags or "python" in profile.domain_tags

    def test_empty_project_no_crash(self, tmp_path):
        profile = extract_context(tmp_path)
        assert profile.tech_stack == []

    def test_does_not_read_claude_md(self, tmp_path):
        # CLAUDE.md mentions fastapi — but it must NOT be read (forbidden source)
        (tmp_path / "CLAUDE.md").write_text("This project uses FastAPI and Redis.\n")
        profile = extract_context(tmp_path)
        assert "fastapi" not in profile.tech_stack
        assert "redis" not in profile.tech_stack

    def test_manifest_signal_not_polluted_by_readme(self, tmp_path):
        # Django mentioned only in README, flask only in requirements.txt
        (tmp_path / "README.md").write_text("We could use Django here.\n")
        (tmp_path / "requirements.txt").write_text("flask\n")
        profile = extract_context(tmp_path)
        assert "flask" in profile.tech_stack
        assert "django" not in profile.tech_stack

    def test_allowlist_only_signals(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\nsome_private_function\n")
        profile = extract_context(tmp_path)
        # Only allowlisted terms should appear
        for signal in profile.tech_stack:
            assert signal in TECH_ALLOWLIST


class TestAllowlist:
    def test_allowlist_is_not_empty(self):
        assert len(TECH_ALLOWLIST) > 20

    def test_common_frameworks_in_allowlist(self):
        for tech in ["fastapi", "django", "react", "postgres", "docker"]:
            assert tech in TECH_ALLOWLIST

    def test_skill_md_not_in_allowlist(self):
        assert "skill.md" not in TECH_ALLOWLIST

    def test_utility_libs_in_allowlist(self):
        for tech in ["requests", "rich", "pyyaml"]:
            assert tech in TECH_ALLOWLIST


class TestSessionSkillsExtraction:
    """Test extraction of recently invoked skills from ~/.claude/sessions/."""

    def test_session_skills_field_exists(self, tmp_path):
        """ContextProfile should include session_skills field."""
        profile = extract_context(tmp_path)
        assert hasattr(profile, "session_skills")
        assert isinstance(profile.session_skills, list)

    def test_skill_usage_dataclass(self):
        """SkillUsage should track skill name, last_seen, mention_count."""
        now = datetime.now()
        skill = SkillUsage(skill_name="trusty", last_seen=now, mention_count=3)
        assert skill.skill_name == "trusty"
        assert skill.last_seen == now
        assert skill.mention_count == 3

    def test_extract_session_skills_no_sessions_dir(self, monkeypatch, tmp_path):
        """Should gracefully return empty list if ~/.claude/sessions doesn't exist."""
        # Mock home directory to a temp path without sessions
        monkeypatch.setenv("HOME", str(tmp_path))
        skills = _extract_session_skills()
        assert skills == []

    def test_extract_session_skills_from_mock_sessions(self, tmp_path, monkeypatch):
        """Should extract skill names from session files."""
        # Create mock sessions directory
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        now_ms = int(datetime.now().timestamp() * 1000)

        # Create a session file with skill in cwd
        session_data = {
            "pid": 12345,
            "sessionId": "test-session",
            "cwd": str(tmp_path / ".claude" / "skills" / "trusty" / "SKILL.md"),
            "startedAt": now_ms - 5000,
            "updatedAt": now_ms,
        }
        (sessions_dir / "12345.json").write_text(json.dumps(session_data))

        skills = _extract_session_skills()
        assert len(skills) == 1
        assert skills[0].skill_name == "trusty"
        assert skills[0].mention_count >= 1

    def test_extract_session_skills_filters_old_sessions(self, tmp_path, monkeypatch):
        """Should only return skills from the last 30 days."""
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        now = datetime.now()
        old_date_ms = int((now - timedelta(days=35)).timestamp() * 1000)
        recent_date_ms = int((now - timedelta(days=5)).timestamp() * 1000)

        # Old session
        old_session = {
            "pid": 10000,
            "cwd": str(tmp_path / ".claude" / "skills" / "old-skill" / "file.py"),
            "updatedAt": old_date_ms,
        }
        (sessions_dir / "10000.json").write_text(json.dumps(old_session))

        # Recent session
        recent_session = {
            "pid": 20000,
            "cwd": str(tmp_path / ".claude" / "skills" / "recent-skill" / "file.py"),
            "updatedAt": recent_date_ms,
        }
        (sessions_dir / "20000.json").write_text(json.dumps(recent_session))

        skills = _extract_session_skills()
        skill_names = [s.skill_name for s in skills]

        assert "recent-skill" in skill_names
        assert "old-skill" not in skill_names

    def test_extract_session_skills_malformed_json_ignored(self, tmp_path, monkeypatch):
        """Should skip malformed JSON files gracefully."""
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        now_ms = int(datetime.now().timestamp() * 1000)

        # Malformed JSON
        (sessions_dir / "bad.json").write_text("{invalid json")

        # Valid JSON
        valid_session = {
            "pid": 99999,
            "cwd": str(tmp_path / ".claude" / "skills" / "good-skill" / "file.py"),
            "updatedAt": now_ms,
        }
        (sessions_dir / "good.json").write_text(json.dumps(valid_session))

        skills = _extract_session_skills()
        assert len(skills) == 1
        assert skills[0].skill_name == "good-skill"

    def test_extract_session_skills_sorted_by_recency(self, tmp_path, monkeypatch):
        """Should return skills sorted by most recent first."""
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        now = datetime.now()

        for i, skill_name in enumerate(["skill-a", "skill-b", "skill-c"]):
            ts_ms = int((now - timedelta(days=i)).timestamp() * 1000)
            session = {
                "pid": 1000 + i,
                "cwd": str(tmp_path / ".claude" / "skills" / skill_name / "file.py"),
                "updatedAt": ts_ms,
            }
            (sessions_dir / f"{1000 + i}.json").write_text(json.dumps(session))

        skills = _extract_session_skills()
        # skill-a is most recent (0 days ago), skill-c is oldest (2 days ago)
        assert skills[0].skill_name == "skill-a"
        assert skills[1].skill_name == "skill-b"
        assert skills[2].skill_name == "skill-c"


# ---------------------------------------------------------------------------
# _extract_session_skills: OSError in outer glob
# ---------------------------------------------------------------------------


class TestExtractSessionSkillsOSError:
    def test_oserror_in_sessions_glob_returns_empty(self, tmp_path, monkeypatch):
        """OSError while iterating sessions dir should be caught and return []."""
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        # Patch glob to raise OSError
        from unittest.mock import patch

        with patch("context_extractor.Path.home", return_value=tmp_path):
            with patch.object(type(sessions_dir), "glob", side_effect=OSError("permission denied")):
                skills = _extract_session_skills()
        assert skills == []

    def test_session_with_skill_adds_to_profile(self, tmp_path, monkeypatch, capsys):
        """extract_context should print 'Recently invoked skills' when session_skills is populated."""
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path))

        now_ms = int(datetime.now().timestamp() * 1000)
        session = {
            "pid": 12345,
            "cwd": str(tmp_path / ".claude" / "skills" / "browse" / "file.py"),
            "updatedAt": now_ms,
        }
        (sessions_dir / "12345.json").write_text(json.dumps(session))

        # Create a minimal project
        (tmp_path / "requirements.txt").write_text("fastapi\n")

        profile = extract_context(str(tmp_path))
        out = capsys.readouterr().out
        assert "browse" in profile.session_skills[0].skill_name
        assert "Recently invoked skills" in out


# ---------------------------------------------------------------------------
# _extract_from_git_log: parsing commits
# ---------------------------------------------------------------------------


class TestExtractFromGitLog:
    def test_active_commits_classified_correctly(self, tmp_path):
        """Commits < 7 days old should go into 'active' bucket."""
        from unittest.mock import patch, MagicMock
        from datetime import datetime, timedelta

        now = datetime.now()
        recent_date = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        stdout = f"{recent_date} +0000 fastapi hello world\n"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stdout

        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)

        assert "fastapi" in signals
        assert "fastapi" in activity["active"]

    def test_recent_commits_classified_correctly(self, tmp_path):
        """Commits 7-30 days old should go into 'recent' bucket."""
        from unittest.mock import patch, MagicMock
        from datetime import datetime, timedelta

        now = datetime.now()
        medium_date = (now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
        stdout = f"{medium_date} +0000 fastapi service update\n"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stdout

        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)

        assert "fastapi" in signals
        assert "fastapi" in activity["recent"]
        assert "fastapi" not in activity["active"]

    def test_dormant_commits_classified_correctly(self, tmp_path):
        """Commits >= 90 days old should go into 'dormant' bucket."""
        from unittest.mock import patch, MagicMock
        from datetime import datetime, timedelta

        now = datetime.now()
        old_date = (now - timedelta(days=120)).strftime("%Y-%m-%d %H:%M:%S")
        stdout = f"{old_date} +0000 pytorch training fix\n"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = stdout

        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)

        assert "pytorch" in signals
        assert "pytorch" in activity["dormant"]

    def test_nonzero_returncode_returns_empty(self, tmp_path):
        """Non-zero exit from git log should return empty signals + activity."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 128  # not a git repo
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)
        assert signals == set()
        assert activity == {}

    def test_timeout_returns_empty(self, tmp_path):
        """TimeoutExpired should be caught and return empty."""
        import subprocess
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 10)):
            signals, activity = _extract_from_git_log(tmp_path)
        assert signals == set()
        assert activity == {}

    def test_git_not_found_returns_empty(self, tmp_path):
        """FileNotFoundError (git not installed) should return empty."""
        from unittest.mock import patch

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            signals, activity = _extract_from_git_log(tmp_path)
        assert signals == set()
        assert activity == {}

    def test_malformed_line_skipped(self, tmp_path):
        """Lines with fewer than 4 parts should be skipped gracefully."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "bad line\n"  # only 2 parts
        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)
        assert signals == set()

    def test_bad_date_line_skipped(self, tmp_path):
        """Lines with invalid date format should be skipped gracefully."""
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not-a-date 00:00:00 +0000 fastapi service\n"
        with patch("subprocess.run", return_value=mock_result):
            signals, activity = _extract_from_git_log(tmp_path)
        # fastapi signal skipped because date parse failed
        assert "fastapi" not in signals


# ---------------------------------------------------------------------------
# _infer_domain_tags: domain mapping
# ---------------------------------------------------------------------------


class TestInferDomainTags:
    def test_known_domain_detected(self):
        tags = _infer_domain_tags({"fastapi"})
        assert "backend" in tags
        assert "python" in tags

    def test_unknown_signals_returns_empty(self):
        tags = _infer_domain_tags({"unknownxyz"})
        assert tags == []

    def test_multiple_domains_detected(self):
        tags = _infer_domain_tags({"react", "pytorch", "docker"})
        assert "frontend" in tags
        assert "ml" in tags
        assert "infra" in tags

    def test_tags_are_sorted(self):
        tags = _infer_domain_tags({"fastapi", "react", "pytorch"})
        assert tags == sorted(tags)

"""Tests for scorer.py."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scorer import (
    score_results,
    _check_installed_skill_usage,
    _compute_recency,
    _compute_yagni,
    WEIGHTS,
)
from hunter import HuntResult
from context_extractor import ContextProfile, SkillUsage


def make_profile(**kwargs) -> ContextProfile:
    defaults = dict(
        tech_stack=["fastapi", "postgres", "pytest"],
        domain_tags=["backend", "python"],
        active_domains=["fastapi"],
        recent_domains=["postgres"],
        dormant_domains=[],
    )
    defaults.update(kwargs)
    return ContextProfile(**defaults)


def make_result(**kwargs) -> HuntResult:
    defaults = dict(
        name="test-skill",
        repo_url="https://github.com/owner/test-skill",
        repo_name="test-skill",
        description="A FastAPI helper skill.",
        stars=100,
        last_commit_date=datetime.now() - timedelta(days=10),
        trust_tier="raw",
        result_type="skill",
    )
    defaults.update(kwargs)
    return HuntResult(**defaults)


class TestScoring:
    def test_returns_sorted_by_score(self):
        profile = make_profile()
        high = make_result(stars=500, name="fastapi-postgres-skill",
                          repo_url="https://github.com/a/a", trust_tier="verified")
        low = make_result(stars=10, name="rust-game-engine",
                         repo_url="https://github.com/b/b", trust_tier="raw")
        results = score_results([low, high], profile)
        assert results[0].hunt_result.repo_url == high.repo_url

    def test_verified_scores_higher_than_raw(self):
        profile = make_profile()
        verified = make_result(repo_url="https://github.com/a/a", trust_tier="verified",
                               stars=50, name="fastapi-skill")
        raw = make_result(repo_url="https://github.com/b/b", trust_tier="raw",
                          stars=50, name="fastapi-skill")
        results = score_results([raw, verified], profile)
        assert results[0].hunt_result.trust_tier == "verified"

    def test_score_between_zero_and_one(self):
        profile = make_profile()
        r = make_result()
        results = score_results([r], profile)
        assert 0.0 <= results[0].total_score <= 1.0

    def test_yagni_active_domain_boosts_score(self):
        profile = make_profile(active_domains=["fastapi"])
        active = make_result(name="fastapi-helper", repo_name="fastapi-helper",
                             repo_url="https://github.com/a/a")
        dormant_profile = make_profile(dormant_domains=["fastapi"], active_domains=[])
        results_active = score_results([active], profile)
        results_dormant = score_results([active], dormant_profile)
        assert results_active[0].total_score > results_dormant[0].total_score

    def test_recent_commit_scores_higher_than_stale(self):
        profile = make_profile()
        fresh = make_result(last_commit_date=datetime.now() - timedelta(days=5),
                            repo_url="https://github.com/a/a")
        stale = make_result(last_commit_date=datetime.now() - timedelta(days=170),
                            repo_url="https://github.com/b/b")
        results = score_results([stale, fresh], profile)
        assert results[0].hunt_result.repo_url == fresh.repo_url

    def test_high_star_count_helps(self):
        profile = make_profile()
        popular = make_result(stars=5000, repo_url="https://github.com/a/a")
        obscure = make_result(stars=10, repo_url="https://github.com/b/b")
        results = score_results([obscure, popular], profile)
        assert results[0].hunt_result.stars == 5000

    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_empty_results(self):
        profile = make_profile()
        results = score_results([], profile)
        assert results == []


class TestInstallLogFeedback:
    """Test Gap 3: install_log → scorer feedback loop (v0.4.0)."""

    def test_dormant_installed_skill_gets_low_score(self, tmp_path, monkeypatch):
        """Skill installed >30d ago with 0 session mentions should get 0.5× multiplier."""
        # Setup: create mock install_log.jsonl
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        old_install_ts = (now - timedelta(days=35)).isoformat()
        
        install_log.write_text(
            json.dumps({
                "skill_name": "old-skill",
                "action": "install",
                "timestamp": old_install_ts,
            }) + "\n"
        )
        
        monkeypatch.setenv("HOME", str(tmp_path))
        
        # Create profile with no session mentions of the skill
        profile = make_profile(session_skills=[])
        
        skill = make_result(
            name="old-skill",
            repo_url="https://github.com/owner/old-skill",
            stars=100,
            last_commit_date=datetime.now() - timedelta(days=10),
        )
        
        results = score_results([skill], profile)
        # Should have dormant multiplier applied (0.5×)
        assert results[0].yagni_multiplier == 0.5

    def test_active_installed_skill_gets_boost(self, tmp_path, monkeypatch):
        """Skill with recent session mentions should get a boost."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_install_ts = (now - timedelta(days=5)).isoformat()
        
        install_log.write_text(
            json.dumps({
                "skill_name": "active-skill",
                "action": "install",
                "timestamp": recent_install_ts,
            }) + "\n"
        )
        
        monkeypatch.setenv("HOME", str(tmp_path))
        
        # Create profile WITH session mentions
        recent_date = datetime.now()
        profile = make_profile(
            session_skills=[
                SkillUsage(
                    skill_name="active-skill",
                    last_seen=recent_date,
                    mention_count=5,
                )
            ]
        )
        
        skill = make_result(
            name="active-skill",
            repo_url="https://github.com/owner/active-skill",
            stars=50,
        )
        
        results = score_results([skill], profile)
        # Should get active boost (up to 1.1×)
        assert results[0].yagni_multiplier >= 1.0

    def test_not_installed_skill_unchanged(self, tmp_path, monkeypatch):
        """Skill not in install_log should use normal YAGNI logic."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        # Empty install_log
        (agent_hunter_dir / "install_log.jsonl").write_text("")
        monkeypatch.setenv("HOME", str(tmp_path))
        
        profile = make_profile(
            active_domains=["fastapi"],
            session_skills=[],
        )
        
        skill = make_result(
            name="fastapi-helper",
            repo_url="https://github.com/owner/fastapi-helper",
            repo_name="fastapi-helper",
            stars=100,
        )
        
        results = score_results([skill], profile)
        # Should use active_domains match (2.0×) not install_log
        assert results[0].yagni_multiplier == 2.0

    def test_check_installed_skill_usage_returns_dormant(self, tmp_path, monkeypatch):
        """_check_installed_skill_usage should detect dormant skills."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        old_ts = (now - timedelta(days=40)).isoformat()
        
        install_log.write_text(
            json.dumps({
                "skill_name": "dormant-skill",
                "action": "install",
                "timestamp": old_ts,
            }) + "\n"
        )
        
        monkeypatch.setenv("HOME", str(tmp_path))
        
        profile = make_profile(session_skills=[])  # No mentions
        status = _check_installed_skill_usage("dormant-skill", profile)
        
        assert status == "dormant"

    def test_check_installed_skill_usage_returns_active(self, tmp_path, monkeypatch):
        """_check_installed_skill_usage should detect actively used skills."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_ts = (now - timedelta(days=10)).isoformat()
        
        install_log.write_text(
            json.dumps({
                "skill_name": "active-skill",
                "action": "install",
                "timestamp": recent_ts,
            }) + "\n"
        )
        
        monkeypatch.setenv("HOME", str(tmp_path))
        
        profile = make_profile(
            session_skills=[
                SkillUsage(
                    skill_name="active-skill",
                    last_seen=datetime.now(),
                    mention_count=3,
                )
            ]
        )
        
        status = _check_installed_skill_usage("active-skill", profile)
        assert status == "active"

    def test_check_installed_skill_usage_returns_none_not_installed(self, tmp_path, monkeypatch):
        """Should return None for skills that aren't installed."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        
        (agent_hunter_dir / "install_log.jsonl").write_text("")
        monkeypatch.setenv("HOME", str(tmp_path))
        
        profile = make_profile(session_skills=[])
        status = _check_installed_skill_usage("never-installed", profile)
        
        assert status is None

    def test_install_log_missing_returns_none(self, tmp_path, monkeypatch):
        """Should gracefully return None if install_log doesn't exist."""
        monkeypatch.setenv("HOME", str(tmp_path))
        # Don't create .agent-hunter directory
        
        profile = make_profile(session_skills=[])
        status = _check_installed_skill_usage("some-skill", profile)
        
        assert status is None


# ---------------------------------------------------------------------------
# _compute_recency edge cases
# ---------------------------------------------------------------------------

class TestComputeRecency:
    def test_string_date_is_parsed(self):
        """ISO string dates should be parsed and scored correctly."""
        from hunter import HuntResult
        r = HuntResult(
            name="x", repo_url="u", stars=1, result_type="skill", trust_tier="raw",
            last_commit_date="2099-01-01",  # future date → recency = 1.0
        )
        score = _compute_recency(r)
        assert score == 1.0

    def test_bad_string_date_returns_neutral(self):
        """Unparseable ISO string should return 0.5 (neutral)."""
        from hunter import HuntResult
        r = HuntResult(
            name="x", repo_url="u", stars=1, result_type="skill", trust_tier="raw",
            last_commit_date="not-a-date",
        )
        score = _compute_recency(r)
        assert score == 0.5

    def test_timezone_aware_date_is_handled(self):
        """Timezone-aware datetime objects should be stripped and scored."""
        from hunter import HuntResult
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        r = HuntResult(
            name="x", repo_url="u", stars=1, result_type="skill", trust_tier="raw",
            last_commit_date=recent,
        )
        score = _compute_recency(r)
        assert score > 0.9  # very recent → near 1.0

    def test_none_date_returns_neutral(self):
        """None last_commit_date should return 0.5."""
        from hunter import HuntResult
        r = HuntResult(
            name="x", repo_url="u", stars=1, result_type="skill", trust_tier="raw",
            last_commit_date=None,
        )
        score = _compute_recency(r)
        assert score == 0.5

    def test_very_old_date_returns_zero(self):
        """Date 180+ days old should return 0.0."""
        from hunter import HuntResult
        r = HuntResult(
            name="x", repo_url="u", stars=1, result_type="skill", trust_tier="raw",
            last_commit_date=datetime.now() - timedelta(days=200),
        )
        score = _compute_recency(r)
        assert score == 0.0


# ---------------------------------------------------------------------------
# _compute_yagni edge cases
# ---------------------------------------------------------------------------

class TestComputeYagni:
    def test_dormant_domain_match_returns_low_multiplier(self):
        """Skill matching dormant git domain should get 0.5× multiplier."""
        from hunter import HuntResult
        profile = make_profile(
            active_domains=[],
            recent_domains=[],
            dormant_domains=["rust"],
        )
        r = HuntResult(
            name="rust-helper", repo_url="u", stars=1, result_type="skill",
            trust_tier="raw", repo_name="rust-helper",
        )
        with patch("scorer.Path.home") as mock_home:
            mock_home.return_value = Path("/nonexistent_path_xyz")
            mult = _compute_yagni(r, profile)
        assert mult == 0.5

    def test_install_active_returns_boost(self, tmp_path, monkeypatch):
        """Skill matching active install_log should get 1.0+ multiplier."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        install_log.write_text(
            json.dumps({
                "skill_name": "myskill",
                "action": "install",
                "timestamp": (now - timedelta(days=5)).isoformat(),
            }) + "\n"
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        profile = make_profile(
            active_domains=[],
            recent_domains=[],
            dormant_domains=[],
            session_skills=[
                SkillUsage(skill_name="myskill", last_seen=datetime.now(), mention_count=2),
            ],
        )
        r = HuntResult(
            name="myskill", repo_url="u", stars=1, result_type="skill",
            trust_tier="raw", repo_name="myskill",
        )
        mult = _compute_yagni(r, profile)
        assert mult >= 1.0

    def test_install_dormant_returns_low_multiplier(self, tmp_path, monkeypatch):
        """Skill matching dormant install_log should get 0.5× multiplier."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        install_log.write_text(
            json.dumps({
                "skill_name": "oldskill",
                "action": "install",
                "timestamp": (now - timedelta(days=40)).isoformat(),
            }) + "\n"
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        profile = make_profile(
            active_domains=[],
            recent_domains=[],
            dormant_domains=[],
            session_skills=[],
        )
        r = HuntResult(
            name="oldskill", repo_url="u", stars=1, result_type="skill",
            trust_tier="raw", repo_name="oldskill",
        )
        mult = _compute_yagni(r, profile)
        assert mult == 0.5


# ---------------------------------------------------------------------------
# _check_installed_skill_usage edge cases
# ---------------------------------------------------------------------------

class TestCheckInstalledSkillUsageEdgeCases:
    def test_oserror_reading_log_returns_none(self, tmp_path, monkeypatch):
        """OSError while reading install_log should return None gracefully."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        # Create the file but make it unreadable by patching open
        (agent_hunter_dir / "install_log.jsonl").write_text("valid line")
        monkeypatch.setenv("HOME", str(tmp_path))

        with patch("builtins.open", side_effect=OSError("permission denied")):
            profile = make_profile(session_skills=[])
            status = _check_installed_skill_usage("some-skill", profile)

        assert status is None

    def test_malformed_json_lines_skipped(self, tmp_path, monkeypatch):
        """Malformed JSON lines in install_log should be silently skipped."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        install_log = agent_hunter_dir / "install_log.jsonl"
        # Mix valid and invalid JSON
        install_log.write_text(
            "not valid json\n"
            "{}\n"
            + json.dumps({
                "skill_name": "good-skill",
                "action": "install",
                "timestamp": (datetime.now() - timedelta(days=40)).isoformat(),
            }) + "\n"
        )
        monkeypatch.setenv("HOME", str(tmp_path))

        profile = make_profile(session_skills=[])
        status = _check_installed_skill_usage("good-skill", profile)
        assert status == "dormant"

    def test_enable_action_updates_install_time(self, tmp_path, monkeypatch):
        """'enable' action should count as install for recency purposes."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        install_log = agent_hunter_dir / "install_log.jsonl"
        # Old install, recent enable → should not be dormant
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        install_log.write_text(
            json.dumps({
                "skill_name": "reenabled-skill",
                "action": "install",
                "timestamp": (now - timedelta(days=60)).isoformat(),
            }) + "\n"
            + json.dumps({
                "skill_name": "reenabled-skill",
                "action": "enable",
                "timestamp": (now - timedelta(days=2)).isoformat(),
            }) + "\n"
        )
        monkeypatch.setenv("HOME", str(tmp_path))

        profile = make_profile(session_skills=[])
        status = _check_installed_skill_usage("reenabled-skill", profile)
        # Recent enable means <30d since last install/enable → not dormant
        assert status is None

    def test_skill_installed_recently_with_no_mentions_is_not_dormant(self, tmp_path, monkeypatch):
        """Skill installed <30d ago with 0 mentions is NOT dormant yet."""
        agent_hunter_dir = tmp_path / ".agent-hunter"
        agent_hunter_dir.mkdir()
        install_log = agent_hunter_dir / "install_log.jsonl"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        install_log.write_text(
            json.dumps({
                "skill_name": "new-skill",
                "action": "install",
                "timestamp": (now - timedelta(days=10)).isoformat(),
            }) + "\n"
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        profile = make_profile(session_skills=[])
        status = _check_installed_skill_usage("new-skill", profile)
        assert status is None  # not dormant, not active → None

    def test_config_weights_override(self):
        """score_results should use custom weights from config when provided."""
        profile = make_profile()
        r = make_result(stars=1, trust_tier="verified", repo_url="https://github.com/a/a")
        custom_weights = {
            "stack_match": 0.0,
            "domain_match": 0.0,
            "star_score": 0.0,
            "recency_score": 0.0,
            "trust_score": 1.0,  # only trust matters
        }
        config = {"scoring": {"weights": custom_weights}}
        results = score_results([r], profile, config=config)
        # trust_score for "verified" = 1.0, total = 1.0 × multiplier
        assert results[0].trust_score == 1.0

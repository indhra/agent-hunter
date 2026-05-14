"""Tests for scorer.py — simplified for v1.0.0-alpha (4-signal scoring)."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scorer import (
    score_results,
    _compute_recency,
    _compute_yagni,
    WEIGHTS,
    YAGNI_MULTIPLIERS,
)
from hunter import HuntResult
from context_extractor import ContextProfile


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
        high = make_result(
            stars=500,
            name="fastapi-postgres-skill",
            repo_url="https://github.com/a/a",
            trust_tier="verified",
        )
        low = make_result(
            stars=10, name="rust-game-engine", repo_url="https://github.com/b/b", trust_tier="raw"
        )
        results = score_results([low, high], profile)
        assert results[0].hunt_result.repo_url == high.repo_url

    def test_verified_scores_higher_than_raw(self):
        profile = make_profile()
        verified = make_result(
            repo_url="https://github.com/a/a", trust_tier="verified", stars=50, name="fastapi-skill"
        )
        raw = make_result(
            repo_url="https://github.com/b/b", trust_tier="raw", stars=50, name="fastapi-skill"
        )
        results = score_results([raw, verified], profile)
        assert results[0].hunt_result.trust_tier == "verified"

    def test_score_between_zero_and_one(self):
        profile = make_profile()
        r = make_result()
        results = score_results([r], profile)
        assert 0.0 <= results[0].total_score <= 1.0

    def test_yagni_active_domain_boosts_score(self):
        profile = make_profile(active_domains=["fastapi"])
        active = make_result(
            name="fastapi-helper", repo_name="fastapi-helper", repo_url="https://github.com/a/a"
        )
        dormant_profile = make_profile(dormant_domains=["fastapi"], active_domains=[])
        results_active = score_results([active], profile)
        results_dormant = score_results([active], dormant_profile)
        assert results_active[0].total_score > results_dormant[0].total_score

    def test_recent_commit_scores_higher_than_stale(self):
        profile = make_profile()
        fresh = make_result(
            last_commit_date=datetime.now() - timedelta(days=5), repo_url="https://github.com/a/a"
        )
        stale = make_result(
            last_commit_date=datetime.now() - timedelta(days=170), repo_url="https://github.com/b/b"
        )
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


# ---------------------------------------------------------------------------
# _compute_recency edge cases
# ---------------------------------------------------------------------------


class TestComputeRecency:
    def test_string_date_is_parsed(self):
        """ISO string dates should be parsed and scored correctly."""
        from hunter import HuntResult

        r = HuntResult(
            name="x",
            repo_url="u",
            stars=1,
            result_type="skill",
            trust_tier="raw",
            last_commit_date="2099-01-01",  # future date → recency = 1.0
        )
        score = _compute_recency(r)
        assert score == 1.0

    def test_bad_string_date_returns_neutral(self):
        """Unparseable ISO string should return 0.5 (neutral)."""
        from hunter import HuntResult

        r = HuntResult(
            name="x",
            repo_url="u",
            stars=1,
            result_type="skill",
            trust_tier="raw",
            last_commit_date="not-a-date",
        )
        score = _compute_recency(r)
        assert score == 0.5

    def test_timezone_aware_date_is_handled(self):
        """Timezone-aware datetime objects should be stripped and scored."""
        from hunter import HuntResult

        recent = datetime.now(timezone.utc) - timedelta(days=5)
        r = HuntResult(
            name="x",
            repo_url="u",
            stars=1,
            result_type="skill",
            trust_tier="raw",
            last_commit_date=recent,
        )
        score = _compute_recency(r)
        assert score > 0.9  # very recent → near 1.0

    def test_none_date_returns_neutral(self):
        """None last_commit_date should return 0.5."""
        from hunter import HuntResult

        r = HuntResult(
            name="x",
            repo_url="u",
            stars=1,
            result_type="skill",
            trust_tier="raw",
            last_commit_date=None,
        )
        score = _compute_recency(r)
        assert score == 0.5

    def test_very_old_date_returns_zero(self):
        """Date 180+ days old should return 0.0."""
        from hunter import HuntResult

        r = HuntResult(
            name="x",
            repo_url="u",
            stars=1,
            result_type="skill",
            trust_tier="raw",
            last_commit_date=datetime.now() - timedelta(days=200),
        )
        score = _compute_recency(r)
        assert score == 0.0


# ---------------------------------------------------------------------------
# _compute_yagni edge cases (simplified for v1.0.0-alpha — git activity only)
# ---------------------------------------------------------------------------


class TestComputeYagni:
    def test_active_domain_match_returns_high_multiplier(self):
        """Skill matching active git domain should get 2.0× multiplier."""
        profile = make_profile(
            active_domains=["fastapi"],
            recent_domains=[],
            dormant_domains=[],
        )
        r = make_result(
            name="fastapi-helper",
            repo_name="fastapi-helper",
        )
        mult = _compute_yagni(r, profile)
        assert mult == YAGNI_MULTIPLIERS["active"]

    def test_recent_domain_match_returns_neutral_multiplier(self):
        """Skill matching recent git domain should get 1.0× multiplier."""
        profile = make_profile(
            active_domains=[],
            recent_domains=["postgres"],
            dormant_domains=[],
        )
        r = make_result(
            name="postgres-helper",
            repo_name="postgres-helper",
        )
        mult = _compute_yagni(r, profile)
        assert mult == YAGNI_MULTIPLIERS["recent"]

    def test_dormant_domain_match_returns_low_multiplier(self):
        """Skill matching dormant git domain should get 0.5× multiplier."""
        profile = make_profile(
            active_domains=[],
            recent_domains=[],
            dormant_domains=["rust"],
        )
        r = make_result(
            name="rust-helper",
            repo_name="rust-helper",
        )
        mult = _compute_yagni(r, profile)
        assert mult == YAGNI_MULTIPLIERS["dormant"]

    def test_no_domain_match_returns_unknown_multiplier(self):
        """Skill with no domain match should get unknown multiplier (1.0×)."""
        profile = make_profile(
            active_domains=["fastapi"],
            recent_domains=["postgres"],
            dormant_domains=["rust"],
        )
        r = make_result(
            name="golang-helper",
            repo_name="golang-helper",
        )
        mult = _compute_yagni(r, profile)
        assert mult == YAGNI_MULTIPLIERS["unknown"]


# ---------------------------------------------------------------------------
# Config-based weights
# ---------------------------------------------------------------------------


class TestConfigBasedWeights:
    """Config dict passed to score_results overrides default WEIGHTS."""

    def test_custom_weights_via_config(self):
        """When config dict with scoring.weights is passed, it overrides WEIGHTS."""
        custom_config = {
            "scoring": {
                "weights": {
                    "stack_match": 0.50,
                    "star_score": 0.10,
                    "recency_score": 0.10,
                    "trust_score": 0.30,
                }
            }
        }
        r = make_result(stars=100)
        profile = make_profile()
        results = score_results([r], profile, config=custom_config)
        assert len(results) == 1
        assert 0.0 <= results[0].total_score <= 1.0

    def test_config_without_weights_falls_back_to_defaults(self):
        """Config without scoring.weights key → use module WEIGHTS."""
        config_no_weights = {"some_other_key": "value"}
        r = make_result(stars=100)
        profile = make_profile()
        results = score_results([r], profile, config=config_no_weights)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Trusted Publishers
# ---------------------------------------------------------------------------


class TestTrustedPublishers:
    """Tests for trusted publisher boost feature."""

    def test_trusted_publisher_boost_applied(self):
        """Skills from trusted publishers should get trust score boost."""
        import os
        from pathlib import Path

        # Set env var to use test fixture
        fixture_path = Path(__file__).parent / "fixtures" / "trusted_publishers_minimal.yaml"
        os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"] = str(fixture_path)

        # Clear cache to force reload
        from scorer import _TRUSTED_PUBLISHERS_CACHE
        import scorer as scorer_module
        scorer_module._TRUSTED_PUBLISHERS_CACHE = None

        try:
            profile = make_profile()
            # Create result with owner matching trusted publisher in test fixture
            trusted = make_result(
                owner="testpublisher",
                repo_url="https://github.com/testpublisher/test-skill",
                trust_tier="raw",  # Base tier is raw (0.4)
            )
            untrusted = make_result(
                owner="unknownpublisher",
                repo_url="https://github.com/unknownpublisher/test-skill",
                trust_tier="raw",
            )

            results = score_results([trusted, untrusted], profile)

            # Find the trusted publisher result
            trusted_result = next(r for r in results if r.hunt_result.owner == "testpublisher")
            untrusted_result = next(r for r in results if r.hunt_result.owner == "unknownpublisher")

            # Trusted publisher should have higher trust score
            # Base raw = 0.4, test fixture boost = 0.20 → 0.6
            assert trusted_result.trust_score > untrusted_result.trust_score
            assert trusted_result.trust_score >= 0.6  # 0.4 + 0.20
            assert trusted_result.trusted_publisher is not None
            assert trusted_result.trusted_publisher["handle"] == "testpublisher"
            assert untrusted_result.trusted_publisher is None

        finally:
            # Clean up env var and cache
            if "AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH" in os.environ:
                del os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"]
            scorer_module._TRUSTED_PUBLISHERS_CACHE = None

    def test_trusted_publisher_boost_caps_at_one(self):
        """Trust score should cap at 1.0 even with large boost."""
        import os
        from pathlib import Path

        fixture_path = Path(__file__).parent / "fixtures" / "trusted_publishers_minimal.yaml"
        os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"] = str(fixture_path)

        import scorer as scorer_module
        scorer_module._TRUSTED_PUBLISHERS_CACHE = None

        try:
            profile = make_profile()
            # Verified tier (1.0) + boost should still cap at 1.0
            verified_trusted = make_result(
                owner="testpublisher",
                repo_url="https://github.com/testpublisher/verified-skill",
                trust_tier="verified",  # Already at 1.0
            )

            results = score_results([verified_trusted], profile)
            assert results[0].trust_score == 1.0  # Capped at 1.0

        finally:
            if "AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH" in os.environ:
                del os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"]
            scorer_module._TRUSTED_PUBLISHERS_CACHE = None

    def test_malformed_yaml_handled_gracefully(self):
        """Malformed YAML should not crash, just return empty dict."""
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("not: valid: yaml: content")
            bad_path = f.name

        os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"] = bad_path

        import scorer as scorer_module
        scorer_module._TRUSTED_PUBLISHERS_CACHE = None

        try:
            profile = make_profile()
            r = make_result(owner="testpublisher")
            results = score_results([r], profile)

            # Should work without crashing
            assert len(results) == 1
            # No boost applied due to malformed YAML
            assert results[0].trusted_publisher is None

        finally:
            if "AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH" in os.environ:
                del os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"]
            scorer_module._TRUSTED_PUBLISHERS_CACHE = None
            os.unlink(bad_path)

    def test_missing_yaml_file_handled_gracefully(self):
        """Missing YAML file should not crash."""
        import os

        os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"] = "/nonexistent/path.yaml"

        import scorer as scorer_module
        scorer_module._TRUSTED_PUBLISHERS_CACHE = None

        try:
            profile = make_profile()
            r = make_result(owner="testpublisher")
            results = score_results([r], profile)

            # Should work without crashing
            assert len(results) == 1
            assert results[0].trusted_publisher is None

        finally:
            if "AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH" in os.environ:
                del os.environ["AGENT_HUNTER_TRUSTED_PUBLISHERS_PATH"]
            scorer_module._TRUSTED_PUBLISHERS_CACHE = None


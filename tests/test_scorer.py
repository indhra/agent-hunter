"""Tests for scorer.py."""

import sys
from datetime import datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scorer import score_results, WEIGHTS
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

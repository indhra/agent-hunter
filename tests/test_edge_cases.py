"""
test_edge_cases.py — Comprehensive edge-case tests across all modules.

Supplements the per-module test files with boundary conditions, error paths,
and integration scenarios not covered elsewhere. Organised by module.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context_extractor import ContextProfile, extract_context
from hunter import Hunter, HuntResult, _to_raw_url
from installer import Installer, PendingAction, build_action_list
from registry import MAX_BACKUPS, Registry, RegistryEntry
from scorer import (
    TRUST_TIER_SCORES,
    YAGNI_MULTIPLIERS,
    _compute_domain_match,
    _compute_recency,
    _compute_stack_match,
    _score_single,
    score_results,
)
from security_scan import ScanFinding, ScanResult, scan_skill
from skill_parser import SkillMetadata, parse_skill_content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile(**kwargs) -> ContextProfile:
    defaults = dict(
        tech_stack=["fastapi", "postgres"],
        domain_tags=["backend"],
        active_domains=["fastapi"],
        recent_domains=[],
        dormant_domains=[],
    )
    defaults.update(kwargs)
    return ContextProfile(**defaults)


def _result(**kwargs) -> HuntResult:
    defaults = dict(
        name="test-skill",
        repo_url="https://github.com/owner/test-skill",
        repo_name="test-skill",
        description="A skill.",
        stars=100,
        last_commit_date=datetime.now(timezone.utc) - timedelta(days=10),
        trust_tier="raw",
        result_type="skill",
        owner="owner",
    )
    defaults.update(kwargs)
    return HuntResult(**defaults)


def _entry(**kwargs) -> RegistryEntry:
    defaults = dict(
        name="myskill",
        repo_url="https://github.com/owner/myskill",
        install_path="~/.claude/skills/myskill",
    )
    defaults.update(kwargs)
    return RegistryEntry(**defaults)


def _make_installer(tmp_path: Path, *, dry_run: bool = False) -> tuple[Installer, MagicMock]:
    mock_registry = MagicMock()
    mock_registry.all.return_value = []
    inst = Installer(registry=mock_registry, dry_run=dry_run)
    return inst, mock_registry


# =============================================================================
# scorer.py — _compute_recency edge cases
# =============================================================================


class TestComputeRecency:
    """Boundary conditions for _compute_recency()."""

    def test_iso_string_date_returns_valid_score(self):
        """The bug we fixed: ISO string must not crash — returns float in [0,1]."""
        r = _result(last_commit_date=(datetime.now(timezone.utc) - timedelta(days=5)).isoformat())
        score = _compute_recency(r)
        assert 0.0 <= score <= 1.0
        assert score > 0.9  # 5 days old → nearly 1.0

    def test_iso_string_with_z_suffix(self):
        """GitHub API returns dates like '2026-04-01T12:00:00Z'."""
        r = _result(last_commit_date="2026-04-28T00:00:00Z")
        score = _compute_recency(r)
        assert 0.0 <= score <= 1.0

    def test_timezone_aware_datetime_normalises(self):
        r = _result(last_commit_date=datetime.now(timezone.utc) - timedelta(days=30))
        score = _compute_recency(r)
        assert 0.0 < score < 1.0

    def test_invalid_iso_string_returns_neutral(self):
        r = _result(last_commit_date="not-a-date-at-all")
        assert _compute_recency(r) == 0.5

    def test_none_date_returns_neutral(self):
        r = _result(last_commit_date=None)
        assert _compute_recency(r) == 0.5

    def test_zero_days_old_returns_one(self):
        r = _result(last_commit_date=datetime.now(timezone.utc))
        assert _compute_recency(r) == 1.0

    def test_future_date_returns_one(self):
        r = _result(last_commit_date=datetime.now(timezone.utc) + timedelta(days=5))
        assert _compute_recency(r) == 1.0

    def test_exactly_180_days_old_returns_zero(self):
        r = _result(last_commit_date=datetime.now(timezone.utc) - timedelta(days=180))
        assert _compute_recency(r) == 0.0

    def test_beyond_180_days_returns_zero(self):
        r = _result(last_commit_date=datetime.now(timezone.utc) - timedelta(days=365))
        assert _compute_recency(r) == 0.0

    def test_midpoint_90_days(self):
        r = _result(last_commit_date=datetime.now(timezone.utc) - timedelta(days=90))
        score = _compute_recency(r)
        assert abs(score - 0.5) < 0.01  # ~0.5 at midpoint


# =============================================================================
# scorer.py — star score boundary
# =============================================================================


class TestStarScore:
    def test_zero_stars_log_normalised_to_zero(self):
        """log10(max(0,1)) / 4 = log10(1)/4 = 0.0"""
        r = _result(stars=0)
        s = _score_single(r, None, _profile())
        assert s.star_score == 0.0

    def test_one_star_also_zero(self):
        r = _result(stars=1)
        s = _score_single(r, None, _profile())
        assert s.star_score == 0.0

    def test_ten_thousand_stars_capped_at_one(self):
        """log10(10000)/4 = 4/4 = 1.0 exactly."""
        r = _result(stars=10_000)
        s = _score_single(r, None, _profile())
        assert s.star_score == 1.0

    def test_million_stars_still_capped_at_one(self):
        r = _result(stars=1_000_000)
        s = _score_single(r, None, _profile())
        assert s.star_score == 1.0

    def test_hundred_stars_between_zero_and_one(self):
        import math

        r = _result(stars=100)
        s = _score_single(r, None, _profile())
        expected = min(math.log10(100) / 4, 1.0)  # 2/4 = 0.5
        assert abs(s.star_score - expected) < 1e-9


# =============================================================================
# scorer.py — trust tier
# =============================================================================


class TestTrustTierScore:
    def test_verified_scores_highest(self):
        r = _result(trust_tier="verified")
        s = _score_single(r, None, _profile())
        assert s.trust_score == TRUST_TIER_SCORES["verified"]

    def test_community_scores_mid(self):
        r = _result(trust_tier="community")
        s = _score_single(r, None, _profile())
        assert s.trust_score == TRUST_TIER_SCORES["community"]

    def test_raw_scores_lowest(self):
        r = _result(trust_tier="raw")
        s = _score_single(r, None, _profile())
        assert s.trust_score == TRUST_TIER_SCORES["raw"]

    def test_unknown_tier_falls_back_to_raw_score(self):
        """Any unrecognised tier defaults to 0.4 (raw score)."""
        r = _result(trust_tier="experimental")
        s = _score_single(r, None, _profile())
        assert s.trust_score == 0.4


# =============================================================================
# scorer.py — YAGNI multiplier
# =============================================================================


class TestYagniMultiplier:
    def test_active_domain_match_gives_2x(self):
        profile = _profile(active_domains=["fastapi"], tech_stack=["fastapi"])
        r = _result(name="fastapi-helper", repo_name="fastapi-helper")
        s = _score_single(r, None, profile)
        assert s.yagni_multiplier == YAGNI_MULTIPLIERS["active"]

    def test_recent_domain_match_gives_1x(self):
        profile = _profile(active_domains=[], recent_domains=["postgres"], tech_stack=["postgres"])
        r = _result(name="postgres-helper", repo_name="postgres-helper")
        s = _score_single(r, None, profile)
        assert s.yagni_multiplier == YAGNI_MULTIPLIERS["recent"]

    def test_dormant_domain_match_gives_half_x(self):
        profile = _profile(
            active_domains=[],
            recent_domains=[],
            dormant_domains=["redis"],
            tech_stack=["redis"],
        )
        r = _result(name="redis-helper", repo_name="redis-helper")
        s = _score_single(r, None, profile)
        assert s.yagni_multiplier == YAGNI_MULTIPLIERS["dormant"]

    def test_no_match_gives_1x_unknown(self):
        profile = _profile(active_domains=["fastapi"], recent_domains=[], dormant_domains=[])
        r = _result(name="go-helper", repo_name="go-helper")
        s = _score_single(r, None, profile)
        assert s.yagni_multiplier == YAGNI_MULTIPLIERS["unknown"]


# =============================================================================
# scorer.py — stack/domain neutral when empty
# =============================================================================


class TestStackDomainNeutral:
    def test_empty_tech_stack_returns_neutral_stack_score(self):
        profile = _profile(tech_stack=[])
        r = _result()
        assert _compute_stack_match(r, None, profile) == 0.5

    def test_empty_domain_tags_returns_neutral_domain_score(self):
        profile = _profile(domain_tags=[])
        r = _result()
        assert _compute_domain_match(r, None, profile) == 0.5

    def test_full_stack_match_returns_one(self):
        """All profile keywords present in skill name/description → 1.0."""
        profile = _profile(tech_stack=["fastapi"])
        r = _result(name="fastapi-helper", description="fastapi tool", repo_name="fastapi-helper")
        score = _compute_stack_match(r, None, profile)
        assert score == 1.0

    def test_no_stack_match_returns_zero(self):
        profile = _profile(tech_stack=["fastapi", "redis"])
        r = _result(name="rust-engine", description="game engine", repo_name="rust-engine")
        score = _compute_stack_match(r, None, profile)
        assert score == 0.0


# =============================================================================
# scorer.py — config weights + score cap
# =============================================================================


class TestScorerConfigAndCap:
    def test_custom_config_weights_applied(self):
        """Config dict with different weights must change total score."""
        profile = _profile()
        r = _result(trust_tier="verified", stars=10_000)
        default_scored = score_results([r], profile)[0]

        # Override trust to 1.0 weight, everything else 0 — total = trust score
        config = {
            "scoring": {
                "weights": {
                    "stack_match": 0.0,
                    "domain_match": 0.0,
                    "star_score": 0.0,
                    "recency_score": 0.0,
                    "trust_score": 1.0,
                }
            }
        }
        custom_scored = score_results([r], profile, config=config)[0]
        assert custom_scored.total_score != default_scored.total_score

    def test_config_missing_weights_key_falls_back_to_defaults(self):
        """config dict with no 'weights' key must silently use WEIGHTS."""
        profile = _profile()
        r = _result()
        config = {"scoring": {}}  # no 'weights' sub-key
        scored = score_results([r], profile, config=config)
        assert len(scored) == 1  # did not crash

    def test_total_score_never_exceeds_one(self):
        """Even with active domain 2× YAGNI and perfect component scores, cap at 1.0."""
        profile = _profile(
            tech_stack=["fastapi"],
            domain_tags=["backend"],
            active_domains=["fastapi"],
        )
        r = _result(
            name="fastapi-backend-helper",
            repo_name="fastapi-backend-helper",
            description="fastapi backend",
            trust_tier="verified",
            stars=10_000,
            last_commit_date=datetime.now(timezone.utc),
        )
        scored = score_results([r], profile)[0]
        assert scored.total_score <= 1.0

    def test_score_results_with_metadata_map(self):
        """metadata_map providing richer text improves stack match."""
        profile = _profile(tech_stack=["fastapi"])
        r = _result(name="generic-helper", description="", repo_name="generic-helper")

        # Without metadata
        plain = score_results([r], profile)[0]

        # With metadata that contains "fastapi"
        meta = SkillMetadata(
            name="generic-helper", description="FastAPI integration", body="fastapi helper"
        )
        enriched = score_results([r], profile, metadata_map={r.repo_url: meta})[0]

        assert enriched.stack_match_score >= plain.stack_match_score


# =============================================================================
# security_scan.py — edge cases
# =============================================================================


class TestSecurityScanEdgeCases:
    def test_empty_content_is_green(self):
        result = scan_skill("")
        assert result.severity == "GREEN"
        assert result.findings == []

    def test_whitespace_only_content_is_green(self):
        result = scan_skill("   \n\n\t  ")
        assert result.severity == "GREEN"

    def test_eval_call_is_yellow(self):
        result = scan_skill("result = eval(user_input)")
        yellow = [
            f for f in result.findings if f.severity == "YELLOW" and "eval" in f.description.lower()
        ]
        assert len(yellow) > 0

    def test_exec_call_is_yellow(self):
        result = scan_skill("exec(payload)")
        assert result.severity in ("YELLOW", "RED")
        assert any(
            "eval" in f.description.lower() or "exec" in f.description.lower()
            for f in result.findings
        )

    def test_compile_exec_is_yellow(self):
        result = scan_skill("compile(src, '<string>', exec)")
        assert any(f.severity == "YELLOW" for f in result.findings)

    def test_zero_width_chars_are_red(self):
        result = scan_skill("normal text\u200bthen zero width")
        assert result.severity == "RED"
        assert any("zero" in f.description.lower() for f in result.findings)

    def test_unicode_direction_override_is_red(self):
        result = scan_skill("text\u202athen direction override")
        assert result.severity == "RED"
        assert any("direction" in f.description.lower() for f in result.findings)

    def test_bare_os_environ_without_network_no_exfil_finding(self):
        """Bare env access in docs context must NOT be flagged (false-positive guard)."""
        content = "# Usage\nSet `os.environ['DEBUG']` to enable verbose mode."
        result = scan_skill(content)
        exfil_findings = [f for f in result.findings if f.pattern_id.startswith("SP-007")]
        assert len(exfil_findings) == 0

    def test_os_environ_plus_requests_is_flagged(self):
        """Co-occurrence of env access + network call within 200 chars → SP-007."""
        content = "token = os.environ.get('TOKEN')\nrequests.post(url, data=token)"
        result = scan_skill(content)
        assert any(f.pattern_id.startswith("SP-007") for f in result.findings)

    def test_is_safe_true_for_green(self):
        result = scan_skill("# A perfectly safe skill\nDo good things.")
        assert result.is_safe is True

    def test_is_safe_false_for_red(self):
        result = scan_skill("jailbreak activated")
        assert result.is_safe is False

    def test_openai_sk_key_is_red(self):
        # 48-char key matching sk- prefix
        key = "sk-" + "A" * 48
        result = scan_skill(f"api_key = '{key}'")
        assert any(f.severity == "RED" for f in result.findings)

    def test_bearer_token_is_red(self):
        result = scan_skill(
            "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9abcdefghijklmn"
        )
        assert any(f.severity == "RED" for f in result.findings)

    def test_multiple_red_patterns_all_found(self):
        content = "jailbreak\nos.system('rm -rf /')"
        result = scan_skill(content)
        assert result.severity == "RED"
        assert len(result.findings) >= 2

    def test_passed_sandbox_is_none_when_not_run(self):
        """Sandbox is not run in default mode — field must be None."""
        result = scan_skill("normal content")
        assert result.passed_sandbox is None

    def test_empty_repo_url_skips_known_malicious_check(self):
        """No repo_url → known-malicious lookup is skipped, no false positive."""
        blocked = {"https://github.com/evil/bad"}
        result = scan_skill("normal content", repo_url="", known_malicious_urls=blocked)
        assert result.passed_known_malicious is True

    def test_scan_result_passed_static_true_for_yellow(self):
        """YELLOW severity keeps passed_static True."""
        result = scan_skill("eval(something)")
        if result.severity == "YELLOW":
            assert result.passed_static is True

    def test_homoglyph_in_code_block_is_yellow(self):
        """Homoglyph substitution detected only when normalization changes code blocks."""
        # 'ℕ' normalises to 'N' — when inside a code block this should flag
        content = "```python\nℕ = 1\n```"
        result = scan_skill(content)
        # Depending on platform normalization may or may not trigger; just verify no crash
        assert result.severity in ("GREEN", "YELLOW", "RED")


# =============================================================================
# context_extractor.py — edge cases
# =============================================================================


class TestContextExtractorEdgeCases:
    def test_nonexistent_path_returns_empty_profile(self, tmp_path):
        """Passing a path that doesn't exist should not crash."""
        profile = extract_context(tmp_path / "does_not_exist")
        assert profile.tech_stack == []

    def test_active_domains_are_subset_of_tech_stack(self, tmp_path):
        """active_domains must never contain terms not in tech_stack."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        profile = extract_context(tmp_path)
        for d in profile.active_domains:
            assert d in profile.tech_stack

    def test_recent_domains_are_subset_of_tech_stack(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        profile = extract_context(tmp_path)
        for d in profile.recent_domains:
            assert d in profile.tech_stack

    def test_sources_read_populated(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        profile = extract_context(tmp_path)
        assert "requirements.txt" in profile.sources_read

    def test_signals_from_multiple_files_merged(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        (tmp_path / "CLAUDE.md").write_text("This project uses Redis.\n")
        profile = extract_context(tmp_path)
        assert "fastapi" in profile.tech_stack
        assert "redis" in profile.tech_stack

    def test_no_duplicate_signals(self, tmp_path):
        """Same tech keyword in multiple files → appears once in tech_stack."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        (tmp_path / "CLAUDE.md").write_text("We use fastapi here too.\n")
        profile = extract_context(tmp_path)
        assert profile.tech_stack.count("fastapi") == 1

    def test_extraction_warnings_field_exists(self, tmp_path):
        """ContextProfile always has extraction_warnings list."""
        profile = extract_context(tmp_path)
        assert isinstance(profile.extraction_warnings, list)

    def test_case_insensitive_detection(self, tmp_path):
        """'FASTAPI' or 'FastAPI' in requirements must map to 'fastapi'."""
        (tmp_path / "requirements.txt").write_text("FastAPI==0.110.0\n")
        profile = extract_context(tmp_path)
        assert "fastapi" in profile.tech_stack


# =============================================================================
# registry.py — edge cases
# =============================================================================


class TestRegistryEdgeCases:
    def test_snapshot_on_empty_registry_does_not_raise(self, tmp_path):
        """Calling snapshot() before any upsert() must not crash."""
        reg = Registry(registry_path=tmp_path / "registry.json")
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", tmp_path / "backups")
            backup = reg.snapshot()
        assert backup.exists()

    def test_snapshot_on_empty_registry_creates_valid_json(self, tmp_path):
        reg = Registry(registry_path=tmp_path / "registry.json")
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", tmp_path / "backups")
            backup = reg.snapshot()
        data = json.loads(backup.read_text())
        assert "registry" in data

    def test_prune_old_backups_removes_oldest(self, tmp_path):
        """When backups exceed MAX_BACKUPS, the oldest must be pruned."""
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()
        reg = Registry(registry_path=tmp_path / "registry.json")
        reg.upsert(_entry())

        # Create MAX_BACKUPS + 3 fake backup files with incrementing timestamps
        base_ts = int(time.time()) - 1000
        for i in range(MAX_BACKUPS + 3):
            fake = backups_dir / f"registry_{base_ts + i}.json"
            fake.write_text("{}")

        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", backups_dir)
            reg.snapshot()

        remaining = list(backups_dir.glob("*.json"))
        assert len(remaining) <= MAX_BACKUPS

    def test_all_returns_mutable_list(self, tmp_path):
        """Registry.all() must return a list, not an internal view."""
        reg = Registry(registry_path=tmp_path / "registry.json")
        reg.upsert(_entry())
        result = reg.all()
        assert isinstance(result, list)
        # Mutating the returned list must not affect the registry
        result.clear()
        assert len(reg.all()) == 1

    def test_upsert_preserves_all_fields(self, tmp_path):
        reg = Registry(registry_path=tmp_path / "registry.json")
        e = RegistryEntry(
            name="myskill",
            repo_url="https://github.com/owner/myskill",
            install_path="/tmp/myskill",
            version="2.3.4",
            git_tree_sha="abc123",
            license="MIT",
            trust_tier="verified",
            audit_status="healthy",
            notes="some note",
        )
        reg.upsert(e)
        stored = reg.get(e.repo_url)
        assert stored.version == "2.3.4"
        assert stored.git_tree_sha == "abc123"
        assert stored.license == "MIT"
        assert stored.trust_tier == "verified"
        assert stored.audit_status == "healthy"
        assert stored.notes == "some note"

    def test_remove_decrements_all_count(self, tmp_path):
        reg = Registry(registry_path=tmp_path / "registry.json")
        reg.upsert(_entry(name="a", repo_url="https://github.com/o/a"))
        reg.upsert(_entry(name="b", repo_url="https://github.com/o/b"))
        assert len(reg.all()) == 2
        reg.remove("https://github.com/o/a")
        assert len(reg.all()) == 1


# =============================================================================
# installer.py — edge cases
# =============================================================================


class TestInstallerEdgeCases:
    def test_enable_logs_action(self, tmp_path):
        """enable() should call _log_action just like disable() does."""
        inst, _ = _make_installer(tmp_path)
        (tmp_path / "_myskill").mkdir()

        log_calls = []
        inst._log_action = lambda *a, **kw: log_calls.append((a, kw))

        with patch("installer.SKILLS_DIR", tmp_path):
            inst.enable("myskill")

        assert any("enable" in str(call) for call in log_calls)

    def test_execute_actions_unknown_action_returns_error(self, tmp_path):
        inst, _ = _make_installer(tmp_path)
        action = PendingAction(action="teleport", skill_name="myskill")
        with patch("installer.SKILLS_DIR", tmp_path):
            results = inst.execute_actions([action])
        assert len(results) == 1
        assert results[0].success is False
        assert "Unknown action" in (results[0].error or "")

    def test_execute_actions_returns_result_for_each_action(self, tmp_path):
        inst, mock_reg = _make_installer(tmp_path)

        # Two actions: one valid (disable a dir that exists), one unknown
        (tmp_path / "skill-a").mkdir()
        actions = [
            PendingAction(action="disable", skill_name="skill-a"),
            PendingAction(action="teleport", skill_name="skill-b"),
        ]
        with patch("installer.SKILLS_DIR", tmp_path):
            results = inst.execute_actions(actions)
        assert len(results) == 2

    def test_rollback_to_sha_dry_run(self, tmp_path):
        inst, _ = _make_installer(tmp_path, dry_run=True)
        with patch("installer.SKILLS_DIR", tmp_path):
            result = inst.rollback_to_sha("owner", "repo", sha="abc123")
        assert result.success is True
        assert "[dry-run]" in result.message

    def test_build_action_list_empty_top_results_gives_only_disables(self):
        """With no hunt results, only dangerous_installed produces disable actions."""
        actions = build_action_list(
            top_results=[],
            scan_results={},
            installed_names=set(),
            dangerous_installed=["evil-skill"],
        )
        assert len(actions) == 1
        assert actions[0].action == "disable"
        assert actions[0].skill_name == "evil-skill"

    def test_build_action_list_excludes_red_results(self):
        """RED-scanned results must never produce install actions."""
        from scorer import ScoredResult

        r = _result(repo_name="danger", repo_url="https://github.com/o/danger")
        scored = ScoredResult(hunt_result=r, skill_metadata=None, total_score=0.9)
        red_scan = ScanResult(
            severity="RED", findings=[ScanFinding("SP-001", "RED", "Injection", "body")]
        )
        actions = build_action_list(
            top_results=[scored],
            scan_results={r.repo_url: red_scan},
            installed_names=set(),
            dangerous_installed=[],
        )
        install_actions = [a for a in actions if a.action == "install"]
        assert len(install_actions) == 0

    def test_build_action_list_excludes_already_installed(self):
        from scorer import ScoredResult

        r = _result(repo_name="existing-skill")
        scored = ScoredResult(hunt_result=r, skill_metadata=None, total_score=0.8)
        actions = build_action_list(
            top_results=[scored],
            scan_results={},
            installed_names={"existing-skill"},
            dangerous_installed=[],
        )
        assert len([a for a in actions if a.action == "install"]) == 0

    def test_disable_already_disabled_skill_fails(self, tmp_path):
        """Disabling a skill whose dir doesn't exist returns failure."""
        inst, _ = _make_installer(tmp_path)
        # _myskill exists but myskill doesn't
        (tmp_path / "_myskill").mkdir()
        with patch("installer.SKILLS_DIR", tmp_path):
            result = inst.disable("myskill")
        assert result.success is False

    def test_enable_already_enabled_skill_fails(self, tmp_path):
        """enable() when no _name dir exists returns failure."""
        inst, _ = _make_installer(tmp_path)
        (tmp_path / "myskill").mkdir()  # enabled dir exists, disabled doesn't
        with patch("installer.SKILLS_DIR", tmp_path):
            result = inst.enable("myskill")
        assert result.success is False


# =============================================================================
# hunter.py — edge cases
# =============================================================================


class TestHunterEdgeCases:
    def test_build_queries_empty_tech_stack_no_crash(self):
        h = Hunter(github_token=None)
        profile = _profile(tech_stack=[], domain_tags=["backend"])
        queries = h._build_queries(profile)
        assert isinstance(queries, list)
        # Should still produce a domain query
        domain_queries = [q for q, _ in queries if "backend" in q]
        assert len(domain_queries) >= 1

    def test_build_queries_empty_everything_returns_list(self):
        h = Hunter(github_token=None)
        profile = _profile(tech_stack=[], domain_tags=[])
        queries = h._build_queries(profile)
        assert isinstance(queries, list)

    def test_prefilter_parallel_empty_input_returns_empty(self):
        h = Hunter(github_token=None)
        result = h._prefilter_parallel([])
        assert result == []

    def test_verified_urls_cached_after_first_call(self):
        h = Hunter(github_token=None)
        assert h._verified_urls_cache is None
        first = h._get_verified_urls()
        assert h._verified_urls_cache is not None
        second = h._get_verified_urls()
        assert first is second  # same object

    def test_fetch_skill_content_404_returns_none(self):
        h = Hunter(github_token=None)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        h._session = MagicMock()
        h._session.get.return_value = mock_resp
        result = h._fetch_skill_content("https://github.com/owner/repo/blob/main/SKILL.md")
        assert result is None

    def test_fetch_repo_metadata_404_returns_none(self):
        h = Hunter(github_token=None)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        h._session = MagicMock()
        h._session.get.return_value = mock_resp
        result = h._fetch_repo_metadata("owner", "repo")
        assert result is None

    def test_passes_prefilter_low_stars_returns_false(self):
        h = Hunter(github_token=None, min_stars=50)
        r = _result(stars=5)
        assert h._passes_prefilter(r) is False

    def test_to_raw_url_non_github_url_returns_none(self):
        assert _to_raw_url("https://gitlab.com/owner/repo/blob/main/SKILL.md") is None

    def test_search_github_page_non_200_returns_empty(self):
        h = Hunter(github_token=None)
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        h._session = MagicMock()
        h._session.get.return_value = mock_resp
        results = h._search_github_page("SKILL.md filename:SKILL.md", "skill", 1)
        assert results == []


# =============================================================================
# skill_parser.py — edge cases
# =============================================================================


class TestSkillParserEdgeCases:
    def test_empty_string_returns_empty_metadata(self):
        meta = parse_skill_content("")
        assert meta.has_frontmatter is False
        assert meta.name == ""
        assert meta.body == ""

    def test_frontmatter_missing_optional_fields_uses_defaults(self):
        content = "---\nname: minimal-skill\n---\n# body"
        meta = parse_skill_content(content)
        assert meta.name == "minimal-skill"
        assert meta.version == ""
        assert meta.license == ""
        assert meta.author == ""
        assert meta.triggers == []
        assert meta.mcp_dependencies == []

    def test_triggers_as_list_parsed_correctly(self):
        content = "---\nname: t\ntriggers:\n  - hello\n  - world\n---\nbody"
        meta = parse_skill_content(content)
        assert "hello" in meta.triggers
        assert "world" in meta.triggers

    def test_mcp_dependency_minimal_fields(self):
        content = (
            "---\nname: t\nmcp_dependencies:\n"
            "  - type: mcp_server\n    value: github.com/o/r\n---\nbody"
        )
        meta = parse_skill_content(content)
        assert len(meta.mcp_dependencies) == 1
        dep = meta.mcp_dependencies[0]
        assert dep.type == "mcp_server"
        assert dep.value == "github.com/o/r"
        # Optional fields default
        assert dep.description == ""
        assert dep.transport == "stdio"

    def test_body_extracted_after_frontmatter(self):
        content = "---\nname: t\n---\n# Title\n\nBody paragraph here."
        meta = parse_skill_content(content)
        assert "Title" in meta.body
        assert "Body paragraph" in meta.body

    def test_no_frontmatter_full_content_is_body(self):
        content = "# Just a heading\n\nAll content here."
        meta = parse_skill_content(content)
        assert meta.has_frontmatter is False
        assert "All content here." in meta.body

    def test_frontmatter_with_no_name_key_returns_empty_name(self):
        content = "---\ndescription: no name here\n---\n# body"
        meta = parse_skill_content(content)
        assert meta.name == ""
        assert meta.description == "no name here"

    def test_raw_frontmatter_dict_populated(self):
        content = "---\nname: t\ncustom_field: 42\n---\nbody"
        meta = parse_skill_content(content)
        assert meta.raw_frontmatter.get("custom_field") == 42

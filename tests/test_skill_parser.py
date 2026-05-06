"""Tests for skill_parser.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skill_parser import (
    parse_skill_content,
    resolve_skill_dependencies,
    SkillDependency,
    SkillParseError,
    TRUST_TIER_ORDER,
)


VALID_SKILL = """\
---
name: "test-skill"
description: "A test skill."
version: "1.0.0"
license: "MIT"
author: "test-author"
compatibility:
  claude: ">=1.0.0"
triggers:
  - "help me test"
mcp_dependencies:
  - type: mcp_server
    value: "github.com/owner/mcp"
    description: "Test MCP"
    transport: stdio
skill_dependencies:
  - name: "skill-audit"
    repo: "pors/skill-audit"
    role: "security_scan_delegate"
    min_trust_tier: "community"
    optional: true
    fallback: "built_in_scanner"
  - name: "skill-scanner"
    repo: "cisco-ai-defense/skill-scanner"
    role: "secondary_scanner"
    min_trust_tier: "verified"
    optional: false
    fallback: "none"
---

# test-skill

This is the body.
"""

NO_FRONTMATTER = "# Just a heading\n\nBody text without frontmatter."

MALFORMED_YAML = "---\nname: [unclosed bracket\n---\n# body"

MINIMAL_FRONTMATTER = "---\nname: minimal\n---\n# body"


class TestParsing:
    def test_valid_skill_name(self):
        meta = parse_skill_content(VALID_SKILL)
        assert meta.name == "test-skill"

    def test_valid_skill_version(self):
        meta = parse_skill_content(VALID_SKILL)
        assert meta.version == "1.0.0"

    def test_valid_skill_triggers(self):
        meta = parse_skill_content(VALID_SKILL)
        assert "help me test" in meta.triggers

    def test_valid_skill_mcp_dependency(self):
        meta = parse_skill_content(VALID_SKILL)
        assert len(meta.mcp_dependencies) == 1
        assert meta.mcp_dependencies[0].value == "github.com/owner/mcp"

    def test_valid_skill_body(self):
        meta = parse_skill_content(VALID_SKILL)
        assert "body" in meta.body.lower()

    def test_no_frontmatter_returns_body(self):
        meta = parse_skill_content(NO_FRONTMATTER)
        assert meta.has_frontmatter is False
        assert "Body text" in meta.body

    def test_no_frontmatter_empty_name(self):
        meta = parse_skill_content(NO_FRONTMATTER)
        assert meta.name == ""

    def test_malformed_yaml_raises(self):
        with pytest.raises(SkillParseError):
            parse_skill_content(MALFORMED_YAML)

    def test_minimal_frontmatter_no_error(self):
        meta = parse_skill_content(MINIMAL_FRONTMATTER)
        assert meta.name == "minimal"
        assert meta.version == ""
        assert meta.license == ""

    def test_has_frontmatter_flag(self):
        meta = parse_skill_content(VALID_SKILL)
        assert meta.has_frontmatter is True

    def test_fixtures_clean_skill_parseable(self):
        fixtures = Path(__file__).parent / "fixtures" / "clean_skill.md"
        content = fixtures.read_text()
        meta = parse_skill_content(content)
        assert meta.has_frontmatter is True
        assert meta.name != ""


# ---------------------------------------------------------------------------
# Skill dependency parsing
# ---------------------------------------------------------------------------


class TestSkillDependencyParsing:
    def test_skill_dependencies_parsed(self):
        meta = parse_skill_content(VALID_SKILL)
        assert len(meta.skill_dependencies) == 2

    def test_first_dep_fields(self):
        meta = parse_skill_content(VALID_SKILL)
        dep = meta.skill_dependencies[0]
        assert dep.name == "skill-audit"
        assert dep.repo == "pors/skill-audit"
        assert dep.role == "security_scan_delegate"
        assert dep.min_trust_tier == "community"
        assert dep.optional is True
        assert dep.fallback == "built_in_scanner"

    def test_second_dep_fields(self):
        meta = parse_skill_content(VALID_SKILL)
        dep = meta.skill_dependencies[1]
        assert dep.name == "skill-scanner"
        assert dep.repo == "cisco-ai-defense/skill-scanner"
        assert dep.role == "secondary_scanner"
        assert dep.min_trust_tier == "verified"
        assert dep.optional is False
        assert dep.fallback == "none"

    def test_no_skill_dependencies_empty_list(self):
        minimal = "---\nname: minimal\n---\n# body"
        meta = parse_skill_content(minimal)
        assert meta.skill_dependencies == []

    def test_dep_missing_role_skipped(self):
        # A dep without 'role' should be silently skipped
        content = """\
---
name: x
skill_dependencies:
  - name: "orphan"
    repo: "owner/orphan"
---
# body
"""
        meta = parse_skill_content(content)
        assert meta.skill_dependencies == []

    def test_dep_missing_name_skipped(self):
        content = """\
---
name: x
skill_dependencies:
  - role: "some_role"
    repo: "owner/thing"
---
# body
"""
        meta = parse_skill_content(content)
        assert meta.skill_dependencies == []

    def test_trust_tier_order_constants(self):
        assert TRUST_TIER_ORDER["verified"] > TRUST_TIER_ORDER["community"]
        assert TRUST_TIER_ORDER["community"] > TRUST_TIER_ORDER["raw"]


# ---------------------------------------------------------------------------
# Skill dependency resolver
# ---------------------------------------------------------------------------

VERIFIED_MD = """\
# Verified Skills

### skill-audit
- **Repo:** https://github.com/pors/skill-audit
- **Version reviewed:** v1.0.0
"""

SKILL_DEP_DELEGATE = SkillDependency(
    name="skill-audit",
    repo="pors/skill-audit",
    role="security_scan_delegate",
    min_trust_tier="community",
    optional=True,
    fallback="built_in_scanner",
)

SKILL_DEP_SCANNER = SkillDependency(
    name="skill-scanner",
    repo="cisco-ai-defense/skill-scanner",
    role="secondary_scanner",
    min_trust_tier="verified",
    optional=True,
    fallback="none",
)


class TestResolveSkillDependencies:
    def test_not_installed_returns_not_installed(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        results = resolve_skill_dependencies([SKILL_DEP_DELEGATE], skills_dir=skills_dir)
        r = results["security_scan_delegate"]
        assert r.status == "not_installed"
        assert r.use_fallback is True
        assert r.skill_path is None

    def test_installed_raw_meets_community_gate(self, tmp_path):
        # community gate requires tier >= 2; raw=1 — should fail
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-audit").mkdir(parents=True)
        verified_md = tmp_path / "VERIFIED_SKILLS.md"
        verified_md.write_text("")  # no verified entries

        results = resolve_skill_dependencies(
            [SKILL_DEP_DELEGATE],
            skills_dir=skills_dir,
            verified_skills_path=verified_md,
        )
        r = results["security_scan_delegate"]
        # min_trust_tier="community" (2) but actual="raw" (1) → trust_insufficient
        assert r.status == "trust_insufficient"
        assert r.trust_tier == "raw"
        assert r.use_fallback is True

    def test_installed_verified_satisfies_community_gate(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-audit").mkdir(parents=True)
        verified_md = tmp_path / "VERIFIED_SKILLS.md"
        verified_md.write_text(VERIFIED_MD)

        results = resolve_skill_dependencies(
            [SKILL_DEP_DELEGATE],
            skills_dir=skills_dir,
            verified_skills_path=verified_md,
        )
        r = results["security_scan_delegate"]
        assert r.status == "satisfied"
        assert r.trust_tier == "verified"
        assert r.use_fallback is False
        assert r.skill_path is not None

    def test_disabled_skill_returns_disabled(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "_skill-audit").mkdir(parents=True)
        verified_md = tmp_path / "VERIFIED_SKILLS.md"
        verified_md.write_text(VERIFIED_MD)

        results = resolve_skill_dependencies(
            [SKILL_DEP_DELEGATE],
            skills_dir=skills_dir,
            verified_skills_path=verified_md,
        )
        r = results["security_scan_delegate"]
        assert r.status == "disabled"
        assert r.use_fallback is True

    def test_repo_basename_match(self, tmp_path):
        # Install as repo basename (cisco-ai-defense/skill-scanner → skill-scanner dir)
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-scanner").mkdir(parents=True)
        verified_md = tmp_path / "VERIFIED_SKILLS.md"
        verified_md.write_text("- **Repo:** https://github.com/cisco-ai-defense/skill-scanner\n")

        results = resolve_skill_dependencies(
            [SKILL_DEP_SCANNER],
            skills_dir=skills_dir,
            verified_skills_path=verified_md,
        )
        r = results["secondary_scanner"]
        assert r.status == "satisfied"

    def test_skills_dir_missing_returns_not_installed(self, tmp_path):
        # skills_dir doesn't exist at all
        skills_dir = tmp_path / "nonexistent"
        results = resolve_skill_dependencies([SKILL_DEP_DELEGATE], skills_dir=skills_dir)
        r = results["security_scan_delegate"]
        assert r.status == "not_installed"

    def test_empty_dependencies_returns_empty(self, tmp_path):
        results = resolve_skill_dependencies([], skills_dir=tmp_path)
        assert results == {}

    def test_multiple_deps_keyed_by_role(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        results = resolve_skill_dependencies(
            [SKILL_DEP_DELEGATE, SKILL_DEP_SCANNER], skills_dir=skills_dir
        )
        assert "security_scan_delegate" in results
        assert "secondary_scanner" in results

    def test_verified_skills_file_missing_defaults_raw(self, tmp_path):
        skills_dir = tmp_path / "skills"
        (skills_dir / "skill-audit").mkdir(parents=True)
        missing_verified = tmp_path / "no_such_file.md"

        results = resolve_skill_dependencies(
            [SKILL_DEP_DELEGATE],
            skills_dir=skills_dir,
            verified_skills_path=missing_verified,
        )
        r = results["security_scan_delegate"]
        # No verified file → tier is raw → fails community gate
        assert r.trust_tier == "raw"

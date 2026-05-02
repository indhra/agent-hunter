"""Tests for skill_parser.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from skill_parser import parse_skill_content, SkillParseError


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

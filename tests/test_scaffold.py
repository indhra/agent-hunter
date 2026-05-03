"""
test_scaffold.py — Tests for scaffold.py.

Covers scaffold_skill(), _load_template(), _fill_template(), _slugify().
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scaffold import scaffold_skill, _load_template, _fill_template, _slugify  # noqa: E402
from context_extractor import ContextProfile  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(tech_stack=None, domain_tags=None) -> ContextProfile:
    p = ContextProfile()
    p.tech_stack = tech_stack if tech_stack is not None else ["fastapi", "python"]
    p.domain_tags = domain_tags if domain_tags is not None else ["backend", "python"]
    return p


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_simple_name(self):
        assert _slugify("my-skill") == "my-skill"

    def test_spaces_converted_to_dashes(self):
        assert _slugify("my skill") == "my-skill"

    def test_underscores_converted_to_dashes(self):
        assert _slugify("my_skill") == "my-skill"

    def test_uppercase_lowercased(self):
        assert _slugify("MySkill") == "myskill"

    def test_special_chars_stripped(self):
        assert _slugify("my!skill@#") == "myskill"

    def test_trailing_dashes_stripped(self):
        assert _slugify("-my-skill-") == "my-skill"


# ---------------------------------------------------------------------------
# _fill_template
# ---------------------------------------------------------------------------

class TestFillTemplate:
    def test_fills_skill_name(self):
        template = "name: {{skill_name}}"
        profile = _make_profile()
        result = _fill_template(template, name="my-skill", profile=profile, author="user")
        assert "my-skill" in result

    def test_fills_stack_signals(self):
        template = "stack: {{detected_stack}}"
        profile = _make_profile(tech_stack=["fastapi", "python"])
        result = _fill_template(template, name="x", profile=profile, author="")
        assert "fastapi" in result

    def test_fills_author(self):
        template = "author: {{author}}"
        profile = _make_profile()
        result = _fill_template(template, name="x", profile=profile, author="indhra")
        assert "indhra" in result

    def test_empty_stack_uses_fallback(self):
        template = "{{detected_stack}}"
        profile = _make_profile(tech_stack=[], domain_tags=[])
        result = _fill_template(template, name="x", profile=profile, author="")
        assert "your stack" in result

    def test_empty_domains_uses_fallback(self):
        template = "{{skill_description}}"
        profile = _make_profile(tech_stack=[], domain_tags=[])
        result = _fill_template(template, name="x", profile=profile, author="")
        assert "general" in result

    def test_trigger_uses_name(self):
        template = "{{primary_trigger}}"
        profile = _make_profile()
        result = _fill_template(template, name="my-skill", profile=profile, author="")
        assert "my skill" in result


# ---------------------------------------------------------------------------
# _load_template
# ---------------------------------------------------------------------------

class TestLoadTemplate:
    def test_loads_from_assets_if_exists(self, tmp_path):
        fake_template = "# Template content"
        with patch("scaffold.TEMPLATE_PATH", tmp_path / "template.md"):
            (tmp_path / "template.md").write_text(fake_template)
            result = _load_template()
        assert result == fake_template

    def test_fallback_minimal_template_when_missing(self, tmp_path):
        with patch("scaffold.TEMPLATE_PATH", tmp_path / "nonexistent.md"):
            result = _load_template()
        # Should return the MINIMAL_TEMPLATE string (not empty)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# scaffold_skill
# ---------------------------------------------------------------------------

class TestScaffoldSkill:
    def test_creates_file_at_default_path(self, tmp_path, capsys):
        profile = _make_profile()
        output = scaffold_skill(
            name="my-skill",
            output_path=tmp_path / "my-skill" / "SKILL.md",
            profile=profile,
        )
        assert output.exists()
        content = output.read_text()
        assert "my-skill" in content

    def test_extracts_context_when_no_profile(self, tmp_path, capsys):
        """When profile is None, scaffold_skill should call extract_context."""
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        output_path = tmp_path / "gen" / "SKILL.md"
        with patch("scaffold.extract_context", return_value=_make_profile()) as mock_ec:
            scaffold_skill(
                name="auto-skill",
                output_path=output_path,
                profile=None,
                project_root=str(tmp_path),
            )
        mock_ec.assert_called_once()

    def test_output_path_parent_created(self, tmp_path, capsys):
        """scaffold_skill should create the output directory if it doesn't exist."""
        profile = _make_profile()
        output_path = tmp_path / "deep" / "nested" / "SKILL.md"
        assert not output_path.parent.exists()
        scaffold_skill(name="deep-skill", output_path=output_path, profile=profile)
        assert output_path.exists()

    def test_author_included_in_output(self, tmp_path, capsys):
        profile = _make_profile()
        output_path = tmp_path / "SKILL.md"
        scaffold_skill(name="x", output_path=output_path, profile=profile, author="myhandle")
        content = output_path.read_text()
        assert "myhandle" in content

    def test_prints_next_steps(self, tmp_path, capsys):
        profile = _make_profile()
        output_path = tmp_path / "SKILL.md"
        scaffold_skill(name="x", output_path=output_path, profile=profile)
        out = capsys.readouterr().out
        assert "Next steps" in out
        assert "Scaffold created" in out

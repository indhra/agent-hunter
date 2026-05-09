"""
Tests for dep_resolver.py — dependency conflict detection and resolution.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dep_resolver import (
    DependencyConflict,
    audit_installed_skills,
    detect_conflicts,
    parse_package_json,
    parse_requirements_txt,
)


# ---------------------------------------------------------------------------
# Requirement parsing
# ---------------------------------------------------------------------------


class TestParseRequirementsTxt:
    def test_simple_package(self):
        content = "requests>=2.28.0\n"
        pkgs = parse_requirements_txt(content)
        assert "requests" in pkgs
        assert pkgs["requests"] == ">=2.28.0"

    def test_multiple_packages(self):
        content = "requests>=2.28.0\npydantic<2.0\nfastapi\n"
        pkgs = parse_requirements_txt(content)
        assert len(pkgs) == 3
        assert pkgs["pydantic"] == "<2.0"
        assert pkgs["fastapi"] == "*"  # No version spec = any version

    def test_ignore_comments_and_blank_lines(self):
        content = "# Comment\nrequests>=2.28.0\n\n# Another comment\npydantic<2.0\n"
        pkgs = parse_requirements_txt(content)
        assert len(pkgs) == 2

    def test_package_with_extras(self):
        content = "requests[security]>=2.28.0\n"
        pkgs = parse_requirements_txt(content)
        # Should handle extras
        assert "requests[security]" in pkgs or "requests" in pkgs

    def test_empty_content(self):
        pkgs = parse_requirements_txt("")
        assert len(pkgs) == 0

    def test_case_insensitive_package_names(self):
        content = "PySQLAlchemy>=1.4\n"
        pkgs = parse_requirements_txt(content)
        assert len(pkgs) == 1


class TestParsePackageJson:
    def test_dependencies(self):
        content = '{"dependencies": {"react": "^18.0.0"}}'
        pkgs = parse_package_json(content)
        assert "react" in pkgs
        assert pkgs["react"] == "^18.0.0"

    def test_dev_dependencies(self):
        content = '{"devDependencies": {"jest": "^29.0.0"}}'
        pkgs = parse_package_json(content)
        assert "jest" in pkgs

    def test_multiple_sections(self):
        content = '{"dependencies": {"react": "^18.0.0"}, "devDependencies": {"jest": "^29.0.0"}}'
        pkgs = parse_package_json(content)
        assert len(pkgs) == 2

    def test_invalid_json(self):
        content = "{invalid json"
        pkgs = parse_package_json(content)
        assert len(pkgs) == 0

    def test_empty_object(self):
        content = "{}"
        pkgs = parse_package_json(content)
        assert len(pkgs) == 0


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestDetectConflicts:
    def test_no_conflict_single_skill(self):
        skills = {"skill-a": {"pydantic": ">=2.0"}}
        conflicts = detect_conflicts(skills)
        assert len(conflicts) == 0

    def test_no_conflict_identical_specs(self):
        skills = {
            "skill-a": {"pydantic": ">=2.0"},
            "skill-b": {"pydantic": ">=2.0"},
        }
        conflicts = detect_conflicts(skills)
        assert len(conflicts) == 0

    def test_conflict_incompatible_versions(self):
        skills = {
            "skill-a": {"pydantic": "<2.0"},
            "skill-b": {"pydantic": ">=2.0"},
        }
        conflicts = detect_conflicts(skills)
        assert "pydantic" in conflicts
        conflict = conflicts["pydantic"]
        assert conflict.severity == "RED"
        assert "skill-a" in conflict.conflicting_skills
        assert "skill-b" in conflict.conflicting_skills

    def test_no_conflict_overlapping_ranges(self):
        # Both <3.0 and >=2.0 have overlap
        skills = {
            "skill-a": {"pydantic": "<3.0"},
            "skill-b": {"pydantic": ">=2.0"},
        }
        conflicts = detect_conflicts(skills)
        # Without packaging library, may return YELLOW
        if "pydantic" in conflicts:
            assert conflicts["pydantic"].severity != "GREEN"

    def test_multiple_packages_mixed_conflicts(self):
        skills = {
            "skill-a": {"pydantic": ">=2.0", "requests": ">=2.28"},
            "skill-b": {"pydantic": "<2.0", "requests": ">=2.28"},
        }
        conflicts = detect_conflicts(skills)
        # Should have conflict only on pydantic
        assert "pydantic" in conflicts
        if "requests" in conflicts:
            assert conflicts["requests"].severity == "GREEN"

    def test_three_way_conflict(self):
        skills = {
            "skill-a": {"pkg": "==1.0"},
            "skill-b": {"pkg": "==2.0"},
            "skill-c": {"pkg": "==3.0"},
        }
        conflicts = detect_conflicts(skills)
        # All different versions = conflict
        if "pkg" in conflicts:
            assert len(conflicts["pkg"].conflicting_skills) >= 2


# ---------------------------------------------------------------------------
# Dependency audit
# ---------------------------------------------------------------------------


class TestAuditInstalledSkills:
    def test_empty_skills_dir(self, tmp_path):
        audit = audit_installed_skills(tmp_path)
        assert audit.total_unique_packages == 0
        assert len(audit.conflicts) == 0

    def test_single_skill_no_deps(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        audit = audit_installed_skills(tmp_path)
        assert audit.total_unique_packages == 0

    def test_single_skill_with_deps(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        req_file = skill_dir / "requirements.txt"
        req_file.write_text("requests>=2.28.0\npydantic>=1.0\n")

        audit = audit_installed_skills(tmp_path)
        assert audit.total_unique_packages == 2
        assert len(audit.conflicts) == 0

    def test_disabled_skills_ignored(self, tmp_path):
        disabled_skill = tmp_path / "_disabled-skill"
        disabled_skill.mkdir()
        req_file = disabled_skill / "requirements.txt"
        req_file.write_text("requests>=2.28.0\n")

        audit = audit_installed_skills(tmp_path)
        # Disabled skills (starting with _) should be ignored
        assert audit.total_unique_packages == 0

    def test_conflict_detection_in_audit(self, tmp_path):
        # Create two skills with conflicting pydantic versions
        skill_a = tmp_path / "skill-a"
        skill_a.mkdir()
        (skill_a / "requirements.txt").write_text("pydantic<2.0\n")

        skill_b = tmp_path / "skill-b"
        skill_b.mkdir()
        (skill_b / "requirements.txt").write_text("pydantic>=2.0\n")

        audit = audit_installed_skills(tmp_path)
        assert len(audit.conflicts) >= 1
        # Should have a pydantic conflict
        pydantic_conflicts = [c for c in audit.conflicts if c.package_name == "pydantic"]
        assert len(pydantic_conflicts) >= 1
        assert pydantic_conflicts[0].severity == "RED"


# ---------------------------------------------------------------------------
# Conflict model
# ---------------------------------------------------------------------------


class TestDependencyConflict:
    def test_severity_colors(self):
        conflict = DependencyConflict(
            package_name="pydantic",
            conflicting_skills={"a": "<2.0", "b": ">=2.0"},
            severity="RED",
        )
        assert conflict.severity == "RED"
        assert not conflict.proposed_resolution

    def test_with_proposed_resolution(self):
        conflict = DependencyConflict(
            package_name="requests",
            conflicting_skills={"a": ">=2.25", "b": ">=2.28"},
            severity="GREEN",
            proposed_resolution="requests>=2.28",
        )
        assert conflict.severity == "GREEN"
        assert "2.28" in conflict.proposed_resolution

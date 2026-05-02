"""Tests for context_extractor.py."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context_extractor import extract_context, TECH_ALLOWLIST


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

    def test_extracts_from_claude_md(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("This project uses FastAPI and Redis.\n")
        profile = extract_context(tmp_path)
        assert "fastapi" in profile.tech_stack
        assert "redis" in profile.tech_stack

    def test_allowlist_only_signals(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text(
            "The variable mySecretProjectName uses fastapi and some_private_function.\n"
        )
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

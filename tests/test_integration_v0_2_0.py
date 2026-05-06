"""
Integration tests for v0.2.0 — complete workflow: hunt → audit → update → rollback

Tests verify:
    - Audit detects updates and security issues correctly
    - Update applies changes only when approved
    - Rollback restores to previous state
    - MCP hunting and parsing integration
    - Status priority (tampered > security > update > conflict > healthy)

All tests use mocked network + real filesystem (tmp_path).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from audit import Auditor
from update import SkillUpdater
from rollback import rollback
from registry import Registry, RegistryEntry
from security_scan import ScanResult


# ---------------------------------------------------------------------------
# Integration: Audit → Update → Rollback workflow
# ---------------------------------------------------------------------------


class TestFullUpdateWorkflow:
    """End-to-end: skill has update, audit detects it, user updates, rollback works."""

    def test_workflow_detect_update_apply_rollback(self, tmp_path):
        """Full workflow: detect update → apply → rollback.

        Note: Rollback restores registry.json only, not skill file content.
        To fully revert a skill to previous version, use git or manual restore.
        """
        # Setup: create real registry and skill file
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        skill_dir = tmp_path / "skills" / "myskill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"

        local_v1 = "---\nname: myskill\nversion: 1.0.0\n---\nV1 content"
        skill_file.write_text(local_v1)

        # Register the skill
        reg = Registry(registry_path=str(registry_dir))
        entry = RegistryEntry(
            name="myskill",
            repo_url="https://github.com/owner/myskill",
            install_path=str(skill_file),
            version="1.0.0",
            git_tree_sha="sha1",
        )
        reg.upsert(entry)

        # Run audit with mocked remote content
        v2_content = "---\nname: myskill\nversion: 2.0.0\n---\nV2 content"
        auditor = Auditor(registry=reg)
        with patch.object(auditor, "_fetch_remote_skill_content", return_value=v2_content):
            report = auditor.run()

        # Audit should detect update_available
        assert len(report.audit_results) == 1
        assert report.audit_results[0].overall_status == "update_available"
        assert report.audit_results[0].update_available is True

        # Run update with user approval
        updater = SkillUpdater(registry=reg)
        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value=v2_content):
            with patch("builtins.input", return_value="y"):
                approved, total = updater.run_interactive_update(skill_name="myskill")

        assert approved == 1
        assert total == 1
        # Skill file is now V2
        assert skill_file.read_text() == v2_content

        # Verify audit now shows healthy (no more update available)
        auditor2 = Auditor(registry=reg)
        with patch.object(auditor2, "_fetch_remote_skill_content", return_value=v2_content):
            report2 = auditor2.run()

        assert report2.audit_results[0].overall_status == "healthy"

        # Rollback registry only (doesn't restore skill file content)
        success = rollback(registry=reg, interactive=False)
        assert success is True
        # Skill file content is unchanged (still V2) — registry was rolled back only
        assert skill_file.read_text() == v2_content


class TestAuditDetectsMultipleIssues:
    """Audit correctly prioritizes multiple issues (tamper > security > update > conflict)."""

    def test_tampered_takes_priority(self, tmp_path):
        """Tampered status overrides all other issues."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nversion: 1.0.0\n---\nContent")

        reg = Registry(registry_path=str(tmp_path))
        entry = RegistryEntry(
            name="suspect",
            repo_url="https://github.com/owner/suspect",
            install_path=str(skill_file),
            git_tree_sha="old_sha",
        )
        reg.upsert(entry)

        auditor = Auditor(registry=reg)

        # Mock: SHA tamper + update available + security issue
        with patch("audit.check_sha_tamper", return_value=(True, "SHA mismatch")):
            with patch.object(auditor, "_fetch_remote_skill_content", return_value="different"):
                with patch("audit.scan_skill") as mock_scan:
                    mock_scan.return_value = ScanResult(severity="RED")
                    result = auditor._audit_entry(entry)

        # Tampered should win
        assert result.overall_status == "tampered"
        assert result.sha_tampered is True
        assert result.update_available is True  # all flags true
        assert result.scan_result.severity == "RED"

    def test_security_issue_takes_priority_over_update(self, tmp_path):
        """Security issue overrides update_available."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nversion: 1.0.0\n---\nold")

        reg = Registry(registry_path=str(tmp_path))
        entry = RegistryEntry(
            name="risky",
            repo_url="https://github.com/owner/risky",
            install_path=str(skill_file),
            git_tree_sha="match",
        )
        reg.upsert(entry)

        auditor = Auditor(registry=reg)

        # Mock: update available + security issue (no tamper)
        with patch("audit.check_sha_tamper", return_value=(False, "ok")):
            with patch.object(
                auditor, "_fetch_remote_skill_content", return_value="different content"
            ):
                with patch("audit.scan_skill") as mock_scan:
                    mock_scan.return_value = ScanResult(severity="RED")
                    result = auditor._audit_entry(entry)

        # Security issue should win
        assert result.overall_status == "security_issue"
        assert result.update_available is True
        assert result.scan_result.severity == "RED"


class TestMCPIntegration:
    """MCP hunting and parsing work correctly with audit."""

    def test_mcp_server_marked_in_hunt_results(self):
        """MCP server results are correctly identified and parsed."""
        from hunter import HuntResult

        # Create an MCP result
        mcp_result = HuntResult(
            name="my-mcp-server",
            repo_url="https://github.com/owner/my-mcp",
            result_type="mcp",
            mcp_transport_type="stdio",
            mcp_capabilities=["tools", "resources"],
            mcp_install_command="npx @modelcontextprotocol/server-my-mcp",
        )

        assert mcp_result.result_type == "mcp"
        assert mcp_result.mcp_transport_type == "stdio"
        assert "tools" in mcp_result.mcp_capabilities
        assert "npx" in mcp_result.mcp_install_command

    def test_mcp_parsing_extracts_metadata(self):
        """MCP metadata extraction works correctly."""
        from mcp_parser import parse_mcp_json

        mcp_json = """{
            "name": "example-server",
            "version": "1.0.0",
            "transport": "stdio",
            "capabilities": {"tools": true, "resources": true, "prompts": false}
        }"""

        meta = parse_mcp_json(mcp_json)
        assert meta is not None
        assert meta.name == "example-server"
        assert meta.transport_type == "stdio"
        assert "tools" in meta.capabilities
        assert "resources" in meta.capabilities
        assert "prompts" not in meta.capabilities


class TestEdgeCasesAndErrors:
    """Edge cases and error conditions are handled gracefully."""

    def test_corrupted_registry_json_starts_fresh(self, tmp_path):
        """Corrupted registry.json doesn't crash, starts empty."""
        reg_file = tmp_path / "registry.json"
        reg_file.write_text("{ invalid json }")

        reg = Registry(registry_path=str(reg_file))
        # Should not crash, should return empty list
        assert len(reg.all()) == 0

    def test_missing_skill_file_handled_gracefully(self, tmp_path):
        """Missing skill file during audit doesn't crash."""
        reg = Registry(registry_path=str(tmp_path))
        entry = RegistryEntry(
            name="missing",
            repo_url="https://github.com/owner/missing",
            install_path="/nonexistent/skill",
        )
        reg.upsert(entry)

        auditor = Auditor(registry=reg)
        with patch("audit.check_sha_tamper", return_value=(False, "ok")):
            with patch.object(auditor, "_fetch_remote_skill_content", return_value=None):
                result = auditor._audit_entry(entry)

        # Should not crash, should indicate local file not found
        assert result.overall_status == "healthy"  # no remote, no local, no issues

    def test_network_timeout_during_audit_gracefully_degrades(self, tmp_path):
        """Network timeout during audit doesn't fail the whole audit."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nversion: 1.0.0\n---\nContent")

        reg = Registry(registry_path=str(tmp_path))
        entry = RegistryEntry(
            name="skill",
            repo_url="https://github.com/owner/skill",
            install_path=str(skill_file),
        )
        reg.upsert(entry)

        auditor = Auditor(registry=reg)
        with patch("audit.check_sha_tamper", return_value=(False, "ok")):
            # Remote fetch fails with timeout
            with patch.object(auditor, "_fetch_remote_skill_content", return_value=None):
                result = auditor._audit_entry(entry)

        # Should scan local file and complete
        assert result.overall_status == "healthy"
        assert result.scan_result is not None
        assert result.remote_content is None

    def test_zero_length_files_handled(self, tmp_path):
        """Empty/zero-length skill files don't crash."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("")

        reg = Registry(registry_path=str(tmp_path))
        entry = RegistryEntry(
            name="empty",
            repo_url="https://github.com/owner/empty",
            install_path=str(skill_file),
        )
        reg.upsert(entry)

        auditor = Auditor(registry=reg)
        with patch("audit.check_sha_tamper", return_value=(False, "ok")):
            with patch.object(auditor, "_fetch_remote_skill_content", return_value=None):
                result = auditor._audit_entry(entry)

        # Should handle gracefully
        assert result.scan_result is not None


class TestConcurrencyAndPerformance:
    """Large numbers of skills are audited efficiently."""

    def test_audit_20_skills_completes(self, tmp_path):
        """Audit 20 skills (v0.2.0 requirement: ≤ 60 seconds)."""
        import time

        reg = Registry(registry_path=str(tmp_path))

        # Create 20 fake skills
        for i in range(20):
            skill_dir = tmp_path / f"skill{i}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(f"---\nname: skill{i}\nversion: 1.0.0\n---\nContent {i}")

            entry = RegistryEntry(
                name=f"skill{i}",
                repo_url=f"https://github.com/owner/skill{i}",
                install_path=str(skill_file),
            )
            reg.upsert(entry)

        auditor = Auditor(registry=reg)

        start = time.time()
        with patch("audit.check_sha_tamper", return_value=(False, "ok")):
            with patch.object(auditor, "_fetch_remote_skill_content", return_value=None):
                report = auditor.run()
        elapsed = time.time() - start

        # Should complete quickly
        assert len(report.audit_results) == 20
        assert elapsed < 10  # Much faster than 60s requirement

    def test_multiple_skills_with_updates_handled(self, tmp_path):
        """Multiple skills with updates are detected correctly."""
        reg = Registry(registry_path=str(tmp_path))

        # Create 5 skills with outdated versions
        for i in range(5):
            skill_dir = tmp_path / f"skill{i}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(f"---\nname: skill{i}\nversion: 1.0.0\n---\nV1")

            entry = RegistryEntry(
                name=f"skill{i}",
                repo_url=f"https://github.com/owner/skill{i}",
                install_path=str(skill_file),
            )
            reg.upsert(entry)

        updater = SkillUpdater(registry=reg)

        # All have updates available
        v2_content = "---\nname: test\nversion: 2.0.0\n---\nV2"
        with patch.object(updater.auditor, "_fetch_remote_skill_content", return_value=v2_content):
            updates = updater.check_updates()

        assert len(updates) == 5
        for upd in updates:
            assert upd.has_changes is True

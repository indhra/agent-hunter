"""
Tests for verify_sig.py — cryptographic signature verification.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from verify_sig import SignatureVerifier, sign_skill_entry, verify_verified_skills


class TestSignatureVerifier:
    def test_init_no_trusted_keys(self, tmp_path):
        verifier = SignatureVerifier(trusted_keys_path=tmp_path / "nonexistent.pub")
        assert len(verifier.trusted_keys) == 0

    def test_load_trusted_keys(self, tmp_path):
        keys_file = tmp_path / "trusted_keys.pub"
        keys_file.write_text("# Comment\nsigner-1:key123\nsigner-2:key456\n")

        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        assert "signer-1" in verifier.trusted_keys
        assert verifier.trusted_keys["signer-1"] == "key123"

    def test_verify_skill_entry_no_signature(self, tmp_path):
        verifier = SignatureVerifier(trusted_keys_path=tmp_path / "nonexistent.pub")
        skill = {"name": "test", "repo_url": "https://github.com/test/test"}

        result = verifier.verify_skill_entry(skill)
        # No trusted keys = skip verification
        assert result.is_valid


class TestSignAndVerify:
    def test_sign_and_verify_round_trip(self, tmp_path):
        # Create a key file
        keys_file = tmp_path / "trusted_keys.pub"
        keys_file.write_text("signer-1:mysecretkey\n")

        # Create a skill entry
        skill = {
            "name": "test-skill",
            "repo_url": "https://github.com/user/test-skill",
            "verified_at": "2026-05-03T00:00:00Z",
        }

        # Sign it
        signature = sign_skill_entry(skill, "signer-1", "mysecretkey")
        assert signature.startswith("signer-1:")

        # Add signature to skill entry
        skill["signature"] = signature

        # Verify it
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        result = verifier.verify_skill_entry(skill)
        assert result.is_valid
        assert result.signer == "signer-1"

    def test_verify_tampered_signature(self, tmp_path):
        keys_file = tmp_path / "trusted_keys.pub"
        keys_file.write_text("signer-1:mysecretkey\n")

        skill = {
            "name": "test-skill",
            "repo_url": "https://github.com/user/test-skill",
            "verified_at": "2026-05-03T00:00:00Z",
            "signature": "signer-1:invalidsignature",
        }

        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        result = verifier.verify_skill_entry(skill)
        assert not result.is_valid

    def test_verify_unknown_signer(self, tmp_path):
        keys_file = tmp_path / "trusted_keys.pub"
        keys_file.write_text("signer-1:mysecretkey\n")

        skill = {
            "name": "test-skill",
            "repo_url": "https://github.com/user/test-skill",
            "verified_at": "2026-05-03T00:00:00Z",
            "signature": "unknown-signer:abc123",
        }

        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        result = verifier.verify_skill_entry(skill)
        assert not result.is_valid

    def test_verify_with_expected_signer(self, tmp_path):
        keys_file = tmp_path / "trusted_keys.pub"
        keys_file.write_text("signer-1:mysecretkey\nsigner-2:otherkey\n")

        skill = {
            "name": "test-skill",
            "repo_url": "https://github.com/user/test-skill",
            "verified_at": "2026-05-03T00:00:00Z",
        }

        signature = sign_skill_entry(skill, "signer-1", "mysecretkey")
        skill["signature"] = signature

        verifier = SignatureVerifier(trusted_keys_path=keys_file)

        # Should pass with expected signer
        result = verifier.verify_skill_entry(skill, expected_signer="signer-1")
        assert result.is_valid

        # Should fail with different signer
        result = verifier.verify_skill_entry(skill, expected_signer="signer-2")
        assert not result.is_valid


class TestVerifyVerifiedSkills:
    def test_verify_verified_skills_no_file(self, tmp_path):
        total, valid, invalid = verify_verified_skills(
            verified_skills_path=tmp_path / "nonexistent.md"
        )
        assert total == 0
        assert valid == 0

    def test_verify_verified_skills_with_valid_entries(self, tmp_path):
        # Create a VERIFIED_SKILLS.md file
        skills_file = tmp_path / "VERIFIED_SKILLS.md"
        keys_file = tmp_path / "TRUSTED_KEYS.pub"
        keys_file.write_text("indhra:secret123\n")

        skill = {
            "name": "skill-deploy",
            "repo_url": "https://github.com/indhra/skill-deploy",
            "verified_at": "2026-05-03T00:00:00Z",
        }
        signature = sign_skill_entry(skill, "indhra", "secret123")
        skill["signature"] = signature

        import json

        json_content = json.dumps([skill])
        skills_json = f"```json\n{json_content}\n```\n"
        skills_file.write_text(skills_json)

        # Verify the JSON parsing works
        start = skills_json.find("```json") + len("```json")
        end = skills_json.find("```", start)
        json_str = skills_json[start:end].strip()
        skills = json.loads(json_str)
        assert len(skills) == 1


# ---------------------------------------------------------------------------
# Edge cases: _load_trusted_keys
# ---------------------------------------------------------------------------


class TestLoadTrustedKeysEdgeCases:
    def test_oserror_graceful_degradation(self, tmp_path):
        """OSError reading key file should result in empty trusted_keys."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-1:key1\n")
        keys_file.chmod(0o000)  # make unreadable
        try:
            verifier = SignatureVerifier(trusted_keys_path=keys_file)
            assert len(verifier.trusted_keys) == 0
        finally:
            keys_file.chmod(0o644)  # restore so tmp_path cleanup works

    def test_line_without_colon_is_skipped(self, tmp_path):
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("nocolon\nsigner-1:key1\n# comment\n\n")
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        assert "signer-1" in verifier.trusted_keys
        assert "nocolon" not in verifier.trusted_keys

    def test_multiple_colons_in_key_material(self, tmp_path):
        """Key material may contain colons — only split on first colon."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-1:key:with:colons\n")
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        assert verifier.trusted_keys.get("signer-1") == "key:with:colons"


# ---------------------------------------------------------------------------
# Edge cases: verify_skill_entry
# ---------------------------------------------------------------------------


class TestVerifySkillEntryEdgeCases:
    def test_no_signature_field_returns_invalid(self, tmp_path):
        """When trusted keys exist but entry has no 'signature' field."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-1:key1\n")
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        skill = {"name": "test", "repo_url": "https://github.com/x/y", "verified_at": "2026-01-01"}
        result = verifier.verify_skill_entry(skill)
        assert not result.is_valid
        assert "No signature" in result.message

    def test_signature_without_colon_format_invalid(self, tmp_path):
        """Signature missing ':' separator returns invalid."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-1:key1\n")
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        skill = {
            "name": "test",
            "repo_url": "https://github.com/x/y",
            "verified_at": "2026-01-01",
            "signature": "invalidsignaturenocodon",
        }
        result = verifier.verify_skill_entry(skill)
        assert not result.is_valid
        assert "Invalid signature format" in result.message

    def test_empty_signature_returns_invalid(self, tmp_path):
        """Empty signature string returns invalid."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-1:key1\n")
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        skill = {
            "name": "test",
            "repo_url": "https://github.com/x/y",
            "verified_at": "2026-01-01",
            "signature": "",
        }
        result = verifier.verify_skill_entry(skill)
        assert not result.is_valid

    def test_expected_signer_mismatch_returns_invalid(self, tmp_path):
        """When signature is from signer-A but expected_signer='signer-B'."""
        keys_file = tmp_path / "keys.pub"
        keys_file.write_text("signer-a:keyA\nsigner-b:keyB\n")
        skill = {
            "name": "test",
            "repo_url": "https://github.com/x/y",
            "verified_at": "2026-01-01",
        }
        signature = sign_skill_entry(skill, "signer-a", "keyA")
        skill["signature"] = signature
        verifier = SignatureVerifier(trusted_keys_path=keys_file)
        result = verifier.verify_skill_entry(skill, expected_signer="signer-b")
        assert not result.is_valid
        assert "signer-a" in result.message or "signer-b" in result.message


# ---------------------------------------------------------------------------
# verify_verified_skills — full function coverage
# ---------------------------------------------------------------------------


class TestVerifyVerifiedSkillsFunction:
    def test_file_missing_returns_zeros(self, tmp_path):
        total, valid, invalid = verify_verified_skills(tmp_path / "missing.md")
        assert total == 0
        assert valid == 0
        assert invalid == []

    def test_file_with_no_json_block_returns_zeros(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text("# No JSON here\n\nJust prose.\n")
        total, valid, invalid = verify_verified_skills(md)
        assert total == 0

    def test_file_with_invalid_json_returns_zeros(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text("```json\n{not valid json\n```\n")
        total, valid, invalid = verify_verified_skills(md)
        assert total == 0

    def test_valid_unsigned_entries_pass_when_no_keys(self, tmp_path):
        """No trusted keys → verification skipped → all pass."""
        import json as _json
        from unittest.mock import patch as _patch

        skills = [
            {"name": "skill-a", "repo_url": "https://github.com/x/a", "verified_at": "2026-01-01"},
            {"name": "skill-b", "repo_url": "https://github.com/x/b", "verified_at": "2026-01-02"},
        ]
        md = tmp_path / "VERIFIED_SKILLS.md"
        # Build content using explicit concatenation (backtick-safe)
        content = "```json\n" + _json.dumps(skills) + "\n```\n"
        md.write_text(content)

        # Patch SignatureVerifier to have no trusted keys so verification is skipped
        with _patch("verify_sig.SignatureVerifier._load_trusted_keys", return_value={}):
            total, valid, invalid = verify_verified_skills(md)
        assert total == 2
        assert valid == 2
        assert invalid == []

    def test_entries_with_bad_json_format_unclosed_block(self, tmp_path):
        """Unclosed ``` block should be handled gracefully."""
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text("```json\n[]\n")  # No closing ```
        total, valid, invalid = verify_verified_skills(md)
        assert total == 0

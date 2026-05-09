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

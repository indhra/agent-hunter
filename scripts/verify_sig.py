"""
verify_sig.py — Cryptographic signature verification for verified skills (v0.8.0+).

Responsibilities:
    - Load trusted signer keys from references/TRUSTED_KEYS.pub
    - Validate HMAC-SHA256 signatures on verified skill entries
    - Support migration path to Ed25519 (cryptography library optional)
    - Graceful degradation if verification unavailable

No LLM calls. Local file I/O only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VerificationResult:
    """Result of signature verification."""

    is_valid: bool
    message: str
    signer: Optional[str] = None


class SignatureVerifier:
    """Validates signatures on verified skill entries."""

    def __init__(self, trusted_keys_path: Optional[Path] = None) -> None:
        """Initialize verifier with trusted keys.

        Args:
            trusted_keys_path: Path to TRUSTED_KEYS.pub file. If None, uses
                               references/TRUSTED_KEYS.pub from repo root.
        """
        self.trusted_keys_path = (
            trusted_keys_path or Path(__file__).parent.parent / "references" / "TRUSTED_KEYS.pub"
        )
        self.trusted_keys: dict[str, str] = {}  # {signer_id: key_material}
        self._load_trusted_keys()

    def _load_trusted_keys(self) -> None:
        """Load trusted signer keys from TRUSTED_KEYS.pub.

        Format:
            # signer-id-1
            HMAC-SHA256:key_material_as_base64
            # signer-id-2
            HMAC-SHA256:another_key_material
        """
        if not self.trusted_keys_path.exists():
            return  # Graceful degradation: no keys available

        try:
            content = self.trusted_keys_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse: signer-id:key_material
                if ":" not in line:
                    continue

                signer_id, key_material = line.split(":", 1)
                self.trusted_keys[signer_id.strip()] = key_material.strip()
        except (OSError, ValueError):
            pass  # Graceful degradation on read/parse error

    def verify_skill_entry(
        self, skill_entry: dict, expected_signer: Optional[str] = None
    ) -> VerificationResult:
        """Verify signature on a skill entry.

        Args:
            skill_entry: Dict with keys: name, repo_url, signature, verified_at
            expected_signer: If provided, signature must be from this signer

        Returns:
            VerificationResult with is_valid=True/False and message
        """
        if not self.trusted_keys:
            return VerificationResult(
                is_valid=True,
                message="No trusted keys configured; verification skipped",
                signer=None,
            )

        signature = skill_entry.get("signature", "")
        if not signature:
            return VerificationResult(
                is_valid=False,
                message="No signature present on skill entry",
                signer=None,
            )

        # Parse signature: format is "signer-id:signature-value"
        if ":" not in signature:
            return VerificationResult(
                is_valid=False,
                message="Invalid signature format (expected 'signer-id:value')",
                signer=None,
            )

        signer_id, sig_value = signature.split(":", 1)
        signer_id = signer_id.strip()
        sig_value = sig_value.strip()

        if expected_signer and signer_id != expected_signer:
            return VerificationResult(
                is_valid=False,
                message=f"Signature from {signer_id}, expected {expected_signer}",
                signer=signer_id,
            )

        if signer_id not in self.trusted_keys:
            return VerificationResult(
                is_valid=False,
                message=f"Unknown signer: {signer_id}",
                signer=signer_id,
            )

        # Compute expected signature: HMAC-SHA256({name, repo_url, verified_at}, key)
        key_material = self.trusted_keys[signer_id]
        content_to_sign = json.dumps(
            {
                "name": skill_entry.get("name", ""),
                "repo_url": skill_entry.get("repo_url", ""),
                "verified_at": skill_entry.get("verified_at", ""),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        try:
            expected_sig = hmac.new(
                key_material.encode("utf-8"),
                content_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        except Exception as exc:
            return VerificationResult(
                is_valid=False,
                message=f"Signature computation failed: {exc}",
                signer=signer_id,
            )

        if not hmac.compare_digest(sig_value, expected_sig):
            return VerificationResult(
                is_valid=False,
                message="Signature mismatch — this skill may have been tampered",
                signer=signer_id,
            )

        return VerificationResult(
            is_valid=True,
            message="Signature verified",
            signer=signer_id,
        )


def sign_skill_entry(skill_entry: dict, signer_id: str, signer_key: str) -> str:
    """Sign a skill entry with HMAC-SHA256.

    Used by maintainers to sign verified skills (not part of runtime).

    Args:
        skill_entry: Dict with name, repo_url, verified_at
        signer_id: ID of the signer
        signer_key: Secret key material (base64 or plain string)

    Returns:
        Signature string in format "signer-id:hexdigest"
    """
    content_to_sign = json.dumps(
        {
            "name": skill_entry.get("name", ""),
            "repo_url": skill_entry.get("repo_url", ""),
            "verified_at": skill_entry.get("verified_at", ""),
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    sig = hmac.new(
        signer_key.encode("utf-8"),
        content_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{signer_id}:{sig}"


# Convenience function
def verify_verified_skills(
    verified_skills_path: Optional[Path] = None,
) -> tuple[int, int, list[str]]:
    """Verify all skills in VERIFIED_SKILLS.md.

    Args:
        verified_skills_path: Path to VERIFIED_SKILLS.md. If None, uses
                             references/VERIFIED_SKILLS.md from repo root.

    Returns:
        (total_verified, valid_sigs, invalid_sigs)
    """
    if verified_skills_path is None:
        verified_skills_path = Path(__file__).parent.parent / "references" / "VERIFIED_SKILLS.md"

    if not verified_skills_path.exists():
        return (0, 0, [])

    verifier = SignatureVerifier()
    total = 0
    valid = 0
    invalid = []

    try:
        content = verified_skills_path.read_text(encoding="utf-8")
        # Parse JSON array from the file content
        # Simplified: look for ```json...``` blocks
        start = content.find("```json")
        if start == -1:
            return (0, 0, [])

        start += len("```json")
        end = content.find("```", start)
        if end == -1:
            return (0, 0, [])

        json_str = content[start:end].strip()
        skills = json.loads(json_str)

        for skill in skills:
            total += 1
            result = verifier.verify_skill_entry(skill)
            if result.is_valid:
                valid += 1
            else:
                invalid.append(f"{skill.get('name', 'unknown')}: {result.message}")
    except (json.JSONDecodeError, OSError, ValueError):
        pass

    return (total, valid, invalid)

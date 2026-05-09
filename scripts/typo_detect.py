"""
typo_detect.py — Detect typo-squatted skill names (v0.8.0+).

Responsibilities:
    - Compute Levenshtein distance between skill names
    - Flag skills similar to verified/known skills
    - Configurable similarity threshold (default: 2)
    - No network I/O, purely algorithmic

No LLM calls. Local computation only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TypoMatch:
    """Result of typo detection."""

    is_typo: bool
    similar_to: Optional[str] = None
    distance: int = 0
    message: str = ""


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Minimum edit distance (insertions, deletions, substitutions)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            # than s2
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


class TypoDetector:
    """Detects typo-squatted skill names."""

    def __init__(
        self,
        verified_skills: Optional[list[str]] = None,
        threshold: int = 2,
    ) -> None:
        """Initialize detector with known good skill names.

        Args:
            verified_skills: List of known good skill names (e.g., from VERIFIED_SKILLS.md)
            threshold: Maximum Levenshtein distance to flag as typo
        """
        self.verified_skills = verified_skills or []
        self.threshold = threshold

    def detect(self, skill_name: str) -> TypoMatch:
        """Check if a skill name is a potential typo.

        Args:
            skill_name: Name of the skill to check

        Returns:
            TypoMatch with is_typo=True/False and similar_to if applicable
        """
        # Normalize names: lowercase, remove common prefixes/suffixes
        normalized = skill_name.lower().strip()

        best_match = None
        best_distance = self.threshold + 1

        for verified in self.verified_skills:
            verified_normalized = verified.lower().strip()
            distance = levenshtein_distance(normalized, verified_normalized)

            # Skip exact matches (distance 0) — they're not typos
            if distance == 0:
                return TypoMatch(is_typo=False, message="")

            # If distance <= threshold, it's a potential typo
            if distance <= self.threshold and distance < best_distance:
                best_distance = distance
                best_match = verified

        if best_match:
            return TypoMatch(
                is_typo=True,
                similar_to=best_match,
                distance=best_distance,
                message=f"Similar to verified skill '{best_match}' (distance: {best_distance}). Did you mean this one?",
            )

        return TypoMatch(
            is_typo=False,
            message="",
        )

    def detect_multiple(self, skill_names: list[str]) -> list[tuple[str, TypoMatch]]:
        """Check multiple skill names for typos.

        Args:
            skill_names: List of skill names to check

        Returns:
            List of (skill_name, TypoMatch) tuples
        """
        return [(name, self.detect(name)) for name in skill_names]


def load_verified_skills_from_file(verified_skills_path: Optional[Path] = None) -> list[str]:
    """Load verified skill names from VERIFIED_SKILLS.md.

    Args:
        verified_skills_path: Path to VERIFIED_SKILLS.md. If None, uses
                             references/VERIFIED_SKILLS.md from repo root.

    Returns:
        List of verified skill names
    """
    if verified_skills_path is None:
        verified_skills_path = Path(__file__).parent.parent / "references" / "VERIFIED_SKILLS.md"

    if not verified_skills_path.exists():
        return []

    try:
        import json

        content = verified_skills_path.read_text(encoding="utf-8")
        # Parse JSON array from ```json...``` block
        start = content.find("```json")
        if start == -1:
            return []

        start += len("```json")
        end = content.find("```", start)
        if end == -1:
            return []

        json_str = content[start:end].strip()
        skills = json.loads(json_str)

        names = []
        for skill in skills:
            if isinstance(skill, dict) and "name" in skill:
                names.append(skill["name"])

        return names
    except (json.JSONDecodeError, OSError, ValueError):
        return []

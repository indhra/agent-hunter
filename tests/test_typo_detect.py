"""
Tests for typo_detect.py — typo-squat detection.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from typo_detect import TypoDetector, levenshtein_distance, load_verified_skills_from_file


class TestLevenshteinDistance:
    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_one_insertion(self):
        assert levenshtein_distance("helo", "hello") == 1

    def test_one_deletion(self):
        assert levenshtein_distance("hello", "hell") == 1

    def test_one_substitution(self):
        assert levenshtein_distance("hallo", "hello") == 1

    def test_multiple_edits(self):
        # "kitten" to "sitting" requires 3 edits
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_empty_strings(self):
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("hello", "") == 5
        assert levenshtein_distance("", "hello") == 5

    def test_case_sensitive(self):
        # Distance between "Hello" and "hello" is 1 (one substitution)
        assert levenshtein_distance("Hello", "hello") == 1

    def test_typo_examples(self):
        # Common typos
        assert levenshtein_distance("skll-deploy", "skill-deploy") == 1  # substitution: i -> l
        assert levenshtein_distance("react-uer", "react-user") == 1  # substitution
        assert levenshtein_distance("deply", "deploy") == 1  # substitution


class TestTypoDetector:
    def test_no_typo(self):
        detector = TypoDetector(verified_skills=["skill-deploy", "react-user"])

        result = detector.detect("skill-deploy")
        assert not result.is_typo
        assert result.message == ""

    def test_detects_one_char_typo(self):
        detector = TypoDetector(verified_skills=["skill-deploy"])

        result = detector.detect("skll-deploy")  # One typo
        assert result.is_typo
        assert result.similar_to == "skill-deploy"
        assert result.distance <= 2

    def test_detects_substitution_typo(self):
        detector = TypoDetector(verified_skills=["react-user"])

        result = detector.detect("react-uer")
        assert result.is_typo
        assert result.similar_to == "react-user"

    def test_case_insensitive_detection(self):
        detector = TypoDetector(verified_skills=["Skill-Deploy"])

        result = detector.detect("skill-deploy")
        assert not result.is_typo

    def test_threshold_respected(self):
        detector = TypoDetector(verified_skills=["skill-deploy"], threshold=1)

        # "skll-deploy" is distance 1, should match with threshold 1
        result = detector.detect("skll-deploy")
        assert result.is_typo  # Should match because distance == threshold

        # "skl-depoy" is distance 2, should NOT match with threshold 1
        result = detector.detect("skl-depoy")
        assert not result.is_typo  # Should not match because distance > threshold

    def test_closest_match_chosen(self):
        detector = TypoDetector(
            verified_skills=["skill-deploy", "skill-deployment"],
            threshold=3,
        )

        result = detector.detect("skll-deploy")
        assert result.is_typo
        # "skll-deploy" is distance 2 from "skill-deploy"
        # and distance 5 from "skill-deployment"
        # So it should match "skill-deploy"
        assert result.similar_to == "skill-deploy"

    def test_detect_multiple(self):
        detector = TypoDetector(verified_skills=["skill-deploy", "react-user"])

        results = detector.detect_multiple(["skill-deploy", "skll-deploy", "react-uer"])

        assert len(results) == 3
        assert not results[0][1].is_typo  # "skill-deploy" is good
        assert results[1][1].is_typo  # "skll-deploy" is typo
        assert results[2][1].is_typo  # "react-uer" is typo


class TestLoadVerifiedSkills:
    def test_load_nonexistent_file(self, tmp_path):
        skills = load_verified_skills_from_file(verified_skills_path=tmp_path / "nonexistent.md")
        assert len(skills) == 0

    def test_load_from_file(self, tmp_path):
        import json

        skills_file = tmp_path / "VERIFIED_SKILLS.md"
        skills_data = [
            {"name": "skill-deploy", "repo_url": "https://github.com/test/deploy"},
            {"name": "react-user", "repo_url": "https://github.com/test/user"},
        ]

        json_content = json.dumps(skills_data)
        skills_file.write_text(f"# Verified Skills\n\n```json\n{json_content}\n```\n")

        skills = load_verified_skills_from_file(verified_skills_path=skills_file)
        assert len(skills) == 2
        assert "skill-deploy" in skills
        assert "react-user" in skills

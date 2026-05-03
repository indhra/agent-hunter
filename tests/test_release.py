"""Test suite for release.py script."""

import pytest
from pathlib import Path
from scripts.release import read_changelog


class TestReadChangelog:
    """Test CHANGELOG.md parsing."""

    def test_read_unreleased_section(self, tmp_path):
        """Test reading [Unreleased] section."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [Unreleased]

### Added
- Feature A
- Feature B

### Fixed
- Bug fix C

## [0.4.0] - 2026-04-01

### Added
- Old feature
"""
        )

        result = read_changelog("Unreleased", changelog)
        assert result is not None
        assert "Feature A" in result
        assert "Feature B" in result
        assert "Bug fix C" in result
        assert "Old feature" not in result  # Should not include next section

    def test_read_versioned_section(self, tmp_path):
        """Test reading a versioned section."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.1] - 2026-05-03

### Added
- New feature

### Fixed
- Bug fix

## [0.4.0] - 2026-04-01

### Added
- Old feature
"""
        )

        result = read_changelog("0.4.1", changelog)
        assert result is not None
        assert "New feature" in result
        assert "Bug fix" in result
        assert "Old feature" not in result

    def test_version_not_found(self, tmp_path):
        """Test reading non-existent version."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.0] - 2026-04-01

### Added
- Feature
"""
        )

        result = read_changelog("0.5.0", changelog)
        assert result is None

    def test_changelog_file_not_found(self, tmp_path):
        """Test when CHANGELOG.md doesn't exist."""
        result = read_changelog("0.4.0", tmp_path / "nonexistent.md")
        assert result is None

    def test_empty_changelog_section(self, tmp_path):
        """Test section with no content."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.1] - 2026-05-03

## [0.4.0] - 2026-04-01

### Added
- Feature
"""
        )

        result = read_changelog("0.4.1", changelog)
        # Should match but be mostly whitespace
        assert result is not None
        assert "Feature" not in result

    def test_malformed_version_header(self, tmp_path):
        """Test with malformed version headers."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## v0.4.1 - 2026-05-03
Should not match this

## [0.4.0] - 2026-04-01
Should match this
"""
        )

        result = read_changelog("0.4.1", changelog)
        # Should handle both formats gracefully
        assert result is None or "Should not match" in result or result.strip() == ""

    def test_version_with_leading_v(self, tmp_path):
        """Test reading version with 'v' prefix."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [v0.4.1] - 2026-05-03

### Added
- Feature with v prefix

## [0.4.0] - 2026-04-01
"""
        )

        result = read_changelog("v0.4.1", changelog)
        assert result is not None
        assert "Feature with v prefix" in result

    def test_multiline_entries(self, tmp_path):
        """Test reading multiline change entries."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.1] - 2026-05-03

### Added
- Feature A with
  multiple lines of
  description text

### Fixed
- Bug fix with details
  spanning multiple
  lines

## [0.4.0] - 2026-04-01
"""
        )

        result = read_changelog("0.4.1", changelog)
        assert result is not None
        assert "multiple lines of" in result
        assert "spanning multiple" in result

    def test_special_characters_in_notes(self, tmp_path):
        """Test changelog with special characters."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.1] - 2026-05-03

### Added
- Feature with `code` blocks
- Feature with [links](https://example.com)
- Feature with emoji 🚀

## [0.4.0] - 2026-04-01
"""
        )

        result = read_changelog("0.4.1", changelog)
        assert result is not None
        assert "`code`" in result
        assert "[links]" in result
        assert "🚀" in result

    def test_actual_changelog_file(self):
        """Test with actual CHANGELOG.md in repo."""
        changelog_path = Path("CHANGELOG.md")
        if not changelog_path.exists():
            pytest.skip("CHANGELOG.md not found in repo")

        # Test [Unreleased] section exists
        result = read_changelog("Unreleased", changelog_path)
        assert result is not None, "[Unreleased] section should exist"
        assert len(result) > 0, "[Unreleased] section should not be empty"

    def test_release_notes_format_consistency(self, tmp_path):
        """Test that release notes maintain consistent format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [0.4.1] - 2026-05-03

### Added
- Feature A

### Fixed
- Bug fix B

### Changed
- Breaking change C

### Security
- Security patch D

## [0.4.0] - 2026-04-01
"""
        )

        result = read_changelog("0.4.1", changelog)
        assert result is not None
        # All standard sections should be present
        assert "### Added" in result
        assert "### Fixed" in result
        assert "### Changed" in result
        assert "### Security" in result

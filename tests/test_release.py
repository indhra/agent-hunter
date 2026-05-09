"""Test suite for release.py script."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from release import create_github_release, read_changelog, run_command, tag_and_push


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


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_run_command_success(self):
        result = run_command(["echo", "hello"])
        assert result == "hello"

    def test_run_command_returns_stdout(self):
        result = run_command(["python3", "-c", "print('test-output')"])
        assert result == "test-output"

    def test_run_command_raises_on_failure(self):
        with pytest.raises(subprocess.CalledProcessError):
            run_command(["false"])

    def test_run_command_check_false_no_raise(self):
        # Should not raise when check=False
        result = run_command(["false"], check=False)
        assert result == ""  # empty stdout

    def test_run_command_strips_output(self):
        result = run_command(["echo", "  trimmed  "])
        assert result == "trimmed"


# ---------------------------------------------------------------------------
# tag_and_push
# ---------------------------------------------------------------------------


class TestTagAndPush:
    def test_tag_and_push_success(self):
        with (
            patch("release.run_command") as mock_cmd,
        ):
            # Simulate tag doesn't exist (rev-parse fails) then tag + push succeed
            def side_effect(cmd, check=True):
                if "rev-parse" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return "ok"

            mock_cmd.side_effect = side_effect
            result = tag_and_push("1.2.3", "Release notes")
        assert result is True

    def test_tag_already_exists_skips_creation(self, capsys):
        with patch("release.run_command") as mock_cmd:
            # Simulate tag exists (rev-parse succeeds)
            mock_cmd.return_value = "abc123"
            result = tag_and_push("1.2.3", "Release notes")
        assert result is True
        captured = capsys.readouterr()
        assert "already exists" in captured.out

    def test_tag_and_push_adds_v_prefix(self):
        with patch("release.run_command") as mock_cmd:
            calls_made = []

            def side_effect(cmd, check=True):
                calls_made.append(cmd)
                if "rev-parse" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return "ok"

            mock_cmd.side_effect = side_effect
            tag_and_push("1.2.3", "notes")

        # Should have called git tag with v1.2.3
        tag_calls = [c for c in calls_made if "tag" in c and "-a" in c]
        assert any("v1.2.3" in str(c) for c in tag_calls)

    def test_tag_v_prefix_not_doubled(self):
        with patch("release.run_command") as mock_cmd:
            calls_made = []

            def side_effect(cmd, check=True):
                calls_made.append(cmd)
                if "rev-parse" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return "ok"

            mock_cmd.side_effect = side_effect
            tag_and_push("v1.2.3", "notes")

        # Should use v1.2.3 not vv1.2.3
        tag_calls = [c for c in calls_made if "tag" in c and "-a" in c]
        assert not any("vv1.2.3" in str(c) for c in tag_calls)
        assert any("v1.2.3" in str(c) for c in tag_calls)

    def test_tag_creation_failure_returns_false(self):
        with patch("release.run_command") as mock_cmd:

            def side_effect(cmd, check=True):
                if "rev-parse" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                if "tag" in cmd and "-a" in cmd:
                    raise subprocess.CalledProcessError(1, cmd)
                return "ok"

            mock_cmd.side_effect = side_effect
            result = tag_and_push("1.2.3", "notes")
        assert result is False


# ---------------------------------------------------------------------------
# create_github_release
# ---------------------------------------------------------------------------


class TestCreateGithubRelease:
    def test_uses_gh_cli_when_available(self):
        with patch("release.run_command") as mock_cmd:
            mock_cmd.return_value = "ok"
            result = create_github_release("1.2.3", "Release notes")
        assert result is True
        called_cmd = mock_cmd.call_args[0][0]
        assert "gh" in called_cmd
        assert "release" in called_cmd

    def test_returns_false_when_gh_not_found(self, capsys):
        with patch("release.run_command", side_effect=FileNotFoundError("gh not found")):
            result = create_github_release("1.2.3", "Release notes")
        assert result is False
        captured = capsys.readouterr()
        assert "gh" in captured.out.lower() or "CLI" in captured.out

    def test_adds_v_prefix_to_tag(self):
        with patch("release.run_command") as mock_cmd:
            mock_cmd.return_value = "ok"
            create_github_release("1.2.3", "notes")

        cmd = mock_cmd.call_args[0][0]
        assert "v1.2.3" in cmd

    def test_v_prefix_not_doubled(self):
        with patch("release.run_command") as mock_cmd:
            mock_cmd.return_value = "ok"
            create_github_release("v1.2.3", "notes")

        cmd = mock_cmd.call_args[0][0]
        assert "v1.2.3" in cmd
        assert "vv1.2.3" not in str(cmd)


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


class TestMain:
    def _make_changelog(self, tmp_path: Path) -> Path:
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [1.0.0] - 2026-05-09\n\n### Added\n- Initial release\n\n"
            "## [0.9.0] - 2026-04-01\n\n### Added\n- Old feature\n"
        )
        return changelog

    def test_main_success_skip_github(self, tmp_path):
        changelog = self._make_changelog(tmp_path)
        with (
            patch("release.tag_and_push", return_value=True),
            patch(
                "sys.argv",
                [
                    "release.py",
                    "--version",
                    "1.0.0",
                    "--changelog",
                    str(changelog),
                    "--skip-github",
                ],
            ),
        ):
            import release

            # main() returns normally on success (no sys.exit call)
            release.main()

    def test_main_exits_1_on_missing_changelog_version(self, tmp_path):
        changelog = self._make_changelog(tmp_path)
        with (
            patch("sys.argv", ["release.py", "--version", "9.9.9", "--changelog", str(changelog)]),
        ):
            import release

            with pytest.raises(SystemExit) as exc_info:
                release.main()
        assert exc_info.value.code == 1

    def test_main_exits_1_when_tag_push_fails(self, tmp_path):
        changelog = self._make_changelog(tmp_path)
        with (
            patch("release.tag_and_push", return_value=False),
            patch(
                "sys.argv",
                [
                    "release.py",
                    "--version",
                    "1.0.0",
                    "--changelog",
                    str(changelog),
                    "--skip-github",
                ],
            ),
        ):
            import release

            with pytest.raises(SystemExit) as exc_info:
                release.main()
        assert exc_info.value.code == 1

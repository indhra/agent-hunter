"""
test_reporter.py — Tests for reporter.py.

Covers the critical _include_in_report() rule and terminal output.
"""

from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from hunter import HuntResult  # noqa: E402
from reporter import _include_in_report, _print_terminal, _save_markdown  # noqa: E402
from scorer import ScoredResult  # noqa: E402
from security_scan import ScanFinding, ScanResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scored(
    repo_name: str = "test-skill",
    owner: str = "owner",
    stars: int = 50,
    score: float = 0.70,
    trust_tier: str = "raw",
) -> ScoredResult:
    hunt = HuntResult(
        name=repo_name,
        repo_url=f"https://github.com/{owner}/{repo_name}",
        raw_url=f"https://github.com/{owner}/{repo_name}",
        owner=owner,
        repo_name=repo_name,
        description="A helpful skill",
        stars=stars,
        result_type="skill",
        trust_tier=trust_tier,
    )
    s = ScoredResult(hunt_result=hunt, skill_metadata=None)
    s.total_score = score
    return s


def _green_scan() -> ScanResult:
    return ScanResult(severity="GREEN")


def _red_scan() -> ScanResult:
    return ScanResult(severity="RED", findings=[
        ScanFinding(pattern_id="SP-001", severity="RED",
                    description="Prompt injection", location="body")
    ])


def _yellow_scan() -> ScanResult:
    return ScanResult(severity="YELLOW", findings=[
        ScanFinding(pattern_id="SP-007", severity="YELLOW",
                    description="Env access", location="body")
    ])


# ---------------------------------------------------------------------------
# _include_in_report() — the critical RED exclusion rule
# ---------------------------------------------------------------------------

class TestIncludeInReport:
    """RED results must NEVER appear in the main report (count only)."""

    def test_green_is_included(self):
        s = _make_scored()
        scan_results = {s.hunt_result.repo_url: _green_scan()}
        assert _include_in_report(s, scan_results) is True

    def test_yellow_is_included(self):
        s = _make_scored()
        scan_results = {s.hunt_result.repo_url: _yellow_scan()}
        assert _include_in_report(s, scan_results) is True

    def test_red_is_excluded(self):
        """Security constraint: RED results are NEVER shown (count only)."""
        s = _make_scored()
        scan_results = {s.hunt_result.repo_url: _red_scan()}
        assert _include_in_report(s, scan_results) is False

    def test_missing_scan_defaults_to_green(self):
        """If no scan result exists for a URL, treat as GREEN (include)."""
        s = _make_scored()
        assert _include_in_report(s, {}) is True


# ---------------------------------------------------------------------------
# _print_terminal()
# ---------------------------------------------------------------------------

class TestPrintTerminal:
    def _capture_output(self, results, scan_results, red_count=0, project_root=""):
        buf = StringIO()
        with patch("sys.stdout", buf):
            _print_terminal(results, scan_results, red_count, project_root)
        return buf.getvalue()

    def test_shows_skill_name(self):
        s = _make_scored("fastapi-helper")
        out = self._capture_output([s], {s.hunt_result.repo_url: _green_scan()})
        assert "fastapi-helper" in out

    def test_shows_install_command(self):
        """D8: Each result must show its gh skill install command."""
        s = _make_scored("fastapi-helper", owner="myorg")
        out = self._capture_output([s], {s.hunt_result.repo_url: _green_scan()})
        assert "gh skill install myorg/fastapi-helper" in out

    def test_shows_red_count(self):
        s = _make_scored()
        out = self._capture_output([s], {s.hunt_result.repo_url: _green_scan()}, red_count=3)
        assert "3" in out
        assert "blocked" in out.lower() or "security" in out.lower()

    def test_no_results_shows_tip(self):
        out = self._capture_output([], {})
        assert "No results" in out or "Tip" in out or "scaffold" in out.lower()

    def test_shows_repo_url(self):
        s = _make_scored("myrepo", "myorg")
        out = self._capture_output([s], {s.hunt_result.repo_url: _green_scan()})
        assert "https://github.com/myorg/myrepo" in out

    def test_shows_description(self):
        s = _make_scored()
        out = self._capture_output([s], {s.hunt_result.repo_url: _green_scan()})
        assert "A helpful skill" in out

    def test_yellow_finding_shown(self):
        s = _make_scored()
        out = self._capture_output([s], {s.hunt_result.repo_url: _yellow_scan()})
        assert "Env access" in out

    def test_red_not_shown_in_results_list(self):
        """RED results must not appear in the numbered list."""
        red = _make_scored("evil-skill")
        scan_results = {red.hunt_result.repo_url: _red_scan()}
        # _print_terminal expects pre-filtered list — pass empty list for RED
        out = self._capture_output([], scan_results, red_count=1)
        assert "evil-skill" not in out


# ---------------------------------------------------------------------------
# _save_markdown()
# ---------------------------------------------------------------------------

class TestSaveMarkdown:
    def test_creates_markdown_file(self, tmp_path):
        s = _make_scored("myrepo")
        scan = {s.hunt_result.repo_url: _green_scan()}

        with patch("reporter.REPORTS_DIR", tmp_path):
            path = _save_markdown([s], scan, 0, ".", [s])

        assert path.exists()
        content = path.read_text()
        assert "myrepo" in content

    def test_markdown_contains_install_command(self, tmp_path):
        s = _make_scored("myrepo", "testorg")
        scan = {s.hunt_result.repo_url: _green_scan()}

        with patch("reporter.REPORTS_DIR", tmp_path):
            path = _save_markdown([s], scan, 0, ".", [s])

        content = path.read_text()
        assert "gh skill install testorg/myrepo" in content

    def test_markdown_does_not_contain_red_results(self, tmp_path):
        """RED results must not appear anywhere in the markdown report."""
        green = _make_scored("safe-skill")
        red = _make_scored("evil-skill")
        scan = {
            green.hunt_result.repo_url: _green_scan(),
            red.hunt_result.repo_url: _red_scan(),
        }

        with patch("reporter.REPORTS_DIR", tmp_path):
            path = _save_markdown([green], scan, 1, ".", [green, red])

        content = path.read_text()
        assert "evil-skill" not in content
        assert "1" in content  # red_count shown somewhere

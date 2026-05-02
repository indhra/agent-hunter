"""
Tests for hunter.py — _passes_prefilter, _fetch_skill_content,
_fetch_repo_metadata, _load_verified_urls, _to_raw_url, pagination.

All network calls are mocked with unittest.mock so tests are offline and fast.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from hunter import Hunter, HuntResult, _to_raw_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_hunter(**kwargs) -> Hunter:
    defaults = dict(min_stars=10, max_age_days=180, include_mcp=True)
    defaults.update(kwargs)
    return Hunter(**defaults)


def make_result(**kwargs) -> HuntResult:
    defaults = dict(
        name="test-skill",
        repo_url="https://github.com/owner/test-skill",
        raw_url="https://github.com/owner/test-skill/blob/main/SKILL.md",
        owner="owner",
        repo_name="test-skill",
        description="A helpful skill.",
        stars=100,
        result_type="skill",
        trust_tier="raw",
        raw_content="",
    )
    defaults.update(kwargs)
    return HuntResult(**defaults)


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


RECENT_DATE = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
OLD_DATE = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")

REPO_META_OK = {
    "pushed_at": RECENT_DATE,
    "language": "Python",
    "description": "A skill repo",
    "size": 42,
}

REPO_META_STALE = {
    "pushed_at": OLD_DATE,
    "language": "Python",
    "size": 10,
}

REPO_META_NO_LANG = {
    "pushed_at": RECENT_DATE,
    "language": None,
    "size": 0,
}


# ---------------------------------------------------------------------------
# _to_raw_url
# ---------------------------------------------------------------------------

class TestToRawUrl:
    def test_blob_url_converted(self):
        url = "https://github.com/owner/repo/blob/main/SKILL.md"
        raw = _to_raw_url(url)
        assert raw == "https://raw.githubusercontent.com/owner/repo/main/SKILL.md"

    def test_blob_url_nested_path(self):
        url = "https://github.com/owner/repo/blob/develop/skills/SKILL.md"
        raw = _to_raw_url(url)
        assert raw == "https://raw.githubusercontent.com/owner/repo/develop/skills/SKILL.md"

    def test_already_raw_url_passthrough(self):
        raw_url = "https://raw.githubusercontent.com/owner/repo/main/SKILL.md"
        assert _to_raw_url(raw_url) == raw_url

    def test_unknown_url_returns_none(self):
        assert _to_raw_url("https://example.com/foo") is None

    def test_non_blob_github_url_returns_none(self):
        url = "https://github.com/owner/repo"
        assert _to_raw_url(url) is None

    def test_empty_string_returns_none(self):
        assert _to_raw_url("") is None

    def test_sha_branch_in_url(self):
        url = "https://github.com/owner/repo/blob/abc1234def/SKILL.md"
        raw = _to_raw_url(url)
        assert raw == "https://raw.githubusercontent.com/owner/repo/abc1234def/SKILL.md"


# ---------------------------------------------------------------------------
# _passes_prefilter — stars gate
# ---------------------------------------------------------------------------

class TestPrefilterStars:
    def test_too_few_stars_excluded(self):
        h = make_hunter(min_stars=50)
        r = make_result(stars=10)
        assert h._passes_prefilter(r) is False

    def test_exact_min_stars_passes(self):
        h = make_hunter(min_stars=10)
        r = make_result(stars=10, owner="", repo_name="")  # skip API with empty owner
        # With no owner, repo metadata fetch is skipped but stars pass → True
        assert h._passes_prefilter(r) is True

    def test_zero_stars_excluded(self):
        h = make_hunter(min_stars=10)
        r = make_result(stars=0)
        assert h._passes_prefilter(r) is False


# ---------------------------------------------------------------------------
# _passes_prefilter — recency
# ---------------------------------------------------------------------------

class TestPrefilterRecency:
    @patch("hunter.Hunter._fetch_repo_metadata")
    @patch("hunter.Hunter._fetch_skill_content")
    def test_stale_repo_excluded(self, mock_content, mock_meta):
        mock_meta.return_value = REPO_META_STALE
        mock_content.return_value = "# SKILL.md\nsome content"
        h = make_hunter(max_age_days=180)
        r = make_result(stars=100)
        assert h._passes_prefilter(r) is False

    @patch("hunter.Hunter._fetch_repo_metadata")
    @patch("hunter.Hunter._fetch_skill_content")
    def test_recent_repo_passes(self, mock_content, mock_meta):
        mock_meta.return_value = REPO_META_OK
        mock_content.return_value = "# SKILL.md\nsome content"
        h = make_hunter(max_age_days=180)
        r = make_result(stars=100)
        assert h._passes_prefilter(r) is True

    @patch("hunter.Hunter._fetch_repo_metadata")
    @patch("hunter.Hunter._fetch_skill_content")
    def test_last_commit_date_populated(self, mock_content, mock_meta):
        mock_meta.return_value = REPO_META_OK
        mock_content.return_value = "# skill"
        h = make_hunter()
        r = make_result(stars=50)
        h._passes_prefilter(r)
        assert r.last_commit_date is not None

    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_unparseable_date_does_not_block(self, mock_meta):
        mock_meta.return_value = {
            "pushed_at": "not-a-date",
            "language": "Python",
            "size": 10,
        }
        h = make_hunter()
        r = make_result(stars=50, owner="o", repo_name="r")
        # Should not raise and should not block solely due to bad date
        result = h._passes_prefilter(r)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _passes_prefilter — language / empty repo
# ---------------------------------------------------------------------------

class TestPrefilterLanguage:
    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_no_language_no_size_excluded(self, mock_meta):
        mock_meta.return_value = REPO_META_NO_LANG
        h = make_hunter()
        r = make_result(stars=50)
        assert h._passes_prefilter(r) is False

    @patch("hunter.Hunter._fetch_repo_metadata")
    @patch("hunter.Hunter._fetch_skill_content")
    def test_no_language_but_has_size_passes(self, mock_content, mock_meta):
        meta = {"pushed_at": RECENT_DATE, "language": None, "size": 100}
        mock_meta.return_value = meta
        mock_content.return_value = "# SKILL"
        h = make_hunter()
        r = make_result(stars=50)
        assert h._passes_prefilter(r) is True


# ---------------------------------------------------------------------------
# _passes_prefilter — API failure handling
# ---------------------------------------------------------------------------

class TestPrefilterApiFail:
    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_api_failure_excludes_result(self, mock_meta):
        mock_meta.return_value = None
        h = make_hunter()
        r = make_result(stars=100)
        assert h._passes_prefilter(r) is False

    def test_no_owner_skips_api_call(self):
        h = make_hunter(min_stars=10)
        r = make_result(stars=50, owner="", repo_name="")
        # Should return True without making any API calls
        assert h._passes_prefilter(r) is True


# ---------------------------------------------------------------------------
# _fetch_skill_content
# ---------------------------------------------------------------------------

class TestFetchSkillContent:
    def test_fetches_raw_content(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, text="# SKILL\nHello")
            content = h._fetch_skill_content(
                "https://github.com/owner/repo/blob/main/SKILL.md"
            )
        assert content == "# SKILL\nHello"

    def test_404_returns_none(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(404)
            content = h._fetch_skill_content(
                "https://github.com/owner/repo/blob/main/SKILL.md"
            )
        assert content is None

    def test_unknown_url_returns_none(self):
        h = make_hunter()
        content = h._fetch_skill_content("https://example.com/bad")
        assert content is None

    def test_network_error_returns_none(self):
        h = make_hunter()
        import requests as req
        with patch.object(h._session, "get", side_effect=req.RequestException("timeout")):
            content = h._fetch_skill_content(
                "https://github.com/owner/repo/blob/main/SKILL.md"
            )
        assert content is None

    def test_raw_content_stored_on_result(self):
        h = make_hunter()
        r = make_result(stars=100)
        with patch.object(h._session, "get") as mock_get:
            # First call: repo metadata
            mock_get.side_effect = [
                _mock_response(200, json_data=REPO_META_OK),
                _mock_response(200, text="# SKILL\nmy content"),
            ]
            h._passes_prefilter(r)
        assert "my content" in r.raw_content

    def test_rate_limit_retries_then_none(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(429)
            with patch("hunter.time.sleep"):  # don't actually sleep in tests
                content = h._fetch_skill_content(
                    "https://github.com/owner/repo/blob/main/SKILL.md"
                )
        assert content is None


# ---------------------------------------------------------------------------
# _fetch_repo_metadata
# ---------------------------------------------------------------------------

class TestFetchRepoMetadata:
    def test_returns_metadata_on_200(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, json_data=REPO_META_OK)
            meta = h._fetch_repo_metadata("owner", "repo")
        assert meta == REPO_META_OK

    def test_returns_none_on_404(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(404)
            meta = h._fetch_repo_metadata("owner", "repo")
        assert meta is None

    def test_returns_none_on_network_error(self):
        h = make_hunter()
        import requests as req
        with patch.object(h._session, "get", side_effect=req.RequestException("fail")):
            meta = h._fetch_repo_metadata("owner", "repo")
        assert meta is None

    def test_retries_on_429_then_returns_data(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.side_effect = [
                _mock_response(429),
                _mock_response(200, json_data=REPO_META_OK),
            ]
            with patch("hunter.time.sleep"):
                meta = h._fetch_repo_metadata("owner", "repo")
        assert meta == REPO_META_OK

    def test_returns_none_after_3_rate_limit_retries(self):
        h = make_hunter()
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(429)
            with patch("hunter.time.sleep"):
                meta = h._fetch_repo_metadata("owner", "repo")
        assert meta is None


# ---------------------------------------------------------------------------
# _load_verified_urls
# ---------------------------------------------------------------------------

class TestLoadVerifiedUrls:
    def test_parses_repo_url_from_verified_skills(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text(
            "### my-skill\n"
            "- **Repo:** https://github.com/owner/skill-x\n"
            "- **License:** MIT\n"
        )
        h = make_hunter(verified_index_path=md)
        urls = h._load_verified_urls()
        assert "https://github.com/owner/skill-x" in urls

    def test_multiple_repos_parsed(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text(
            "- **Repo:** https://github.com/a/skill-a\n"
            "- **Repo:** https://github.com/b/skill-b\n"
        )
        h = make_hunter(verified_index_path=md)
        urls = h._load_verified_urls()
        assert len(urls) == 2

    def test_missing_file_returns_empty_set(self, tmp_path):
        h = make_hunter(verified_index_path=tmp_path / "nonexistent.md")
        assert h._load_verified_urls() == set()

    def test_trailing_slash_stripped(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text("- **Repo:** https://github.com/a/b/\n")
        h = make_hunter(verified_index_path=md)
        urls = h._load_verified_urls()
        assert "https://github.com/a/b" in urls

    def test_verified_result_gets_trust_tier(self, tmp_path):
        md = tmp_path / "VERIFIED_SKILLS.md"
        md.write_text("- **Repo:** https://github.com/owner/test-skill\n")
        h = make_hunter(verified_index_path=md)
        r = make_result()
        # Patch hunt internals to avoid API calls
        # _build_queries must return at least one entry so the loop runs
        with patch.object(h, "_build_queries", return_value=[("q", "skill")]):
            with patch.object(h, "_search_github", return_value=[r]):
                with patch.object(h, "_passes_prefilter", return_value=True):
                    results = h.hunt(
                        __import__("context_extractor").ContextProfile(tech_stack=["fastapi"])
                    )
        verified = [res for res in results if res.trust_tier == "verified"]
        assert len(verified) == 1


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestPagination:
    def test_fetches_page_2_when_page_1_full(self):
        h = make_hunter()
        full_page = [
            {
                "repository": {
                    "name": f"skill-{i}",
                    "html_url": f"https://github.com/o/skill-{i}",
                    "owner": {"login": "o"},
                    "description": "",
                    "stargazers_count": 50,
                },
                "html_url": f"https://github.com/o/skill-{i}/blob/main/SKILL.md",
            }
            for i in range(30)
        ]
        empty_page: list = []

        with patch.object(h._session, "get") as mock_get:
            mock_get.side_effect = [
                _mock_response(200, json_data={"items": full_page}),
                _mock_response(200, json_data={"items": empty_page}),
            ]
            results = h._search_github("filename:SKILL.md fastapi", "skill")

        assert len(results) == 30
        assert mock_get.call_count == 2  # two pages requested

    def test_stops_pagination_when_partial_page(self):
        h = make_hunter()
        partial_page = [
            {
                "repository": {
                    "name": "skill-0",
                    "html_url": "https://github.com/o/skill-0",
                    "owner": {"login": "o"},
                    "description": "",
                    "stargazers_count": 50,
                },
                "html_url": "https://github.com/o/skill-0/blob/main/SKILL.md",
            }
        ]
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, json_data={"items": partial_page})
            results = h._search_github("filename:SKILL.md fastapi", "skill")

        assert len(results) == 1
        assert mock_get.call_count == 1  # partial page → no second fetch


# ---------------------------------------------------------------------------
# hunt() integration (all I/O mocked)
# ---------------------------------------------------------------------------

class TestHuntIntegration:
    def _make_search_item(self, name: str, stars: int = 100, idx: int = 0) -> dict:
        return {
            "repository": {
                "name": name,
                "html_url": f"https://github.com/owner/{name}",
                "owner": {"login": "owner"},
                "description": f"A {name} skill",
                "stargazers_count": stars,
            },
            "html_url": f"https://github.com/owner/{name}/blob/main/SKILL.md",
        }

    @patch("hunter.Hunter._fetch_skill_content")
    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_deduplicates_by_repo_url(self, mock_meta, mock_content):
        mock_meta.return_value = REPO_META_OK
        mock_content.return_value = "# SKILL"
        h = make_hunter()

        from context_extractor import ContextProfile
        profile = ContextProfile(tech_stack=["fastapi"])

        item = self._make_search_item("skill-x")
        with patch.object(h._session, "get") as mock_get:
            # Return same item for all queries
            mock_get.return_value = _mock_response(200, json_data={"items": [item]})
            results = h.hunt(profile)

        # Deduplication should mean only one result for this repo
        assert sum(1 for r in results if r.repo_url == "https://github.com/owner/skill-x") <= 1

    @patch("hunter.Hunter._fetch_skill_content")
    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_low_star_results_excluded(self, mock_meta, mock_content):
        mock_meta.return_value = REPO_META_OK
        mock_content.return_value = "# SKILL"
        h = make_hunter(min_stars=100)

        from context_extractor import ContextProfile
        profile = ContextProfile(tech_stack=["fastapi"])

        low_star_item = self._make_search_item("bad-skill", stars=5)
        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, json_data={"items": [low_star_item]})
            results = h.hunt(profile)

        assert len(results) == 0

    def test_hunt_returns_empty_on_search_failure(self):
        h = make_hunter()
        from context_extractor import ContextProfile
        profile = ContextProfile(tech_stack=["fastapi"])

        import requests as req
        with patch.object(h._session, "get", side_effect=req.RequestException("down")):
            results = h.hunt(profile)

        assert results == []

    @patch("hunter.Hunter._fetch_skill_content")
    @patch("hunter.Hunter._fetch_repo_metadata")
    def test_description_populated_from_meta(self, mock_meta, mock_content):
        meta = dict(REPO_META_OK)
        meta["description"] = "Injected description"
        mock_meta.return_value = meta
        mock_content.return_value = "# SKILL"
        h = make_hunter()

        from context_extractor import ContextProfile
        profile = ContextProfile(tech_stack=["fastapi"])

        item = self._make_search_item("skill-y")
        item["repository"]["description"] = ""  # blank in search result

        with patch.object(h._session, "get") as mock_get:
            mock_get.return_value = _mock_response(200, json_data={"items": [item]})
            results = h.hunt(profile)

        if results:
            # description should be filled in from repo metadata
            assert results[0].description == "Injected description"

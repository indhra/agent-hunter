"""
hunter.py — Hunt GitHub for SKILL.md files and MCP server configs.

Responsibility:
    Given a ContextProfile, search GitHub for relevant skills and MCP servers.
    Apply the pre-filter pipeline before returning results.
    Consult trust tiers in order: Verified → Community → Raw GitHub.

Input:  ContextProfile, optional GITHUB_TOKEN
Output: List[HuntResult] (unscored — scoring is done by scorer.py)

Rate limits:
    Authenticated (GITHUB_TOKEN set): 5,000 requests/hour
    Unauthenticated: 60 requests/hour

No LLM calls. Network access to GitHub API only.
"""

from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from context_extractor import ContextProfile
from mcp_parser import parse_mcp_json, is_mcp_server_py


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
SEARCH_ENDPOINT = f"{GITHUB_API}/search/code"
PRE_FILTER_MIN_STARS = 10
PRE_FILTER_MAX_AGE_DAYS = 180
RATE_LIMIT_BACKOFF_SECONDS = 60


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class HuntResult:
    name: str = ""
    repo_url: str = ""
    raw_url: str = ""
    skill_url: str = ""
    description: str = ""
    stars: int = 0
    last_commit_date: Optional[datetime] = None
    owner: str = ""
    repo_name: str = ""
    license: str = ""
    contributors_count: int = 0
    result_type: str = "skill"           # "skill" or "mcp"
    trust_tier: str = "raw"             # "verified", "community", "raw"
    git_tree_sha: str = ""
    raw_content: str = ""               # raw SKILL.md/mcp.json content
    # MCP-specific fields
    mcp_transport_type: str = ""        # "stdio", "sse", "http" (MCP only)
    mcp_install_command: str = ""       # e.g., "npx @mcp/server-name" (MCP only)
    mcp_capabilities: list[str] = None  # ["resources", "tools", "prompts"] (MCP only)

    def __post_init__(self) -> None:
        if self.mcp_capabilities is None:
            self.mcp_capabilities = []


# ---------------------------------------------------------------------------
# Main hunter
# ---------------------------------------------------------------------------

class Hunter:
    """GitHub skill and MCP server hunter."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        min_stars: int = PRE_FILTER_MIN_STARS,
        max_age_days: int = PRE_FILTER_MAX_AGE_DAYS,
        include_mcp: bool = True,
        verified_index_path: Optional[Path] = None,
    ) -> None:
        self.token = github_token or os.environ.get("GITHUB_TOKEN")
        self.min_stars = min_stars
        self.max_age_days = max_age_days
        self.include_mcp = include_mcp
        self.verified_index_path = verified_index_path
        self._session = requests.Session()
        if self.token:
            self._session.headers["Authorization"] = f"Bearer {self.token}"
        self._session.headers["Accept"] = "application/vnd.github+json"
        self._session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        # Cache verified URLs at init time — file doesn't change during a hunt
        self._verified_urls_cache: Optional[set[str]] = None

    def hunt(self, profile: ContextProfile) -> list[HuntResult]:
        """Run the full hunt pipeline for a given ContextProfile.

        Args:
            profile: ContextProfile from context_extractor.py.

        Returns:
            List of HuntResult objects that passed pre-filtering,
            deduplicated by repo URL. Trust tier assigned.
        """
        results: dict[str, HuntResult] = {}  # keyed by repo_url for dedup

        # --- Query construction ---
        queries = self._build_queries(profile)

        for query, result_type in queries:
            batch = self._search_github(query, result_type)
            for r in batch:
                if r.repo_url not in results:
                    results[r.repo_url] = r

        # --- Pre-filter (parallel to avoid serial API call bottleneck) ---
        filtered = self._prefilter_parallel(list(results.values()))

        # --- Assign trust tiers ---
        verified_urls = self._get_verified_urls()
        for r in filtered:
            if r.repo_url in verified_urls:
                r.trust_tier = "verified"
            # Community tier: TODO in v0.2.1 — check community-reviewed list

        return filtered

    def _build_queries(self, profile: ContextProfile) -> list[tuple[str, str]]:
        """Build a list of (query_string, result_type) tuples."""
        queries = []

        # Per-technology skill queries
        for tech in profile.tech_stack[:5]:  # top 5 to stay within rate limits
            queries.append((f"filename:SKILL.md {tech}", "skill"))

        # Domain-level skill query
        if profile.domain_tags:
            domain_q = " ".join(profile.domain_tags[:3])
            queries.append((f"filename:SKILL.md language:markdown {domain_q}", "skill"))

        # MCP server queries
        if self.include_mcp:
            for tech in profile.tech_stack[:3]:
                queries.append((f"filename:mcp.json {tech}", "mcp"))
                queries.append((f'filename:server.py "mcp" {tech}', "mcp"))

        return queries

    def _prefilter_parallel(
        self, candidates: list[HuntResult], max_workers: int = 5
    ) -> list[HuntResult]:
        """Run _passes_prefilter concurrently to avoid serial API call bottleneck.

        Uses a bounded thread pool (max_workers=5) to stay well within
        rate limits while eliminating the O(N) sequential wait time.
        """
        if not candidates:
            return []

        passed: list[HuntResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self._passes_prefilter, r): r for r in candidates}
            for fut in as_completed(futures):
                try:
                    if fut.result():
                        passed.append(futures[fut])
                except Exception as exc:
                    r = futures[fut]
                    print(f"[agent-hunter] Prefilter error for {r.repo_url}: {exc}")
        return passed

    def _get_verified_urls(self) -> set[str]:
        """Return verified URLs, loading and caching from disk on first call."""
        if self._verified_urls_cache is None:
            self._verified_urls_cache = self._load_verified_urls()
        return self._verified_urls_cache

    def _search_github(self, query: str, result_type: str) -> list[HuntResult]:
        """Execute a GitHub code search query with simple pagination.

        Fetches up to two pages (page 1 + page 2, 30 results each = up to 60)
        to improve recall without hammering rate limits on unauthenticated access.
        """
        results: list[HuntResult] = []
        for page in range(1, 3):  # pages 1 and 2
            batch = self._search_github_page(query, result_type, page)
            results.extend(batch)
            if len(batch) < 30:
                break  # last page — no point fetching next
        return results

    def _search_github_page(self, query: str, result_type: str, page: int = 1) -> list[HuntResult]:
        """Fetch a single page of GitHub code search results."""
        for attempt in range(3):
            try:
                resp = self._session.get(
                    SEARCH_ENDPOINT,
                    params={"q": query, "per_page": 30, "page": page},
                    timeout=15,
                )
            except requests.RequestException as exc:
                print(f"[agent-hunter] Search failed for '{query}': {exc}")
                return []

            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RATE_LIMIT_BACKOFF_SECONDS))
                print(f"[agent-hunter] Rate limited searching. Waiting {wait}s (attempt {attempt+1}/3)...")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                print(f"[agent-hunter] GitHub API error {resp.status_code} for query: {query}")
                return []

            items = resp.json().get("items", [])
            break
        else:
            return []

        results = []
        for item in items:
            repo = item.get("repository", {})
            r = HuntResult(
                name=repo.get("name", ""),
                repo_url=repo.get("html_url", ""),
                raw_url=item.get("html_url", ""),
                owner=repo.get("owner", {}).get("login", ""),
                repo_name=repo.get("name", ""),
                description=repo.get("description") or "",
                stars=repo.get("stargazers_count", 0),
                result_type=result_type,
                trust_tier="raw",
            )
            results.append(r)

        return results

    def _passes_prefilter(self, r: HuntResult) -> bool:
        """Apply pre-filter pipeline to a single result.

        Checks (in order):
            1. Stars >= min_stars (fast, no extra API call).
            2. Repo pushed_at recency (fetches repo metadata via GitHub API).
            3. Repo has at least one code language (not a docs-only repo).
            4. For skills: fetch raw SKILL.md content and store it.
            5. For MCP: fetch mcp.json/server.py and extract metadata.

        Returns:
            True if the result passes all checks, False to exclude it.
        """
        # 1. Stars check — fast, already populated from search results
        if r.stars < self.min_stars:
            return False

        # 2 & 3. Fetch repo metadata for recency + language checks
        if r.owner and r.repo_name:
            meta = self._fetch_repo_metadata(r.owner, r.repo_name)
            if meta is None:
                # Could not verify — skip rather than show unverified result
                return False

            pushed_at_str = meta.get("pushed_at") or meta.get("updated_at")
            if pushed_at_str:
                try:
                    pushed_at = datetime.fromisoformat(pushed_at_str.rstrip("Z"))
                    r.last_commit_date = pushed_at
                    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=self.max_age_days)
                    if pushed_at < cutoff:
                        return False
                except ValueError:
                    pass  # unparseable date — don't block on it

            # Repos with no detected language are likely docs-only; skip
            if meta.get("language") is None and meta.get("size", 1) == 0:
                return False

            # Carry over description if we don't have one yet
            if not r.description and meta.get("description"):
                r.description = meta["description"] or ""

        # 4 & 5. Fetch and parse content (SKILL.md for skills, mcp.json for MCP)
        if r.result_type == "skill" and r.raw_url and not r.raw_content:
            content = self._fetch_skill_content(r.raw_url)
            if content is not None:
                r.raw_content = content
        elif r.result_type == "mcp" and r.raw_url and not r.raw_content:
            # Try to fetch mcp.json first, fall back to server.py detection
            content = self._fetch_mcp_json(r.raw_url, r.owner, r.repo_name)
            if content:
                r.raw_content = content
                mcp_meta = parse_mcp_json(content)
                if mcp_meta:
                    r.name = mcp_meta.name or r.repo_name
                    r.mcp_transport_type = mcp_meta.transport_type
                    r.mcp_install_command = mcp_meta.install_command
                    r.mcp_capabilities = mcp_meta.capabilities

        return True

    def _fetch_repo_metadata(self, owner: str, repo_name: str) -> Optional[dict]:
        """Fetch repository metadata from GitHub API.

        Args:
            owner: Repository owner login.
            repo_name: Repository name.

        Returns:
            Dict of repo fields, or None on failure.
        """
        url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
        for attempt in range(3):
            try:
                resp = self._session.get(url, timeout=10)
            except requests.RequestException as exc:
                print(f"[agent-hunter] Repo metadata fetch failed ({owner}/{repo_name}): {exc}")
                return None

            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RATE_LIMIT_BACKOFF_SECONDS))
                print(f"[agent-hunter] Rate limited fetching repo metadata. Waiting {wait}s...")
                time.sleep(wait)
                continue
            # Any other error
            print(f"[agent-hunter] GitHub API {resp.status_code} for {owner}/{repo_name}")
            return None
        return None

    def _fetch_skill_content(self, html_url: str) -> Optional[str]:
        """Fetch raw SKILL.md content from GitHub.

        Converts a GitHub blob URL to a raw.githubusercontent.com URL:
            https://github.com/owner/repo/blob/main/SKILL.md
            → https://raw.githubusercontent.com/owner/repo/main/SKILL.md

        Also handles direct raw URLs passed through unchanged.

        Args:
            html_url: GitHub HTML URL of the SKILL.md file.

        Returns:
            Raw content string, or None on failure.
        """
        raw_url = _to_raw_url(html_url)
        if raw_url is None:
            return None

        for attempt in range(3):
            try:
                resp = self._session.get(raw_url, timeout=15)
            except requests.RequestException as exc:
                print(f"[agent-hunter] Content fetch failed ({raw_url}): {exc}")
                return None

            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return None
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", RATE_LIMIT_BACKOFF_SECONDS))
                print(f"[agent-hunter] Rate limited fetching content. Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"[agent-hunter] GitHub {resp.status_code} fetching: {raw_url}")
            return None
        return None

    def _fetch_mcp_json(self, html_url: str, owner: str, repo_name: str) -> Optional[str]:
        """Fetch mcp.json or detect MCP server from GitHub.

        Tries in order:
            1. Direct mcp.json file in repo root
            2. server.py file (check for MCP imports)

        Args:
            html_url: GitHub HTML URL (usually from search result)
            owner: Repository owner
            repo_name: Repository name

        Returns:
            mcp.json content if found, server.py content if MCP-like, None otherwise.
        """
        # Try mcp.json in root
        mcp_json_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/mcp.json"
        resp = None
        try:
            resp = self._session.get(mcp_json_url, timeout=10)
            if resp.status_code == 200:
                return resp.text
        except requests.RequestException:
            pass

        # Fallback: try server.py to detect MCP pattern
        server_py_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/main/server.py"
        try:
            resp = self._session.get(server_py_url, timeout=10)
            if resp.status_code == 200:
                content = resp.text
                if is_mcp_server_py(content):
                    return content
        except requests.RequestException:
            pass

        return None

    def _load_verified_urls(self) -> set[str]:
        """Load verified skill repo URLs from VERIFIED_SKILLS.md.

        Parses lines matching:
            - **Repo:** https://github.com/owner/repo

        Returns:
            Set of GitHub repo HTML URLs that are verified.
        """
        index_path = self.verified_index_path or (
            Path(__file__).parent.parent / "references" / "VERIFIED_SKILLS.md"
        )
        if not index_path.exists():
            return set()

        urls: set[str] = set()
        repo_line = re.compile(r"\*\*Repo:\*\*\s*(https://github\.com/[^\s]+)")
        try:
            for line in index_path.read_text(encoding="utf-8").splitlines():
                m = repo_line.search(line)
                if m:
                    urls.add(m.group(1).rstrip("/"))
        except OSError:
            pass
        return urls


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_GITHUB_BLOB_RE = re.compile(
    r"^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$"
)


def _to_raw_url(html_url: str) -> Optional[str]:
    """Convert a GitHub blob URL to a raw.githubusercontent.com URL.

    Handles:
        https://github.com/owner/repo/blob/main/SKILL.md
        → https://raw.githubusercontent.com/owner/repo/main/SKILL.md

    Also passes through raw.githubusercontent.com URLs unchanged.

    Returns:
        Raw URL string, or None if the URL is unrecognised.
    """
    if html_url.startswith("https://raw.githubusercontent.com/"):
        return html_url
    m = _GITHUB_BLOB_RE.match(html_url)
    if not m:
        return None
    owner, repo, branch, path = m.groups()
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys
    from context_extractor import extract_context

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    profile = extract_context(root)

    hunter = Hunter()
    results = hunter.hunt(profile)

    print(f"\n[agent-hunter] Found {len(results)} results after pre-filtering\n")
    for r in results[:10]:
        print(f"  {r.trust_tier:12} {r.stars:5}⭐  {r.repo_url}")

"""
context_extractor.py — Extract tech signal keywords from the current project.

Responsibility:
    Read dependency manifests ONLY and extract tech signal keywords from an
    explicit allowlist. Never read docs, README files, git commit messages,
    or agent instruction files (CLAUDE.md, SKILL.md, etc.).

Allowed sources:
    requirements.txt, requirements-dev.txt, requirements-test.txt,
    pyproject.toml, package.json, Cargo.toml, go.mod

Forbidden sources (produce false signals from documentation mentions):
    CLAUDE.md, SKILL.md, any *.md file, README files,
    git commit message bodies, YAML frontmatter trigger/description fields

Input:  Project root directory (str or Path)
Output: ContextProfile dataclass

Privacy guarantee:
    Only keywords from TECH_ALLOWLIST cross any boundary.
    After extraction, signals are printed to stdout so the user
    can verify exactly what was found.

No LLM calls. No network access.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# Tech signal allowlist — the ONLY strings that may be extracted
# ---------------------------------------------------------------------------
# Add new entries here to expand context detection.
# Rule: only library/framework/tool names, never project-specific strings.

TECH_ALLOWLIST: set[str] = {
    # Python web
    "fastapi",
    "django",
    "flask",
    "starlette",
    "tornado",
    "aiohttp",
    "sanic",
    # Python data / ML
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "scikit-learn",
    "pytorch",
    "tensorflow",
    "keras",
    "xgboost",
    "lightgbm",
    "polars",
    "dask",
    "ray",
    "mlflow",
    "wandb",
    "huggingface",
    "transformers",
    "langchain",
    "llamaindex",
    "pydantic",
    # Python infra
    "celery",
    "redis",
    "sqlalchemy",
    "alembic",
    "asyncpg",
    "psycopg2",
    "pymongo",
    "elasticsearch",
    "kafka",
    "rabbitmq",
    "boto3",
    "aws",
    "gcp",
    "azure",
    # Python testing / tooling
    "pytest",
    "unittest",
    "hypothesis",
    "mypy",
    "ruff",
    "black",
    "isort",
    # Node / JS
    "react",
    "nextjs",
    "next.js",
    "vue",
    "nuxt",
    "angular",
    "svelte",
    "express",
    "fastify",
    "nestjs",
    "graphql",
    "apollo",
    "prisma",
    "typescript",
    "javascript",
    "node",
    "nodejs",
    "bun",
    "deno",
    # Databases
    "postgres",
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "dynamodb",
    "cassandra",
    "clickhouse",
    "bigquery",
    "snowflake",
    "supabase",
    # Infrastructure
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "pulumi",
    "ansible",
    "nginx",
    "caddy",
    "traefik",
    "cloudflare",
    # Languages
    "python",
    "rust",
    "go",
    "golang",
    "java",
    "kotlin",
    "swift",
    "ruby",
    "elixir",
    "haskell",
    "c++",
    "cpp",
    # CI / DevOps
    "github-actions",
    "circleci",
    "gitlab-ci",
    "jenkins",
    "argocd",
    # Python utilities
    "requests",
    "httpx",
    "rich",
    "click",
    "typer",
    "pyyaml",
    "yaml",
    # AI / Agent
    "claude",
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "langchain",
    "mcp",
    "agentskills",
}

# Pattern: word boundary around each allowlisted term (case-insensitive)
_ALLOWLIST_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(TECH_ALLOWLIST, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SkillUsage:
    """Track a skill's usage: when last invoked and how many times."""

    skill_name: str
    last_seen: datetime
    mention_count: int


@dataclass
class ContextProfile:
    tech_stack: list[str] = field(default_factory=list)  # all detected tech
    domain_tags: list[str] = field(default_factory=list)  # inferred domains
    intent_keywords: list[str] = field(default_factory=list)  # dynamic user intent
    active_domains: list[str] = field(default_factory=list)  # commits in last 7d
    recent_domains: list[str] = field(default_factory=list)  # commits in last 30d
    dormant_domains: list[str] = field(default_factory=list)  # no commits in 90+d
    sources_read: list[str] = field(default_factory=list)  # files that were read
    extraction_warnings: list[str] = field(default_factory=list)
    session_skills: list[SkillUsage] = field(default_factory=list)  # recently invoked skills


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def extract_context(project_root: str | Path, intent: str | None = None) -> ContextProfile:
    """Extract tech signal keywords from a project directory.

    Reads dependency manifests only: requirements.txt, pyproject.toml,
    package.json, Cargo.toml, go.mod. Does NOT read docs, CLAUDE.md,
    SKILL.md, README files, or git commit messages.

    Args:
        project_root: Path to the project root directory.
        intent: Optional user intent string to focus the search.

    Returns:
        ContextProfile with tech_stack, domain_tags, and activity buckets.
    """
    root = Path(project_root).resolve()
    profile = ContextProfile()
    all_signals: set[str] = set()

    if intent:
        # Extract alphanumeric words from intent, lowercase, ignore short words
        intent_words = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", intent) if len(w) > 2]
        profile.intent_keywords = intent_words

    # --- Read dependency files ---
    dep_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
    ]
    for fname in dep_files:
        fpath = root / fname
        if fpath.exists():
            signals = _extract_signals_from_file(fpath)
            all_signals.update(signals)
            profile.sources_read.append(fname)

    # --- Read git log for activity bucketing only (no signal extraction) ---
    # Commit messages are a forbidden signal source — they document intent, not deps.
    _, git_activity = _extract_from_git_log(root)
    if git_activity:
        profile.sources_read.append("git log (last 50)")

    profile.tech_stack = sorted(all_signals)
    profile.domain_tags = _infer_domain_tags(all_signals)

    # Bucket by git activity
    active_set = git_activity.get("active", set())
    recent_set = git_activity.get("recent", set())
    dormant_set = git_activity.get("dormant", set())
    profile.active_domains = _filter_by_activity(profile.tech_stack, active_set)
    profile.recent_domains = _filter_by_activity(profile.tech_stack, recent_set)
    profile.dormant_domains = _filter_by_activity(profile.tech_stack, dormant_set)

    # Extract recently invoked skills from ~/.claude/sessions/ (v0.1.5)
    profile.session_skills = _extract_session_skills()

    # Print signals for user verification (privacy transparency)
    print(f"[agent-hunter] Context extracted from: {', '.join(profile.sources_read)}")
    print(f"[agent-hunter] Tech signals found: {', '.join(profile.tech_stack)}")
    print(f"[agent-hunter] Domain tags: {', '.join(profile.domain_tags)}")
    if profile.session_skills:
        skills_str = ", ".join([s.skill_name for s in profile.session_skills])
        print(f"[agent-hunter] Recently invoked skills: {skills_str}")

    return profile


def _parse_skill_from_session(cwd: str) -> str | None:
    """Extract skill name from session cwd path. Returns None if not a skill session."""
    if "/.claude/skills/" not in cwd:
        return None
    parts = cwd.split("/.claude/skills/")
    if len(parts) <= 1:
        return None
    skill_name = parts[1].split("/")[0]
    if skill_name and not skill_name.startswith("."):
        return skill_name
    return None


def _update_skill_mention(skill_mentions: dict[str, dict], skill_name: str, ts: datetime) -> None:
    """Update skill mention count and timestamp."""
    if skill_name not in skill_mentions:
        skill_mentions[skill_name] = {"last_seen": ts, "mention_count": 0}
    skill_mentions[skill_name]["mention_count"] += 1
    if ts > skill_mentions[skill_name]["last_seen"]:
        skill_mentions[skill_name]["last_seen"] = ts


def _extract_session_skills() -> list[SkillUsage]:
    """
    Extract recently invoked skills from ~/.claude/sessions/.

    Reads session metadata files and aggregates skill mentions from
    the last 30 days. Returns list of SkillUsage sorted by most recent.

    Privacy: Only skill names are extracted — no file paths, no commands.

    Returns:
        List of SkillUsage objects sorted by last_seen (most recent first).
    """
    sessions_dir = Path.home() / ".claude" / "sessions"
    if not sessions_dir.exists():
        return []

    skill_mentions: dict[str, dict] = {}  # {skill_name: {last_seen, mention_count}}
    cutoff = datetime.now() - timedelta(days=30)

    try:
        for session_file in sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                cwd = data.get("cwd", "")
                skill_name = _parse_skill_from_session(cwd)
                if skill_name:
                    ts_ms = data.get("updatedAt", 0)
                    ts = datetime.fromtimestamp(ts_ms / 1000.0)
                    if ts >= cutoff:
                        _update_skill_mention(skill_mentions, skill_name, ts)
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                # Skip malformed session files
                continue
    except OSError:
        # Sessions directory might not be readable
        pass

    # Convert to SkillUsage list, sorted by most recent first
    results = [
        SkillUsage(
            skill_name=name,
            last_seen=info["last_seen"],
            mention_count=info["mention_count"],
        )
        for name, info in skill_mentions.items()
    ]
    return sorted(results, key=lambda s: s.last_seen, reverse=True)


def _extract_signals_from_file(path: Path) -> set[str]:
    """Extract allowlisted tech keywords from a single file."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    return {m.lower() for m in _ALLOWLIST_PATTERN.findall(content)}


def _filter_by_activity(tech_stack: list[str], activity_set: set[str]) -> list[str]:
    """Filter tech stack by activity.

    The sentinel value "__all__" means every tech in ``tech_stack`` is active
    for that bucket.

    Args:
        tech_stack: Technology names discovered from dependency manifests.
        activity_set: Bucket set containing tech names or "__all__".

    Returns:
        Filtered tech names that belong to the activity bucket. Returns an
        empty list when ``activity_set`` is empty.
    """
    return [tech for tech in tech_stack if "__all__" in activity_set or tech in activity_set]


def _extract_from_git_log(root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Extract activity buckets from git commit dates only.

    Privacy constraint: commit subjects are never read or parsed.

    Returns:
        Tuple of ``(signals, activity_buckets)`` where ``signals`` is always an
        empty set, and ``activity_buckets`` contains active/recent/dormant sets.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%ai", "-50"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return set(), {}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return set(), {}

    now = datetime.now()
    signals: set[str] = set()
    activity: dict[str, set[str]] = {"active": set(), "recent": set(), "dormant": set()}

    for line in result.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        try:
            # Parse date: "2026-04-15 10:30:00 +0000"
            date_str = f"{parts[0]} {parts[1]}"
            commit_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        age = now - commit_date
        if age <= timedelta(days=7):
            activity["active"].add("__all__")
        elif age <= timedelta(days=30):
            activity["recent"].add("__all__")
        elif age >= timedelta(days=90):
            activity["dormant"].add("__all__")

    return signals, activity


def _infer_domain_tags(signals: set[str]) -> list[str]:
    """Infer high-level domain tags from tech signals."""
    domain_map = {
        "backend": {"fastapi", "django", "flask", "express", "nestjs", "fastify"},
        "frontend": {"react", "vue", "angular", "svelte", "nextjs", "nuxt"},
        "ml": {"pytorch", "tensorflow", "sklearn", "scikit-learn", "xgboost", "mlflow"},
        "data": {"pandas", "polars", "dask", "bigquery", "snowflake", "clickhouse"},
        "infra": {"docker", "kubernetes", "terraform", "ansible"},
        "database": {"postgres", "mysql", "mongodb", "redis", "dynamodb", "sqlite"},
        "python": {"python", "fastapi", "django", "flask", "pytest", "pydantic"},
        "typescript": {"typescript", "react", "vue", "nextjs", "nestjs"},
        "rust": {"rust"},
        "go": {"go", "golang"},
        "ai-agent": {"claude", "openai", "langchain", "mcp", "agentskills"},
    }
    tags = []
    for domain, keywords in domain_map.items():
        if keywords & signals:
            tags.append(domain)
    return sorted(tags)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    profile = extract_context(root)
    print("\n--- Full Context Profile ---")
    print(f"Tech stack:      {profile.tech_stack}")
    print(f"Domain tags:     {profile.domain_tags}")
    print(f"Active domains:  {profile.active_domains}")
    print(f"Recent domains:  {profile.recent_domains}")
    print(f"Dormant domains: {profile.dormant_domains}")

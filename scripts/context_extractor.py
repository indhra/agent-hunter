"""
context_extractor.py — Extract tech signal keywords from the current project.

Responsibility:
    Read project files (CLAUDE.md, requirements.txt, pyproject.toml,
    package.json, Cargo.toml, git log) and extract ONLY tech signal
    keywords from an explicit allowlist. Never extract file paths,
    variable names, function names, or any project-specific strings.

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
    "fastapi", "django", "flask", "starlette", "tornado", "aiohttp", "sanic",
    # Python data / ML
    "pandas", "numpy", "scipy", "sklearn", "scikit-learn", "pytorch", "tensorflow",
    "keras", "xgboost", "lightgbm", "polars", "dask", "ray", "mlflow", "wandb",
    "huggingface", "transformers", "langchain", "llamaindex", "pydantic",
    # Python infra
    "celery", "redis", "sqlalchemy", "alembic", "asyncpg", "psycopg2", "pymongo",
    "elasticsearch", "kafka", "rabbitmq", "boto3", "aws", "gcp", "azure",
    # Python testing / tooling
    "pytest", "unittest", "hypothesis", "mypy", "ruff", "black", "isort",
    # Node / JS
    "react", "nextjs", "next.js", "vue", "nuxt", "angular", "svelte",
    "express", "fastify", "nestjs", "graphql", "apollo", "prisma",
    "typescript", "javascript", "node", "nodejs", "bun", "deno",
    # Databases
    "postgres", "postgresql", "mysql", "sqlite", "mongodb", "dynamodb",
    "cassandra", "clickhouse", "bigquery", "snowflake", "supabase",
    # Infrastructure
    "docker", "kubernetes", "k8s", "terraform", "pulumi", "ansible",
    "nginx", "caddy", "traefik", "cloudflare",
    # Languages
    "python", "rust", "go", "golang", "java", "kotlin", "swift",
    "ruby", "elixir", "haskell", "c++", "cpp",
    # CI / DevOps
    "github-actions", "circleci", "gitlab-ci", "jenkins", "argocd",
    # AI / Agent
    "claude", "openai", "anthropic", "gemini", "ollama", "langchain",
    "mcp", "agentskills", "skill.md",
}

# Pattern: word boundary around each allowlisted term (case-insensitive)
_ALLOWLIST_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in sorted(TECH_ALLOWLIST, key=len, reverse=True)) + r')\b',
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
    tech_stack: list[str] = field(default_factory=list)      # all detected tech
    domain_tags: list[str] = field(default_factory=list)      # inferred domains
    active_domains: list[str] = field(default_factory=list)   # commits in last 7d
    recent_domains: list[str] = field(default_factory=list)   # commits in last 30d
    dormant_domains: list[str] = field(default_factory=list)  # no commits in 90+d
    sources_read: list[str] = field(default_factory=list)     # files that were read
    extraction_warnings: list[str] = field(default_factory=list)
    session_skills: list[SkillUsage] = field(default_factory=list)  # recently invoked skills


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

def extract_context(project_root: str | Path) -> ContextProfile:
    """Extract tech signal keywords from a project directory.

    Reads: CLAUDE.md, AGENTS.md, requirements.txt, pyproject.toml,
    package.json, Cargo.toml, git log (last 50 commits).

    Args:
        project_root: Path to the project root directory.

    Returns:
        ContextProfile with tech_stack, domain_tags, and activity buckets.
    """
    root = Path(project_root).resolve()
    profile = ContextProfile()
    all_signals: set[str] = set()

    # --- Read dependency files ---
    dep_files = [
        "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
        "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    ]
    for fname in dep_files:
        fpath = root / fname
        if fpath.exists():
            signals = _extract_signals_from_file(fpath)
            all_signals.update(signals)
            profile.sources_read.append(fname)

    # --- Read agent instruction files ---
    agent_files = ["CLAUDE.md", "AGENTS.md", "COPILOT-instructions.md", ".cursorrules"]
    for fname in agent_files:
        fpath = root / fname
        if fpath.exists():
            signals = _extract_signals_from_file(fpath)
            all_signals.update(signals)
            profile.sources_read.append(fname)

    # --- Read git log (last 50 commits) ---
    git_signals, git_activity = _extract_from_git_log(root)
    all_signals.update(git_signals)
    if git_activity:
        profile.sources_read.append("git log (last 50)")

    profile.tech_stack = sorted(all_signals)
    profile.domain_tags = _infer_domain_tags(all_signals)

    # Bucket by git activity
    profile.active_domains = [t for t in profile.tech_stack if t in git_activity.get("active", set())]
    profile.recent_domains = [t for t in profile.tech_stack if t in git_activity.get("recent", set())]
    profile.dormant_domains = [t for t in profile.tech_stack if t in git_activity.get("dormant", set())]

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
                # Session file format: {pid, sessionId, cwd, startedAt, ...}
                # We look for mentions of skills in the cwd or any other available context
                # For now, we parse the cwd to detect project context
                cwd = data.get("cwd", "")
                # Extract skill names from cwd path (e.g., "~/.claude/skills/trusty/...")
                if "/.claude/skills/" in cwd:
                    parts = cwd.split("/.claude/skills/")
                    if len(parts) > 1:
                        skill_name = parts[1].split("/")[0]
                        if skill_name and not skill_name.startswith("."):
                            ts_ms = data.get("updatedAt", 0)
                            ts = datetime.fromtimestamp(ts_ms / 1000.0)
                            
                            if ts >= cutoff:
                                if skill_name not in skill_mentions:
                                    skill_mentions[skill_name] = {
                                        "last_seen": ts,
                                        "mention_count": 0,
                                    }
                                skill_mentions[skill_name]["mention_count"] += 1
                                # Update to most recent timestamp
                                if ts > skill_mentions[skill_name]["last_seen"]:
                                    skill_mentions[skill_name]["last_seen"] = ts
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


def _extract_from_git_log(root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Extract tech signals from git log. Returns (signals, activity_buckets)."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--format=%ai %s", "-50"],
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
        parts = line.split(" ", 3)
        if len(parts) < 4:
            continue
        try:
            # Parse date: "2026-04-15 10:30:00 +0000"
            date_str = f"{parts[0]} {parts[1]}"
            commit_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            commit_text = parts[3]  # commit message — extract signals only
        except (ValueError, IndexError):
            continue

        line_signals = {m.lower() for m in _ALLOWLIST_PATTERN.findall(commit_text)}
        signals.update(line_signals)

        age = now - commit_date
        for sig in line_signals:
            if age <= timedelta(days=7):
                activity["active"].add(sig)
            elif age <= timedelta(days=30):
                activity["recent"].add(sig)
            elif age >= timedelta(days=90):
                activity["dormant"].add(sig)

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

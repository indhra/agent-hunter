"""
skill_parser.py — Parse SKILL.md YAML frontmatter into a structured dict.

Responsibility:
    Extract metadata (name, description, version, license, author,
    mcp_dependencies, compatibility) from a SKILL.md file. Handles
    missing optional fields, malformed YAML, and files with no frontmatter.

Input:  Path to a SKILL.md file (str or Path)
Output: SkillMetadata dataclass

No LLM calls. No network access. Pure file parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkillParseError(Exception):
    """Raised when a SKILL.md file cannot be parsed."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class McpDependency:
    type: str  # e.g. "mcp_server"
    value: str  # e.g. "github.com/owner/mcp-server"
    description: str = ""
    transport: str = "stdio"


@dataclass
class SkillDependency:
    """A skill that agent-hunter can delegate to if installed and trusted."""

    name: str  # expected directory name in ~/.claude/skills/
    repo: str  # "owner/repo" on GitHub
    role: str  # e.g. "security_scan_delegate", "secondary_scanner"
    min_trust_tier: str = "community"  # minimum required tier: "verified", "community", "raw"
    optional: bool = True  # if False, abort when not satisfied
    fallback: str = "none"  # label for built-in fallback ("built_in_scanner", "none", etc.)


# Trust tier ordering (higher = more trusted)
TRUST_TIER_ORDER: dict[str, int] = {"verified": 3, "community": 2, "raw": 1}


@dataclass
class ResolvedDep:
    """Result of resolving one SkillDependency against installed skills."""

    dep: SkillDependency
    status: str  # "satisfied" | "not_installed" | "trust_insufficient" | "disabled"
    skill_path: Path | None
    trust_tier: str  # actual tier of the installed skill, or "" if not found
    use_fallback: bool  # True unless status == "satisfied"


@dataclass
class SkillMetadata:
    name: str = ""
    description: str = ""
    version: str = ""
    license: str = ""
    author: str = ""
    mcp_dependencies: list[McpDependency] = field(default_factory=list)
    skill_dependencies: list[SkillDependency] = field(default_factory=list)
    compatibility: dict[str, Any] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    body: str = ""  # raw SKILL.md body (after frontmatter)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)
    has_frontmatter: bool = False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_skill(path: str | Path) -> SkillMetadata:
    """Parse a SKILL.md file and return a SkillMetadata object.

    Args:
        path: Absolute or relative path to the SKILL.md file.

    Returns:
        SkillMetadata with all available fields populated.
        Missing optional fields default to empty string / empty list.

    Raises:
        SkillParseError: If the file cannot be read or YAML is malformed.
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SKILL.md not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SkillParseError(f"Cannot read {path}: {exc}") from exc

    return parse_skill_content(content)


def parse_skill_content(content: str) -> SkillMetadata:
    """Parse SKILL.md content string (useful for testing without a file).

    Args:
        content: Raw SKILL.md file content.

    Returns:
        SkillMetadata object.

    Raises:
        SkillParseError: If YAML frontmatter is present but malformed.
    """
    meta = SkillMetadata()
    match = FRONTMATTER_PATTERN.match(content)

    if not match:
        # No frontmatter — return body only
        meta.body = content.strip()
        return meta

    meta.has_frontmatter = True
    frontmatter_str = match.group(1)
    meta.body = content[match.end() :].strip()

    try:
        raw = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"Malformed YAML frontmatter: {exc}") from exc

    meta.raw_frontmatter = raw
    meta.name = str(raw.get("name", ""))
    meta.description = str(raw.get("description", ""))
    meta.version = str(raw.get("version", ""))
    meta.license = str(raw.get("license", ""))
    meta.author = str(raw.get("author", ""))
    meta.compatibility = raw.get("compatibility", {}) or {}
    meta.triggers = raw.get("triggers", []) or []

    # Parse mcp_dependencies
    raw_deps = raw.get("mcp_dependencies", []) or []
    for dep in raw_deps:
        if isinstance(dep, dict):
            meta.mcp_dependencies.append(
                McpDependency(
                    type=dep.get("type", ""),
                    value=dep.get("value", ""),
                    description=dep.get("description", ""),
                    transport=dep.get("transport", "stdio"),
                )
            )

    # Parse skill_dependencies
    raw_skill_deps = raw.get("skill_dependencies", []) or []
    for dep in raw_skill_deps:
        if isinstance(dep, dict) and dep.get("name") and dep.get("role"):
            meta.skill_dependencies.append(
                SkillDependency(
                    name=str(dep.get("name", "")),
                    repo=str(dep.get("repo", "")),
                    role=str(dep.get("role", "")),
                    min_trust_tier=str(dep.get("min_trust_tier", "community")),
                    optional=bool(dep.get("optional", True)),
                    fallback=str(dep.get("fallback", "none")),
                )
            )

    return meta


# ---------------------------------------------------------------------------
# Skill dependency resolver
# ---------------------------------------------------------------------------

_VERIFIED_SKILLS_PATH = Path(__file__).parent.parent / "references" / "VERIFIED_SKILLS.md"
_SKILLS_DIR = Path.home() / ".claude" / "skills"
_VERIFIED_REPO_PATTERN = re.compile(
    r"\*\*Repo:\*\*\s*https://github\.com/([\w.\-]+/[\w.\-]+)", re.IGNORECASE
)


def _load_verified_repos(verified_path: Path) -> frozenset[str]:
    """Return the set of 'owner/repo' strings listed in VERIFIED_SKILLS.md.

    Args:
        verified_path: Path to references/VERIFIED_SKILLS.md.

    Returns:
        frozenset of lowercase 'owner/repo' strings. Empty if file not found.
    """
    if not verified_path.exists():
        return frozenset()
    try:
        text = verified_path.read_text(encoding="utf-8")
        return frozenset(m.group(1).lower() for m in _VERIFIED_REPO_PATTERN.finditer(text))
    except OSError:
        return frozenset()


def resolve_skill_dependencies(
    dependencies: list[SkillDependency],
    skills_dir: Path | None = None,
    verified_skills_path: Path | None = None,
) -> dict[str, "ResolvedDep"]:
    """Check installed skills against declared skill_dependencies.

    For each dependency, looks in skills_dir for a matching directory,
    determines its trust tier (verified vs. raw), and checks whether it
    meets the declared min_trust_tier gate.

    Trust tiers (descending): verified > community > raw.
    Community tier is a v0.2.1 stub — currently all non-verified installs
    are treated as 'raw'.

    Args:
        dependencies: List of SkillDependency objects from frontmatter.
        skills_dir: Root directory for installed skills.
                    Defaults to ~/.claude/skills/.
        verified_skills_path: Path to references/VERIFIED_SKILLS.md.
                              Defaults to the bundled references file.

    Returns:
        dict keyed by role (SkillDependency.role) → ResolvedDep.
        If two deps share the same role, the last one wins.
    """
    sd = skills_dir if skills_dir is not None else _SKILLS_DIR
    vp = verified_skills_path if verified_skills_path is not None else _VERIFIED_SKILLS_PATH
    verified_repos = _load_verified_repos(vp)

    results: dict[str, ResolvedDep] = {}

    for dep in dependencies:
        resolved = _resolve_one(dep, sd, verified_repos)
        results[dep.role] = resolved

    return results


def _resolve_one(
    dep: SkillDependency,
    skills_dir: Path,
    verified_repos: frozenset[str],
) -> ResolvedDep:
    """Resolve a single SkillDependency against the filesystem."""
    # Candidate directory names: declared name, repo basename, disabled variant
    repo_basename = dep.repo.split("/")[-1] if "/" in dep.repo else dep.name
    candidates = [dep.name, repo_basename]
    candidates = list(dict.fromkeys(candidates))  # deduplicate, preserve order

    for candidate in candidates:
        active_path = skills_dir / candidate
        disabled_path = skills_dir / f"_{candidate}"

        if disabled_path.exists() and disabled_path.is_dir():
            return ResolvedDep(
                dep=dep,
                status="disabled",
                skill_path=disabled_path,
                trust_tier="",
                use_fallback=True,
            )

        if active_path.exists() and active_path.is_dir():
            tier = "verified" if dep.repo.lower() in verified_repos else "raw"
            required = TRUST_TIER_ORDER.get(dep.min_trust_tier, 1)
            actual = TRUST_TIER_ORDER.get(tier, 1)
            if actual >= required:
                return ResolvedDep(
                    dep=dep,
                    status="satisfied",
                    skill_path=active_path,
                    trust_tier=tier,
                    use_fallback=False,
                )
            return ResolvedDep(
                dep=dep,
                status="trust_insufficient",
                skill_path=active_path,
                trust_tier=tier,
                use_fallback=True,
            )

    return ResolvedDep(
        dep=dep,
        status="not_installed",
        skill_path=None,
        trust_tier="",
        use_fallback=True,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys
    import json

    if len(sys.argv) == 2 and sys.argv[1] == "--resolve-deps":
        # Resolve skill_dependencies declared in agent-hunter's own SKILL.md
        _own_skill_md = Path(__file__).parent.parent / "SKILL.md"
        try:
            _meta = parse_skill(_own_skill_md)
        except (SkillParseError, FileNotFoundError) as _e:
            print(f"ERROR: {_e}", file=sys.stderr)
            sys.exit(1)
        _resolved = resolve_skill_dependencies(_meta.skill_dependencies)
        _output: dict[str, object] = {}
        for _role, _r in _resolved.items():
            _output[_role] = {
                "status": _r.status,
                "trust_tier": _r.trust_tier,
                "use_fallback": _r.use_fallback,
                "fallback": _r.dep.fallback,
                "path": str(_r.skill_path) if _r.skill_path else None,
            }
        print(json.dumps(_output, indent=2))
    elif len(sys.argv) == 2:
        try:
            skill = parse_skill(sys.argv[1])
            print(
                json.dumps(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "version": skill.version,
                        "license": skill.license,
                        "author": skill.author,
                        "has_frontmatter": skill.has_frontmatter,
                        "triggers": skill.triggers,
                        "mcp_dependencies": [
                            {"type": d.type, "value": d.value, "transport": d.transport}
                            for d in skill.mcp_dependencies
                        ],
                        "skill_dependencies": [
                            {
                                "name": d.name,
                                "repo": d.repo,
                                "role": d.role,
                                "min_trust_tier": d.min_trust_tier,
                                "optional": d.optional,
                                "fallback": d.fallback,
                            }
                            for d in skill.skill_dependencies
                        ],
                    },
                    indent=2,
                )
            )
        except (SkillParseError, FileNotFoundError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: python skill_parser.py <path/to/SKILL.md>")
        print("       python skill_parser.py --resolve-deps")
        sys.exit(1)

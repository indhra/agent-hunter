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
    type: str                # e.g. "mcp_server"
    value: str               # e.g. "github.com/owner/mcp-server"
    description: str = ""
    transport: str = "stdio"


@dataclass
class SkillMetadata:
    name: str = ""
    description: str = ""
    version: str = ""
    license: str = ""
    author: str = ""
    mcp_dependencies: list[McpDependency] = field(default_factory=list)
    compatibility: dict[str, Any] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    body: str = ""           # raw SKILL.md body (after frontmatter)
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)
    has_frontmatter: bool = False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)


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
    meta.body = content[match.end():].strip()

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

    return meta


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) != 2:
        print("Usage: python skill_parser.py <path/to/SKILL.md>")
        sys.exit(1)

    try:
        skill = parse_skill(sys.argv[1])
        print(json.dumps({
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
        }, indent=2))
    except (SkillParseError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

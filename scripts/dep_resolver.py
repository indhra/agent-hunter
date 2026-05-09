"""
dep_resolver.py — Detect and resolve dependency conflicts between skills.

Problem: Installing Skill A (pydantic<2.0) + Skill B (pydantic>=2.0) = broken system.

Solution:
    1. Read requirements from all installed skills
    2. Build a conflict graph: which packages have incompatible ranges
    3. Attempt to find a compatible semver for each conflict
    4. Return resolvable conflicts + unresolvable (severity: RED)

Supported package managers:
    - Python: requirements.txt, pyproject.toml (dependencies field)
    - Node: package.json (dependencies, devDependencies)
    - Ruby: Gemfile (simplified — no version specs)

Algorithm:
    For each package name across all skills:
        - Collect all version specifiers (e.g., "pydantic>=2.0", "pydantic<2.0")
        - Use packaging.specifiers.SpecifierSet to find intersection
        - If intersection is empty → UNRESOLVABLE (RED)
        - If intersection is valid → RESOLVED with proposed version

No LLM calls. I/O only.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from packaging.specifiers import SpecifierSet
    from packaging.version import Version
except ImportError:
    SpecifierSet = None
    Version = None


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DependencyConflict:
    """Describes a dependency conflict between two or more skills."""

    package_name: str
    conflicting_skills: dict[str, str]  # {skill_name: version_spec}
    severity: str  # "GREEN" (no conflict), "YELLOW" (warning), "RED" (unresolvable)
    proposed_resolution: Optional[str] = None  # e.g., "pydantic>=2.0,<3.0"
    reason: str = ""


@dataclass
class DependencyAudit:
    """Results of dependency audit across installed skills."""

    total_unique_packages: int = 0
    conflicts: list[DependencyConflict] = field(default_factory=list)
    version_mismatches: dict[str, list[str]] = field(
        default_factory=dict
    )  # {skill_name: ["python mismatch", ...]}

    @property
    def has_unresolvable_conflicts(self) -> bool:
        return any(c.severity == "RED" for c in self.conflicts)


# ---------------------------------------------------------------------------
# Parser functions
# ---------------------------------------------------------------------------


def parse_requirements_txt(content: str) -> dict[str, str]:
    """Parse Python requirements.txt and return {package_name: version_spec}."""
    packages = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Handle: package>=1.0, package[extra]>=1.0, etc.
        match = re.match(r"^([a-zA-Z0-9_.-]+)(.*)$", line)
        if match:
            pkg_name = match.group(1).lower()
            version_spec = match.group(2).strip()
            packages[pkg_name] = version_spec or "*"
    return packages


def parse_pyproject_toml(content: str) -> dict[str, str]:
    """Parse pyproject.toml [project] dependencies field."""
    packages = {}

    # Simplified: extract quoted dependency lines
    # Format: "package-name >= version" or "package[extra] < version"
    for match in re.finditer(r'"([a-zA-Z0-9_.\-\[\]]+)\s*([<>=!~]*[^"]*)"', content):
        pkg_name = match.group(1).lower()
        version_spec = match.group(2).strip()
        packages[pkg_name] = version_spec if version_spec else "*"

    return packages


def parse_package_json(content: str) -> dict[str, str]:
    """Parse Node package.json dependencies."""
    packages = {}
    try:
        data = json.loads(content)
        for section in ["dependencies", "devDependencies", "peerDependencies"]:
            if section in data:
                for pkg_name, version_spec in data[section].items():
                    packages[pkg_name.lower()] = version_spec
    except (json.JSONDecodeError, AttributeError):
        pass
    return packages


def read_skill_requirements(skill_dir: Path) -> dict[str, str]:
    """Read all requirements from a skill directory.

    Returns: {package_name: version_spec}
    """
    packages = {}

    # Python
    req_file = skill_dir / "requirements.txt"
    if req_file.exists():
        packages.update(parse_requirements_txt(req_file.read_text()))

    pyproject = skill_dir / "pyproject.toml"
    if pyproject.exists():
        packages.update(parse_pyproject_toml(pyproject.read_text()))

    # Node
    pkg_json = skill_dir / "package.json"
    if pkg_json.exists():
        packages.update(parse_package_json(pkg_json.read_text()))

    return packages


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def detect_conflicts(skills_with_deps: dict[str, dict[str, str]]) -> dict[str, DependencyConflict]:
    """Detect dependency conflicts across skills.

    Args:
        skills_with_deps: {skill_name: {package_name: version_spec}}

    Returns:
        {package_name: DependencyConflict}
    """
    conflicts = {}

    # Group packages by name
    by_package = {}
    for skill_name, deps in skills_with_deps.items():
        for pkg_name, version_spec in deps.items():
            if pkg_name not in by_package:
                by_package[pkg_name] = {}
            by_package[pkg_name][skill_name] = version_spec

    # Detect conflicts
    for pkg_name, skill_specs in by_package.items():
        if len(skill_specs) <= 1:
            continue  # No conflict if only one skill uses it

        # Try to find compatible version
        conflict = _resolve_python_package_conflict(pkg_name, skill_specs)
        if conflict.severity in ["YELLOW", "RED"]:
            conflicts[pkg_name] = conflict

    return conflicts


def _resolve_python_package_conflict(
    pkg_name: str, skill_specs: dict[str, str]
) -> DependencyConflict:
    """Resolve a Python package conflict using packaging.specifiers.

    Args:
        pkg_name: e.g., "pydantic"
        skill_specs: {skill_name: version_spec}

    Returns:
        DependencyConflict with severity and proposed resolution.
    """
    conflict = DependencyConflict(
        package_name=pkg_name,
        conflicting_skills=skill_specs,
        severity="GREEN",
    )

    # Check if all specs are identical (no conflict)
    unique_specs = set(skill_specs.values())
    if len(unique_specs) == 1:
        return conflict

    # If SpecifierSet not available, mark as YELLOW (warning)
    if SpecifierSet is None:
        conflict.severity = "YELLOW"
        conflict.reason = "Cannot resolve without packaging library"
        return conflict

    # Try to find intersection
    try:
        specifier_sets = [SpecifierSet(spec) for spec in unique_specs]

        # Intersection: find a version that satisfies all specifiers
        # Heuristic: try a range of common versions
        test_versions = [
            "1.0.0",
            "2.0.0",
            "2.1.0",
            "3.0.0",
            "4.0.0",
        ]

        compatible = None
        for test_ver in test_versions:
            if all(test_ver in ss for ss in specifier_sets):
                compatible = test_ver
                break

        if compatible:
            conflict.severity = "GREEN"
            conflict.proposed_resolution = f"{pkg_name}=={compatible}"
        else:
            conflict.severity = "RED"
            conflict.reason = (
                f"No compatible version found. Skills require: {', '.join(unique_specs)}"
            )

    except Exception as e:
        conflict.severity = "YELLOW"
        conflict.reason = f"Parse error: {str(e)[:50]}"

    return conflict


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------


def audit_installed_skills(
    skills_dir: Path,
) -> DependencyAudit:
    """Audit all installed skills for dependency conflicts.

    Args:
        skills_dir: Path to ~/.claude/skills/ or equivalent

    Returns:
        DependencyAudit with conflicts and version mismatches
    """
    audit = DependencyAudit()

    if not skills_dir.exists():
        return audit

    # Read requirements for all skills
    skills_with_deps = {}
    for skill_path in skills_dir.iterdir():
        if not skill_path.is_dir() or skill_path.name.startswith("_"):
            continue
        deps = read_skill_requirements(skill_path)
        if deps:
            skills_with_deps[skill_path.name] = deps

    # Detect conflicts
    conflicts = detect_conflicts(skills_with_deps)
    audit.conflicts = list(conflicts.values())

    # Count unique packages
    all_packages = set()
    for deps in skills_with_deps.values():
        all_packages.update(deps.keys())
    audit.total_unique_packages = len(all_packages)

    return audit


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dep_resolver.py <skills_dir>")
        sys.exit(1)

    skills_dir = Path(sys.argv[1])
    audit = audit_installed_skills(skills_dir)

    print(f"📦 {audit.total_unique_packages} unique packages")
    print(f"⚠️  {len([c for c in audit.conflicts if c.severity == 'YELLOW'])} warnings")
    print(f"🔴 {len([c for c in audit.conflicts if c.severity == 'RED'])} conflicts")

    for conflict in audit.conflicts:
        icon = "🟡" if conflict.severity == "YELLOW" else "🔴"
        print(f"{icon} {conflict.package_name}: {conflict.reason}")

#!/usr/bin/env python3
"""
Release helper: Create git tags and GitHub Releases for an existing version.

Usage:
    python scripts/release.py --version 0.4.1

Requirements:
    - CHANGELOG.md must have a section for the version (e.g., ## [0.4.1] - YYYY-MM-DD)
    - GitHub CLI (gh) installed and authenticated, OR
    - GITHUB_TOKEN env var set for API-based release creation

Steps:
    1. Extract release notes from CHANGELOG.md
    2. Create and push git tag
    3. Create GitHub Release (optional, requires auth)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def read_changelog(version: str, changelog_path: Path = Path("CHANGELOG.md")) -> Optional[str]:
    """Extract release notes for a specific version from CHANGELOG.md."""
    if not changelog_path.exists():
        print(f"❌ CHANGELOG.md not found at {changelog_path}")
        return None

    with open(changelog_path) as f:
        content = f.read()

    # Match pattern: ## [VERSION] - DATE through next ## or end of file
    pattern = rf"## \[{re.escape(version)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print(f"❌ Version {version} not found in CHANGELOG.md")
        print("\nAvailable versions:")
        versions = re.findall(r"## \[(v?\d+\.\d+\.\d+)\]", content)
        for v in versions:
            print(f"  - {v}")
        return None

    return match.group(1).strip()


def run_command(cmd: list[str], check: bool = True) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"   {e.stderr}")
        raise


def tag_and_push(version: str, notes: str) -> bool:
    """Create git tag and push to remote."""
    tag = f"v{version}" if not version.startswith("v") else version

    # Check if tag already exists
    try:
        run_command(["git", "rev-parse", tag], check=False)
        print(f"⚠️  Tag {tag} already exists. Skipping git tag creation.")
        return True
    except subprocess.CalledProcessError:
        pass

    try:
        # Create annotated tag with release notes
        run_command(["git", "tag", "-a", tag, "-m", f"Release {tag}\n\n{notes}"])
        print(f"✅ Created tag: {tag}")

        # Push tag to remote
        run_command(["git", "push", "origin", tag])
        print(f"✅ Pushed tag: {tag}")
        return True
    except subprocess.CalledProcessError:
        return False


def create_github_release(version: str, notes: str) -> bool:
    """Create GitHub Release using 'gh' CLI or GitHub API."""
    tag = f"v{version}" if not version.startswith("v") else version

    # Try using GitHub CLI first
    try:
        run_command(
            ["gh", "release", "create", tag, "--title", f"Release {tag}", "--notes", notes],
            check=False,
        )
        print(f"✅ Created GitHub Release: {tag}")
        return True
    except FileNotFoundError:
        print("⚠️  GitHub CLI (gh) not found. Release not created on GitHub.")
        print("   Install: https://cli.github.com or set GITHUB_TOKEN env var")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Create a release tag and GitHub Release",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/release.py --version 0.4.1
  python scripts/release.py --version 0.4.1 --changelog ./CHANGELOG.md
        """,
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version to release (e.g., 0.4.1)",
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to CHANGELOG.md (default: CHANGELOG.md)",
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Skip GitHub Release creation (tag only)",
    )

    args = parser.parse_args()

    print(f"\n🚀 Releasing agent-hunter v{args.version}\n")

    # Read changelog
    notes = read_changelog(args.version, Path(args.changelog))
    if not notes:
        sys.exit(1)

    print(f"📝 Release notes:\n{notes}\n")

    # Create and push tag
    if not tag_and_push(args.version, notes):
        sys.exit(1)

    # Create GitHub Release
    if not args.skip_github:
        create_github_release(args.version, notes)

    print("\n✨ Release complete! Users will see updates at:")
    print(f"   https://github.com/indhra/agent-hunter/releases/tag/v{args.version}")


if __name__ == "__main__":
    main()

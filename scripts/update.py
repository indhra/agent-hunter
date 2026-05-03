"""
update.py — Update installed skills to newer versions.

Command: agent-hunter update [skill-name]

When audit detects "update_available" status, this command:
    1. Fetches remote content
    2. Shows a diff of what changed
    3. Prompts user for confirmation
    4. Updates if approved

Never auto-installs. Human always in the loop.

No LLM calls. Network access to GitHub only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from registry import Registry, RegistryEntry
from audit import Auditor


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class UpdateRequest:
    """Represents a request to update a skill."""

    def __init__(self, entry: RegistryEntry, remote_content: str, local_content: str):
        self.entry = entry
        self.remote_content = remote_content
        self.local_content = local_content
        self.approved = False

    @property
    def has_changes(self) -> bool:
        """Check if remote differs from local."""
        return self.remote_content != self.local_content


# ---------------------------------------------------------------------------
# Main updater
# ---------------------------------------------------------------------------

class SkillUpdater:
    """Manages skill updates with user confirmation."""

    def __init__(self, registry: Optional[Registry] = None) -> None:
        self.registry = registry or Registry()
        self.auditor = Auditor(registry=self.registry)

    def check_updates(self, skill_name: Optional[str] = None) -> list[UpdateRequest]:
        """Check for available updates.

        Args:
            skill_name: Specific skill to check, or None for all installed.

        Returns:
            List of UpdateRequest objects for skills with available updates.
        """
        updates = []
        entries = self.registry.all()

        for entry in entries:
            if skill_name and entry.name != skill_name:
                continue

            # Fetch remote content via auditor's method
            remote_content = self.auditor._fetch_remote_skill_content(entry)
            if remote_content is None:
                continue

            # Get local content
            local_path = Path(entry.install_path)
            if not local_path.exists():
                continue

            local_content = local_path.read_text(encoding="utf-8", errors="ignore")

            # Check if different
            if remote_content != local_content:
                updates.append(UpdateRequest(entry, remote_content, local_content))

        return updates

    def prompt_update(self, request: UpdateRequest) -> bool:
        """Prompt user to approve an update.

        Args:
            request: UpdateRequest with local/remote content.

        Returns:
            True if user approved, False otherwise.
        """
        print(f"\n{'═' * 70}")
        print(f"  📦 {request.entry.name}")
        print(f"  Repo: {request.entry.repo_url}")
        print(f"{'═' * 70}\n")

        # Show a brief summary of changes
        local_lines = request.local_content.count('\n')
        remote_lines = request.remote_content.count('\n')
        print(f"  Local version:  {local_lines} lines")
        print(f"  Remote version: {remote_lines} lines")
        if remote_lines > local_lines:
            print(f"  Δ +{remote_lines - local_lines} lines")
        elif remote_lines < local_lines:
            print(f"  Δ {remote_lines - local_lines} lines")
        else:
            print("  Δ Content changed (same line count)")

        # Extract version from frontmatter if possible
        local_version = _extract_version(request.local_content)
        remote_version = _extract_version(request.remote_content)
        if local_version and remote_version and local_version != remote_version:
            print(f"  Version: {local_version} → {remote_version}")

        print()

        try:
            confirm = input("  Update? [y/N] ").strip().lower()
        except EOFError:
            print("  Update cancelled (non-interactive context).")
            return False

        return confirm == "y"

    def apply_update(self, request: UpdateRequest) -> bool:
        """Apply the update to a skill.

        Args:
            request: UpdateRequest to apply.

        Returns:
            True if successful, False otherwise.
        """
        try:
            install_path = Path(request.entry.install_path)
            install_path.write_text(request.remote_content, encoding="utf-8")
            request.approved = True
            return True
        except OSError as e:
            print(f"  ❌ Update failed: {e}")
            return False

    def run_interactive_update(
        self, skill_name: Optional[str] = None
    ) -> tuple[int, int]:
        """Run interactive update workflow.

        Args:
            skill_name: Specific skill to update, or None for all with updates.

        Returns:
            (successful_count, total_count) tuple.
        """
        updates = self.check_updates(skill_name=skill_name)

        if not updates:
            print("\n[agent-hunter] No updates available.")
            return 0, 0

        print(f"\n[agent-hunter] Found {len(updates)} update(s)\n")

        approved_count = 0
        for req in updates:
            if self.prompt_update(req):
                if self.apply_update(req):
                    print(f"  ✅ Updated: {req.entry.name}")
                    approved_count += 1
                else:
                    print(f"  ❌ Failed: {req.entry.name}")
            else:
                print(f"  ⏭️  Skipped: {req.entry.name}")

        print(f"\n{'═' * 70}")
        print(f"  Updates applied: {approved_count}/{len(updates)}")
        if approved_count > 0:
            print("  Run `agent-hunter audit` to verify updated skills.")
        print(f"{'═' * 70}\n")

        return approved_count, len(updates)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_version(content: str) -> Optional[str]:
    """Extract version from SKILL.md YAML frontmatter only."""
    lines = content.split('\n')
    in_frontmatter = False
    for line in lines:
        if line.startswith('---'):
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break  # end of frontmatter
        if in_frontmatter and line.startswith('version:'):
            return line.split(':', 1)[1].strip().strip('"\'')
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Update installed skills to newer versions")
    parser.add_argument("skill", nargs="?", help="Specific skill to update (optional)")
    args = parser.parse_args()

    updater = SkillUpdater()
    approved, total = updater.run_interactive_update(skill_name=args.skill)
    sys.exit(0 if approved == total else 1)

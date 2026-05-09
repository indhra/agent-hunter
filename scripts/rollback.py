"""
rollback.py — Restore registry and installed skills to a safe state.

Command: agent-hunter rollback [--to <snapshot>] [--force]

Use when:
    - SHA tamper detection flagged a skill after an update
    - A bad update broke the registry
    - You want to undo the last audit/update operation
    - You suspect a skill was poisoned

Rollback is instant — it restores registry.json and skill git SHAs.
Pre-audit/pre-update snapshots ensure recovery points exist.

No LLM calls. No network access (only local git operations).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from registry import Registry, BACKUPS_DIR


# ---------------------------------------------------------------------------
# Paths (with environment variable overrides for testability)
# ---------------------------------------------------------------------------


def _get_skills_dir() -> Path:
    """Get skills directory with env var override support."""
    override = os.getenv("AGENT_HUNTER_SKILLS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "skills"


def rollback(
    to_snapshot: Optional[Path] = None,
    registry: Optional[Registry] = None,
    interactive: bool = True,
    force: bool = False,
) -> bool:
    """Restore registry and installed skills to a previous snapshot state.

    Args:
        to_snapshot: Specific snapshot path to restore. If None, lists available.
        registry: Registry instance. Defaults to the standard one.
        interactive: If True, prompt for confirmation before restoring.
        force: If True, skip confirmation and diff preview.

    Returns:
        True if rollback succeeded, False otherwise.
    """
    reg = registry or Registry()
    snapshots = reg.list_snapshots()

    if not snapshots:
        print("[agent-hunter] No snapshots available. Cannot rollback.")
        print("               Snapshots are created before each audit and update.")
        print(f"               Snapshot location: {BACKUPS_DIR}")
        return False

    # Select target snapshot
    if to_snapshot:
        target_snapshot = None
        for s in snapshots:
            if s["path"] == to_snapshot or s["path"].name == str(to_snapshot):
                target_snapshot = s
                break
        if not target_snapshot:
            print(f"[agent-hunter] Snapshot not found: {to_snapshot}")
            print("\n  Available snapshots:")
            for i, snap in enumerate(snapshots, 1):
                print(f"    {i}. {snap['path'].name} ({snap['trigger']})")
            return False
    else:
        if interactive and not force:
            # Show list and let user pick
            print("\n[agent-hunter] Available snapshots:")
            for i, snap in enumerate(snapshots, 1):
                ts = (
                    datetime.fromisoformat(snap["snapshot_time"]) if snap["snapshot_time"] else None
                )
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S UTC") if ts else "unknown"
                print(
                    f"  {i}. {snap['path'].name}\n"
                    f"     Time: {ts_str}\n"
                    f"     Trigger: {snap['trigger']}\n"
                )

            try:
                choice = input("Enter snapshot number to restore (or 'q' to cancel): ").strip()
                if choice.lower() == "q":
                    print("[agent-hunter] Rollback cancelled.")
                    return False
                idx = int(choice) - 1
                if idx < 0 or idx >= len(snapshots):
                    print("[agent-hunter] Invalid selection.")
                    return False
                target_snapshot = snapshots[idx]
            except (ValueError, EOFError):
                print("\n[agent-hunter] Rollback cancelled (invalid input or non-interactive).")
                return False
        else:
            # Use most recent snapshot
            target_snapshot = snapshots[-1]

    # Verify the snapshot file actually exists on disk
    if not target_snapshot["path"].exists():
        print(f"[agent-hunter] Snapshot file not found: {target_snapshot['path'].name}")
        print("               The snapshot may have been manually deleted.")
        return False

    # Validate snapshot integrity
    is_valid, msg = reg.validate_snapshot_integrity(target_snapshot["path"])
    if not is_valid:
        print("[agent-hunter] Snapshot integrity check FAILED:")
        print(f"  {msg}")
        print("  Rollback aborted. This snapshot may have been corrupted.")
        return False

    # Show what will happen
    print(f"\n[agent-hunter] Rollback target: {target_snapshot['path'].name}")
    if target_snapshot["snapshot_time"]:
        ts = datetime.fromisoformat(target_snapshot["snapshot_time"])
        print(f"               Created: {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"               Trigger: {target_snapshot['trigger']}")

    if interactive and not force:
        print("\n  This will restore:")
        print("    - Registry entries")
        print("    - All installed skill git SHAs")
        try:
            confirm = input("\n  Proceed? [y/N] ").strip().lower()
        except EOFError:
            print("\n[agent-hunter] Rollback cancelled (non-interactive context).")
            return False
        if confirm != "y":
            print("[agent-hunter] Rollback cancelled.")
            return False

    # Save current state as a snapshot before we modify anything (safety net)
    try:
        if reg.registry_path.exists():
            current_snapshot = reg.snapshot(trigger="pre_rollback")
            print(f"[agent-hunter] Saved current state: {current_snapshot.name}")
    except Exception as e:
        print(f"[agent-hunter] Warning: Could not save pre-rollback snapshot: {e}")

    # Perform rollback
    try:
        # Step 1: Restore registry
        success = reg.restore_from_snapshot(target_snapshot["path"])
        if success is False:
            print("[agent-hunter] ✗ Registry restore failed")
            return False
        print("[agent-hunter] ✓ Registry restored")

        # Step 2: Restore skill git SHAs
        restored_skills = _restore_skill_shas(reg)
        for skill_name, success in restored_skills.items():
            status = "✓" if success else "✗"
            print(f"[agent-hunter] {status} {skill_name}")

        print("\n✅ Rollback complete.")
        print("   Run `agent-hunter audit` to verify the restored state.")
        return True

    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        print("   Your previous state was saved as: pre_rollback_*.json")
        return False


def _restore_skill_shas(registry: Registry) -> dict[str, bool]:
    """Restore git SHAs for all installed skills.

    For each skill in the registry, run `git reset --hard <stored-sha>`
    in the skill's installation directory.

    Returns:
        {skill_name: success_bool}
    """
    results = {}
    skills_dir = _get_skills_dir()

    for entry in registry.all():
        skill_name = entry.name
        skill_path = skills_dir / skill_name
        stored_sha = entry.git_tree_sha

        if not skill_path.exists():
            # Skill not installed locally (maybe uninstalled since snapshot)
            results[skill_name] = True
            continue

        if not stored_sha:
            # No SHA stored, skip
            results[skill_name] = True
            continue

        try:
            subprocess.run(
                ["git", "reset", "--hard", stored_sha],
                cwd=str(skill_path),
                check=True,
                capture_output=True,
            )
            results[skill_name] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results[skill_name] = False

    return results


def _parse_backup_timestamp(path: Path) -> Optional[str]:
    """Parse a human-readable timestamp from backup filename (registry_<unix_ts>.json)."""
    try:
        ts_str = path.stem.replace("registry_", "")
        ts = int(ts_str)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return None


def _restore_specific(registry, backup_path: Path) -> bool:
    """Restore a specific backup file to the registry path.

    Args:
        registry: Registry instance to update.
        backup_path: Path to the backup file to restore.

    Returns:
        True if successful, False on error.
    """
    try:
        shutil.copy(backup_path, registry.registry_path)
        registry._load()
        return True
    except (OSError, FileNotFoundError) as exc:
        print(f"[agent-hunter] Error restoring backup: {exc}")
        return False


def list_backups_cmd() -> None:
    """Print available backups for the user to choose from."""
    reg = Registry()
    backups = reg.list_backups()
    if not backups:
        print("[agent-hunter] No backups found.")
        return

    print(f"\n[agent-hunter] Available backups ({len(backups)}):\n")
    for i, b in enumerate(reversed(backups), 1):
        ts = _parse_backup_timestamp(b)
        print(f"  {i}. {b.name}  ({ts or 'unknown time'})")
    print("\n  To restore a specific backup:")
    print("  agent-hunter rollback --backup <filename>")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(
        description="Rollback agent-hunter registry to a previous state"
    )
    parser.add_argument("--backup", help="Specific backup filename to restore", default=None)
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if args.list:
        list_backups_cmd()
        sys.exit(0)

    backup_path = None
    if args.backup:
        backup_path = BACKUPS_DIR / args.backup
        if not backup_path.exists():
            print(f"[agent-hunter] Backup not found: {backup_path}")
            sys.exit(1)

    success = rollback(to_backup=backup_path, interactive=not args.yes)
    sys.exit(0 if success else 1)

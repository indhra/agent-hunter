"""
rollback.py — Restore the registry to the last known healthy state.

Command: agent-hunter rollback

Use when:
    - SHA tamper detection flagged a skill after an update
    - A bad update broke the registry
    - You want to undo the last audit/update operation

Rollback is instant — it restores the registry.json from the most recent
backup written before the last audit or update operation.

No LLM calls. No network access.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from registry import Registry, BACKUPS_DIR


def rollback(
    to_backup: Optional[Path] = None,
    registry: Optional[Registry] = None,
    interactive: bool = True,
) -> bool:
    """Restore registry to a previous backup state.

    Args:
        to_backup: Specific backup path to restore. If None, uses the most recent.
        registry: Registry instance. Defaults to the standard one.
        interactive: If True, prompt for confirmation before restoring.

    Returns:
        True if rollback succeeded, False otherwise.
    """
    reg = registry or Registry()
    backups = reg.list_backups()

    if not backups:
        print("[agent-hunter] No backups available. Cannot rollback.")
        print("               Backups are created before each audit and update.")
        print(f"               Backup location: {BACKUPS_DIR}")
        return False

    target = to_backup or backups[-1]

    if not target.exists():
        print(f"[agent-hunter] Backup not found: {target}")
        return False

    # Show what we're about to do
    backup_ts = _parse_backup_timestamp(target)
    print(f"\n[agent-hunter] Rollback target: {target.name}")
    if backup_ts:
        print(f"               Created at:     {backup_ts}")
    print(f"\n  Current registry: {reg.registry_path}")
    print(f"  Will be replaced by: {target.name}")

    if interactive:
        try:
            confirm = input("\n  Proceed? [y/N] ").strip().lower()
        except EOFError:
            print("\n[agent-hunter] Rollback cancelled (non-interactive context).")
            return False
        if confirm != "y":
            print("[agent-hunter] Rollback cancelled.")
            return False

    # Write a snapshot of current state before overwriting (safety net)
    if reg.registry_path.exists():
        current_snapshot = reg.snapshot()
        print(f"[agent-hunter] Saved current state as: {current_snapshot.name}")

    # Restore
    restored = reg.restore_latest() if to_backup is None else _restore_specific(reg, target)

    if restored:
        print(f"\n✅ Rollback complete. Registry restored from: {target.name}")
        print("   Run `agent-hunter audit` to verify the restored state.")
        return True
    else:
        print("\n❌ Rollback failed.")
        return False


def _restore_specific(registry: Registry, backup_path: Path) -> bool:
    """Restore from a specific backup file."""
    import shutil
    try:
        shutil.copy2(backup_path, registry.registry_path)
        registry._load()
        return True
    except OSError as e:
        print(f"[agent-hunter] Restore error: {e}")
        return False


def _parse_backup_timestamp(path: Path) -> Optional[str]:
    """Parse a human-readable timestamp from backup filename (registry_<unix_ts>.json)."""
    try:
        ts_str = path.stem.replace("registry_", "")
        ts = int(ts_str)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return None


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

    parser = argparse.ArgumentParser(description="Rollback agent-hunter registry to a previous state")
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

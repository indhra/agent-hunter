"""
registry.py — Read/write the agent-hunter local registry.

Registry file: ~/.agent-hunter/registry.json

Responsibilities:
    - Track installed skills with SHA, version, install date, trust tier
    - Deduplication by repo URL
    - SHA tamper detection (compare stored SHA vs. current remote SHA)
    - Write pre-audit/pre-update snapshots for rollback

No LLM calls. Local file I/O + GitHub API (SHA fetch only).
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REGISTRY_DIR = Path.home() / ".agent-hunter"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
BACKUPS_DIR = REGISTRY_DIR / "backups"
MAX_BACKUPS = 10


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RegistryEntry:
    name: str
    repo_url: str
    install_path: str
    version: str = ""
    git_tree_sha: str = ""          # stored at install time for tamper detection
    license: str = ""
    trust_tier: str = "raw"
    installed_at: str = ""
    last_audit_at: str = ""
    audit_status: str = "unknown"   # "healthy", "update_available", "tampered", "security_issue"
    notes: str = ""


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

class Registry:
    """agent-hunter local skill registry."""

    def __init__(self, registry_path: Path | str = REGISTRY_FILE) -> None:
        # Convert string to Path, handle directory vs file path
        path = Path(registry_path) if isinstance(registry_path, str) else registry_path
        if path.is_dir() or (not path.exists() and not path.suffix):
            # If it's a directory or looks like one, append registry.json
            self.registry_path = path / "registry.json"
        else:
            self.registry_path = path
        self._entries: dict[str, RegistryEntry] = {}  # keyed by repo_url
        self._ensure_dir()
        self._load()

    # --- Public API ---

    def all(self) -> list[RegistryEntry]:
        """Return all registered skill entries."""
        return list(self._entries.values())

    def get(self, repo_url: str) -> Optional[RegistryEntry]:
        """Get a single entry by repo URL."""
        return self._entries.get(repo_url)

    def upsert(self, entry: RegistryEntry) -> None:
        """Insert or update a registry entry."""
        if not entry.installed_at:
            entry.installed_at = datetime.now(timezone.utc).isoformat()
        self._entries[entry.repo_url] = entry
        self._save()

    def remove(self, repo_url: str) -> bool:
        """Remove an entry by repo URL. Returns True if it existed."""
        if repo_url in self._entries:
            del self._entries[repo_url]
            self._save()
            return True
        return False

    def snapshot(self) -> Path:
        """Write a timestamped backup of the current registry for rollback.

        If the registry file does not exist yet (no skills installed), writes
        an empty registry file first so the backup is well-formed.

        Returns the path of the backup file.
        """
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save()  # write empty registry so shutil.copy2 has a source
        ts = int(time.time())
        backup_path = BACKUPS_DIR / f"registry_{ts}.json"
        shutil.copy2(self.registry_path, backup_path)
        self._prune_old_backups()
        return backup_path

    def restore_latest(self) -> Optional[Path]:
        """Restore registry from the most recent backup.

        Returns the backup path used, or None if no backup exists.
        """
        backups = self._list_backups()
        if not backups:
            return None
        latest = backups[-1]
        shutil.copy2(latest, self.registry_path)
        self._load()
        return latest

    def list_backups(self) -> list[Path]:
        """Return available backup paths, oldest first."""
        return self._list_backups()

    # --- Internal ---

    def _ensure_dir(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if not self.registry_path.exists():
            self._entries = {}
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            self._entries = {
                url: RegistryEntry(**entry)
                for url, entry in raw.get("entries", {}).items()
            }
        except (json.JSONDecodeError, TypeError, KeyError):
            self._entries = {}

    def _save(self) -> None:
        data = {
            "version": "1",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": {url: asdict(e) for url, e in self._entries.items()},
        }
        self.registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _list_backups(self) -> list[Path]:
        if not BACKUPS_DIR.exists():
            return []
        return sorted(BACKUPS_DIR.glob("registry_*.json"))

    def _prune_old_backups(self) -> None:
        backups = self._list_backups()
        for old in backups[:-MAX_BACKUPS]:
            old.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# SHA tamper detection
# ---------------------------------------------------------------------------

def check_sha_tamper(entry: RegistryEntry, token: Optional[str] = None) -> tuple[bool, str]:
    """Compare stored SHA against current remote SHA.

    Args:
        entry: RegistryEntry with stored git_tree_sha and repo_url.
        token: Optional GitHub personal access token for authenticated requests.

    Returns:
        (is_tampered, message) — True if SHA mismatch detected.
    """
    if not entry.git_tree_sha:
        return False, "No SHA stored — install before first audit to baseline."

    current_sha = _fetch_remote_sha(entry.repo_url, token=token)
    if current_sha is None:
        return False, "Could not fetch remote SHA (network error or rate limit)."

    if current_sha != entry.git_tree_sha:
        return True, (
            f"SHA mismatch detected.\n"
            f"  Stored:  {entry.git_tree_sha}\n"
            f"  Current: {current_sha}\n"
            f"  This skill may have been tampered with or silently updated."
        )

    return False, "SHA matches — no tampering detected."


def _fetch_remote_sha(repo_url: str, token: Optional[str] = None) -> Optional[str]:
    """Fetch the current git tree SHA for the default branch of a GitHub repo.

    Args:
        repo_url: Full GitHub repository URL.
        token: Optional GitHub personal access token. When provided, requests are
               authenticated and count against the 5,000/hr authenticated rate limit
               instead of the 60/hr unauthenticated limit.
    """
    try:
        import requests
        # Convert https://github.com/owner/repo to API call
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(api_url, timeout=10, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("sha")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    reg = Registry()
    entries = reg.all()

    if not entries:
        print("Registry is empty. No skills installed yet.")
        sys.exit(0)

    print(f"Registry: {len(entries)} skill(s)\n")
    for e in entries:
        status_icon = {"healthy": "🟢", "update_available": "🟡",
                       "tampered": "🔴", "security_issue": "🔴"}.get(e.audit_status, "⚪")
        print(f"  {status_icon}  {e.name:<30} {e.version:<10} {e.trust_tier}")

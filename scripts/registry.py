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
import os
import subprocess
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths (with environment variable overrides for testability)
# ---------------------------------------------------------------------------


def _get_registry_dir() -> Path:
    """Get registry directory with env var override support."""
    override = os.getenv("AGENT_HUNTER_REGISTRY_DIR")
    if override:
        return Path(override).parent
    return Path.home() / ".agent-hunter"


def _get_registry_file() -> Path:
    """Get registry file path with env var override support."""
    override = os.getenv("AGENT_HUNTER_REGISTRY")
    if override:
        return Path(override)
    return _get_registry_dir() / "registry.json"


def _get_backups_dir() -> Path:
    """Get backups directory with env var override support."""
    override = os.getenv("AGENT_HUNTER_BACKUPS")
    if override:
        return Path(override)
    return _get_registry_dir() / "backups"


# Module-level constants (for backward compatibility)
REGISTRY_DIR = _get_registry_dir()
REGISTRY_FILE = _get_registry_file()
BACKUPS_DIR = _get_backups_dir()
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
    git_tree_sha: str = ""  # stored at install time for tamper detection
    license: str = ""
    trust_tier: str = "raw"
    installed_at: str = ""
    last_audit_at: str = ""
    audit_status: str = "unknown"  # "healthy", "update_available", "tampered", "security_issue"
    notes: str = ""
    # Version compatibility tracking (v0.7.0+)
    python_version_tested: str = ""  # e.g., "3.10", "3.11"
    node_version_tested: str = ""  # e.g., "18.0", "20.0"
    ruby_version_tested: str = ""  # e.g., "3.0", "3.1"
    # Web-of-trust tracking (v0.8.0+)
    author_trusted: bool = False  # True if author is in trusted_authors list
    author_name: str = ""  # GitHub owner/author name


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

    def snapshot(self, trigger: str = "manual") -> Path:
        """Write a timestamped backup of the current registry for rollback.

        If the registry file does not exist yet (no skills installed), writes
        an empty registry file first so the backup is well-formed.

        Args:
            trigger: Reason for snapshot: "pre_audit", "pre_update", "manual", etc.

        Returns:
            Path of the backup file.
        """
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save()  # write empty registry so shutil.copy2 has a source

        # Get current git branch (if in a git repo, else "unknown")
        git_branch = "unknown"
        try:
            git_branch = (
                subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
                .decode("utf-8")
                .strip()
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass  # Not a git repo or git not installed

        # Create snapshot with metadata + CRC32 checksum.
        # CRC32 is computed over the compact JSON of the registry dict
        # (same format used by validate_snapshot_integrity) so roundtrips match.
        registry_content = self.registry_path.read_bytes()
        registry_data = json.loads(registry_content.decode("utf-8"))
        registry_compact = json.dumps(
            registry_data, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        crc32_checksum = zlib.crc32(registry_compact) & 0xFFFFFFFF

        snapshot_data = {
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "git_branch": git_branch,
            "crc32": f"{crc32_checksum:08x}",
            "registry": registry_data,
        }

        # Use descriptive naming: pre_audit_20260503_143022.json
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{trigger}_{ts_str}.json"
        backup_path = BACKUPS_DIR / backup_name

        backup_path.write_text(
            json.dumps(snapshot_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._prune_old_snapshots()
        return backup_path

    def list_snapshots(self) -> list[dict]:
        """List available snapshots with metadata.

        Returns:
            list of {path, snapshot_time, trigger, git_branch, crc32}
        """
        if not BACKUPS_DIR.exists():
            return []

        snapshots = []
        for snapshot_file in sorted(BACKUPS_DIR.glob("*.json")):
            try:
                data = json.loads(snapshot_file.read_text(encoding="utf-8"))
                # Validate snapshot has required metadata (v0.5.0+)
                if "snapshot_time" in data and "trigger" in data:
                    snapshots.append(
                        {
                            "path": snapshot_file,
                            "snapshot_time": data.get("snapshot_time"),
                            "trigger": data.get("trigger"),
                            "git_branch": data.get("git_branch", "unknown"),
                            "crc32": data.get("crc32"),
                        }
                    )
            except (json.JSONDecodeError, OSError):
                pass  # Skip corrupted snapshots
        return snapshots

    def validate_snapshot_integrity(self, snapshot_path: Path) -> tuple[bool, str]:
        """Validate snapshot CRC32 checksum.

        Args:
            snapshot_path: Path to snapshot file

        Returns:
            (is_valid, message)
        """
        try:
            data = json.loads(snapshot_path.read_text(encoding="utf-8"))
            stored_crc = data.get("crc32")
            registry_data = data.get("registry")

            if not stored_crc or not registry_data:
                return False, "Snapshot missing CRC32 or registry data"

            # Recompute CRC32 of the registry content
            registry_json = json.dumps(
                registry_data, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            computed_crc = zlib.crc32(registry_json) & 0xFFFFFFFF
            computed_crc_str = f"{computed_crc:08x}"

            if computed_crc_str != stored_crc:
                return False, (
                    f"Snapshot integrity check failed (CRC32 mismatch).\n"
                    f"  Stored:   {stored_crc}\n"
                    f"  Computed: {computed_crc_str}\n"
                    f"  This snapshot may have been corrupted or tampered with."
                )

            return True, "Snapshot integrity verified"
        except (json.JSONDecodeError, OSError, KeyError) as e:
            return False, f"Failed to validate snapshot: {e}"

    def restore_from_snapshot(self, snapshot_path: Path) -> bool:
        """Restore registry from a snapshot file.

        Args:
            snapshot_path: Path to snapshot file

        Returns:
            True if restore succeeded, False otherwise

        Raises:
            ValueError if snapshot integrity check fails
        """
        is_valid, msg = self.validate_snapshot_integrity(snapshot_path)
        if not is_valid:
            raise ValueError(msg)

        try:
            data = json.loads(snapshot_path.read_text(encoding="utf-8"))
            registry_data = data.get("registry")

            # Restore by writing registry data directly
            self.registry_path.write_text(
                json.dumps(registry_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._load()
            return True
        except (json.JSONDecodeError, OSError) as e:
            raise ValueError(f"Failed to restore from snapshot: {e}")

    def restore_latest(self) -> Optional[Path]:
        """Restore registry from the most recent snapshot.

        Returns the snapshot path used, or None if no snapshot exists.
        """
        snapshots = self.list_snapshots()
        if not snapshots:
            return None

        latest = snapshots[-1]  # Newest (sorted by filename)
        try:
            self.restore_from_snapshot(latest["path"])
            return latest["path"]
        except ValueError:
            return None

    def list_backups(self) -> list[Path]:
        """Return available backup paths (for backward compatibility).

        Use list_snapshots() for metadata-rich snapshot information.
        """
        return [s["path"] for s in self.list_snapshots()]

    def _prune_old_snapshots(self) -> None:
        """Keep only the most recent snapshots, delete older ones."""
        from pathlib import Path

        config_file = Path.home() / ".agent-hunter" / "config.json"
        max_snapshots = MAX_BACKUPS  # default (configurable via max_snapshots_kept)
        retention_days = 90  # default

        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
                max_snapshots = config.get("max_snapshots_kept", MAX_BACKUPS)
                retention_days = config.get("snapshot_retention_days", 90)
            except (json.JSONDecodeError, OSError):
                pass

        # Sort by mtime so chronological order is preserved regardless of filename prefix
        snapshots = sorted(BACKUPS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)

        # Delete old by count
        for old in snapshots[:-max_snapshots]:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass

        # Delete old by age
        cutoff_time = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
        for snapshot_file in BACKUPS_DIR.glob("*.json"):
            if snapshot_file.stat().st_mtime < cutoff_time:
                try:
                    snapshot_file.unlink(missing_ok=True)
                except OSError:
                    pass

    def _ensure_dir(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if not self.registry_path.exists():
            self._entries = {}
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
            self._entries = {
                url: RegistryEntry(**entry) for url, entry in raw.get("entries", {}).items()
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

    def check_version_compatibility(
        self, entry: RegistryEntry, current_python: Optional[str] = None
    ) -> tuple[str, str]:
        """Check if skill's tested version matches host environment.

        Args:
            entry: RegistryEntry with version_tested fields
            current_python: Current Python version (e.g., "3.12"). If None, detected from sys.

        Returns:
            (status, message)
            status: "green" (compatible), "yellow" (warning), "red" (incompatible)
            message: Human-readable explanation
        """
        if current_python is None:
            import sys

            current_python = f"{sys.version_info.major}.{sys.version_info.minor}"

        # No version metadata = green (assume it works)
        if not entry.python_version_tested:
            return ("green", "")

        tested = entry.python_version_tested
        current_major, current_minor = map(int, current_python.split(".")[:2])
        tested_major, tested_minor = map(int, tested.split(".")[:2])

        # Same major version = green
        if tested_major == current_major:
            return ("green", "")

        # Minor version mismatch = yellow (may work, not guaranteed)
        if tested_major == current_major and tested_minor != current_minor:
            return (
                "yellow",
                f"Tested on Python {tested}, you're using {current_python}. May work, not guaranteed.",
            )

        # Major version mismatch = red (likely incompatible)
        return (
            "red",
            f"Tested on Python {tested}, you're using {current_python}. Likely incompatible.",
        )


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
# Web-of-trust support (v0.8.0)
# ---------------------------------------------------------------------------


def load_trusted_authors() -> dict[str, dict]:
    """Load trusted authors from references/trusted_authors.json.

    Returns:
        Dict mapping author_id → author metadata including score_bonus.
        Returns empty dict if file not found or parsing fails.
    """
    trusted_path = Path(__file__).parent.parent / "references" / "trusted_authors.json"
    if not trusted_path.exists():
        return {}

    try:
        with open(trusted_path, encoding="utf-8") as f:
            authors = json.load(f)
            if not isinstance(authors, list):
                return {}
            # Convert list to dict keyed by author_id
            return {author["author_id"]: author for author in authors if "author_id" in author}
    except (json.JSONDecodeError, OSError):
        return {}


def extract_author_from_url(repo_url: str) -> Optional[str]:
    """Extract GitHub author/owner from a repo URL.

    Args:
        repo_url: GitHub URL, e.g., "https://github.com/indhra/skill-deploy"

    Returns:
        Author ID (owner name) or None if URL cannot be parsed.
    """
    # Example: https://github.com/owner/repo → owner
    if "github.com" not in repo_url:
        return None

    parts = repo_url.rstrip("/").split("/")
    if len(parts) >= 4:
        return parts[-2]  # second-to-last part is the owner
    return None


def check_author_trust(repo_url: str, trusted_authors: Optional[dict] = None) -> tuple[bool, float]:
    """Check if a repo's author is trusted and return score bonus.

    Args:
        repo_url: GitHub repository URL
        trusted_authors: Optional pre-loaded trusted authors dict.
                        If None, loads from file.

    Returns:
        (is_trusted, score_bonus)
        - is_trusted: True if author is in trusted list
        - score_bonus: multiplier (1.0 if not trusted, e.g. 1.15 if trusted)
    """
    if trusted_authors is None:
        trusted_authors = load_trusted_authors()

    if not trusted_authors:
        return False, 1.0

    author = extract_author_from_url(repo_url)
    if not author:
        return False, 1.0

    if author in trusted_authors:
        bonus = trusted_authors[author].get("score_bonus", 0.10)
        # Apply as multiplier: score_bonus of 0.15 → 1.15× multiplier
        return True, 1.0 + bonus

    return False, 1.0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys

    reg = Registry()
    entries = reg.all()

    if not entries:
        print("Registry is empty. No skills installed yet.")
        sys.exit(0)

    print(f"Registry: {len(entries)} skill(s)\n")
    for e in entries:
        status_icon = {
            "healthy": "🟢",
            "update_available": "🟡",
            "tampered": "🔴",
            "security_issue": "🔴",
        }.get(e.audit_status, "⚪")
        print(f"  {status_icon}  {e.name:<30} {e.version:<10} {e.trust_tier}")

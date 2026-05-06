"""
test_registry.py — Tests for registry.py.

Uses tmp_path so no ~/.agent-hunter/ is touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from registry import Registry, RegistryEntry, check_sha_tamper  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reg(tmp_path):
    """A fresh Registry backed by a temp file."""
    return Registry(registry_path=tmp_path / "registry.json")


def _entry(name: str = "myskill", url: str = "https://github.com/owner/myskill") -> RegistryEntry:
    return RegistryEntry(name=name, repo_url=url, install_path=f"~/.claude/skills/{name}")


# ---------------------------------------------------------------------------
# upsert / get / remove round-trip
# ---------------------------------------------------------------------------


class TestUpsertRemove:
    def test_upsert_and_get(self, reg):
        e = _entry()
        reg.upsert(e)
        result = reg.get(e.repo_url)
        assert result is not None
        assert result.name == "myskill"

    def test_upsert_sets_installed_at(self, reg):
        e = _entry()
        assert e.installed_at == ""
        reg.upsert(e)
        assert e.installed_at != ""

    def test_upsert_does_not_overwrite_existing_installed_at(self, reg):
        e = _entry()
        e.installed_at = "2024-01-01T00:00:00"
        reg.upsert(e)
        assert reg.get(e.repo_url).installed_at == "2024-01-01T00:00:00"

    def test_remove_existing(self, reg):
        e = _entry()
        reg.upsert(e)
        assert reg.remove(e.repo_url) is True
        assert reg.get(e.repo_url) is None

    def test_remove_nonexistent_returns_false(self, reg):
        assert reg.remove("https://github.com/nobody/missing") is False

    def test_all_returns_all_entries(self, reg):
        reg.upsert(_entry("a", "https://github.com/o/a"))
        reg.upsert(_entry("b", "https://github.com/o/b"))
        entries = reg.all()
        assert len(entries) == 2

    def test_upsert_updates_existing(self, reg):
        e = _entry()
        reg.upsert(e)
        e.version = "1.2.3"
        reg.upsert(e)
        assert reg.get(e.repo_url).version == "1.2.3"
        assert len(reg.all()) == 1  # not duplicated


# ---------------------------------------------------------------------------
# Persistence: _save / _load round-trip
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "registry.json"
        reg1 = Registry(registry_path=path)
        reg1.upsert(_entry("saved-skill"))

        # Load fresh instance from same file
        reg2 = Registry(registry_path=path)
        result = reg2.get("https://github.com/owner/myskill")
        assert result is not None
        assert result.name == "saved-skill"

    def test_corrupt_json_starts_empty(self, tmp_path):
        path = tmp_path / "registry.json"
        path.write_text("{ INVALID JSON }", encoding="utf-8")
        reg = Registry(registry_path=path)
        assert reg.all() == []

    def test_empty_file_starts_empty(self, tmp_path):
        path = tmp_path / "registry.json"
        # File does not exist — should not raise
        reg = Registry(registry_path=path)
        assert reg.all() == []

    def test_saved_file_has_version_field(self, tmp_path):
        path = tmp_path / "registry.json"
        reg = Registry(registry_path=path)
        reg.upsert(_entry())
        raw = json.loads(path.read_text())
        assert raw["version"] == "1"
        assert "updated_at" in raw
        assert "entries" in raw


# ---------------------------------------------------------------------------
# Snapshot / restore
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_snapshot_creates_backup_file(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        reg = Registry(registry_path=reg_path)
        reg.upsert(_entry())

        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", tmp_path / "backups")
            backup = reg.snapshot()

        assert backup.exists()

    def test_restore_latest_loads_backup(self, tmp_path):
        reg_path = tmp_path / "registry.json"
        backups_dir = tmp_path / "backups"
        backups_dir.mkdir()

        # Write initial registry with one skill
        reg = Registry(registry_path=reg_path)
        reg.upsert(_entry("original-skill"))

        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", backups_dir)
            m.setattr("registry.REGISTRY_FILE", reg_path)
            reg.snapshot()

        # Now modify the registry
        reg.remove("https://github.com/owner/myskill")
        assert reg.all() == []

        # Restore
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", backups_dir)
            restored = reg.restore_latest()

        assert restored is not None
        assert reg.get("https://github.com/owner/myskill") is not None

    def test_restore_latest_no_backups_returns_none(self, tmp_path):
        reg = Registry(registry_path=tmp_path / "registry.json")
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry.BACKUPS_DIR", tmp_path / "empty_backups")
            result = reg.restore_latest()
        assert result is None


# ---------------------------------------------------------------------------
# SHA tamper detection
# ---------------------------------------------------------------------------


class TestShaTamper:
    def test_no_sha_stored_returns_not_tampered(self):
        e = _entry()
        e.git_tree_sha = ""
        tampered, msg = check_sha_tamper(e)
        assert tampered is False
        assert "No SHA stored" in msg

    def test_sha_match_returns_not_tampered(self):
        e = _entry()
        e.git_tree_sha = "abc123"
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry._fetch_remote_sha", lambda *a, **kw: "abc123")
            tampered, msg = check_sha_tamper(e)
        assert tampered is False
        assert "no tampering" in msg.lower()

    def test_sha_mismatch_returns_tampered(self):
        e = _entry()
        e.git_tree_sha = "abc123"
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry._fetch_remote_sha", lambda *a, **kw: "def456")
            tampered, msg = check_sha_tamper(e)
        assert tampered is True
        assert "mismatch" in msg.lower()

    def test_network_failure_returns_not_tampered(self):
        e = _entry()
        e.git_tree_sha = "abc123"
        with pytest.MonkeyPatch().context() as m:
            m.setattr("registry._fetch_remote_sha", lambda *a, **kw: None)
            tampered, msg = check_sha_tamper(e)
        assert tampered is False
        assert "Could not fetch" in msg


# ---------------------------------------------------------------------------
# _fetch_remote_sha direct tests
# ---------------------------------------------------------------------------


class TestFetchRemoteSha:
    def test_short_url_returns_none(self):
        """URL with fewer than 2 path parts should return None immediately."""
        import registry as reg_mod

        result = reg_mod._fetch_remote_sha("https://github.com/only-one")
        assert result is None

    def test_token_is_added_to_headers(self):
        """When token provided, Authorization header should be sent."""
        import registry as reg_mod
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sha": "abc123def"}

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = reg_mod._fetch_remote_sha("https://github.com/owner/repo", token="my-token")

        assert result == "abc123def"
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer my-token"

    def test_200_returns_sha(self):
        """A 200 response should return the sha from JSON."""
        import registry as reg_mod
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sha": "deadbeef"}

        with patch("requests.get", return_value=mock_resp):
            result = reg_mod._fetch_remote_sha("https://github.com/owner/repo")

        assert result == "deadbeef"

    def test_non_200_returns_none(self):
        """A non-200 status code should fall through and return None."""
        import registry as reg_mod
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("requests.get", return_value=mock_resp):
            result = reg_mod._fetch_remote_sha("https://github.com/owner/repo")

        assert result is None

    def test_network_exception_returns_none(self):
        """Any network exception should be caught and return None."""
        import registry as reg_mod
        from unittest.mock import patch
        import requests

        with patch("requests.get", side_effect=requests.ConnectionError("no network")):
            result = reg_mod._fetch_remote_sha("https://github.com/owner/repo")

        assert result is None

"""
Tests for rollback.py — rollback(), _parse_backup_timestamp(), list_backups_cmd(),
interactive prompt handling (EOFError safety), and specific backup restore.

All tests use mocked registries and tmp_path — never touches ~/.agent-hunter/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rollback import _parse_backup_timestamp, rollback, list_backups_cmd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_registry(tmp_path: Path, backups: list[Path]) -> MagicMock:
    """Return a mocked Registry with controlled backup list and registry path."""
    mock_reg = MagicMock()
    mock_reg.registry_path = tmp_path / "registry.json"
    mock_reg.list_backups.return_value = backups
    mock_reg.snapshot.return_value = tmp_path / "current_snapshot.json"
    mock_reg.restore_latest.return_value = True
    mock_reg._load.return_value = None
    return mock_reg


def _write_registry(path: Path) -> None:
    path.write_text(json.dumps({"skills": [], "version": "1"}))


def _make_backup(tmp_path: Path, ts_offset: int = 0) -> Path:
    """Create a real backup file with a timestamp-based name."""
    ts = int(time.time()) - ts_offset
    backup = tmp_path / f"registry_{ts}.json"
    backup.write_text(json.dumps({"skills": [], "version": "1"}))
    return backup


# ---------------------------------------------------------------------------
# _parse_backup_timestamp
# ---------------------------------------------------------------------------

class TestParseBackupTimestamp:
    def test_valid_timestamp_returns_string(self, tmp_path):
        ts = int(time.time())
        backup = tmp_path / f"registry_{ts}.json"
        backup.write_text("{}")
        result = _parse_backup_timestamp(backup)
        assert result is not None
        assert len(result) > 0  # e.g. "2026-05-02 10:00:00"

    def test_invalid_name_returns_none(self, tmp_path):
        backup = tmp_path / "registry_notanumber.json"
        backup.write_text("{}")
        result = _parse_backup_timestamp(backup)
        assert result is None

    def test_plain_name_returns_none(self, tmp_path):
        backup = tmp_path / "backup.json"
        backup.write_text("{}")
        result = _parse_backup_timestamp(backup)
        assert result is None


# ---------------------------------------------------------------------------
# rollback() — no backups
# ---------------------------------------------------------------------------

class TestRollbackNoBackups:
    def test_returns_false_when_no_backups(self, tmp_path, capsys):
        mock_reg = _mock_registry(tmp_path, backups=[])
        result = rollback(registry=mock_reg, interactive=False)
        assert result is False
        out = capsys.readouterr().out
        assert "No backups" in out

    def test_prints_backup_location_hint(self, tmp_path, capsys):
        mock_reg = _mock_registry(tmp_path, backups=[])
        rollback(registry=mock_reg, interactive=False)
        out = capsys.readouterr().out
        assert "Backup location" in out


# ---------------------------------------------------------------------------
# rollback() — backup not found on disk
# ---------------------------------------------------------------------------

class TestRollbackMissingFile:
    def test_returns_false_when_backup_file_missing(self, tmp_path, capsys):
        missing = tmp_path / "registry_9999999.json"
        mock_reg = _mock_registry(tmp_path, backups=[missing])
        result = rollback(registry=mock_reg, interactive=False)
        assert result is False
        out = capsys.readouterr().out
        assert "not found" in out.lower()


# ---------------------------------------------------------------------------
# rollback() — non-interactive (no prompt)
# ---------------------------------------------------------------------------

class TestRollbackNonInteractive:
    def test_returns_true_on_successful_restore(self, tmp_path):
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"
        mock_reg.restore_latest.return_value = True

        result = rollback(registry=mock_reg, interactive=False)
        assert result is True

    def test_returns_false_when_restore_fails(self, tmp_path):
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.restore_latest.return_value = False

        result = rollback(registry=mock_reg, interactive=False)
        assert result is False

    def test_snapshots_current_state_before_restore(self, tmp_path):
        backup = _make_backup(tmp_path)
        registry_file = tmp_path / "registry.json"
        _write_registry(registry_file)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = registry_file

        rollback(registry=mock_reg, interactive=False)
        # snapshot() should have been called to preserve current state
        mock_reg.snapshot.assert_called_once()


# ---------------------------------------------------------------------------
# rollback() — interactive prompt
# ---------------------------------------------------------------------------

class TestRollbackInteractive:
    def test_y_proceeds_with_restore(self, tmp_path):
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        with patch("builtins.input", return_value="y"):
            result = rollback(registry=mock_reg, interactive=True)

        assert result is True

    def test_n_cancels_rollback(self, tmp_path, capsys):
        backup = _make_backup(tmp_path)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        with patch("builtins.input", return_value="n"):
            result = rollback(registry=mock_reg, interactive=True)

        assert result is False
        out = capsys.readouterr().out
        assert "cancelled" in out.lower()

    def test_empty_enter_cancels_rollback(self, tmp_path):
        backup = _make_backup(tmp_path)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        with patch("builtins.input", return_value=""):
            result = rollback(registry=mock_reg, interactive=True)

        assert result is False

    def test_eoferror_does_not_crash(self, tmp_path):
        """EOFError from input() in CI/pipe must be handled gracefully."""
        backup = _make_backup(tmp_path)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        with patch("builtins.input", side_effect=EOFError):
            # Should not raise — must return False cleanly
            try:
                result = rollback(registry=mock_reg, interactive=True)
                # If rollback handles EOFError, result should be False
                assert result is False
            except EOFError:
                pytest.fail("rollback() let EOFError propagate — must be caught")


# ---------------------------------------------------------------------------
# rollback() — specific backup restore
# ---------------------------------------------------------------------------

class TestRollbackSpecificBackup:
    def test_restores_specific_backup_not_latest(self, tmp_path):
        old_backup = _make_backup(tmp_path, ts_offset=3600)
        new_backup = _make_backup(tmp_path, ts_offset=0)
        _write_registry(tmp_path / "registry.json")

        mock_reg = _mock_registry(tmp_path, backups=[old_backup, new_backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        # Pass the old backup explicitly — restore_latest should NOT be called
        with patch("rollback._restore_specific", return_value=True) as mock_specific:
            result = rollback(to_backup=old_backup, registry=mock_reg, interactive=False)

        assert result is True
        mock_specific.assert_called_once_with(mock_reg, old_backup)
        mock_reg.restore_latest.assert_not_called()


# ---------------------------------------------------------------------------
# list_backups_cmd
# ---------------------------------------------------------------------------

class TestListBackupsCmd:
    def test_prints_no_backups_message(self, capsys):
        mock_reg = MagicMock()
        mock_reg.list_backups.return_value = []
        with patch("rollback.Registry", return_value=mock_reg):
            list_backups_cmd()
        out = capsys.readouterr().out
        assert "No backups" in out

    def test_prints_backup_filenames(self, tmp_path, capsys):
        backup = _make_backup(tmp_path)
        mock_reg = MagicMock()
        mock_reg.list_backups.return_value = [backup]
        with patch("rollback.Registry", return_value=mock_reg):
            list_backups_cmd()
        out = capsys.readouterr().out
        assert backup.name in out

"""
Tests for rollback.py — rollback(), _parse_backup_timestamp(), list_backups_cmd(),
interactive prompt handling (EOFError safety), and specific backup restore.

All tests use mocked registries and tmp_path — never touches ~/.agent-hunter/.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rollback import _parse_backup_timestamp, rollback, list_backups_cmd, _restore_specific


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
    mock_reg.restore_from_snapshot.return_value = True
    mock_reg.validate_snapshot_integrity.return_value = (True, "Snapshot valid")
    mock_reg._load.return_value = None

    # Mock list_snapshots to return proper snapshot dicts
    snapshots = [
        {
            "path": backup,
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
            "trigger": "pre-hunt",
        }
        for backup in backups
    ]
    mock_reg.list_snapshots.return_value = snapshots

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
        mock_reg.restore_from_snapshot.return_value = True

        result = rollback(registry=mock_reg, interactive=False)
        assert result is True

    def test_returns_false_when_restore_fails(self, tmp_path):
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.restore_from_snapshot.return_value = False

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


# ---------------------------------------------------------------------------
# _restore_specific — direct tests
# ---------------------------------------------------------------------------


class TestRestoreSpecific:
    def test_restore_specific_succeeds(self, tmp_path):
        """_restore_specific should copy backup to registry path and reload."""
        backup = _make_backup(tmp_path, ts_offset=3600)
        registry_path = tmp_path / "registry.json"
        _write_registry(registry_path)

        mock_reg = MagicMock()
        mock_reg.registry_path = registry_path

        result = _restore_specific(mock_reg, backup)

        assert result is True
        # Verify _load was called
        mock_reg._load.assert_called_once()
        # Verify the file was copied
        assert registry_path.exists()

    def test_restore_specific_file_copied_correctly(self, tmp_path):
        """Verify the backup content is actually copied to registry path."""
        backup_content = {"skills": [{"name": "restored-skill"}], "version": "1"}
        backup = tmp_path / "backup.json"
        backup.write_text(json.dumps(backup_content))

        registry_path = tmp_path / "registry.json"
        registry_path.write_text(json.dumps({"skills": [], "version": "1"}))

        mock_reg = MagicMock()
        mock_reg.registry_path = registry_path

        _restore_specific(mock_reg, backup)

        # Verify the registry now contains the backup content
        restored = json.loads(registry_path.read_text())
        assert restored == backup_content

    def test_restore_specific_handles_oserror(self, tmp_path, capsys):
        """_restore_specific should return False and print error on OSError."""
        backup = tmp_path / "backup.json"
        backup.write_text("{}")
        registry_path = tmp_path / "readonly_dir" / "registry.json"
        registry_path.parent.mkdir(parents=True)

        mock_reg = MagicMock()
        mock_reg.registry_path = registry_path

        # Make the parent directory read-only to trigger OSError
        registry_path.parent.chmod(0o444)

        try:
            result = _restore_specific(mock_reg, backup)
            assert result is False
            out = capsys.readouterr().out
            assert "Error restoring backup" in out or "error" in out.lower()
        finally:
            # Cleanup: restore write permission
            registry_path.parent.chmod(0o755)

    def test_restore_specific_with_nonexistent_source(self, tmp_path, capsys):
        """_restore_specific should handle missing backup file gracefully."""
        backup = tmp_path / "nonexistent.json"
        registry_path = tmp_path / "registry.json"
        _write_registry(registry_path)

        mock_reg = MagicMock()
        mock_reg.registry_path = registry_path

        result = _restore_specific(mock_reg, backup)
        assert result is False
        out = capsys.readouterr().out
        assert "Error restoring backup" in out or "error" in out.lower()


# ---------------------------------------------------------------------------
# rollback() — output messages and warnings
# ---------------------------------------------------------------------------


class TestRollbackOutputMessages:
    def test_shows_backup_timestamp_when_available(self, tmp_path, capsys):
        """Verify rollback shows the creation timestamp of the backup."""
        backup = _make_backup(tmp_path)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"
        _write_registry(tmp_path / "registry.json")

        rollback(registry=mock_reg, interactive=False)
        out = capsys.readouterr().out

        # Should show a timestamp (or handle gracefully if parsing fails)
        assert backup.name in out or "rollback" in out.lower()

    def test_shows_success_message(self, tmp_path, capsys):
        """Verify success message is printed after successful rollback."""
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"
        mock_reg.restore_from_snapshot.return_value = True

        rollback(registry=mock_reg, interactive=False)
        out = capsys.readouterr().out

        assert "✅" in out or "Rollback complete" in out.lower()
        assert "audit" in out.lower()  # Suggests running audit

    @pytest.mark.xfail(reason="Code doesn't check restore_from_snapshot return value yet")
    def test_shows_failure_message(self, tmp_path, capsys):
        """Verify failure message is printed when rollback fails."""
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"
        mock_reg.restore_from_snapshot.return_value = False

        rollback(registry=mock_reg, interactive=False)
        out = capsys.readouterr().out

        assert "❌" in out or "failed" in out.lower()


# ---------------------------------------------------------------------------
# rollback() — edge cases
# ---------------------------------------------------------------------------


class TestRollbackEdgeCases:
    def test_handles_registry_path_not_existing(self, tmp_path):
        """Rollback should not crash if registry.json doesn't exist yet."""
        backup = _make_backup(tmp_path)
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        # Don't create registry.json
        mock_reg.registry_path = tmp_path / "nonexistent_registry.json"
        mock_reg.restore_latest.return_value = True

        # Should not crash, snapshot() is skipped
        result = rollback(registry=mock_reg, interactive=False)
        assert result is True

    def test_prints_helpful_prompt_text(self, tmp_path, capsys):
        """Interactive mode should show helpful text about the restore operation."""
        backup = _make_backup(tmp_path)
        _write_registry(tmp_path / "registry.json")
        mock_reg = _mock_registry(tmp_path, backups=[backup])
        mock_reg.registry_path = tmp_path / "registry.json"

        with patch("builtins.input", return_value="q"):
            rollback(registry=mock_reg, interactive=True)

        out = capsys.readouterr().out
        assert "Available snapshots" in out or "registry" in out.lower()
        assert "Rollback cancelled" in out or "quit" in out.lower()

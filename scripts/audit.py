"""
audit.py — Standalone audit command for installed skills.

Command: agent-hunter audit

Checks every skill in the registry:
    - SHA tamper detection (stored SHA vs. current remote SHA)
    - Re-runs security scan on current remote content
    - Trigger conflict detection (cosine similarity ≥ 0.8)
    - License compatibility check
    - Dependency conflict detection (v0.3.0+)

Writes a pre-audit snapshot to backups/ before running (enables rollback).

Output: Health table per skill — 🟢 Healthy / 🟡 Update available / 🔴 Issue

No LLM calls.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from registry import Registry, RegistryEntry, check_sha_tamper
from security_scan import scan_skill, ScanResult


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AuditEntryResult:
    entry: RegistryEntry
    sha_tampered: bool = False
    sha_message: str = ""
    scan_result: Optional[ScanResult] = None
    conflicts: list[str] = field(default_factory=list)  # names of conflicting skills
    license_issue: Optional[str] = None
    overall_status: str = "healthy"  # "healthy", "update_available", "tampered", "security_issue", "conflict"
    update_available: bool = False  # True if remote content differs from installed
    remote_content: Optional[str] = None  # cached remote SKILL.md for comparison


@dataclass
class AuditReport:
    audit_results: list[AuditEntryResult] = field(default_factory=list)
    audit_at: str = ""
    backup_path: Optional[Path] = None

    @property
    def has_issues(self) -> bool:
        return any(r.overall_status != "healthy" for r in self.audit_results)


# ---------------------------------------------------------------------------
# Main auditor
# ---------------------------------------------------------------------------

class Auditor:
    """Runs the full audit pipeline on all installed skills."""

    def __init__(
        self,
        registry: Optional[Registry] = None,
        conflict_threshold: float = 0.8,
    ) -> None:
        self.registry = registry or Registry()
        self.conflict_threshold = conflict_threshold

    def run(self) -> AuditReport:
        """Run the full audit. Returns an AuditReport.

        Side effect: writes a pre-audit registry snapshot for rollback.
        """
        report = AuditReport(audit_at=datetime.now(timezone.utc).isoformat())

        # Snapshot before audit (enables rollback if something goes wrong)
        if self.registry.registry_path.exists():
            report.backup_path = self.registry.snapshot()
            print(f"[agent-hunter] Pre-audit snapshot saved: {report.backup_path}")

        entries = self.registry.all()
        if not entries:
            print("[agent-hunter] No installed skills to audit.")
            return report

        print(f"[agent-hunter] Auditing {len(entries)} installed skill(s)...\n")

        for entry in entries:
            result = self._audit_entry(entry)
            report.audit_results.append(result)
            self._update_registry_status(entry, result)

        self._detect_conflicts(report.audit_results)
        self._print_report(report)
        return report

    def _audit_entry(self, entry: RegistryEntry) -> AuditEntryResult:
        """Run all checks on a single registry entry."""
        result = AuditEntryResult(entry=entry)

        # --- SHA tamper check ---
        tampered, msg = check_sha_tamper(entry)
        result.sha_tampered = tampered
        result.sha_message = msg

        # --- Fetch remote content for update detection and security re-scan ---
        remote_content = self._fetch_remote_skill_content(entry)
        result.remote_content = remote_content

        # --- Re-run security scan on remote content (if available) or local fallback ---
        if remote_content:
            result.scan_result = scan_skill(content=remote_content, repo_url=entry.repo_url)
            # Detect if local differs from remote (indicates update available)
            install_path = Path(entry.install_path)
            if install_path.exists():
                local_content = install_path.read_text(encoding="utf-8", errors="ignore")
                result.update_available = (local_content != remote_content)
        else:
            # Fallback: scan locally installed if we can't fetch remote
            install_path = Path(entry.install_path)
            if install_path.exists():
                content = install_path.read_text(encoding="utf-8", errors="ignore")
                result.scan_result = scan_skill(content=content, repo_url=entry.repo_url)
            else:
                result.scan_result = ScanResult(scan_error=f"Install path not found: {entry.install_path}")

        # --- License check ---
        result.license_issue = _check_license_compat(entry.license)

        # --- Set overall status (priority: tampered > security_issue > update_available > conflict > healthy) ---
        if tampered:
            result.overall_status = "tampered"
        elif result.scan_result and result.scan_result.severity == "RED":
            result.overall_status = "security_issue"
        elif result.update_available:
            result.overall_status = "update_available"
        elif result.license_issue:
            result.overall_status = "conflict"
        else:
            result.overall_status = "healthy"

        return result

    def _detect_conflicts(self, results: list[AuditEntryResult]) -> None:
        """Detect trigger description conflicts between installed skills (v0.3.0+).

        TODO: implement cosine similarity on trigger description strings.
        Placeholder for v0.3.0.
        """
        pass

    def _fetch_remote_skill_content(self, entry: RegistryEntry) -> Optional[str]:
        """Fetch the current SKILL.md from GitHub for the skill.

        Returns:
            Remote SKILL.md content, or None if unavailable (network error, 404, etc).
        """
        if not entry.repo_url:
            return None

        # Parse repo_url → convert to raw.githubusercontent URL for SKILL.md
        parts = entry.repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[-2], parts[-1]

        # Try main branch first, then master
        for branch in ("main", "master"):
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/SKILL.md"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    return resp.text
            except requests.RequestException:
                continue

        return None

    def _update_registry_status(self, entry: RegistryEntry, result: AuditEntryResult) -> None:
        """Persist the audit status back to registry."""
        entry.audit_status = result.overall_status
        entry.last_audit_at = datetime.now(timezone.utc).isoformat()
        self.registry.upsert(entry)

    def _print_report(self, report: AuditReport) -> None:
        """Print the audit health table."""
        print(f"{'═' * 60}")
        print(f"  agent-hunter · Audit Report · {report.audit_at[:10]}")
        print(f"{'═' * 60}\n")

        status_icons = {
            "healthy": "🟢",
            "update_available": "🟡",
            "tampered": "🔴",
            "security_issue": "🔴",
            "conflict": "🟡",
        }

        for r in report.audit_results:
            icon = status_icons.get(r.overall_status, "⚪")
            print(f"  {icon}  {r.entry.name:<30} {r.overall_status}")
            if r.sha_tampered:
                print(f"       ⚠️  SHA MISMATCH — {r.sha_message[:80]}")
            if r.update_available:
                print(f"       🟡 Update available — run `agent-hunter update {r.entry.name}`")
            if r.scan_result and r.scan_result.severity != "GREEN":
                for f in r.scan_result.findings[:2]:
                    sev = "🔴" if f.severity == "RED" else "🟡"
                    print(f"       {sev} {f.description}")
            if r.license_issue:
                print(f"       🟡 License: {r.license_issue}")

        print()
        if report.backup_path:
            print(f"  Backup saved to: {report.backup_path}")
            print("  To rollback: agent-hunter rollback")
        print(f"{'═' * 60}\n")


def _check_license_compat(skill_license: str) -> Optional[str]:
    """Check if a skill's license is compatible with common project licenses."""
    if not skill_license:
        return None
    gpl_variants = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-2.1", "LGPL-3.0"}
    if skill_license.upper() in {v.upper() for v in gpl_variants}:
        return f"{skill_license} skill may have license compatibility implications for MIT/BSD projects."
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    auditor = Auditor()
    report = auditor.run()
    sys.exit(1 if report.has_issues else 0)

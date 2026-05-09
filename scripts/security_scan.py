"""
security_scan.py — Multi-layer security scan for SKILL.md files.

Layers:
    1. Static analysis: prompt injection, shell exec, Unicode attacks, secrets
    2. Known-malicious index check (references/KNOWN_MALICIOUS.md)
    3. Runtime sandbox scan (subprocess or Docker, if enabled)
    4. pors/skill-audit integration (if installed)

Input:  SkillMetadata + raw content string
Output: ScanResult dataclass

Severity:
    RED    — immediate block, never show in results
    YELLOW — show with warning, user decides
    GREEN  — passed all checks

No LLM calls. Minimal network access (only to fetch SHA for tamper check).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScanError(Exception):
    """Raised when the scan itself fails (not when content is malicious)."""


# ---------------------------------------------------------------------------
# Patterns (from references/SECURITY_PATTERNS.md)
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules)", re.I),
    re.compile(
        r"do\s+not\s+(follow|obey|respect)\s+(the\s+)?(rules|guidelines|instructions)", re.I
    ),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"system\s*:\s*(you|ignore|override)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\s*mode", re.I),
    re.compile(r"developer\s*mode\s*(enabled|activated|on)", re.I),
    re.compile(r"(override|bypass|circumvent)\s+(the\s+)?(system|host|agent|claude)", re.I),
]

SHELL_EXEC_PATTERNS = [
    re.compile(r"os\.system\s*\("),
    re.compile(
        r"subprocess\.(run|call|Popen|check_output)\s*\([\s\S]*?shell\s*=\s*True", re.MULTILINE
    ),
    re.compile(r"commands\.getoutput\s*\("),
    re.compile(r'__import__\s*\(\s*[\'"]os[\'"]\s*\)\s*\.\s*system'),
]

EVAL_EXEC_PATTERNS = [
    re.compile(r"\beval\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"compile\s*\(.*exec"),
]

SECRET_PATTERNS = [
    re.compile(
        r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{20,}'
    ),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"sk-[a-zA-Z0-9]{48}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.=]{20,}"),
]

ENV_EXFIL_PATTERNS = [
    # Flag env access only when it co-occurs with a network call or exfiltration target
    # within 200 chars (spanning lines). Bare os.environ/os.getenv in docs is normal.
    re.compile(
        r"(?i)(os\.environ|os\.getenv)[\s\S]{0,200}?(requests\.|urllib|http\.client|socket\.connect|subprocess\.run|curl)"
    ),
    re.compile(
        r"(?i)(requests\.|urllib|http\.client|socket\.connect|subprocess\.run|curl)[\s\S]{0,200}?(os\.environ|os\.getenv)"
    ),
]

OBFUSCATION_PATTERNS = [
    # Dynamic code unpacking that can bypass static analysis
    re.compile(r"base64\.b64decode\s*\("),
    re.compile(r"base64\.decodebytes\s*\("),
    re.compile(r"codecs\.decode\s*\("),
    re.compile(r"\.decode\s*\(\s*['\"]base64['\"]\s*\)"),
    re.compile(r"marshal\.loads\s*\("),
    re.compile(r"pickle\.loads\s*\("),
    re.compile(r"dill\.loads\s*\("),
    re.compile(r"cloudpickle\.loads\s*\("),
    # Decode+exec pattern (highly suspicious)
    re.compile(
        r"(?i)(base64\.b64decode|codecs\.decode|marshal\.loads|pickle\.loads)[\s\S]{0,150}?(eval|exec|compile|__import__)"
    ),
]

UNICODE_DIRECTION_OVERRIDE = re.compile(r"[‪-‮⁦-⁩]")  # nosec B613
ZERO_WIDTH_CHARS = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060]")  # nosec B613


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ScanFinding:
    pattern_id: str
    severity: str  # "RED" or "YELLOW"
    description: str
    location: str  # "description", "body", "companion_script"
    matched_text: str = ""


@dataclass
class ScanResult:
    severity: str = "GREEN"  # "GREEN", "YELLOW", "RED"
    findings: list[ScanFinding] = field(default_factory=list)
    passed_static: bool = True
    passed_known_malicious: bool = True
    passed_sandbox: Optional[bool] = None  # None = sandbox not run
    scan_error: Optional[str] = None

    @property
    def is_safe(self) -> bool:
        return self.severity != "RED"


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------


def scan_skill(
    content: str,
    description: str = "",
    repo_url: str = "",
    known_malicious_urls: Optional[set[str]] = None,
) -> ScanResult:
    """Run all static security checks on a SKILL.md.

    Args:
        content: Full raw SKILL.md content.
        description: Extracted description field (scanned separately —
                     it's the primary attack surface since it loads at session start).
        repo_url: GitHub URL for known-malicious index lookup.
        known_malicious_urls: Pre-loaded set of blocked repo URLs.

    Returns:
        ScanResult with severity (GREEN/YELLOW/RED) and findings list.
    """
    result = ScanResult()
    known_malicious_urls = known_malicious_urls or set()

    # --- Known-malicious index (fastest check — do first) ---
    if repo_url and repo_url in known_malicious_urls:
        result.findings.append(
            ScanFinding(
                pattern_id="KM-001",
                severity="RED",
                description="Repository is in known-malicious index",
                location="repo",
            )
        )
        result.passed_known_malicious = False

    # --- Prompt injection in description (highest priority) ---
    _check_patterns(
        text=description,
        patterns=PROMPT_INJECTION_PATTERNS,
        location="description",
        pattern_id_prefix="SP-001",
        severity="RED",
        description="Prompt injection pattern in skill description",
        result=result,
    )

    # --- Full content checks ---
    _check_patterns(
        content,
        PROMPT_INJECTION_PATTERNS,
        "body",
        "SP-001",
        "RED",
        "Prompt injection pattern in skill body",
        result,
    )
    _check_patterns(
        content, SHELL_EXEC_PATTERNS, "body", "SP-002", "RED", "Unguarded shell execution", result
    )
    _check_patterns(
        content, EVAL_EXEC_PATTERNS, "body", "SP-006", "YELLOW", "Unguarded eval/exec", result
    )
    _check_patterns(
        content,
        SECRET_PATTERNS,
        "body",
        "SP-005",
        "RED",
        "Embedded API key or secret token",
        result,
    )
    _check_patterns(
        content,
        ENV_EXFIL_PATTERNS,
        "body",
        "SP-007",
        "YELLOW",
        "Environment variable access",
        result,
    )
    _check_patterns(
        content,
        OBFUSCATION_PATTERNS,
        "body",
        "SP-009",
        "RED",
        "Dynamic code unpacking detected (base64, marshal, pickle)",
        result,
    )

    # --- Unicode checks ---
    if UNICODE_DIRECTION_OVERRIDE.search(content):
        result.findings.append(
            ScanFinding(
                pattern_id="SP-003",
                severity="RED",
                description="Hidden Unicode direction override character",
                location="body",
            )
        )
    if ZERO_WIDTH_CHARS.search(content):
        result.findings.append(
            ScanFinding(
                pattern_id="SP-004",
                severity="RED",
                description="Zero-width character found (possible obfuscation)",
                location="body",
            )
        )

    # --- Homoglyph check ---
    if _has_homoglyphs(content):
        result.findings.append(
            ScanFinding(
                pattern_id="SP-008",
                severity="YELLOW",
                description="Possible homoglyph substitution detected",
                location="body",
            )
        )

    # --- Set overall severity ---
    if any(f.severity == "RED" for f in result.findings):
        result.severity = "RED"
        result.passed_static = False
    elif result.findings:
        result.severity = "YELLOW"
        result.passed_static = True
    else:
        result.severity = "GREEN"
        result.passed_static = True

    return result


def _check_patterns(
    text: str,
    patterns: list[re.Pattern],
    location: str,
    pattern_id_prefix: str,
    severity: str,
    description: str,
    result: ScanResult,
) -> None:
    """Check a list of regex patterns against text and append findings."""
    for i, pattern in enumerate(patterns):
        match = pattern.search(text)
        if match:
            result.findings.append(
                ScanFinding(
                    pattern_id=f"{pattern_id_prefix}.{i + 1}",
                    severity=severity,
                    description=description,
                    location=location,
                    matched_text=match.group(0)[:100],
                )
            )


def _has_homoglyphs(text: str) -> bool:
    """Detect possible homoglyph substitution in code blocks."""
    normalized = unicodedata.normalize("NFKC", text)
    # If normalization changes the text AND the change is in a code-like context
    if normalized != text:
        # Check if non-ASCII chars appear near code patterns
        code_pattern = re.compile(r"`[^`]*`|```[\s\S]*?```")
        for match in code_pattern.finditer(text):
            code_block = match.group()
            if unicodedata.normalize("NFKC", code_block) != code_block:
                return True
    return False


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import sys

    if len(sys.argv) < 2:
        print("Usage: python security_scan.py <path/to/SKILL.md>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    # Extract description from frontmatter if present
    import yaml

    desc = ""
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
            desc = fm.get("description", "")
        except yaml.YAMLError:
            pass

    result = scan_skill(content=content, description=desc)

    icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(result.severity, "❓")
    print(f"{icon} {result.severity}")

    if result.findings:
        print("\nFindings:")
        for f in result.findings:
            sev_icon = "🔴" if f.severity == "RED" else "🟡"
            print(f"  {sev_icon} [{f.pattern_id}] {f.description}")
            if f.matched_text:
                print(f"      matched: {f.matched_text!r}")
    else:
        print("No issues found.")

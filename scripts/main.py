"""
main.py — CLI entry point for agent-hunter.

Orchestrates the full pipeline by wiring together the I/O scripts.

Commands:
    hunt [project_root]     — Discover skills/MCP servers for your project.
    audit                   — Health-check all installed skills.
    rollback                — Restore registry to last known good state.
    context [project_root]  — Show what context agent-hunter sees for your project.
    scaffold <name>         — Generate a SKILL.md stub for a new skill.
    update                  — (v0.3.0 stub) Re-scan and update installed skills.

Usage:
    python scripts/main.py hunt [project_root]
    python scripts/main.py audit
    python scripts/main.py rollback
    python scripts/main.py context [project_root]
    python scripts/main.py scaffold <skill-name>
    python scripts/main.py update

Error handling (per SPEC.md §13):
    - GitHub API unreachable → clear message, non-zero exit, no partial results
    - Zero results → suggest scaffold, non-zero exit
    - Rate limit hit → message with backoff notice, non-zero exit
    - Security RED block → count reported, blocked results never shown
    - Registry file corrupt → show error path, suggest manual fix, non-zero exit
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow running as `python scripts/main.py` from repo root
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from context_extractor import extract_context  # noqa: E402
from hunter import Hunter  # noqa: E402
from scorer import score_results  # noqa: E402
from security_scan import scan_skill, ScanResult  # noqa: E402
from reporter import render_hunt_report  # noqa: E402
from rollback import rollback as do_rollback  # noqa: E402
from scaffold import scaffold_skill  # noqa: E402
from skill_parser import parse_skill_content, SkillMetadata  # noqa: E402
from audit import Auditor  # noqa: E402


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_DEFAULTS_PATH = Path(__file__).parent.parent / "config" / "defaults.json"
_USER_CONFIG_PATH = Path.home() / ".agent-hunter" / "config.json"


def _load_config() -> dict:
    """Load config: user config overrides defaults."""
    config: dict = {}
    if _DEFAULTS_PATH.exists():
        try:
            config = json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[agent-hunter] Warning: could not load defaults.json: {exc}")

    if _USER_CONFIG_PATH.exists():
        try:
            user = json.loads(_USER_CONFIG_PATH.read_text(encoding="utf-8"))
            config = _deep_merge(config, user)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[agent-hunter] Warning: could not load user config: {exc}")

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# Command: hunt
# ---------------------------------------------------------------------------

def cmd_hunt(args: list[str]) -> int:
    """Run the full hunt pipeline.

    Returns:
        0 on success with results, 1 if no results or error.
    """
    project_root = args[0] if args else "."
    root_path = Path(project_root).resolve()

    if not root_path.exists():
        print(f"[agent-hunter] Error: project root not found: {root_path}")
        return 1

    config = _load_config()
    hunt_cfg = config.get("hunt", {})

    # --- Extract context ---
    print(f"[agent-hunter] Extracting context from: {root_path}")
    try:
        profile = extract_context(root_path)
    except Exception as exc:
        print(f"[agent-hunter] Context extraction failed: {exc}")
        return 1

    if not profile.tech_stack:
        print("[agent-hunter] No tech stack detected — cannot search without signal.")
        print("  Tip: Add a requirements.txt, package.json, or pyproject.toml to your project.")
        return 1

    print(f"[agent-hunter] Stack: {', '.join(profile.tech_stack[:8])}")

    # --- Hunt GitHub ---
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("[agent-hunter] Note: GITHUB_TOKEN not set — using unauthenticated rate limit (60/hr).")

    hunter = Hunter(
        github_token=github_token,
        min_stars=hunt_cfg.get("min_stars", 10),
        max_age_days=hunt_cfg.get("max_age_days", 180),
        include_mcp=hunt_cfg.get("include_mcp_servers", True),
    )

    print("[agent-hunter] Hunting GitHub for skills and MCP servers...")
    try:
        results = hunter.hunt(profile)
    except Exception as exc:
        print(f"[agent-hunter] Hunt failed: {exc}")
        return 1

    if not results:
        print("[agent-hunter] No results found after pre-filtering.")
        print("  Tip: Try `agent-hunter scaffold <name>` to create a skill for your stack.")
        return 1

    print(f"[agent-hunter] Found {len(results)} candidate(s) after pre-filtering. Scanning...")

    # --- Security scan each result ---
    scan_results: dict[str, ScanResult] = {}
    for r in results:
        scan = scan_skill(
            content=r.raw_content,
            description=r.description,
            repo_url=r.repo_url,
        )
        scan_results[r.repo_url] = scan

    red_blocked = sum(1 for s in scan_results.values() if s.severity == "RED")
    if red_blocked:
        print(f"[agent-hunter] {red_blocked} result(s) blocked by security scan.")

    # --- Parse metadata for scored results ---
    metadata_map: dict[str, SkillMetadata] = {}
    for r in results:
        if r.raw_content:
            try:
                meta = parse_skill_content(r.raw_content)
                metadata_map[r.repo_url] = meta
            except Exception:
                pass  # missing metadata is fine — scorer handles None gracefully

    # --- Score and rank ---
    scored = score_results(results, profile, metadata_map)

    # --- Render report ---
    top_n = hunt_cfg.get("top_n_shown", 5)
    render_hunt_report(
        scored_results=scored,
        scan_results=scan_results,
        project_root=str(root_path),
        top_n=top_n,
    )

    visible = [s for s in scored if scan_results.get(s.hunt_result.repo_url, ScanResult()).severity != "RED"]
    return 0 if visible else 1


# ---------------------------------------------------------------------------
# Command: context
# ---------------------------------------------------------------------------

def cmd_context(args: list[str]) -> int:
    """Show the context profile that agent-hunter sees for the project."""
    project_root = args[0] if args else "."
    root_path = Path(project_root).resolve()

    if not root_path.exists():
        print(f"[agent-hunter] Error: path not found: {root_path}")
        return 1

    try:
        profile = extract_context(root_path)
    except Exception as exc:
        print(f"[agent-hunter] Context extraction failed: {exc}")
        return 1

    print(f"\n{'═' * 60}")
    print("  agent-hunter · Context Profile")
    print(f"  Project: {root_path}")
    print(f"{'═' * 60}\n")
    print(f"  Tech stack ({len(profile.tech_stack)} detected):")
    for t in profile.tech_stack:
        print(f"    · {t}")
    if profile.domain_tags:
        print(f"\n  Domain tags: {', '.join(profile.domain_tags)}")
    if profile.active_domains:
        print(f"  Active (last 7d): {', '.join(profile.active_domains)}")
    if profile.recent_domains:
        print(f"  Recent (last 30d): {', '.join(profile.recent_domains)}")
    if profile.dormant_domains:
        print(f"  Dormant (90+d): {', '.join(profile.dormant_domains)}")
    if profile.sources_read:
        print(f"\n  Sources read: {', '.join(profile.sources_read)}")
    if profile.extraction_warnings:
        print("\n  Warnings:")
        for w in profile.extraction_warnings:
            print(f"    ⚠️  {w}")
    print(f"\n{'═' * 60}\n")
    return 0


# ---------------------------------------------------------------------------
# Command: audit
# ---------------------------------------------------------------------------

def cmd_audit(_args: list[str]) -> int:
    """Run the full audit on all installed skills."""
    try:
        auditor = Auditor()
        report = auditor.run()
        return 1 if report.has_issues else 0
    except Exception as exc:
        print(f"[agent-hunter] Audit failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: rollback
# ---------------------------------------------------------------------------

def cmd_rollback(_args: list[str]) -> int:
    """Restore registry to last known good state."""
    try:
        success = do_rollback(interactive=True)
        return 0 if success else 1
    except Exception as exc:
        print(f"[agent-hunter] Rollback failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: scaffold
# ---------------------------------------------------------------------------

def cmd_scaffold(args: list[str]) -> int:
    """Generate a SKILL.md stub for a new skill."""
    if not args:
        print("[agent-hunter] Error: scaffold requires a skill name.")
        print("  Usage: agent-hunter scaffold <name>")
        return 1

    name = args[0]
    project_root = args[1] if len(args) > 1 else "."

    try:
        scaffold_skill(name=name, project_root=project_root)
        return 0
    except Exception as exc:
        print(f"[agent-hunter] Scaffold failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: update (v0.3.0 stub)
# ---------------------------------------------------------------------------

def cmd_update(_args: list[str]) -> int:
    """Update installed skills (v0.3.0 feature — not yet implemented)."""
    print("[agent-hunter] `update` is planned for v0.3.0.")
    print("  For now, re-run `agent-hunter hunt` to find newer versions manually.")
    return 0


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

USAGE = """\
agent-hunter — proactive SKILL.md and MCP server discovery

Usage:
  agent-hunter hunt [project_root]    Discover skills for your project
  agent-hunter audit                  Health-check installed skills
  agent-hunter rollback               Restore registry to last good state
  agent-hunter context [project_root] Show detected project context
  agent-hunter scaffold <name>        Generate a new SKILL.md stub
  agent-hunter update                 Update installed skills (v0.3.0)

Options:
  -h, --help    Show this message and exit

Environment:
  GITHUB_TOKEN  GitHub personal access token (5000 req/hr vs 60/hr unauth)
"""


def cmd_help(_args: list[str]) -> int:
    print(USAGE)
    return 0


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_COMMANDS: dict[str, object] = {
    "hunt":     cmd_hunt,
    "audit":    cmd_audit,
    "rollback": cmd_rollback,
    "context":  cmd_context,
    "scaffold": cmd_scaffold,
    "update":   cmd_update,
    "help":     cmd_help,
    "--help":   cmd_help,
    "-h":       cmd_help,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse command line and dispatch to the appropriate handler.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, non-zero = failure).
    """
    argv = argv if argv is not None else sys.argv[1:]

    if not argv:
        cmd_help([])
        return 1

    command = argv[0]
    rest = argv[1:]

    handler = _COMMANDS.get(command)
    if handler is None:
        print(f"[agent-hunter] Unknown command: '{command}'")
        print("  Run `agent-hunter --help` for usage.")
        return 1

    return handler(rest)  # type: ignore[operator]


if __name__ == "__main__":
    sys.exit(main())

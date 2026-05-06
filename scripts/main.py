"""
main.py — CLI entry point for agent-hunter.

Orchestrates the full pipeline by wiring together the I/O scripts.

Commands:
    hunt [project_root]     — Discover skills/MCP servers for your project.
    audit                   — Health-check all installed skills.
    update [skill_name]     — Update installed skills interactively.
    rollback                — Restore registry to last known good state.
    context [project_root]  — Show what context agent-hunter sees for your project.
    scaffold <name>         — Generate a SKILL.md stub for a new skill.
    install <owner> <repo>  — Install a skill directly by owner/repo.
    remove <skill_name>     — Permanently remove an installed skill.
    enable <skill_name>     — Re-enable a disabled (_prefixed) skill.

Usage:
    python scripts/main.py hunt [project_root]
    python scripts/main.py audit
    python scripts/main.py update [skill_name]
    python scripts/main.py rollback
    python scripts/main.py context [project_root]
    python scripts/main.py scaffold <skill-name>
    python scripts/main.py install <owner> <repo>
    python scripts/main.py remove <skill_name>
    python scripts/main.py enable <skill_name>

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
from installer import Installer, build_action_list, PendingAction  # noqa: E402
from update import SkillUpdater  # noqa: E402
from registry import Registry  # noqa: E402


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
# Helpers for hunt command (confirm + execute actions)
# ---------------------------------------------------------------------------


def _list_installed_skills() -> set[str]:
    """Return set of currently installed skill directory names."""
    skills_dir = Path.home() / ".claude" / "skills"
    if not skills_dir.exists():
        return set()
    return {d.name for d in skills_dir.iterdir() if d.is_dir()}


def _get_dangerous_installed() -> list[str]:
    """Return names of installed skills that are currently RED-flagged.

    Queries the registry for each installed skill to check if it was
    last-scanned as RED.
    """

    installed = _list_installed_skills()
    registry = Registry()
    dangerous = []

    for skill_name in installed:
        # Skip disabled skills (those starting with _)
        if skill_name.startswith("_"):
            continue

        # Look up in registry by repo name to get latest scan severity
        entries = registry.all()
        for entry in entries:
            if entry.name == skill_name:
                # If audit_status is "security_issue", it's dangerous
                if entry.audit_status == "security_issue":
                    dangerous.append(skill_name)
                break

    return dangerous


def _prompt_confirm_actions(
    actions: list[PendingAction], *, auto_yes: bool = False
) -> list[PendingAction]:
    """Display action summary and ask user for confirmation.

    Args:
        actions: Pending install/disable actions to confirm.
        auto_yes: When True, skip the prompt and confirm all actions.

    Returns:
        List of confirmed PendingAction items (may be subset if user skips some).
    """
    if not actions:
        return []

    print("\n" + "─" * 70)
    print("  READY TO ACT — here's what I'll do:")
    print("─" * 70)

    installs = [a for a in actions if a.action == "install"]
    disables = [a for a in actions if a.action == "disable"]

    if installs:
        print(f"\n  INSTALL  ({len(installs)} skills → ~/.claude/skills/)")
        for i, act in enumerate(installs, 1):
            print(f"    {i}. {act.skill_name:40} {act.repo_url}")
            if act.reason:
                print(f"       ({act.reason})")

    if disables:
        print(f"\n  DISABLE  ({len(disables)} dangerous skill(s) — soft-disable, reversible)")
        for i, act in enumerate(disables, 1):
            print(f"    {i}. {act.skill_name:40} {act.reason}")

    print("\n  Note: YELLOW skills are included — review security findings")
    print("  above before confirming. You can remove any from the list.")
    print("\n" + "─" * 70)

    # --yes flag or non-interactive stdin: auto-confirm all
    if auto_yes or not sys.stdin.isatty():
        print("  Auto-confirmed (--yes or non-interactive mode).")
        return actions

    # Get user input
    response = input("  Proceed? [y/N] or type numbers to skip (e.g. '1,3'): ").strip().lower()

    if response in ("y", "yes"):
        return actions
    elif response in ("n", "no", ""):
        print("[agent-hunter] Cancelled.")
        return []
    else:
        # Parse skip list (e.g. "1,3" means skip first and third)
        try:
            skip_indices = {int(x.strip()) - 1 for x in response.split(",")}
            confirmed = [a for i, a in enumerate(actions) if i not in skip_indices]
            if confirmed:
                print(f"[agent-hunter] Confirmed {len(confirmed)}/{len(actions)} action(s).")
            else:
                print("[agent-hunter] No actions confirmed.")
            return confirmed
        except (ValueError, IndexError):
            print("[agent-hunter] Invalid input. Cancelled.")
            return []


# ---------------------------------------------------------------------------
# Command: hunt
# ---------------------------------------------------------------------------


def cmd_hunt(args: list[str]) -> int:
    """Run the full hunt pipeline.

    Flags:
        --yes            Skip confirmation prompt and execute all actions.
        --print-actions  Print pending actions as JSON to stdout, then exit 0.
                         SKILL.md reads this output to present confirmation in chat.

    Returns:
        0 on success with results, 1 if no results or error.
    """
    project_root = "."
    intent = None
    yes = "--yes" in args
    print_actions = "--print-actions" in args

    # Remove flag tokens before positional parsing
    positional = [a for a in args if a not in ("--yes", "--print-actions")]

    # Simple explicit argument parsing
    if positional:
        if positional[0] != "--intent":
            project_root = positional[0]

        try:
            intent_idx = positional.index("--intent")
            if intent_idx + 1 < len(positional):
                intent = positional[intent_idx + 1]
        except ValueError:
            pass

    root_path = Path(project_root).resolve()

    if not root_path.exists():
        print(f"[agent-hunter] Error: project root not found: {root_path}")
        return 1

    config = _load_config()
    hunt_cfg = config.get("hunt", {})

    # --- Extract context ---
    print(f"[agent-hunter] Extracting context from: {root_path}")
    if intent:
        print(f"[agent-hunter] Custom intent provided: '{intent}'")

    try:
        profile = extract_context(root_path, intent=intent)
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
        print(
            "[agent-hunter] Note: GITHUB_TOKEN not set — using unauthenticated rate limit (60/hr)."
        )

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

    visible = [
        s
        for s in scored
        if scan_results.get(s.hunt_result.repo_url, ScanResult()).severity != "RED"
    ]

    # --- Build, confirm, and execute actions (Step 7-9 in SKILL.md) ---
    if not visible:
        return 1

    print("\n[agent-hunter] Step 7: Building action list...\n")

    installed_names = _list_installed_skills()
    dangerous_installed = _get_dangerous_installed()

    # Build action list from top N visible results + dangerous installed
    actions = build_action_list(
        top_results=visible[:top_n],
        scan_results=scan_results,
        installed_names=installed_names,
        dangerous_installed=dangerous_installed,
    )

    if not actions:
        print("[agent-hunter] No new actions to take. All recommendations are already installed.")
        return 0

    # --- Step 8: Confirm actions ---
    if print_actions:
        # SKILL.md mode: print JSON for the LLM to read, then exit without executing.
        # SKILL.md presents this list in chat and calls installer directly.
        output = {
            "pending_actions": [
                {
                    "action": a.action,
                    "skill_name": a.skill_name,
                    "repo_url": a.repo_url,
                    "reason": a.reason,
                }
                for a in actions
            ]
        }
        print(json.dumps(output, indent=2))
        return 0

    confirmed_actions = _prompt_confirm_actions(actions, auto_yes=yes)

    if not confirmed_actions:
        print("[agent-hunter] No actions confirmed. Exiting.")
        return 1

    # --- Step 9: Execute confirmed actions ---
    print("\n[agent-hunter] Executing confirmed actions...\n")
    installer = Installer()
    results = installer.execute_actions(confirmed_actions)

    # Summary
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    print("\n" + "─" * 70)
    print(f"  Summary: {successful}/{len(results)} action(s) succeeded")
    if failed > 0:
        print(f"  ⚠️  {failed} action(s) failed — review messages above")
    print("─" * 70 + "\n")

    return 0 if failed == 0 else 1


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
    """Run the full audit on all installed skills.

    Creates a pre-audit snapshot before running audit (v0.5.0+).
    """

    try:
        # Create pre-audit snapshot for safe recovery (v0.5.0)
        reg = Registry()
        snapshot_path = reg.snapshot(trigger="pre_audit")
        print(f"[agent-hunter] Snapshot created: {snapshot_path.name}")

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
# Command: install
# ---------------------------------------------------------------------------


def cmd_install(args: list[str]) -> int:
    """Install a skill directly by GitHub owner/repo."""
    if len(args) < 2:
        print("[agent-hunter] Error: install requires <owner> <repo>.")
        print("  Usage: agent-hunter install <owner> <repo>")
        return 1
    owner, repo = args[0], args[1]
    try:
        installer = Installer()
        result = installer.install(owner, repo)
        if result.success:
            print(f"[agent-hunter] {result.message}")
            return 0
        else:
            print(f"[agent-hunter] Install failed: {result.error}")
            return 1
    except Exception as exc:
        print(f"[agent-hunter] Install failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: remove
# ---------------------------------------------------------------------------


def cmd_remove(args: list[str]) -> int:
    """Permanently remove an installed skill."""
    if not args:
        print("[agent-hunter] Error: remove requires a skill name.")
        print("  Usage: agent-hunter remove <skill_name>")
        return 1
    skill_name = args[0]
    try:
        installer = Installer()
        result = installer.uninstall(skill_name)
        if result.success:
            print(f"[agent-hunter] {result.message}")
            return 0
        else:
            print(f"[agent-hunter] Remove failed: {result.error}")
            return 1
    except Exception as exc:
        print(f"[agent-hunter] Remove failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: enable
# ---------------------------------------------------------------------------


def cmd_enable(args: list[str]) -> int:
    """Re-enable a disabled (_prefixed) skill."""
    if not args:
        print("[agent-hunter] Error: enable requires a skill name.")
        print("  Usage: agent-hunter enable <skill_name>")
        return 1
    skill_name = args[0]
    try:
        installer = Installer()
        result = installer.enable(skill_name)
        if result.success:
            print(f"[agent-hunter] {result.message}")
            return 0
        else:
            print(f"[agent-hunter] Enable failed: {result.error}")
            return 1
    except Exception as exc:
        print(f"[agent-hunter] Enable failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------


def cmd_update(args: list[str]) -> int:
    """Update installed skills interactively.

    Creates a pre-update snapshot before running updates (v0.5.0+).
    """

    skill_name = args[0] if args else None
    try:
        # Create pre-update snapshot for safe recovery (v0.5.0)
        reg = Registry()
        snapshot_path = reg.snapshot(trigger="pre_update")
        print(f"[agent-hunter] Snapshot created: {snapshot_path.name}")

        updater = SkillUpdater()
        approved, total = updater.run_interactive_update(skill_name=skill_name)
        return 0 if approved == total else 1
    except Exception as exc:
        print(f"[agent-hunter] Update failed: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Command: contribute
# ---------------------------------------------------------------------------


def cmd_contribute(args: list[str]) -> int:
    """Contribute an installed skill to the verified index (v0.4.0).

    Validates the skill, runs security scan, validates frontmatter,
    and opens a GitHub issue with pre-filled template.

    Usage: agent-hunter contribute <skill_name>
    """
    if not args:
        print("[agent-hunter] Error: contribute requires a skill name.")
        print("  Usage: agent-hunter contribute <skill_name>")
        return 1

    skill_name = args[0]

    try:
        from pathlib import Path
        from security_scan import scan_skill
        from skill_parser import parse_skill_content
        import subprocess

        # Check if skill is installed
        skill_path = Path.home() / ".claude" / "skills" / skill_name
        if not skill_path.exists():
            print(f"[agent-hunter] Error: Skill '{skill_name}' not found in ~/.claude/skills/")
            return 1

        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            print(f"[agent-hunter] Error: {skill_file} not found")
            return 1

        # Read skill content
        content = skill_file.read_text(encoding="utf-8", errors="ignore")

        # Run security scan
        scan_result = scan_skill(content=content, repo_url="")

        if scan_result.severity == "RED":
            print(f"[agent-hunter] Error: Security scan FAILED for '{skill_name}'")
            print("  RED findings prevent contribution:")
            for finding in scan_result.findings:
                if finding.severity == "RED":
                    print(f"    - {finding.description}")
            return 1

        # Validate YAML frontmatter
        try:
            parsed = parse_skill_content(content)
        except Exception as e:
            print(f"[agent-hunter] Error: Invalid SKILL.md frontmatter: {e}")
            return 1

        # Check required fields in raw frontmatter
        required_fields = {"name", "version", "trigger", "domain_tags"}
        available_fields = set(parsed.raw_frontmatter.keys())
        missing = required_fields - available_fields
        if missing:
            print(
                f"[agent-hunter] Error: Missing required fields in SKILL.md: {', '.join(sorted(missing))}"
            )
            return 1

        # Get registry info if available
        registry_info = ""
        try:
            registry = Registry()
            for entry in registry.all():
                if entry.name == skill_name:
                    registry_info = f"\nRepo: {entry.repo_url}\nStars: {entry.stars}\nTrust Tier: {entry.trust_tier}"
                    break
        except Exception:
            pass

        # Build issue template
        template_path = Path(__file__).parent.parent / "assets" / "contribute_template.md"
        if template_path.exists():
            template = template_path.read_text(encoding="utf-8")
        else:
            template = _default_contribute_template()

        # Fill template
        filled_issue = template.format(
            skill_name=skill_name,
            registry_info=registry_info,
            scan_status="✅ PASSED" if scan_result.severity == "GREEN" else "⚠️ WARNINGS",
            findings_summary=_summarize_findings(scan_result),
            version=parsed.version or "N/A",
        )

        issue_title = f"Contribute: {skill_name}"
        issue_body = filled_issue

        # Try to use GitHub CLI
        try:
            # Check if gh is available
            subprocess.run(["which", "gh"], check=True, capture_output=True)

            # Create issue via GitHub CLI
            cmd = [
                "gh",
                "issue",
                "create",
                "--repo",
                "indhra/agent-hunter",
                "--title",
                issue_title,
                "--body",
                issue_body,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Extract issue URL from output
                output_lines = result.stdout.strip().split("\n")
                print("[agent-hunter] ✅ Contribution issue created!")
                print(f"  {output_lines[-1] if output_lines else 'See GitHub for the issue'}")
                return 0
            else:
                print(f"[agent-hunter] Error creating GitHub issue: {result.stderr}")
                print("\nFallback: Here's the issue template to post manually:")
                print("=" * 60)
                print(f"Title: {issue_title}")
                print("=" * 60)
                print(issue_body)
                return 1
        except (FileNotFoundError, subprocess.CalledProcessError):
            # gh not installed, print template
            print("[agent-hunter] ℹ️  GitHub CLI (gh) not found. Here's your contribution template:")
            print("=" * 60)
            print(f"Title: {issue_title}")
            print("=" * 60)
            print(issue_body)
            print("=" * 60)
            print("Post this to: https://github.com/indhra/agent-hunter/issues/new")
            return 0

    except Exception as e:
        print(f"[agent-hunter] Contribute failed: {e}")
        return 1


def _summarize_findings(scan_result) -> str:
    """Summarize security scan findings."""
    if not scan_result.findings:
        return "No findings"

    red_count = sum(1 for f in scan_result.findings if f.severity == "RED")
    yellow_count = sum(1 for f in scan_result.findings if f.severity == "YELLOW")

    summary = []
    if red_count > 0:
        summary.append(f"🔴 {red_count} RED")
    if yellow_count > 0:
        summary.append(f"🟡 {yellow_count} YELLOW")

    return ", ".join(summary) if summary else "No findings"


def _default_contribute_template() -> str:
    """Default contribution template if assets/contribute_template.md is missing."""
    return """\
## Contribute: {skill_name}

**Skill Name:** {skill_name}
{registry_info}

**Security Scan Result:** {scan_status}
{findings_summary}

### Self-Certification Checklist

Please verify that your skill meets these requirements before submitting:

- [ ] **Skill naming:** Follows Claude skill naming conventions (lowercase, hyphens, descriptive)
- [ ] **Frontmatter complete:** SKILL.md has all required fields (name, version, trigger, domain_tags)
- [ ] **Tested locally:** Skill has been tested in Claude and works as expected
- [ ] **No credentials:** No hardcoded API keys, tokens, or sensitive data
- [ ] **Security passing:** Passes security scan or findings are documented and justified
- [ ] **Clear value:** Provides clear, documented value for agent-hunter users
- [ ] **Documentation:** Includes clear trigger phrase and usage instructions

### How We Review

Verified skills are reviewed by the agent-hunter maintainers for:
1. **Security:** No malicious code, safe patterns only
2. **Quality:** Clear documentation, useful trigger phrase
3. **Compatibility:** Works well with agent-hunter ecosystem
4. **Utility:** Addresses real developer needs

### Questions?

- See [VERIFIED_SKILLS.md](references/VERIFIED_SKILLS.md) for verified skills
- See [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) for security guidelines
- Open a discussion in [Issues](https://github.com/indhra/agent-hunter/issues)

Thank you for contributing to agent-hunter! 🎉
"""


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

USAGE = """\
agent-hunter — proactive SKILL.md and MCP server discovery

Usage:
  agent-hunter hunt [project_root]    Discover skills for your project
  agent-hunter audit                  Health-check installed skills
  agent-hunter update [skill_name]    Update installed skills
  agent-hunter contribute <skill>     Contribute a skill to verified index
  agent-hunter rollback               Restore registry to last good state
  agent-hunter context [project_root] Show detected project context
  agent-hunter scaffold <name>        Generate a new SKILL.md stub
  agent-hunter install <owner> <repo> Install a skill by owner/repo
  agent-hunter remove <skill_name>    Remove an installed skill
  agent-hunter enable <skill_name>    Re-enable a disabled skill

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
    "hunt": cmd_hunt,
    "audit": cmd_audit,
    "rollback": cmd_rollback,
    "context": cmd_context,
    "scaffold": cmd_scaffold,
    "install": cmd_install,
    "remove": cmd_remove,
    "enable": cmd_enable,
    "update": cmd_update,
    "contribute": cmd_contribute,
    "help": cmd_help,
    "--help": cmd_help,
    "-h": cmd_help,
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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

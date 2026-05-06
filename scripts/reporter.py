"""
reporter.py — Format and output the hunt report.

Output targets:
    1. Terminal: rich table with 🟢/🟡/🔴 trust signals, score bar, "why this"
    2. Markdown: ~/.agent-hunter/reports/hunt_report_YYYY-MM-DD.md

Input:  List[ScoredResult] (from scorer.py, security scan results attached)
Output: None (side effects: terminal print + file write)

No LLM calls. No network access.
Note: The "why this for you" explanation per result is written by the host agent,
      not generated here. This module formats what it receives.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scorer import ScoredResult
from security_scan import ScanResult


REPORTS_DIR = Path.home() / ".agent-hunter" / "reports"

SEVERITY_ICONS = {
    "GREEN": "🟢",
    "YELLOW": "🟡",
    "RED": "🔴",
}

TRUST_LABELS = {
    "verified": "[VERIFIED]",
    "community": "[COMMUNITY]",
    "raw": "[RAW]",
}


# ---------------------------------------------------------------------------
# Main report function
# ---------------------------------------------------------------------------


def render_hunt_report(
    scored_results: list[ScoredResult],
    scan_results: dict[str, ScanResult],  # keyed by repo_url
    project_root: str = "",
    top_n: int = 5,
    save_markdown: bool = True,
) -> None:
    """Render the hunt report to terminal and optionally save as markdown.

    Args:
        scored_results: Ranked list from scorer.py (descending by score).
        scan_results: Security scan results keyed by repo_url.
        project_root: Project path shown in report header.
        top_n: How many top results to show.
        save_markdown: Whether to save a markdown report file.
    """
    top = [r for r in scored_results if _include_in_report(r, scan_results)][:top_n]
    red_count = sum(
        1
        for r in scored_results
        if scan_results.get(r.hunt_result.repo_url, ScanResult()).severity == "RED"
    )

    _print_terminal(top, scan_results, red_count, project_root)

    if save_markdown:
        path = _save_markdown(top, scan_results, red_count, project_root, scored_results)
        print(f"\n[agent-hunter] Report saved: {path}")


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------


def _print_terminal(
    results: list[ScoredResult],
    scan_results: dict[str, ScanResult],
    red_count: int,
    project_root: str,
) -> None:
    """Print the hunt report to stdout with formatting."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'═' * 70}")
    print(f"  agent-hunter · Hunt Report · {now}")
    if project_root:
        print(f"  Project: {project_root}")
    print(f"{'═' * 70}\n")

    if not results:
        print("  No results found matching your project stack.\n")
        print("  Tip: Run `agent-hunter scaffold <name>` to create a skill stub.")
        return

    for i, s in enumerate(results, 1):
        r = s.hunt_result
        scan = scan_results.get(r.repo_url, ScanResult())
        severity_icon = SEVERITY_ICONS.get(scan.severity, "⚪")
        trust_label = TRUST_LABELS.get(r.trust_tier, "[RAW]")
        score_bar = _score_bar(s.total_score)

        print(f"  {i}. {severity_icon} {r.name or r.repo_name}")
        print(f"     {trust_label} · {r.stars}⭐ · score: {score_bar} {s.total_score:.2f}")
        print(f"     {r.repo_url}")
        if r.description:
            print(f"     {r.description[:100]}")
        if s.explanation:
            print(f"     → {s.explanation}")
        if scan.findings:
            for f in scan.findings[:2]:
                icon = "🔴" if f.severity == "RED" else "🟡"
                print(f"     {icon} {f.description}")
        print(f"     Install: gh skill install {r.owner}/{r.repo_name}")
        print()

    if red_count > 0:
        print(f"  ⚠️  {red_count} result(s) blocked by security scan (not shown above).")

    print("  Run any install command above to add a skill to ~/.claude/skills/")
    print("  To audit installed skills: `agent-hunter audit`")
    print(f"{'═' * 70}\n")


def _score_bar(score: float, width: int = 10) -> str:
    """Convert a 0.0–1.0 score to a simple ASCII bar."""
    filled = round(score * width)
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def _include_in_report(s: ScoredResult, scan_results: dict[str, ScanResult]) -> bool:
    """Exclude RED results from the main report (they're counted separately)."""
    scan = scan_results.get(s.hunt_result.repo_url, ScanResult())
    return scan.severity != "RED"


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _save_markdown(
    results: list[ScoredResult],
    scan_results: dict[str, ScanResult],
    red_count: int,
    project_root: str,
    all_scored: list[ScoredResult],
) -> Path:
    """Save the hunt report as a markdown file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"hunt_report_{date_str}.md"

    lines = [
        "# agent-hunter Hunt Report",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Project:** {project_root or 'unknown'}",
        f"**Results shown:** {len(results)} / {len(all_scored)} total (RED blocked: {red_count})",
        "",
        "---",
        "",
    ]

    skills = [r for r in results if r.hunt_result.result_type == "skill"]
    mcps = [r for r in results if r.hunt_result.result_type == "mcp"]

    if skills:
        lines.append("## Skills\n")
        for s in skills:
            lines.extend(_markdown_result(s, scan_results))

    if mcps:
        lines.append("## MCP Servers\n")
        for s in mcps:
            lines.extend(_markdown_result(s, scan_results))

    if red_count > 0:
        lines.append(
            f"\n---\n\n## Blocked Results\n\n{red_count} result(s) failed security scan and were excluded.\n"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _markdown_result(s: ScoredResult, scan_results: dict[str, ScanResult]) -> list[str]:
    r = s.hunt_result
    scan = scan_results.get(r.repo_url, ScanResult())
    severity_icon = SEVERITY_ICONS.get(scan.severity, "⚪")
    trust_label = TRUST_LABELS.get(r.trust_tier, "[RAW]")

    lines = [
        f"### {severity_icon} {r.name or r.repo_name}",
        f"- **Trust:** {trust_label}",
        f"- **Score:** {s.total_score:.2f}",
        f"- **Stars:** {r.stars}",
        f"- **Repo:** {r.repo_url}",
    ]
    if r.description:
        lines.append(f"- **Description:** {r.description[:150]}")

    # MCP-specific info
    if r.result_type == "mcp":
        if r.mcp_transport_type:
            lines.append(f"- **Transport:** {r.mcp_transport_type}")
        if r.mcp_capabilities:
            lines.append(f"- **Capabilities:** {', '.join(r.mcp_capabilities)}")

    if s.explanation:
        lines.append(f"- **Why this for you:** {s.explanation}")

    # Installation command (varies by type)
    if r.result_type == "mcp" and r.mcp_install_command:
        install_cmd = r.mcp_install_command
    else:
        install_cmd = f"gh skill install {r.owner}/{r.repo_name}"

    lines.append(f"\n**Install:**\n```bash\n{install_cmd}\n```\n")
    return lines

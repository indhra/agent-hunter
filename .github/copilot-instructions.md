# agent-hunter — Copilot Instructions

You are helping implement **agent-hunter**: a proactive, security-vetted SKILL.md and MCP server discovery system packaged as a Claude-native skill. It reads a developer's project context, hunts GitHub for relevant skills, security-scans every result, and surfaces ranked recommendations. Think of it as the immune system of an AI agentic team.

**Full spec:** See `SPEC.md` and `ROADMAP.md` in the repo root.

---

## Architecture (read this before touching any file)

The design has a hard constraint: **Python scripts do I/O only. No LLM calls from scripts.** All reasoning happens in `SKILL.md` (the host agent's instructions).

```
SKILL.md (Claude's brain)
    │
    ▼
scripts/ (I/O workers — Python, no LLM)
    context_extractor.py   → reads project files, extracts ONLY tech keywords
    hunter.py              → queries GitHub API for SKILL.md + MCP configs
    skill_parser.py        → parses YAML frontmatter from SKILL.md files
    security_scan.py       → static + runtime security analysis
    scorer.py              → 4-signal relevance scoring + trust tiers
    registry.py            → local registry (~/.agent-hunter/registry.json)
    reporter.py            → terminal + markdown report output
    audit.py               → health check for installed skills
    rollback.py            → restore registry to last known good state
    sandbox.py             → subprocess/docker isolation for suspicious skills
    scaffold.py            → generate SKILL.md stubs for new skills
```

**Data flow for `agent-hunter hunt`:**
```
context_extractor → hunter → security_scan (per result) → scorer → reporter
                       ↓
                   registry (dedup + SHA store)
```

---

## Current Implementation Status

### Fully implemented (do not rewrite unless fixing a bug)
- `skill_parser.py` — complete, 11 tests passing
- `context_extractor.py` — complete, 9 tests passing
- `security_scan.py` — complete, 22 tests passing (10 patterns, static analysis)
- `scorer.py` — complete, 8 tests passing
- `registry.py` — complete (SHA tracking, snapshot/restore)
- `reporter.py` — complete (terminal rich table + markdown save)
- `rollback.py` — complete
- `sandbox.py` — complete (subprocess mode; Docker is a v0.3.0 stub)
- `scaffold.py` — complete

### Needs work (primary focus for v0.1.0)
- **`hunter.py`** — partial. Missing:
  1. `_passes_prefilter()` is stubbed — needs real GitHub repo metadata fetch (stars, last_commit_date)
  2. `_fetch_skill_content()` doesn't exist — needs to fetch raw SKILL.md content from GitHub raw URL
  3. No pagination (currently takes only first 30 results)
  4. MCP server query building needs improvement

### Missing entirely (needed for v0.1.0 end-to-end)
- **`scripts/main.py`** — the CLI entry point that wires all scripts together
  - Commands: `hunt`, `audit`, `rollback`, `context`, `scaffold`, `update`
  - Should call the other scripts in sequence
  - Should handle all error cases from `SPEC.md § 13. Error Handling`

---

## Coding Standards

- **Python 3.10+** — use `match/case` only if it adds real clarity
- **Type hints required** on all public functions and method signatures
- **Docstrings required** (Google style) on all modules and public functions
- **No bare `except:`** — catch specific exceptions, log them, handle gracefully
- **Fail loudly, never silently** — partial results are worse than a clear error message
- **Linter:** `ruff` — run `ruff check .` before committing
- **Tests:** `pytest tests/` — add tests for any new behavior, not just happy paths

---

## Privacy constraint (non-negotiable — enforce in all context-reading code)

`context_extractor.py` may only transmit tech keyword signals from an explicit allowlist (framework names, library names). Never extract: file paths, variable names, function names, class names, commit message text, repo name, or any project-specific string.

This is enforced in code via `TECH_ALLOWLIST` and `_ALLOWLIST_PATTERN` in `context_extractor.py`. Do not bypass or weaken this.

---

## Security constraint (non-negotiable)

`security_scan.py` RED results are NEVER shown to the user. The count is reported only. If you're writing code that filters or renders results, verify this rule is enforced. See `reporter.py:_include_in_report()`.

---

## Config

Default config is in `config/defaults.json`. At runtime, user config lives at `~/.agent-hunter/config.json`. Scripts should read user config if it exists, fall back to defaults.

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run just security scan tests (most important)
pytest tests/test_security_scan.py -v -k "malicious"
pytest tests/test_security_scan.py -v -k "clean"

# Run with coverage
pytest tests/ --cov=scripts --cov-report=term-missing
```

All 50 tests must pass before any commit.

---

## Key decisions already made (don't relitigate these)

1. **Scan → confirm → act flow.** After showing the hunt report, agent-hunter builds an action list (installs + disables) and asks the user ONCE to confirm. Then executes. See SKILL.md Steps 7–8.
2. **Actions: install, disable, rollback.** `installer.py` handles all. Dangerous skills are DISABLED (reversible rename to `_name`), not deleted. Uninstall only if user explicitly requests.
3. **Install scope: personal only.** Always `~/.claude/skills/` — never project-level `.claude/skills/`.
4. **Trust tiers.** Verified → Community → Raw. Raw GitHub results score 0.4 for trust.
5. **SHA tracking.** `git_tree_sha` stored in registry at hunt time. Mismatch = tamper flag.
6. **Rollback.** Pre-audit/update snapshot always written. `rollback.py` restores registry. `installer.py rollback_to_sha` restores actual skill files.
7. **Sandbox mode.** Subprocess (default) masks env vars + temp cwd. Docker is v0.3.0 opt-in.
8. **YAGNI multiplier.** Active domain = 2.0x. Recent = 1.0x. Dormant = 0.5x.
9. **Score weights.** stack=0.30, domain=0.20, stars=0.15, recency=0.15, trust=0.20.
10. **Loop guard.** Max 1 automatic hunt per session (`AGENT_HUNTER_RAN` session flag in SKILL.md).

---

## What to implement next (v0.1.0 sprint)

### Task 1: Complete `hunter.py` pre-filter (most critical)

`_passes_prefilter()` needs to fetch repo metadata from GitHub API and check:
- `stars >= config.min_stars` (default: 10)
- `last_commit_date > (today - config.max_age_days)` (default: 180 days)
- Tech keyword present in SKILL.md body (fetch raw content and check)
- Repo has code files (check `language` from GitHub repo object)

The GitHub Search API returns repo metadata in the `repository` object.
Also add `_fetch_skill_content(html_url)` to fetch raw SKILL.md content:
- Convert `github.com/owner/repo/blob/main/SKILL.md` → `raw.githubusercontent.com/owner/repo/main/SKILL.md`
- Store in `HuntResult.raw_content` — consumed by `security_scan.py` and `skill_parser.py`

Note: `hunter.py` has already been partially updated (pagination added). Check current state before editing.

### Task 2: Create `scripts/main.py`

The CLI entry point. Orchestrates the full scan → confirm → act pipeline.

```python
# Usage:
# python scripts/main.py scan [project_root]    ← full flow: hunt + scan + score + report + confirm + act
# python scripts/main.py audit
# python scripts/main.py rollback [--backup <file>]
# python scripts/main.py context [project_root]
# python scripts/main.py scaffold <name>
# python scripts/main.py install <owner> <repo>
# python scripts/main.py remove <skill_name>
# python scripts/main.py enable <skill_name>
```

The `scan` command flow:
1. `context_extractor.extract_context(root)` → ContextProfile
2. `Hunter().hunt(profile)` → list[HuntResult]
3. For each result: `security_scan.scan_skill(result.raw_content)` → ScanResult
4. `scorer.score_results(results, profile)` → list[ScoredResult]
5. `reporter.render_hunt_report(scored, scan_results)` → terminal output + markdown file
6. `installer.build_action_list(top_results, scan_results, installed, dangerous)` → list[PendingAction]
7. Print action summary (Steps 7–8 in SKILL.md)
8. Wait for user input (`input("Proceed? [y/N]: ")`)
9. If yes: `Installer().execute_actions(actions)` → list[ActionResult]

### Task 3: Add test for `installer.py`

Create `tests/test_installer.py`. Test:
- `install()` with `dry_run=True` returns success without touching filesystem
- `uninstall()` removes the directory
- `disable()` renames `skill-name` → `_skill-name`
- `enable()` renames back
- `build_action_list()` excludes RED results, excludes already-installed

---

## GitHub API notes

- Base URL: `https://api.github.com`
- Search endpoint: `GET /search/code?q=<query>&per_page=30`
- Repo metadata: `GET /repos/{owner}/{repo}`
- Raw content: `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/SKILL.md`
- Auth header: `Authorization: Bearer <GITHUB_TOKEN>`
- Rate limit: 60/hr unauthenticated, 5000/hr authenticated
- On 429: exponential backoff (1s, 2s, 4s). After 3 retries → fail with message.
- Response: `{"items": [{"repository": {"stargazers_count": N, ...}, "html_url": "...", ...}]}`

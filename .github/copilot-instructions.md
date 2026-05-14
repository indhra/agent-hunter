# agent-hunter - Copilot Instructions

You are helping implement **agent-hunter**: a proactive, security-vetted SKILL.md and MCP server discovery system packaged as a Claude-native skill. It reads a developer's project context, hunts GitHub for relevant skills, security-scans every result, and surfaces ranked recommendations. Think of it as the immune system of an AI agentic team.

**Full spec:** See `SPEC.md` and `ROADMAP.md` in the repo root.

---

## Architecture (read this before touching any file)

The design has a hard constraint: **Python scripts do I/O only. No LLM calls from scripts.** All reasoning happens in `SKILL.md` (the host agent's instructions).

```
SKILL.md (Claude's brain)
 │
 ▼
bin/ (bash wrappers - Claude calls these directly, gstack model)
 hunt → full pipeline wrapper
 github-search → pure curl GitHub Code Search (no Python)
 context-extract → wraps context_extractor.py
 security-scan → wraps security_scan.py
 audit → wraps audit.py
 rollback → wraps rollback.py
 scaffold → wraps scaffold.py
 installer → wraps installer.py
 registry → wraps registry.py
 resolve-deps → wraps skill_parser.py --resolve-deps
 │
 ▼
scripts/ (I/O workers - Python, no LLM)
 context_extractor.py → reads project files, extracts ONLY tech keywords
 hunter.py → queries GitHub API for SKILL.md + MCP configs
 skill_parser.py → parses YAML frontmatter from SKILL.md files
 security_scan.py → static + runtime security analysis
 scorer.py → 4-signal relevance scoring + trust tiers
 registry.py → local registry (~/.agent-hunter/registry.json)
 reporter.py → terminal + markdown report output
 audit.py → health check for installed skills
 rollback.py → restore registry to last known good state
 sandbox.py → subprocess/docker isolation for suspicious skills
 scaffold.py → generate SKILL.md stubs for new skills
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
- `skill_parser.py` - complete
- `context_extractor.py` - complete
- `security_scan.py` - complete (10+ patterns, obfuscation detection, sandbox integration)
- `scorer.py` - complete (install_log feedback loop, dormant detection)
- `registry.py` - complete (SHA tracking, snapshot/restore)
- `reporter.py` - complete (terminal rich table + markdown save)
- `rollback.py` - complete
- `sandbox.py` - complete (subprocess mode default; Docker opt-in when available)
- `scaffold.py` - complete
- `dep_resolver.py` - complete (v0.7.0 dependency conflict detection)
- `mcp_parser.py` - complete (v0.5.0 MCP config parsing)
- `typo_detect.py` - complete (v0.8.0 typo-squat detection)
- `verify_sig.py` - complete (v0.8.0 cryptographic signature verification)
- `update.py` - complete (v0.5.0 skill update command)
- `release.py` - complete (v0.5.0 release helper)
- **`scripts/main.py`** - the CLI entry point that wires all scripts together
- **`bin/`** - all 11 bash wrappers complete (gstack model; Claude calls these directly)
 - `bin/github-search` is pure bash/curl - no Python dependency

---

## Coding Standards

- **Python 3.10+** - use `match/case` only if it adds real clarity
- **Type hints required** on all public functions and method signatures
- **Docstrings required** (Google style) on all modules and public functions
- **No bare `except:`** - catch specific exceptions, log them, handle gracefully
- **Fail loudly, never silently** - partial results are worse than a clear error message
- **Linter:** `ruff` - run `ruff check .` before committing
- **Tests:** `pytest tests/` - add tests for any new behavior, not just happy paths

---

## Privacy constraint (non-negotiable - enforce in all context-reading code)

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

All 854 tests must pass before any commit.

---

## Key decisions already made (don't relitigate these)

1. **Scan → confirm → act flow.** After showing the hunt report, agent-hunter builds an action list (installs + disables) and asks the user ONCE to confirm. Then executes. See SKILL.md Steps 7–8.
2. **Actions: install, disable, rollback.** `installer.py` handles all. Dangerous skills are DISABLED (reversible rename to `_name`), not deleted. Uninstall only if user explicitly requests.
3. **Install scope: personal only.** Always `~/.claude/skills/` - never project-level `.claude/skills/`.
4. **Trust tiers.** Verified → Community → Raw. Raw GitHub results score 0.4 for trust.
5. **SHA tracking.** `git_tree_sha` stored in registry at hunt time. Mismatch = tamper flag.
6. **Rollback.** Pre-audit/update snapshot always written. `rollback.py` restores registry. `installer.py rollback_to_sha` restores actual skill files.
7. **Sandbox mode.** Subprocess (default) masks env vars + temp cwd. Docker is v0.3.0 opt-in.
8. **YAGNI multiplier.** Active domain = 2.0x. Recent = 1.0x. Dormant = 0.5x.
9. **Score weights.** stack=0.30, domain=0.20, stars=0.15, recency=0.15, trust=0.20.
10. **Loop guard.** Max 1 automatic hunt per session (`AGENT_HUNTER_RAN` session flag in SKILL.md).

---

## What to implement next (v1.0.0-alpha / Real World QA)

Code is at v1.0.0-alpha. The core product refocus is shipped; now validate the real-world UX and close launch-proof gaps before calling it stable.
Before writing new features, your main assignment is:
1. Try using the tool exactly as a user would (type `/agent-hunter` in Claude Code).
2. Identify bugs or friction in the end-to-end user flow.
3. Note: `GITHUB_TOKEN` is now optional. Curated index (`references/VERIFIED_SKILLS.md`) returns results without any token. Token enables broader GitHub discovery.

Do not start post-v1.0.0 feature work until the v1.0.0-alpha UX is verified on real repos.

## GitHub API notes

- Base URL: `https://api.github.com`
- Search endpoint: `GET /search/code?q=<query>&per_page=30`
- Repo metadata: `GET /repos/{owner}/{repo}`
- Raw content: `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/SKILL.md`
- Auth header: `Authorization: Bearer <GITHUB_TOKEN>`
- Rate limit: **authentication required** - GitHub Code Search requires a token since Feb 2024; unauthenticated requests return 401
- `hunter.py` probes `/rate_limit` first (`_check_auth()`) and surfaces a clear error with token URL on 401
- On 429: exponential backoff (1s, 2s, 4s). After 3 retries → fail with message.
- Response: `{"items": [{"repository": {"stargazers_count": N, ...}, "html_url": "...", ...}]}`

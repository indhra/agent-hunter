# agent-hunter

**Author:** Indhra Kiranu N A

>

This is the repo root for `agent-hunter` - a Claude-native SKILL.md and MCP server discovery tool. It reads your project context, hunts GitHub for relevant skills, security-scans every result, and surfaces ranked recommendations.

**Do not reinvent what's here.** Read `.github/copilot-instructions.md` for full context before editing any script.

---

## Stack

- Python 3.10+
- `PyYAML`, `requests`, `rich` (see `requirements.txt`)
- `pytest` for testing

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (must pass before any commit)
pytest tests/ -v

# Lint
ruff check .

# Full hunt via bin wrapper (preferred)
bin/hunt .

# Or via main.py directly
python scripts/main.py hunt .

# Security scan a specific skill
bin/security-scan path/to/SKILL.md

# Extract context from current project
bin/context-extract .

# Raw GitHub search (pure bash/curl, no Python)
bin/github-search "filename:SKILL.md fastapi"
```

## Key files

| File | What it is |
|---|---|
| `SKILL.md` | The brain - Claude's step-by-step instructions; calls `bin/` scripts |
| `bin/` | Bash wrappers Claude runs directly (gstack model) |
| `bin/github-search` | Pure curl GitHub Code Search - no Python needed |
| `SPEC.md` | Full technical specification (16 sections + robustness additions) |
| `ROADMAP.md` | Versioned roadmap v0.4.0 → v1.0.0 with release gates |
| `scripts/hunter.py` | GitHub API search - completed |
| `scripts/main.py` | CLI entry point - completed |
| `config/defaults.json` | All configurable parameters with comments |

## Hard rules

1. **No LLM API calls from scripts.** Scripts do I/O only. Reasoning lives in SKILL.md.
2. **No auto-install.** Show the install command. User runs it.
3. **Privacy:** `context_extractor.py` may only extract tech keywords from `TECH_ALLOWLIST`. Nothing else.
4. **Security:** RED scan results are never shown. Count only.
5. **Fail loudly.** Partial results are worse than clear error messages.

## Current state

Implemented and tested: all core scripts including `hunter`, `main`, `skill_parser`, `context_extractor`, `security_scan`, `scorer`, `registry`, `reporter`, `rollback`, `sandbox`, `scaffold`, `dep_resolver`, `mcp_parser`, `typo_detect`, `verify_sig`, `update`, `release`.

Code is at v1.0.0-alpha. The repo has been refocused around the top-3 recommendation workflow, and the current branch is green with 634 tests passing. Main priority is real-world validation and launch-proof polishing, not new feature breadth.

See `.github/copilot-instructions.md` for the exact tasks.

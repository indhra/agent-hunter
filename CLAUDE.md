# agent-hunter

**Author:** Indhra Kiranu N A

> Hunt the right skills. Block the bad ones.

This is the repo root for `agent-hunter` — a Claude-native SKILL.md and MCP server discovery tool. It reads your project context, hunts GitHub for relevant skills, security-scans every result, and surfaces ranked recommendations.

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

# Run a hunt (once main.py exists)
python scripts/main.py hunt .

# Run security scan on a specific skill
python scripts/security_scan.py path/to/SKILL.md

# Extract context from current project
python scripts/context_extractor.py .
```

## Key files

| File | What it is |
|---|---|
| `SKILL.md` | The brain — Claude's step-by-step instructions for the hunt pipeline |
| `SPEC.md` | Full technical specification (16 sections + robustness additions) |
| `ROADMAP.md` | Versioned roadmap v0.1.0 → v1.0.0 with release gates |
| `scripts/hunter.py` | GitHub API search — the main gap to implement for v0.1.0 |
| `scripts/main.py` | CLI entry point — needs to be created for v0.1.0 |
| `config/defaults.json` | All configurable parameters with comments |

## Hard rules

1. **No LLM API calls from scripts.** Scripts do I/O only. Reasoning lives in SKILL.md.
2. **No auto-install.** Show the install command. User runs it.
3. **Privacy:** `context_extractor.py` may only extract tech keywords from `TECH_ALLOWLIST`. Nothing else.
4. **Security:** RED scan results are never shown. Count only.
5. **Fail loudly.** Partial results are worse than clear error messages.

## Current state (v0.1.0 in progress)

Implemented and tested: `skill_parser`, `context_extractor`, `security_scan`, `scorer`, `registry`, `reporter`, `rollback`, `sandbox`, `scaffold`.

**Needs work:** `hunter.py` pre-filter completion + raw content fetch. **Needs creation:** `scripts/main.py` CLI entry point.

See `.github/copilot-instructions.md` for the exact tasks.

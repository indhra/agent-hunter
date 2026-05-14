# Changelog

All notable changes to agent-hunter are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- No unreleased changes yet.

## [0.1.0] - 2026-05-14

Initial beta release.

### Changed
- Repositioned agent-hunter as a repo-aware skill package manager focused on the default `hunt` workflow.
- Simplified the product surface around the top 3 recommendations with sharper why-this-fits messaging.
- Tightened first-run docs and setup messaging around global `~/.claude/CLAUDE.md` activation.

### Fixed
- Aligned repo-facing version/status messaging on `v1.0.0-alpha` across docs, packaging metadata, and release notes.

## [0.8.0] - 2026-05-09

### Added
- **Cryptographic signature verification** (`verify_sig.py`) - verified skills in `references/VERIFIED_SKILLS.md` now carry maintainer-signed entries. Tampered or unsigned entries are flagged at hunt time. Sign new entries with `verify_sig.sign_skill_entry()`.
- **Typo-squat detection** (`typo_detect.py`) - catches look-alike skill names (e.g., `trusty` vs `trustyy`). Levenshtein + phonetic fingerprint checks against the verified index. Flagged results are shown as [BLOCKED] with the legitimate skill name surfaced alongside.
- **Author trust pipeline** - `hunter.py` now checks contributor history for sudden ownership changes. New maintainer with < 30-day account age on a high-star repo → [REVIEW] warning in the hunt report.
- All three v0.8.0 features wired into the full hunt pipeline in `main.py`.

### Changed
- `security_scan.py` weight adjustments to account for new trust signals.
- `config/defaults.json`: added `typo_threshold`, `author_trust_min_age_days` parameters.

---

## [0.7.0] - 2026-05-07

### Added
- **Dependency conflict manager** (`dep_resolver.py`) - detects Python/Node version conflicts between installed skills before confirming installs. Reports `pydantic<2 vs pydantic>=2` style conflicts. Does not auto-resolve; surfaces the conflict and lets you decide.
- `--yes` flag on `bin/hunt` - skips the confirm prompt (useful for CI or non-TTY contexts).
- `--print-actions` flag - prints the install/disable action list without executing, so you can review what agent-hunter would do.

---

## [0.6.0] - 2026-05-05

### Added
- **Obfuscation detection** in `security_scan.py` - catches base64-encoded shell payloads, eval(compile(...)) chains, and rotated string literals that bypass simple pattern matching.
- **Docker sandbox** in `sandbox.py` - if Docker is available, suspicious skills run in a disposable `python:3.12-slim` container with no network and a 5-second timeout. Subprocess mode remains the default.
- Sandbox integrated into the security scan pipeline - high-suspicion skills are automatically sandboxed during the scan phase, not just on explicit user request.

### Changed
- `sandbox.py` now detects Docker availability at runtime and falls back to subprocess mode gracefully.

---

## [0.5.0] - 2026-05-04

### Added
- **npm registry MCP search** in `hunter.py` - hunts `npmjs.org` for `@mcp/*` packages alongside GitHub. MCP results appear in a dedicated section of the hunt report.
- **Verified skills seed** (`references/VERIFIED_SKILLS.md`) - 12 reviewed gstack skills pre-loaded in the curated index. Hunt returns these results with zero network calls and zero token required.
- **`scripts/mcp_parser.py`** - parses `mcp.json` config files to extract transport type, declared permissions, and install commands.
- **`scripts/release.py`** - release helper for version tagging, CHANGELOG extraction, and GitHub Release creation.
- **`scripts/update.py`** - skill update command: shows diff per skill, user confirms each update. Never auto-installs.
- Global `~/.claude/CLAUDE.md` injection in `./setup` - agent-hunter's routing triggers are added to the user's global Claude instructions so Claude invokes `/agent-hunter` proactively without per-project setup.
- Proactive routing triggers added to per-project CLAUDE.md blocks injected by `./setup`.

### Changed
- `hunter.py`: curated index queried first (before GitHub API). Returns curated results with no token needed. GitHub search is additive.

---

## [0.4.0] - 2026-05-03

### Added
- Core hunt pipeline (`context_extractor.py`, `hunter.py`, `skill_parser.py`)
- 4-signal relevance scoring with YAGNI multiplier (`scorer.py`)
- Static security scan: prompt injection, shell exec, Unicode, secrets (`security_scan.py`)
- Hunt report: rich terminal output + markdown file (`reporter.py`)
- Registry read/write (`registry.py`)
- SKILL.md brain with session loop guard
- Pre-filter pipeline (10+ stars, 180-day recency, code files, tech name present)
- **gstack-style `bin/` scripts** - Claude calls bash wrappers instead of Python directly:
 `hunt`, `github-search` (pure curl), `context-extract`, `security-scan`,
 `audit`, `rollback`, `scaffold`, `installer`, `registry`, `resolve-deps`
- **PATH setup** - `./setup` now symlinks `~/.local/bin/agent-hunter` so the command
 is available globally after adding `~/.local/bin` to `$PATH`

### Changed
- SKILL.md rewritten to call `~/.claude/skills/agent-hunter/bin/` scripts (gstack model)
 instead of `python scripts/...py` directly
- `hunter.py` - added `_check_auth()` probe before firing any queries; on 401 prints
 a clear error with token URL instead of 12 individual error lines; removed misleading
 "60 req/hr unauthenticated" message (GitHub Code Search requires auth since 2024)
- `setup` - fixed rate-limit footer message to reflect auth requirement

---

<!--
██████████████████████████████████████████████
 CHANGELOG ENTRIES WILL BE ADDED HERE
 as each version ships.
 Format:

## [0.1.0] - YYYY-MM-DD

### Added
- ...

### Fixed
- ...

### Changed
- ...

### Security
- ...
██████████████████████████████████████████████
-->

[Unreleased]: https://github.com/indhra/agent-hunter/compare/v1.0.0-alpha...HEAD
[1.0.0-alpha]: https://github.com/indhra/agent-hunter/compare/v0.8.0...v1.0.0-alpha
[0.8.0]: https://github.com/indhra/agent-hunter/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/indhra/agent-hunter/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/indhra/agent-hunter/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/indhra/agent-hunter/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/indhra/agent-hunter/compare/v0.3.1...v0.4.0

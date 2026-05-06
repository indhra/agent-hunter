# Changelog

All notable changes to agent-hunter are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Core hunt pipeline (`context_extractor.py`, `hunter.py`, `skill_parser.py`)
- 4-signal relevance scoring with YAGNI multiplier (`scorer.py`)
- Static security scan: prompt injection, shell exec, Unicode, secrets (`security_scan.py`)
- Hunt report: rich terminal output + markdown file (`reporter.py`)
- Registry read/write (`registry.py`)
- SKILL.md brain with session loop guard
- Pre-filter pipeline (10+ stars, 180-day recency, code files, tech name present)
- **gstack-style `bin/` scripts** — Claude calls bash wrappers instead of Python directly:
  `hunt`, `github-search` (pure curl), `context-extract`, `security-scan`,
  `audit`, `rollback`, `scaffold`, `installer`, `registry`, `resolve-deps`
- **PATH setup** — `./setup` now symlinks `~/.local/bin/agent-hunter` so the command
  is available globally after adding `~/.local/bin` to `$PATH`

### Changed
- SKILL.md rewritten to call `~/.claude/skills/agent-hunter/bin/` scripts (gstack model)
  instead of `python scripts/...py` directly
- `hunter.py` — added `_check_auth()` probe before firing any queries; on 401 prints
  a clear error with token URL instead of 12 individual error lines; removed misleading
  "60 req/hr unauthenticated" message (GitHub Code Search requires auth since 2024)
- `setup` — fixed rate-limit footer message to reflect auth requirement

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

[Unreleased]: https://github.com/indhra/agent-hunter/compare/HEAD...HEAD

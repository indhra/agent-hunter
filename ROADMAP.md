# agent-hunter · Roadmap

**Version:** 1.0.0
**Last updated:** 2026-05-01
**Status:** Active development

This roadmap is versioned and intentional. Every release ships a working, useful tool — not a preview. Features are added when they've earned their place, proven by real usage.

---

## Versioning Convention

`MAJOR.MINOR.PATCH`

- **MAJOR** — breaking changes to SKILL.md interface, registry schema, or report format
- **MINOR** — new commands, new sources, new scan capabilities (backward-compatible)
- **PATCH** — bug fixes, score tuning, security rule updates, doc corrections

Versions below `v1.0.0` are pre-release. `v1.0.0` is the first production-stable release.

---

## Timeline Overview

```
v0.1.0    v0.1.1    v0.2.0    v0.2.1    v0.3.0    v0.3.1    v1.0.0
  │         │         │         │         │         │         │
Week 1    Week 2    Week 4    Week 6    Week 9    Week 11   Week 16
  │         │         │         │         │         │         │
Core      Score     MCP +     Trust     Conflict  Dep.      GA:
hunt      tuning    Audit +   tiers +   detect +  detect +  Benchmarked
Security  + fixes   SHA +     CVE       Sandbox   Scaffold  Demo ready
scan                Rollback  index     (Docker)  command   Production
```

---

## v0.1.0 · Alpha — Core Hunt + Security Scan

**Status:** 🔨 In development
**Target:** Week 1

This is the foundation. If it doesn't work here, nothing else matters.

### Ships

- **`SKILL.md`** — Brain of the system. Host agent instructions. Defines triggers, loop guard (`AGENT_HUNTER_RAN` session flag, max 1 auto-hunt per session), privacy contract, output format.
- **`context_extractor.py`** — Reads `CLAUDE.md`, `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `git log --oneline -50`. Extracts ONLY tech signal keywords from an explicit allowlist. No code, no paths, no names. Prints extracted signals to stdout so user can verify.
- **`hunter.py`** — GitHub Search API queries (`filename:SKILL.md <tech>`). Authenticated (5,000 req/hr with `GITHUB_TOKEN`) and unauthenticated (60 req/hr) paths both supported.
- **`skill_parser.py`** — YAML frontmatter extraction + body text. Handles missing fields, malformed YAML, and no-frontmatter files gracefully.
- **`security_scan.py`** — Static analysis: prompt injection patterns in description + body, unguarded `exec()` / `subprocess` / `os.system()`, hidden Unicode (U+202E direction override, zero-width chars, homoglyphs), embedded secrets (API keys, tokens). Integrates `pors/skill-audit` if installed.
- **`scorer.py`** — 4-signal relevance score: `(stack_match × 0.35 + domain_match × 0.25 + log_stars × 0.20 + recency_decay × 0.20) × yagni_multiplier`. YAGNI: active domain (7-day commits) = 2.0×, recent (30-day) = 1.0×, dormant (90+ days) = 0.5×.
- **`reporter.py`** — Terminal rich table with 🟢/🟡/🔴 signals + per-result "why this for you" explanation. Saves `~/.agent-hunter/reports/hunt_report_YYYY-MM-DD.md`.
- **`registry.py`** — Read/write `~/.agent-hunter/registry.json`. Snapshot/restore support. SHA storage at install time.
- **`installer.py`** — Executes all file-system actions on `~/.claude/skills/`. Four actions: `install` (via `gh skill install`, falls back to `git clone`), `disable` (rename to `_skill-name` — reversible), `enable` (undo disable), `uninstall` (permanent, only on explicit user request). All actions appended to `~/.agent-hunter/install_log.jsonl`. Never touches RED-flagged results.
- **`rollback.py`** — `agent-hunter rollback`: restores `~/.agent-hunter/registry.json` from the most recent pre-audit/pre-update snapshot. Instant, no network.
- **Pre-filter pipeline** — Applied before scoring. Rejects any result where: `stars < 10`, `last_commit > 180 days ago`, `no code files in repo`, `tech name not found in SKILL.md body`. Runs in parallel (thread pool) to avoid serial API bottleneck.
- **Scan → confirm → act flow** — After showing the hunt report, SKILL.md builds an action summary (INSTALL N skills + DISABLE M dangerous) and asks the user ONCE. On confirmation, `installer.py execute_actions()` runs all items, prints per-result status, and prints a final summary. No partial installs, no silent failures.
- **Hunt command** — `agent-hunter hunt` (also triggers automatically on session start if `AGENT_HUNTER_RAN` not set).
- **Rollback command** — `agent-hunter rollback` restores the registry to the last healthy state.

### Does NOT ship
- MCP server hunting
- Audit, update, scaffold commands
- SHA tamper detection (stored at install, compared in v0.2.0 audit)
- Trust tiers (assigned in hunt, enforced scoring weights from v0.2.1)
- Runtime sandbox (subprocess mode ships in v0.2.0)
- License compatibility check

### Release gate
- Tested manually on 3 real projects (FastAPI+Postgres, Node+React, Rust CLI)
- Top 5 results: ≥ 3 relevant per run
- Zero false-negatives on a 10-item known-malicious skill test set
- Sub-30s hunt time on cold GitHub API (unauthenticated)
- `AGENT_HUNTER_RAN` loop guard verified working

---

## v0.1.1 · Alpha — Score Tuning + Bug Fixes

**Status:** 📋 Planned
**Target:** Week 2

### Ships

- Score weight tuning based on v0.1.0 real-world results
- Fix any false-positive security scan issues surfaced in v0.1.0 testing
- Improve GitHub query construction (better tech-to-query mapping)
- Add `~/.claude/sessions/` transcript context reading (was deferred from v0.1.0)
- Improve `reporter.py` formatting edge cases (long names, missing fields)
- README: add real Quick Start walkthrough after first successful hunt

### Release gate
- At least 5 real-project test runs with score tuning applied
- False-positive rate on security scan ≤ 20% (will tighten in v0.3.x)

---

## v0.2.0 · Beta — MCP Hunting + Audit + Rollback + Sandbox (Basic)

**Status:** 📋 Planned
**Target:** Week 4

This is where agent-hunter becomes a real safety net, not just a search tool.

### Ships

**MCP server hunting**
- `hunter.py` extended: queries `filename:mcp.json <tech>`, `filename:server.py "mcp"`, `topic:mcp-server <tech>`
- Hunt report updated: Skills section + MCP Servers section, clearly separated
- MCP results include: transport type (stdio/SSE), declared permissions, install command

**Audit command**
- `audit.py` — `agent-hunter audit`: reads installed skills from registry, for each:
  - Checks for version updates (compares stored `git_tree_sha` vs. current remote SHA)
  - Re-runs security scan
  - Detects trigger conflicts (cosine similarity ≥ 0.8 on trigger description strings)
  - Checks license compatibility vs. user project LICENSE
  - Outputs health table: 🟢 Healthy / 🟡 Update available / 🔴 Security issue / ⚠️ Conflict
- Completes in ≤ 60s for 20 installed skills

**SHA tracking and tamper detection**
- `registry.py` updated: stores `git_tree_sha` at hunt time
- On audit: if stored SHA ≠ current remote SHA → 🔴 flag with explanation and rollback prompt
- SHA sourced via GitHub Trees API, not just commit SHA (content-addressed)

**Rollback command**
- `rollback.py` — `agent-hunter rollback`: restores `~/.agent-hunter/registry.json` to the last known healthy snapshot
- Before every audit or update, agent-hunter writes a timestamped snapshot to `~/.agent-hunter/backups/`
- Rollback is instant (file restore), no network needed
- User sees: which version they're rolling back to, what changed, confirmation prompt

**Basic sandbox isolation**
- `sandbox.py` — wraps execution of any skill script in a subprocess with:
  - Masked environment variables (`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, etc. replaced with `***`)
  - Restricted working directory (temp dir, not project root)
  - No network access flag (where OS supports it)
- Applied during security scan: high-suspicion skills are executed in sandbox to observe behavior
- Not a full runtime jail yet — Docker option comes in v0.3.0

**Update command**
- `agent-hunter update`: shows delta (what changed) per skill, user confirms each one
- Never auto-installs. Human always in the loop.

**Context command**
- `agent-hunter context`: prints the full `ContextProfile` extracted from current project so user can verify what agent-hunter knows about their stack

### Release gate
- Audit correctly flags a manually tampered skill (SHA mismatch integration test)
- Rollback restores registry to pre-tamper state in < 2s
- MCP results appear correctly in hunt report
- Sandbox successfully masks env vars (verified by test that attempts to read `GITHUB_TOKEN`)

---

## v0.2.1 · Beta — Trust Tiers + CVE Index Integration

**Status:** 📋 Planned
**Target:** Week 6

Raw GitHub search is the weakest link — easily SEO-poisoned, typo-squatted, or flooded with low-quality results. This release adds the trust layer that makes the hunt results genuinely reliable.

### Ships

**Trust tier system**
- Three source tiers, consulted in order:
  1. **Verified** — `references/VERIFIED_SKILLS.md` (manually curated, cryptographically signed entries). Score bonus: `+0.25` to final score.
  2. **Community-reviewed** — submissions via PR that passed peer review. Score bonus: `+0.10`.
  3. **Raw GitHub** — unvetted GitHub Search API results. No bonus. Higher suspicion threshold in security scan.
- Hunt report shows trust tier per result: `[VERIFIED]`, `[COMMUNITY]`, `[RAW]`
- Users can configure minimum tier in `config.json`: `"min_trust_tier": "community"` blocks raw results entirely

**Verified index format**
- `references/VERIFIED_SKILLS.md` extended with structured entries: name, GitHub URL, version, SHA, license, trust_level, reviewer, review_date
- Index is updated via PR with reviewer sign-off (see CONTRIBUTING.md)

**CVE-style index integration**
- `security_scan.py` extended: cross-reference result repos against known-malicious list (format: `{repo_url, cve_id, description, severity}`)
- Community-maintained `references/KNOWN_MALICIOUS.md` (seeded with cases from Snyk ToxicSkills report)
- Any hit → immediate 🔴 exclusion, listed in report footer as "blocked by known-malicious index"

**Score formula updated**
- `total_score = (stack_score × 0.30 + domain_score × 0.20 + star_score × 0.15 + recency_score × 0.15 + trust_score × 0.20) × yagni_multiplier`
- Trust tier weights: Verified = 1.0, Community = 0.7, Raw = 0.4

### Release gate
- Trust tier correctly applied to a set of 20 test skills (10 verified, 5 community, 5 raw)
- Known-malicious index blocks test entries from appearing in results
- Score ordering matches expected output for trust-tier-mixed fixture set

---

## v0.3.0 · Beta — Conflict Detection + Dependency Awareness + Docker Sandbox

**Status:** 📋 Planned
**Target:** Week 9

### Ships

**Trigger conflict detection**
- `audit.py` extended: cosine similarity on all installed skill trigger descriptions
- Threshold 0.8 → conflict flagged: "skill-A and skill-B may both respond to 'deploy'. Consider consolidating."
- Report shows conflicting pair + suggested resolution action

**Dependency awareness**
- `registry.py` extended: reads declared dependencies from skill's requirements (if any skill ships a `requirements.txt`)
- Conflict detection: if Skill A requires `pydantic<2.0` and Skill B requires `pydantic>=2.0` → ⚠️ flag, user is told to resolve manually
- Does NOT auto-resolve. Containerization (true isolation) is a v2.0.0 concern.
- Report section: "Dependency notes" listing potential conflicts

**Docker sandbox option (v0.3.0)**
- `sandbox.py` upgraded: if Docker is installed, runs skill scripts inside a disposable container (`python:3.12-slim` base)
- Container: no network, no volume mounts, 5s execution timeout, killed after test
- User opt-in via config: `"sandbox_mode": "docker"` (default: `"subprocess"`)
- Subprocess mode (v0.2.0) remains default for environments without Docker

**Scaffold command**
- `scaffold.py` — `agent-hunter scaffold <name>`: generates a SKILL.md stub pre-populated with user's detected tech stack signals
- Uses `assets/skill_stub_template.md` as base, fills in detected `tech_stack` and `domain_tags`
- Triggered automatically when hunt returns 0 results ("nothing found — scaffolding a stub for you to build")

**Phase-aware configuration**
- `config.json` supports `"phase": "seed" | "growth" | "scale"`
- `seed`: `min_stars=5`, `max_age_days=365`, aggressive hunt (more results, lower bar)
- `growth`: `min_stars=10`, `max_age_days=180` (current default)
- `scale`: `min_stars=50`, `max_age_days=90`, conservative (only proven, recent, popular)

**License compatibility check**
- `security_scan.py` extended: parse skill's frontmatter `license` field
- Cross-check against user's project `LICENSE` file
- GPL-3.0 skill + MIT project → 🟡 flag with explanation
- AGPL skill in any commercial context → 🔴 flag

### Release gate
- Conflict detection tested with intentionally overlapping trigger fixture set
- Dependency conflict flagged correctly for pydantic version conflict fixture
- Docker sandbox: verified env vars masked, network blocked, execution timeout works
- Scaffold generates valid, parseable SKILL.md on first run

---

## v0.3.1 · Beta — Polish + False Positive Reduction

**Status:** 📋 Planned
**Target:** Week 11

### Ships

- Security scan false-positive rate reduced to ≤ 10% (tuning based on v0.3.0 community data)
- Improved trust tier scoring weights (based on real-world precision data)
- Session transcript context mining improved: better topic extraction
- `reporter.py`: improved markdown report formatting for longer skill lists
- `audit.py`: performance — audit of 50 skills in ≤ 90s
- Bug fixes from community issues filed against v0.3.0

---

## v0.4.0 · Beta — Compound Loop Completion (Feedback + Contribution)

**Status:** 📋 Planned
**Target:** Week 13

This version closes the two open links in the compound learning loop. Without these, the scorer is static — it ranks by stars and recency forever. With them, it gets smarter from actual usage.

### Gap 3 — install_log → scorer feedback

**Problem:** `install_log.jsonl` records every install/disable/uninstall action but nothing reads it back. The scorer has no knowledge of "you installed this skill 3 weeks ago and it was never triggered." The dormant signal exists in the YAGNI multiplier design but is driven by git commit recency — not actual usage history.

**Ships:**
- `scorer.py` extended: reads `~/.agent-hunter/install_log.jsonl` at score time to detect dormant installed skills
  - Installed > 30 days ago + 0 `context_extractor` session matches → apply `dormant` YAGNI multiplier (0.5×) to re-hunt score
  - Installed + actively invoked (matched in `~/.claude/sessions/` transcripts in last 30 days) → boost trust signal (1.1× cap)
- `context_extractor.py` session transcript mining wired into the scorer (was deferred since v0.1.0)
  - Reads `~/.claude/sessions/*.jsonl` for skill name mentions
  - Output: `{"skill_name": str, "last_seen": date, "mention_count": int}` → consumed by scorer
- Registry gains an `install_log_summary()` helper: returns per-skill `{installed_at, last_triggered, trigger_count}` for scorer consumption
- `audit.py` uses the same signal to surface "installed but never triggered" in the audit report

**Release gate:**
- Scorer correctly applies 0.5× to a skill installed 31+ days ago with 0 session mentions
- Scorer correctly boosts a skill with 5+ session mentions in last 30 days
- `audit.py` lists dormant skills (installed >30d, 0 triggers) as a distinct category

---

### Gap 4 — `agent-hunter contribute` command

**Problem:** `scaffold.py` tells users to "open a PR manually." The loop from consumer → contributor is fully open. A user who builds something useful has no path back to the verified index without leaving the tool.

**Ships:**
- `scripts/main.py` gains a `contribute` subcommand: `agent-hunter contribute <skill-name>`
  - Validates the named skill is installed in `~/.claude/skills/`
  - Runs `security_scan.py` on it — blocks contribution if RED result
  - Runs `skill_parser.py` — validates YAML frontmatter is complete (name, version, trigger, domain_tags required)
  - Opens a pre-filled GitHub issue on `indhra/agent-hunter` via `gh issue create` with:
    - Skill name, repo URL, stars, trust tier, security scan result summary
    - Templated body from `assets/contribute_template.md`
  - Falls back to printing the filled template to stdout if `gh` is not installed
- `assets/contribute_template.md` — contribution issue template (skill metadata + self-certification checklist)
- `references/VERIFIED_SKILLS.md` documents the manual review process for maintainers

**Release gate:**
- `contribute` command validates frontmatter and rejects incomplete skills with clear error
- Contribute blocked on RED scan result (test with `tests/fixtures/malicious_skill.md`)
- `gh` fallback: template printed to stdout with correct content when `gh` is not available
- End-to-end: install a scaffolded skill → `contribute` → issue body is correct

---

## v1.0.0 · General Availability — Benchmarked and Production-Ready

**Status:** 📋 Planned
**Target:** Week 16

This is the release that earns the 1.0.0 label. Not a feature dump — a quality gate.

### Ships

- Full test suite: precision/recall benchmarks across 10 real projects (results published in BENCHMARKS.md)
- `references/VERIFIED_SKILLS.md` — 25+ manually verified entries
- `references/SECURITY_PATTERNS.md` — 15+ contributed detection rules, all tested
- `references/KNOWN_MALICIOUS.md` — seeded from Snyk ToxicSkills + community contributions
- `cisco-ai-defense/skill-scanner` as optional secondary scan backend (user opt-in)
- GitHub Actions CI: lints, all tests, security pattern validation, fixture-based scan regression
- All script modules: full docstrings, type hints, error handling per SPEC error table
- SPEC.md finalized, API docs published for all script modules
- demo GIF recorded and in `assets/demo.gif`

### v1.0.0 Benchmark Targets (hard gates — release blocked if not met)

| Metric | Target |
|---|---|
| Precision top-5 (avg across 10 projects) | ≥ 3.5 / 5 |
| False-negative rate (known malicious set) | 0% |
| False-positive rate (security scan) | ≤ 10% |
| Hunt time — authenticated | ≤ 25s |
| Hunt time — unauthenticated | ≤ 60s |
| Audit time — 20 skills | ≤ 45s |
| Rollback time | ≤ 2s |
| Docker sandbox test execution | ≤ 10s |

### ⚠️ User task: Record demo GIF (assign after v1.0.0 code freeze)
> Record a GIF < 45 seconds. No setup shown — just value.
> Tool: [vhs](https://github.com/charmbracelet/vhs) or [asciinema](https://asciinema.org/).
> Script: open FastAPI project → trigger hunt → 6 results with trust signals appear → one selected → install command shown.
> Replace `assets/demo-placeholder.png` with `assets/demo.gif` and update README.

---

## Anti-Features (Permanent Commitments)

These are not "not planned." They are **never.**

| Anti-feature | Why never |
|---|---|
| Auto-install without user confirmation | Trust and security. Human in the loop, always. |
| Telemetry or usage analytics | Privacy by design. Nothing leaves without user knowledge. |
| Paid tier or feature gating | MIT, open source, forever. |
| LLM API calls from Python scripts | Host agent does all reasoning. Scripts do I/O only. |
| Sponsored or boosted results | Not a marketplace. Not ad-driven. |
| Installing RED-flagged skills | Non-negotiable. RED = excluded. Count reported only. |
| Silently hiding partial results | Fail loudly. Partial is worse than nothing. |

---

## Issue Labels

| Label | Meaning |
|---|---|
| `v0.1.0` | Milestone target |
| `security-pattern` | New detection rule for scanner |
| `hunt-source` | New skill/MCP registry source |
| `benchmark` | Precision/recall test data submission |
| `verified-skill` | Candidate for VERIFIED_SKILLS.md |
| `trust-tier` | Trust system improvements |
| `breaking` | Impacts SKILL.md interface or registry schema |
| `good-first-issue` | Accessible for new contributors |

---

*This roadmap is a commitment, not a wish list. Milestone dates move only when blockers are real and documented.*

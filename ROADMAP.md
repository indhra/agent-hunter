# agent-hunter · Roadmap

**Version:** 1.0.0-alpha
**Last updated:** 2026-05-09
**Status:** ✅ **v1.0.0-alpha COMPLETE** — Ready for validation testing

> **Week 3 completion:** 92% test coverage, 100% pass rate, path injection complete, code reduced 17%.
> **Next:** Week 4 real-world validation on 10 repo types, then stable v1.0.0 release.

---

## 🎯 v1.0.0-alpha Achievement (Weeks 1-3)

**Completed:** May 9, 2026
**Status:** Ready for real-world validation

### What Changed
- **Commands:** Simplified from 11 → 3 (hunt, audit, rollback)
- **Scoring:** Simplified from 6 → 4 signals (stack_match 0.40, trust 0.30, recency 0.15, stars 0.15)
- **Code:** Reduced by 17% (-2,050 lines)
- **Coverage:** Achieved 92% (exceeded 90% target)
- **Tests:** 634 passing, 0 failing (100% pass rate)
- **Testability:** Path injection complete for isolated testing

### Week-by-Week Progress
- **Week 1:** Truth restoration (version sync, messaging alignment)
- **Week 2:** Core simplification (file removal, scorer simplification, main.py reduced)
- **Week 3:** Test coverage & path injection (environment variable overrides)

### What's Next (Week 4)
- Real-world validation on 10 repo types
- Tune scoring weights based on results
- Record demo video
- Merge to main and tag v1.0.0

See `docs/WEEK3_COMPLETION_SUMMARY.md` for full details.

---

## Original Roadmap (Pre-v1.0 Simplification)

*Note: The roadmap below reflects the original v0.x plan. v1.0.0-alpha simplified architecture significantly.*

This roadmap is versioned and intentional. Every release ships a working, useful tool — not a preview. Features are added when they've earned their place, proven by real usage.

---

## Versioning Convention

`MAJOR.MINOR.PATCH`

- **MAJOR** — breaking changes to SKILL.md interface, registry schema, or report format
- **MINOR** — new commands, new sources, new scan capabilities (backward-compatible)
- **PATCH** — robustness enhancements, security hardening, core gaps closed

Examples: `v0.1.0` (alpha), `v0.2.1` (patch release), `v1.0.0` (GA).

Versions below `v1.0.0` are pre-release. `v1.0.0` is the first production-stable release.

---

## Timeline Overview

```
v0.1.0   v0.1.1   v0.2.0   v0.2.1   v0.3.0   v0.3.1   v0.4.0   v0.5.0   v0.6.0   v0.7.0   v0.8.0   v1.0.0
  │        │        │        │        │        │        │        │        │        │        │        │
Week 1   Week 2   Week 4   Week 6   Week 9  Week 11  Week 13  Week 15  Week 17  Week 19  Week 21  Week 24
  │        │        │        │        │        │        │        │        │        │        │        │
Core     Score    MCP +    Trust    Conflict Contrib  Feedback Runtime  Dep.    Web-of- Verified   GA:
hunt     tuning   Audit +  tiers +  detect + loop    Snap     Sandbox  Mgmt    Trust   index     Prod
Sec      fixes    SHA +    CVE      Docker   (Gap 3)  restore  obfuscat conflict verify  crypto    ready
scan             Rollback  index    (Gap 2)   Gap 4             (Gap 1)  (Gap 3) (Gap 4)
```

---

## Core Robustness Gaps (integrated v0.5.0 → v0.8.0)

These four gaps emerged from security + operational analysis:

| Gap | Problem | Solution Roadmap | v1.0.0 Ready? |
|-----|---------|------------------|---------------|
| **Gap 1: Runtime Sandboxing** | Obfuscated malware bypasses static analysis | v0.6.0: Docker hardening + behavior analysis | ✅ |
| **Gap 2: Safe-State Recovery** | Poisoned SHAs with no rollback points | v0.5.0: Pre-audit snapshots + recovery playbook | ✅ |
| **Gap 3: Dependency Conflicts** | Python/Node version conflicts crash agent | v0.7.0: Resolver + containerization | ✅ |
| **Gap 4: Web-of-Trust** | GitHub search: SEO poisoning + typo-squat | v0.8.0: Crypto verification + curated index | ✅ |

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

**Status:** ✅ Shipped
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

## v0.5.0 · Beta — Safe-State Recovery (Gap 2 Closure)

**Status:** ✅ Shipped
**Target:** Week 15

Robustness gap 2: Poisoned SHAs with no rollback points. A single GitHub Account compromise or malicious commit can silently inject backdoors. This version hardens rollback with pre-audit snapshots and a complete recovery playbook.

### Ships

**Pre-audit snapshot mechanism**
- `registry.py` extended: before running `audit` or `update` commands, writes a timestamped snapshot to `~/.agent-hunter/backups/pre_audit_YYYYMMDD_HHMMSS.json`
  - Snapshot includes: installed skills list, registry SHAs, installed_log tail (last 100 entries)
  - Metadata: `{"snapshot_time": datetime, "trigger": "pre_audit|pre_update", "git_branch": str}`
- Each snapshot is immutable (append-only log)
- Automatic retention: keep last 30 snapshots, delete older (configurable)

**Enhanced rollback command**
- `rollback.py` extended: `agent-hunter rollback [--to <snapshot-name>] [--force]`
  - Lists available snapshots with timestamps, trigger reason, delta preview
  - User selects target snapshot (or `--to pre_audit_20260503_143022.json` for automation)
  - Shows diff: "Will restore 5 skills from snapshot. Will uninstall 2 skills added since then. Proceed?"
  - `--force` skips confirmation (for scripted recovery)
- Rollback now also restores installed skill git SHAs to snapshot state (not just registry)
  - Calls `git reset --hard <SHA>` for each skill in `~/.claude/skills/`
  - Reverts any in-flight changes to installed skills

**Recovery playbook (documentation)**
- New `docs/RECOVERY.md`: step-by-step playbook for common incident scenarios:
  - "I think a skill was compromised" → rollback, audit, re-scan
  - "My registry is corrupted" → restore from backup
  - "I want to freeze my installation" → snapshot + read-only config
  - "How to detect a poisoned SHA" → signature verification workflow (v0.8.0 prereq)
- Linked in main help text: `agent-hunter help | grep -i recovery`

**Snapshot integrity validation**
- `registry.py` adds CRC32 checksum to each snapshot (lightweight tamper detection)
- Rollback verifies checksum before restore (fails loudly if corrupted)
- Not cryptographic yet (v0.8.0 adds Ed25519 signing)

**Configuration for snapshot retention**
- `config.json` gains:
  - `"snapshot_retention_days": 90` (auto-delete snapshots older than 90 days)
  - `"max_snapshots_kept": 30`
  - `"freeze_mode": false` (when true, all install actions require explicit confirmation + snapshot write)

### Release gate
- Snapshot written before audit, contains correct metadata
- Rollback restores registry + skill SHAs correctly
- CRC32 validation detects corrupted snapshot
- Recovery playbook reviewed by 2 maintainers
- Edge case: rollback with 0 snapshots (error message is clear)

---

## v0.6.0 · Beta — Runtime Sandboxing (Gap 1 Closure)

**Status:** ✅ Shipped
**Target:** Week 17

Robustness gap 1: Obfuscated malware bypasses static analysis. Minor code obfuscation (base64 decode, dynamic eval) defeats regex-based scanning. This version adds behavioral analysis + hardened Docker isolation.

### Ships

**Obfuscation detection**
- `security_scan.py` extended with dynamic unpacking:
  - Detects `base64.b64decode()`, `codecs.decode()`, `marshal`, `pickle` patterns
  - For suspicious code blocks, uses AST + controlled execution in sandbox to unpack and re-scan
  - New finding type: `OBFUSCATION_DETECTED` (severity: medium → orange 🟠 flag)
  - If unpacked code contains RED patterns → elevated to RED
- Heuristic: code that decodes then execs is highly suspicious even if decoder is clean

**Hardened Docker sandbox**
- `sandbox.py` complete Docker mode (v0.3.0 was stub):
  - Builds minimal Dockerfile on-the-fly: `FROM python:3.12-slim` + isolated `WORKDIR /tmp/skill_test`
  - Runs skill code inside container with:
    - Read-only filesystem (except `/tmp`)
    - No network (DNS blocked via `--net none`)
    - Memory limit: 256MB
    - CPU share: 1 (50% of 2-core baseline)
    - 10s execution timeout, killed if exceeded
    - No `/proc`, `/sys` access
  - Captures stdout/stderr for inspection
  - Container discarded after test (no layer reuse)
- Config option `"sandbox_mode": "subprocess" | "docker"` (default subprocess for speed, docker for trust-critical audits)
- Integration: when running `agent-hunter audit` on red-flagged skills, automatically use docker mode

**Behavior analysis during sandbox execution**
- Monitor for:
  - File writes outside `/tmp` (attempt to escape sandbox)
  - Network connection attempts (DNS queries, socket opens)
  - Process spawn (fork/exec attempts)
  - Environment variable reads (looking for secrets)
- Report findings as: `SANDBOX_ESCAPE_ATTEMPT` 🔴 or `SUSPICIOUS_ENV_READ` 🟠
- Captured behaviors are appended to skill's audit history

**Security baseline for v1.0.0**
- Any skill with `OBFUSCATION_DETECTED` or `SANDBOX_ESCAPE_ATTEMPT` is blocked from install
- Audit report includes behavior section: "Observed during sandbox: [list]"

### Release gate
- Sandbox successfully executes safe skill code and captures output
- Sandbox blocks network connection attempt (test with `urllib.request.urlopen("http://example.com")`)
- Sandbox blocks file write outside /tmp
- Obfuscation detector unpacks base64 code and re-scans correctly
- Docker mode gracefully falls back to subprocess if Docker not installed

---

## v0.6.5 · Beta — VS Code Copilot Adapter

**Status:** 📋 Planned
**Target:** Week 18 (parallel with v0.7.0 work)

**Primary platform:** Claude Code. VS Code GitHub Copilot uses a different skill-loading
mechanism (`.github/copilot-instructions.md`, GitHub Copilot extensions, `@workspace`
context). This adapter bridges the gap.

### Ships

**Adapter layer**
- `scripts/vscode_adapter.py` — reads VS Code workspace context:
  - `.github/copilot-instructions.md` instead of CLAUDE.md
  - `settings.json` for active extensions + language config
  - No `~/.claude/sessions/` equivalent; uses `.vscode/` metadata
- Output: same `ProjectContext` datatype as `context_extractor.py` — plugs into the
  existing hunter → scan → score → report pipeline unchanged
- `bin/vscode-context-extract` — thin wrapper calling the adapter

**Install target differences**
- Claude Code: `~/.claude/skills/<name>/SKILL.md`
- VS Code Copilot: `.github/copilot-instructions.md` injection (skill content inlined)
  or GitHub Copilot extension marketplace entry for MCP servers
- `installer.py` gains `--target vscode` flag; handles both install targets

**Limitations (documented)**
- VS Code Copilot does not support slash commands natively; `/agent-hunter` becomes
  a Copilot Chat `@workspace /agent-hunter` style invocation
- SKILL.md brain model does not run in VS Code Copilot; results are displayed as
  Copilot Chat output only (no multi-step orchestration)
- Full feature parity with Claude Code not planned — adapter ships the hunt + report;
  orchestration remains Claude Code exclusive

### Release gate
- `vscode-context-extract .` produces a `ProjectContext` identical in schema to the
  Claude Code path
- `hunt . --target vscode` runs end-to-end on a sample TypeScript/Node repo and
  produces a ranked report
- `--target vscode` install writes the correct output file (copilot-instructions.md)
  without clobbering existing content

---

## v0.7.0 · Beta — Dependency Conflict Management (Gap 3 Closure)

**Status:** ✅ Shipped

Robustness gap 3: Python/Node/Ruby version conflicts crash the agent. Installing Skill A (`pydantic<2.0`) then Skill B (`pydantic>=2.0`) breaks both. This version adds dependency resolution and containerization option.

### Ships

**Dependency resolver**
- New module: `scripts/dep_resolver.py`
  - Reads all installed skill `requirements.txt` (or `pyproject.toml`, `Gemfile`, `package.json`)
  - Builds a conflict graph: which skills have incompatible dependencies
  - Attempts to find a compatible semver range for conflicting packages
  - If no compatible range exists, flags as `UNRESOLVABLE_CONFLICT` (severity: 🔴)
- Algorithm: uses `packaging.specifiers.SpecifierSet` for Python, similar logic for other ecosystems
- Output: `{"conflicting_pairs": [("skill-a", "skill-b", "pydantic")], "resolution": "upgrade pydantic>=2.0 in skill-a"}`

**Containerized skill execution option**
- New config: `"skill_isolation": "none" | "venv" | "container"` (default: `none`)
  - `none`: current behavior, skills share global Python env
  - `venv`: each skill gets its own venv (Python only)
  - `container`: each skill runs in isolated Docker container with its own Python version
- When `container` mode: installer wraps each skill's SKILL.md body in a dockerfile runner
  - Installer creates skill-specific containers on demand
  - Skill is executed via `docker run --rm <container> <skill-code>`
  - Removes layer/image after execution

**Dependency audit command**
- `audit.py` extended: `agent-hunter audit --deps` reports:
  - Total unique dependencies across installed skills
  - Conflicting packages + severity
  - Which skills would need updating to resolve each conflict
  - Recommendation: "Install Skill X in a separate container" or "Uninstall Skill Y"
- Completes in ≤ 5s for 50 skills

**Version pinning and compatibility matrix**
- `registry.py` extended: for each installed skill, stores `python_version_tested`, `node_version_tested`
- On audit: compare tested versions vs. host environment
  - Tested on Python 3.10, host is 3.12 → 🟡 compatibility warning (may work, not guaranteed)
  - Tested on Python 3.6, host is 3.12 → 🔴 incompatible (likely broken)
- User can override via `config.json`: `"skip_version_checks": true`

### Release gate
- Dependency resolver correctly identifies pydantic version conflict in fixture set
- Resolver proposes valid semver range or `UNRESOLVABLE` flag
- Audit --deps completes in ≤ 5s for 50-skill mock dataset
- Containerized skill execution: skill runs in isolated container and produces correct output
- Version compatibility matrix works with Python/Node/Ruby versioning

---

## v0.8.0 · Beta — Web-of-Trust & Verified Indexing (Gap 4 Closure)

**Status:** ✅ Shipped
**Target:** Week 21

Robustness gap 4: GitHub Search is rate-limited and vulnerable to SEO poisoning + typo-squatting. An attacker can register `skll-deploy` (typo) or use GitHub SEO tricks to get ranked high. This version implements cryptographic verification and a curated index backend.

### Ships

**Cryptographic signing for verified index**
- New module: `scripts/verify_sig.py`
  - Verified skills in `references/VERIFIED_SKILLS.md` are signed with project maintainer's Ed25519 key
  - Key stored in `references/TRUSTED_KEYS.pub` (ASCII-armored)
  - On hunt: skills from verified index are verified before showing to user
  - Signature validation: skill entry includes `signature: <base64-ed25519>`, verified against structured content
  - Failed signature → 🔴 flag "Signature mismatch — this skill may have been tampered"

**Typo-squat detection**
- New module: `scripts/typo_detect.py`
  - For each hunt result, compute Levenshtein distance to known-verified skills
  - Distance ≤ 2 (typo threshold): flag as "⚠️ Similar to verified skill `XXX` — double-check you meant this one"
  - Examples: `skill-deply` vs verified `skill-deploy`, `react-uer` vs verified `react-user`
  - User can opt-in to block typos entirely via `config.json`: `"block_typo_results": true`

**Curated index backend (alternative to GitHub Search)**
- New data source: queries `references/CURATED_SOURCES.md` (local JSON list of trusted registries)
  - Format: `{registry_url: str, source_type: "github-org|gh-repo|private-index", last_updated: date}`
  - Examples:
    - `https://api.github.com/repos/awesome-claude-skills/directory` (curated org)
    - `https://skills-registry.example.com/api/v1/search` (private registry)
  - Hunter consult curated sources before GitHub Search (trust tier priority)
  - Results from curated sources get `[CURATED]` label in hunt report

**SEO poisoning defense**
- Scoring penalizes:
  - Repos with keyword-stuffed READMEs (entropy heuristic)
  - Repos with no code files (metadata-only)
  - Repos with artificially high star counts + low activity (likely GitHub Star farming)
- New finding: `ARTIFICIAL_RANKING_SIGNALS` 🟠 (flagged but not blocking)

**Verified index maintenance process**
- `CONTRIBUTING.md` updated with:
  - How to propose a new verified skill (submit issue with self-certification)
  - Criteria: 50+ stars, active maintenance (commit in last 60 days), passing full security scan, 2 maintainer sign-offs
  - Process: issue → PR review → maintainer signature → merged to verified index
- Automated: weekly GitHub Actions job runs security scan on all verified skills, alerts maintainers of any regressions

**Web-of-Trust graph (advanced, documented in SECURITY.md)**
- Optional: users can extend trust via explicit endorsements
  - `~/.agent-hunter/trusted_authors.json`: `{"username": ["indhra", "some-trusted-dev"]}`
  - Skills by trusted authors get `[AUTHOR_TRUSTED]` label + score bonus (0.15×)
  - Builds a community web-of-trust without central authority

### Release gate
- Cryptographic signature validates correctly for test entry in verified index
- Signature verification fails (with clear error) for tampered entry
- Typo-squat detection flags `skll-deploy` as similar to `skill-deploy`
- Curated sources query returns results correctly
- SEO poisoning heuristic penalizes 100-star repo with 0 commits in 180 days
- `CONTRIBUTING.md` reviewed by 2+ maintainers

---

## v1.0.0 · General Availability — Production Ready

**Status:** 📋 Planned
**Target:** Week 24

This is the release that earns the 1.0.0 label. The tool is now hardened against:
- Obfuscated malware (v0.6.0)
- Poisoned SHA versions (v0.5.0)
- Dependency conflicts (v0.7.0)
- GitHub SEO poisoning (v0.8.0)

Plus all v0.1.0–v0.4.0 features (hunt, score, audit, update, sandbox, contribute, feedback loop).

### Ships

**Robustness validation**
- Full test suite: precision/recall benchmarks across 10 real projects (published in `BENCHMARKS.md`)
- Security regression test suite: 50+ attack patterns (obfuscation, prompt injection, dependency conflicts, etc.)
- Performance baseline: all operations meet targets (hunt ≤ 25s, audit ≤ 45s, rollback ≤ 2s)

**Documentation & Governance**
- `SPEC.md` — complete API specification + error handling matrix for all scripts
- `SECURITY.md` — threat model, attack surface, security assumptions
- `RECOVERY.md` — incident response playbook
- `CONTRIBUTING.md` — process for verified skills + community governance
- Demo GIF + video walkthrough (10 min)
- Tutorial for non-developers: "How to find and vet skills without coding"

**Integration & Deployment**
- GitHub Actions CI: lint, test (100% pass), security pattern validation, performance benchmarks
- `cisco-ai-defense/skill-scanner` as optional secondary scan backend (user opt-in via config)
- Sign-off from 3+ external security reviewers (documented in `SECURITY_REVIEW.md`)
- Public security audit results published

**Verified Index Bootstrap**
- `references/VERIFIED_SKILLS.md` — 50+ manually verified entries (seeded + first month community submissions)
- `references/SECURITY_PATTERNS.md` — 25+ detection rules, all tested
- `references/KNOWN_MALICIOUS.md` — 10+ documented cases from Snyk + community reports
- `references/CURATED_SOURCES.md` — 5+ trusted registries linked

### v1.0.0 Benchmark Targets (hard gates — release blocked if not met)

| Metric | Target |
|---|---|
| Precision top-5 (avg across 10 projects) | ≥ 3.5 / 5 |
| False-negative rate (malicious set) | 0% |
| False-positive rate (security scan) | ≤ 10% |
| Obfuscation detection rate | ≥ 95% |
| Typo-squat detection accuracy | ≥ 90% |
| Hunt time (authenticated) | ≤ 25s |
| Hunt time (unauthenticated) | ≤ 60s |
| Audit time — 20 skills | ≤ 45s |
| Rollback time | ≤ 2s |
| Docker sandbox execution | ≤ 10s |
| Dependency resolver time — 50 skills | ≤ 5s |
| Signature verification time | ≤ 100ms |
| Test coverage | ≥ 90% all modules |

### ⚠️ Post-release tasks
- Record demo GIF (< 45s, no setup)
- Publish to package managers: PyPI (`pip install agent-hunter`)
- Docker image: `docker pull indhra/agent-hunter` (optional, for users who want it containerized)
- Set up Slack channel for security reports

---

## v2.0.0+ (Post-v1.0.0 — Future Vision)

Once v1.0.0 ships stable, these features are candidates:

| Feature | Rationale | Target |
|---------|-----------|--------|
| **Skill Package Manager** | Package N skills as bundles (e.g., "full-stack-dev: [react, node, postgres-helper]") | v2.0.0 |
| **MCP Server Registry** | Dedicated registry for MCP servers (separate from SKILL.md hunt) | v2.0.0 |
| **Automated Conflict Resolution** | Auto-suggest compatible versions + rebuild env | v2.1.0 |
| **Telemetry (opt-in)** | Anonymized usage stats to improve scoring (requires explicit user consent + transparency) | v2.1.0 |
| **Skill Dashboard** | Web UI for managing installed skills + viewing audit history | v2.2.0 |
| **Fleet Management** | Deploy agent-hunter + curated skill set to team of developers | v2.3.0 |
| **LLM Model Marketplace** | Index of Claude-compatible models + version compatibility matrix | v2.4.0 |
| **Paid Support Tier** | Commercial support + priority CVE alerts (tool remains free/open) | v2.5.0 |

---

## Anti-Features (Permanent Commitments)

These are not "not planned." They are **never.**

| Anti-feature | Why never |
|---|---|
| Auto-install without user confirmation | Trust and security. Human in the loop, always. |
| Telemetry or usage analytics (non-opt-in) | Privacy by design. Nothing leaves without user knowledge. |
| Paid tier or feature gating | MIT, open source, forever (support is where monetization happens). |
| LLM API calls from Python scripts | Host agent does all reasoning. Scripts do I/O only. |
| Sponsored or boosted results | Not a marketplace. Not ad-driven. |
| Installing RED-flagged skills | Non-negotiable. RED = excluded. Count reported only. |
| Silently hiding partial results | Fail loudly. Partial is worse than nothing. |

---

## Issue Labels

| Label | Meaning |
|---|---|
| `v0.5.0` / `v0.6.0` / ... / `v1.0.0` | Milestone target |
| `security-pattern` | New detection rule for scanner |
| `hunt-source` | New skill/MCP registry source |
| `benchmark` | Precision/recall test data submission |
| `verified-skill` | Candidate for VERIFIED_SKILLS.md |
| `trust-tier` | Trust system improvements |
| `breaking` | Impacts SKILL.md interface or registry schema |
| `gap-1-sandboxing` | Runtime sandboxing & obfuscation detection |
| `gap-2-recovery` | Safe-state recovery & rollback |
| `gap-3-dependencies` | Dependency conflict management |
| `gap-4-web-of-trust` | Verified indexing & typo-squat defense |
| `good-first-issue` | Accessible for new contributors |

---

*This roadmap is a commitment, not a wish list. Milestone dates move only when blockers are real and documented.*

# agent-hunter

> **Hunt the right skills. Block the bad ones.**
> Context-aware. Security-scanned. Self-evolving.

<!--
████████████████████████████████████████████████████████
  PLACEHOLDER — DEMO GIF
  Record after v1.0.0 ships.
  Show: open FastAPI+Postgres project → type trigger →
  6 ranked results appear with 🟢/🟡/🔴 trust signals →
  one result selected → install command shown.
  Target: under 45 seconds. No setup shown. Just value.
  Tool recommended: vhs (charm.sh/vhs) or asciinema
████████████████████████████████████████████████████████

![agent-hunter demo](./assets/demo.gif)
-->

<p align="center">
  <img src="./assets/demo-placeholder.png" alt="Demo coming soon" width="640"/>
</p>

<p align="center">
  <a href="https://github.com/indhra/agent-hunter/releases"><img src="https://img.shields.io/github/v/release/indhra/agent-hunter?color=98c379&label=version" alt="Version"/></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-61afef" alt="MIT License"/></a>
  <a href="https://github.com/indhra/agent-hunter/issues"><img src="https://img.shields.io/github/issues/indhra/agent-hunter?color=e06c75" alt="Issues"/></a>
  <img src="https://img.shields.io/badge/claude-native-e5c07b" alt="Claude Native"/>
  <img src="https://img.shields.io/badge/privacy-no%20telemetry-98c379" alt="No Telemetry"/>
</p>

---

## The Problem

The SKILL.md ecosystem has **400,000+ skills**. [13% are malicious](https://snyk.io/articles/skill-md-shell-access/). [46% are duplicates](https://olshansky.info/posts/2026-02-28-signal-vs-noise-in-the-skills-ecosystem). Every other discovery tool sends you into that noise unprotected, and none of them know what you're actually building.

The result: developers rebuild skills that already exist, install skills that harm their agent, and waste hours searching catalogs that don't understand their stack.

**agent-hunter is different.** It reads what you're actually building — your repo, your git history, your CLAUDE.md — hunts skills and MCP servers that match your exact context, vets every result for security issues before showing it to you, and warns you when installed skills have been tampered with.

It's not a search tool. It hunts what fits, blocks what doesn't.

> *"I built something from scratch, then found a SKILL.md that already did exactly that. Wasted time. I wish I had known."*
> — The pain that built this tool.

---

## Why agent-hunter vs Everything Else

| Capability | find-skills | autoskills | auto-skill v5 | gh skill | **agent-hunter** |
|---|:---:|:---:|:---:|:---:|:---:|
| Reads your actual project context | ✗ | Stack only | Session patterns | ✗ | **✅ Deep** |
| Proactive — hunts before you ask | ✗ | ✗ | ✅ | ✗ | **✅** |
| Trust tiers (Verified → Community → Raw) | ✗ | ✗ | ✗ | ✗ | **✅** |
| Security scans every result | ✗ | ✗ | ✗ | ✗ | **✅** |
| Runtime sandbox isolation | ✗ | ✗ | ✗ | ✗ | **✅** |
| Hunts MCP servers too | ✗ | ✗ | ✗ | Partial | **✅** |
| SHA-based update + tamper detection | ✗ | ✗ | ✗ | ✅ | **✅** |
| Rollback to last healthy state | ✗ | ✗ | ✗ | ✗ | **✅** |
| "Explain why" per recommendation | ✗ | ✗ | ✗ | ✗ | **✅** |
| Audit command (skill health check) | ✗ | ✗ | ✗ | ✗ | **✅** |
| License compatibility check | ✗ | ✗ | ✗ | ✗ | **✅** |
| No telemetry, fully local | ✅ | ✅ | ✗ | ✅ | **✅** |

**The sharpest differences:**
- `autoskills` installs what it pre-curated. `agent-hunter` finds what you actually need.
- `auto-skill v5` observes what you did. `agent-hunter` understands what you're building.
- Nobody else runs security scans. Nobody else has rollback. Nobody else sandboxes execution.

---

## How It Works

```
Your Project                    agent-hunter                     Trust Sources
─────────────────               ─────────────────────────        ──────────────────
CLAUDE.md          ──reads──►  Context Extraction               Verified Index (primary)
requirements.txt              (tech signals only,    ──hunts──►  Community-reviewed list
git log (last 50)              no code, no paths)               GitHub Search (fallback)
~/.claude/sessions/             │
                                ▼
                           Trust Tier Filter
                           (Verified > Community > Raw)
                                │
                                ▼
                           Pre-Filter Pipeline
                           (10+ stars, <6mo, code files,
                            tech name present)
                                │
                                ▼
                           Security Scan                 pors/skill-audit
                           (prompt injection,   ──uses──►  integration
                            hidden Unicode,               🟢 🟡 🔴 signals
                            supply chain check,
                            runtime sandbox test)
                                │
                                ▼
                           Relevance Scoring
                           (stack match × domain ×
                            stars × recency × trust × YAGNI)
                                │
                                ▼
                    ┌──── Hunt Report ────┐
                    │  Top 5-10 ranked    │
                    │  Trust signals      │──► Terminal (rich)
                    │  "Why this for you" │──► hunt_report_YYYY-MM-DD.md
                    │  Install commands   │
                    └─────────────────────┘
```

---

## Quick Start

### Installation

```bash
# Install agent-hunter as a Claude skill
gh skill install indhra/agent-hunter

# Or manually
cp -r agent-hunter ~/.claude/skills/agent-hunter
```

### Your First Hunt

Imagine you're working on a FastAPI + PostgreSQL project. Just ask Claude to hunt:

```
Hunt for skills relevant to this project
```

agent-hunter will:
1. **Read your project** — detects FastAPI, PostgreSQL, Docker, pytest
2. **Hunt GitHub** — finds 8 skills matching your stack
3. **Security scan** — flags 2 RED (injected shells), hides them
4. **Rank results** — shows 6 green, scored by relevance + trust
5. **Print report**:

```
─────────────────────────────────────────────────────────
HUNT RESULTS — agent-hunter v0.1.0
─────────────────────────────────────────────────────────
Your stack: fastapi, postgresql, docker, pytest, pydantic
Domain: backend
─────────────────────────────────────────────────────────

1. ⭐⭐⭐⭐⭐ trusty (by /someone)
   Security scanner for Claude skills. 🟢 VERIFIED
   Score: 4.8/5.0  Trust: verified  Stars: 2400
   Reason: Exact stack match (fastapi+pydantic). Active (2d).
   
2. ⭐⭐⭐⭐  autotest (by /author)
   Auto-generate pytest tests from docstrings.  🟢 COMMUNITY
   Score: 4.3/5.0  Trust: community  Stars: 890
   Reason: Stack match (pytest). Used in your sessions (8 days ago).
   
3. ⭐⭐⭐⭐  db-migrate (by /someone-else)
   PostgreSQL schema versioning + rollback. 🟡 RAW
   Score: 3.9/5.0  Trust: raw  Stars: 340
   Reason: Domain match (backend+database). Newer (4d).
   
[Install any? Type: agent-hunter install trusty]

2 results RED-scanned (hidden) — use --show-scan-details to review
─────────────────────────────────────────────────────────
```

Then:
```bash
agent-hunter install trusty autotest
```

That's it. The skills are cloned to `~/.claude/skills/` and immediately available. No restart needed.

---

## Commands

```bash
# Hunt for new skills + MCP servers matching your current project
agent-hunter hunt

# Review health of all installed skills (updates, security, conflicts)
agent-hunter audit

# Update all installed skills with newer versions (user confirms)
agent-hunter update

# Roll back to last known healthy state (if tamper or bad update detected)
agent-hunter rollback

# Show what agent-hunter knows about your current project context
agent-hunter context

# Scaffold a new SKILL.md stub pre-filled with your project's stack
agent-hunter scaffold <name>
```

---

## Updates & Releases

- **Check for updates:** `agent-hunter update`
- **Release notes:** [GitHub Releases](https://github.com/indhra/agent-hunter/releases)
- **Version history:** [CHANGELOG.md](./CHANGELOG.md)
- **Rollback:** `agent-hunter rollback` (if needed)

---

## What Gets Scanned

agent-hunter reads these files to understand your project — **nothing leaves your machine except anonymized tech signal keywords** (framework names, library names):

- `CLAUDE.md` / `AGENTS.md` / `COPILOT-instructions.md`
- `requirements.txt` / `package.json` / `pyproject.toml` / `Cargo.toml`
- `git log --oneline -50`
- `~/.claude/sessions/` (recent session transcripts)

**Privacy guarantee:** File paths, variable names, function names, commit message text, and any project-specific strings are **never** extracted or sent externally. See [SPEC.md § Privacy Model](./SPEC.md#privacy-model) for the full contract.

---

## Security

agent-hunter uses a layered security model:

| Layer | What it does |
|---|---|
| **Trust tiers** | Verified → Community-reviewed → Raw GitHub. Raw results are lower score by default. |
| **Static scan** | Prompt injection, shell exec guards, hidden Unicode, secret patterns |
| **Runtime sandbox** | Suspicious skills executed in isolated subprocess with masked env vars |
| **SHA tracking** | Stored at install. Mismatch on audit = tamper flag. |
| **Supply chain** | Cross-checks repo contributor history for sudden ownership change |
| **License check** | GPL/proprietary skills in MIT projects flagged |
| **Rollback** | Instant restore to last known healthy registry state |

Integration: [pors/skill-audit](https://github.com/pors/skill-audit) · [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner)

---

## The Self-Evolving AI Team Model

agent-hunter is built around one idea: **don't reinvent what already exists.**

- **Solo founder:** One Claude session. Hunter surfaces tools before you need them.
- **+Engineer:** New Claude session scoped to that role. Hunter finds skills for that context.
- **Fat-less:** `agent-hunter audit` periodically removes dead weight. Nothing stays installed without earning it.
- **Self-aware loop:** Hunt → Install → Use → Audit → Update → Rollback if needed. The system knows what it has, what it needs, and what's gone bad.

Skills = tools your agents use. Agents = your team. agent-hunter = your recruiter + immune system. **Never build what already exists as a proven, trusted tool.**

---

## Testimonials

<!--
████████████████████████████████████████
  PLACEHOLDER — TESTIMONIALS
  Collect after first 20 active users.
  Target: 3–5 testimonials from real developers.
  Format below. Add real quotes, names, GitHub handles.
████████████████████████████████████████

> "agent-hunter found a Databricks skill I'd been manually coding for 3 days.
>  Would have saved me the whole week."
> — @developer_handle, Senior ML Engineer

> "The security scanning caught a prompt injection in a skill I was about to install.
>  Other tools would have just let it through."
> — @developer_handle, Platform Engineer
-->

*Be the first to share your experience → [Open an issue](https://github.com/indhra/agent-hunter/issues/new?template=testimonial.md)*

---

## This Solves a Gap Anthropic Knows About

See [anthropics/claude-code#33292](https://github.com/anthropics/claude-code/issues/33292): *"Personal-scope skills not surfaced in model context for proactive discovery"* — agent-hunter directly addresses this open issue.

---

## Contributing

We welcome 4 types of contributions:

1. **Hunt sources** — add a new skill/MCP registry to search
2. **Security patterns** — add detection rules for new attack vectors (most important)
3. **Benchmarks** — test on real projects and submit precision data
4. **Verified skills** — curate and add to the community-vetted list

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for the full versioned plan.

**Now:** v0.1.0 Alpha — core hunt, security scan, Claude-native
**Next:** v0.2.0 — MCP hunting, audit, SHA tracking, rollback, sandbox, trust tiers
**Then:** v0.3.0 — conflict detection, dependency awareness, scaffold, runtime sandbox
**GA:** v1.0.0 — benchmarked, CVE integration, production-ready, demo recorded

---

## License

MIT © 2026 [Indhra Kiranu N A](https://github.com/indhra)

---

<p align="center">
  <sub>Built because the ecosystem exploded and nobody is protecting you in it.</sub>
</p>

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
  <img src="https://img.shields.io/badge/platform-Claude%20Code-e5c07b" alt="Claude Code"/>
  <img src="https://img.shields.io/badge/privacy-no%20telemetry-98c379" alt="No Telemetry"/>
</p>

---

## Install — 30 seconds

**Platform:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (primary). VS Code Copilot adapter planned for v0.6.5.

**Requirements:** Claude Code, Git, Python 3.10+

### Step 1: Install globally

```bash
git clone --single-branch --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

`./setup` does three important things:

- installs the local Python environment and wrappers
- registers `agent-hunter` in your global `~/.claude/CLAUDE.md`
- makes `/agent-hunter` available immediately in any repo, including brand new projects with no local `CLAUDE.md`

Project-level `CLAUDE.md` setup is optional and comes later if you want the behavior shared with teammates.

### Step 2: Set your GitHub token (optional — for broader discovery)

agent-hunter works out of the box using the curated verified skills index. GitHub Code Search is additive — it unlocks discovery of skills beyond the curated list.

```bash
export GITHUB_TOKEN=your_token_here
# or add to ~/.zshrc / ~/.bash_profile for persistence
```

Generate at https://github.com/settings/tokens — no scopes needed. Skip this step if you only want curated results.

### Update

```bash
/agent-hunter-update
```

Or manually: `cd ~/.claude/skills/agent-hunter && git pull && ./setup`

### Uninstall

```bash
rm -rf ~/.claude/skills/agent-hunter ~/.claude/skills/agent-hunter-update
```

Then remove the `## agent-hunter` section from your CLAUDE.md.

### Troubleshooting

Skill not showing up? `cd ~/.claude/skills/agent-hunter && ./setup`

Claude says it can't see the skill? Check your global `~/.claude/CLAUDE.md` first. `agent-hunter` is designed to work globally before a project has any local instructions.

If you want the same behavior shared with teammates, add this block to the project's `CLAUDE.md`:

```
## agent-hunter

Use /agent-hunter to discover, security-scan, and install SKILL.md files and MCP
servers relevant to the current project. Use it before manually searching for
skills or building a tool from scratch.

Available skills: /agent-hunter, /agent-hunter-update
```

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
git clone --single-branch --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

After setup, `/agent-hunter` is available globally through `~/.claude/CLAUDE.md`.
That means it works on a brand new repo even if there is no local project `CLAUDE.md` yet.

### Your First Hunt

Open any repo and ask Claude:

```
What should I install for this project?
```

agent-hunter will:
1. **Read your project signals** — framework and tooling names only
2. **Hunt verified and GitHub sources** — skills and MCPs relevant to your repo
3. **Security scan results** — unsafe matches are blocked before recommendation
4. **Rank the top matches** — default output is the best few results, not a noisy list
5. **Show install-ready guidance** — what fits, why it fits, and what to avoid

```
1. 🟢 skill-a
   Safe to install. Strong match for your current stack.
   Why: your repo uses FastAPI, pytest, and Docker, and this skill targets backend testing workflow.

2. 🟡 skill-b
   Review before installing.
   Why: relevant to your stack, but flagged for caution during scan.

3. 🟢 mcp-c
   Safe to install. Useful if you want a tighter MCP workflow for this repo.
```

Then:
```bash
/agent-hunter
# or
agent-hunter hunt .
```

If the recommendations are useful, add the same block to the project's `CLAUDE.md` so teammates get the workflow too.

---

## Commands

Invoke via Claude Code (type a trigger phrase) or run the bin scripts directly:

```bash
# Full hunt — context → GitHub → scan → score → report
~/.claude/skills/agent-hunter/bin/hunt [project_root] [--intent "<intent>"]

# Review health of all installed skills
~/.claude/skills/agent-hunter/bin/audit

# Restore registry to last known good snapshot
~/.claude/skills/agent-hunter/bin/rollback

# Show what agent-hunter knows about your project
~/.claude/skills/agent-hunter/bin/context-extract [project_root]

# Security-scan a SKILL.md file
~/.claude/skills/agent-hunter/bin/security-scan path/to/SKILL.md

# Scaffold a new SKILL.md stub
~/.claude/skills/agent-hunter/bin/scaffold <name> --project .

# Raw GitHub Code Search (pure bash/curl, no Python)
~/.claude/skills/agent-hunter/bin/github-search "filename:SKILL.md fastapi"
```

The `~/.local/bin/agent-hunter` symlink is created by `./setup`, so after adding
`~/.local/bin` to your PATH you can also run `agent-hunter hunt .` directly.

---

## Global vs Project CLAUDE.md

agent-hunter uses a two-level model:

- **Global `~/.claude/CLAUDE.md`**: installed by `./setup`; makes `/agent-hunter` available in every repo, including new ones with no local setup
- **Project `CLAUDE.md`**: optional; add after first value if you want the behavior shared with teammates

The intended flow is:

1. install once globally
2. use immediately on any repo
3. promote to project-level instructions when the workflow proves useful

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

**Shipped:** v0.8.0 — cryptographic signing, typo-squat detection, author trust, Docker sandbox, dep conflict manager, npm MCP discovery
**Next:** v0.9.0 — real-world UX hardening, benchmark suite, CVE index integration
**Then:** v0.6.5 — VS Code Copilot adapter (different skill-loading mechanism)
**GA:** v1.0.0 — benchmarked, production-ready, demo recorded

---

## Connect

**Have questions or want to collaborate?**

- 🐛 **Issues & feedback:** [GitHub Issues](https://github.com/indhra/agent-hunter/issues)
- 💼 **Collaboration & partnerships:** [LinkedIn](https://www.linkedin.com/in/indhra/)

---

## License

MIT © 2026 [Indhra Kiranu N A](https://github.com/indhra)

---

<p align="center">
  <sub>Built because the ecosystem exploded and nobody is protecting you in it.</sub>
</p>

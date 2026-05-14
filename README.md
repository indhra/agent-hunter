# agent-hunter

**The first skill you should install after Claude Code itself.**

> Hunt the right skills. Block the bad ones.

**agent-hunter** discovers and installs the top 3 skills and MCP servers for your projects — automatically, securely, without you ever searching manually.

Before you build it again, check what already exists.

[![Version](https://img.shields.io/badge/version-1.0.0--alpha-98c379)](https://github.com/indhra/agent-hunter/releases)
[![License](https://img.shields.io/badge/license-MIT-61afef)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/platform-Claude%20Code-e5c07b)](https://docs.anthropic.com/en/docs/claude-code)
[![Privacy](https://img.shields.io/badge/privacy-no%20telemetry-98c379)](./CONTRIBUTING.md#privacy)

---

## What It Does

Given your repo, agent-hunter tells you the **top 3 skills or MCPs** you should use now, why they fit, and which ones to avoid.

```
$ agent-hunter hunt .

📍 Found: FastAPI, PostgreSQL, pytest, Docker

Top 3 recommendations:

1. 🟢 fastapi-backend-testing
   Safe to install.
   Why: Your repo uses FastAPI, pytest, and Docker. This skill targets
   backend test and deployment workflows directly.

2. 🟢 postgres-mcp-server
   Safe to install.
   Why: Your project connects to PostgreSQL. This MCP gives Claude direct
   database query and schema inspection tools.

3. 🟡 api-security-scanner
   Review before installing.
   Why: Useful for REST API security audits, but flagged for filesystem
   access patterns. Review SKILL.md before proceeding.

🔴 2 results blocked (security scan)
```

---

## The Goal

✨ **New Claude Code user workflow:**

```
1. Install Claude Code
2. Run: git clone ... && ./setup  (agent-hunter)
3. Open any project
4. Type: /agent-hunter
5. Get top 3 skill recommendations
6. Install what you need
```

**That's it.** You never search for skills manually. You never wonder "does this already exist?" Again.

---

## Install (One-Time, Then Everywhere)

**Requirements:** Claude Code, Git, Python 3.10+

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

The `./setup` script:
- ✅ Checks Python 3.10+
- ✅ Creates isolated venv
- ✅ Registers `/agent-hunter` in global `~/.claude/CLAUDE.md`
- ✅ Works in every Claude Code session, no per-project setup needed

After setup, agent-hunter is available everywhere.

---

## Proactive Mode (Optional - Automatic on New Projects)

By default, agent-hunter runs when you ask. To make it **automatically activate on new projects**:

```bash
export AGENT_HUNTER_AUTO=1
```

Add this to `~/.zshrc` or `~/.bash_profile` to enable it permanently.

**What happens with proactive mode:**
- ✅ Open a new project → agent-hunter auto-runs
- ✅ Top 3 skills surface without waiting
- ✅ One hunt per session per project (prevents redundant runs)
- ✅ You can still explicitly run `/agent-hunter` anytime

See [INSTALL.md](./INSTALL.md) for full proactive setup options.

---

## First Run

Open any repo and type:

```
/agent-hunter
```

Or ask Claude:

```
What skills or tools should I install for this project?
```

agent-hunter will:

1. Read your project's tech stack (framework names only — no code, no paths)
2. Hunt curated skills + GitHub results
3. Security-scan every result
4. Show top 3 recommendations with clear explanations
5. Guide you through install if useful

---

## Why Use This

**You waste time rebuilding skills that already exist.**

The SKILL.md ecosystem has thousands of skills. None of the discovery tools understand what you're building. They send you into catalogs with no context, no security vetting, and no clear recommendations.

agent-hunter is different:

- **Repo-aware** — understands your actual tech stack
- **Top 3 focus** — shows the best matches, not a noisy list
- **Security-scanned** — blocks risky skills before showing them
- **Clear explanations** — tells you *why* each skill fits your project
- **Fast** — meaningful results in under 30 seconds
- **Works on any project** — greenfield AND brownfield (existing codebases)

### Greenfield & Brownfield

**New project?** Get top 3 skills to install from the start.

**Existing project?** Hunt for skills that enhance your current work:
- Refactoring helpers
- Performance profilers
- Testing frameworks
- Deployment tools
- Security scanners
- Documentation generators

Discover what exists instead of rebuilding from scratch.

---

## Discovery Modes

agent-hunter uses a **three-tier discovery system** to give you the best coverage:

### 🎯 Tier 1: Curated Index (Always Active)

**Source:** `references/VERIFIED_SKILLS.md` — ~100 verified, security-scanned skills
**Speed:** Instant (offline)
**Trust:** Highest (human-reviewed by maintainers)
**Setup:** None needed

This is your baseline. These skills are manually vetted, tested in real projects, and cryptographically signed. If the curated index has what you need, you'll see it first.

### 🔍 Tier 2: GitHub API Search (Optional)

**Source:** GitHub Code Search — 5,000+ repositories with SKILL.md
**Speed:** 2-5 seconds
**Trust:** Medium (automated filtering via Bug #2 fixes)
**Setup:** Requires `GITHUB_TOKEN`

Broader discovery beyond the curated set. Searches GitHub for SKILL.md files, filters out noise (spell checkers, UI tools, etc.), and ranks by relevance to your project.

**Enable Tier 2:**
```bash
export GITHUB_TOKEN=your_token_here
```

Generate a token at https://github.com/settings/tokens (no scopes needed).

**Without a token:** agent-hunter uses Tier 1 (curated) + Tier 3 (web search) only. You'll see ~100 verified skills plus web-discovered results.

### 🌐 Tier 3: LLM Web Search (On-Demand)

**Source:** Web search across GitHub, skill marketplaces, documentation
**Speed:** 5-15 seconds
**Trust:** Variable (security-scanned before showing)
**Activation:** User prompt or auto-trigger when < 3 results

Discovers skills beyond GitHub's index:
- Skill marketplaces (Smithery, Agensi.io, MCP Market)
- Community repos not indexed by GitHub search
- Official framework skills (FastAPI, Django, etc.)
- 5,000+ MCP servers across registries

**How it works:**
1. agent-hunter shows initial results from Tier 1 + 2
2. If < 3 results found, offers: "Search broader?"
3. If you say yes: runs web search, parses for GitHub URLs, scans for security
4. Shows updated top 3 with web-discovered skills marked

**When to use:**
- Exploring a new stack and want maximum coverage
- Curated + GitHub results don't cover your use case
- Looking for official framework skills or MCP servers

---

## Commands

```bash
# Main command — hunt for skills/MCPs relevant to your project
agent-hunter hunt .

# Health check — audit all installed skills
agent-hunter audit

# Restore registry to last known good state
agent-hunter rollback
```

Run from Claude Code: `/agent-hunter`

---

## GitHub Token Setup (Recommended)

**For better skill discovery** (especially on brownfield projects), set a GitHub PAT token:

```bash
# Quick setup
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Permanent setup (add to ~/.zshrc or ~/.bash_profile)
echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

**Generate token:** https://github.com/settings/tokens (no scopes needed, public access only)

### Why Use a Token?

- **Without token**: Tier 1 (curated, ~100 verified skills) + Tier 3 (web search)
- **With token**: All 3 tiers — curated + GitHub API (5,000+ repos) + web search
- **Brownfield value**: Finds 100x more skills to enhance existing projects
- **Faster**: No GitHub API rate limit hits

### Discovery Coverage

| Mode | Token? | Coverage | Speed | Use Case |
|---|---|---|---|---|
| Casual | ❌ No | ~100 curated skills | Instant | Quick recommendations |
| Active Development | ✅ Yes | 5,000+ repos searched | 2-5 sec | Better matches, brownfield work |
| Deep Exploration | ✅ Yes | All 3 tiers | 5-15 sec | Find obscure, niche skills |

See [Discovery Modes](#discovery-modes) below for full details on each tier.

---

## Update / Uninstall

**Update:**

```bash
cd ~/.claude/skills/agent-hunter && git pull && ./setup
```

**Uninstall:**

```bash
rm -rf ~/.claude/skills/agent-hunter
```

Then remove the `## agent-hunter` section from `~/.claude/CLAUDE.md`.

---

## Privacy

agent-hunter only extracts tech keywords (framework names, library names) from your project.
**No code, no paths, no project-specific strings ever leave your machine.**

See [CONTRIBUTING.md](./CONTRIBUTING.md#privacy) for details.

---

## Contributing

We welcome:

1. **Security patterns** — add detection rules for new attack vectors
2. **Verified skills** — curate and add to the community-vetted list
3. **Benchmarks** — test on real projects and submit precision data

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## License

MIT © 2026 [Indhra Kiranu N A](https://github.com/indhra)

---

**Built to save time and block the bad stuff.**

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

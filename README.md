# agent-hunter

Skill package manager for Claude Code. Discovers relevant skills and MCP servers for your projects.

[![Version](https://img.shields.io/badge/version-1.0.0--alpha-98c379)](https://github.com/indhra/agent-hunter/releases)
[![License](https://img.shields.io/badge/license-MIT-61afef)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/platform-Claude%20Code-e5c07b)](https://docs.anthropic.com/en/docs/claude-code)
[![Privacy](https://img.shields.io/badge/privacy-no%20telemetry-98c379)](./CONTRIBUTING.md#privacy)

---

## What It Does

Given your repository, agent-hunter identifies the top 3 relevant skills or MCPs, explains why they fit, and identifies unsafe ones to avoid.

```
$ agent-hunter hunt .

Found: FastAPI, PostgreSQL, pytest, Docker

Top 3 recommendations:

1. fastapi-backend-testing
 Status: SAFE
 Reason: Your repo uses FastAPI, pytest, and Docker. This skill provides
 test and deployment workflow helpers.

2. postgres-mcp-server
 Status: SAFE
 Reason: PostgreSQL detected. Provides database query and schema tools.

3. api-security-scanner
 Status: REVIEW
 Reason: REST API security audits. Flagged for filesystem access.
 Review SKILL.md before installing.

Blocked (security): 2 results
```

---

## Installation

Requirements: Claude Code, Git, Python 3.10+

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

The setup script:
- Verifies Python 3.10+
- Creates isolated virtual environment
- Registers agent-hunter in global ~/.claude/CLAUDE.md
- Makes /agent-hunter available in all Claude Code sessions

---

## Usage

### Basic Hunt

```bash
/agent-hunter
```

Or:

```bash
agent-hunter hunt /path/to/project
```

### Proactive Mode (Optional)

Enable automatic hunting when opening new projects:

```bash
export AGENT_HUNTER_AUTO=1
```

Add to ~/.zshrc or ~/.bash_profile for permanence.

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

1. Read your project's tech stack (framework names only - no code, no paths)
2. Hunt curated skills + GitHub results
3. Security-scan every result
4. Show top 3 recommendations with clear explanations
5. Guide you through install if useful

---

## Discovery Tiers

### Tier 1: Curated Index (Always Active)

Source: ~100 verified skills (offline)
Speed: Instant
Trust: Highest (human-reviewed)
Setup: None required

Manually vetted skills. Cryptographically signed.

### Tier 2: GitHub API Search (Optional)

Source: GitHub Code Search - 5,000+ repositories with SKILL.md
Speed: 2-5 seconds
Trust: Medium (automated filtering)
Setup: Requires GITHUB_TOKEN

```bash
export GITHUB_TOKEN=your_token
```

Generate at https://github.com/settings/tokens (no scopes required).

### Tier 3: Web Search (On-Demand)

Source: Web search across GitHub, marketplaces, documentation
Speed: 5-15 seconds
Trust: Variable (security-scanned before showing)
Activation: User request or auto-trigger when < 3 results

---

## Commands

```bash
# Main command - hunt for skills/MCPs relevant to your project
agent-hunter hunt .

# Health check - audit all installed skills
agent-hunter audit

# Restore registry to last known good state
agent-hunter rollback
```

Run from Claude Code: `/agent-hunter`

---


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

Extracts tech keywords only (framework names, library names). No code, paths, or project-specific strings leave your machine.

See [CONTRIBUTING.md](./CONTRIBUTING.md#privacy) for details.

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

---

## License

MIT © 2026 [Indhra Kiranu N A](https://github.com/indhra)

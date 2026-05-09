# agent-hunter

**Repo-aware skill package manager for Claude Code.**

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

## Install

**Requirements:** Claude Code, Git, Python 3.10+

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

`./setup` registers `agent-hunter` in your global `~/.claude/CLAUDE.md`. After this, `/agent-hunter` works in any repo, including brand new projects with no local setup.

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

## GitHub Token (Optional)

agent-hunter works out of the box using the curated index. GitHub Code Search unlocks discovery beyond the curated list.

```bash
export GITHUB_TOKEN=your_token_here
# or add to ~/.zshrc / ~/.bash_profile
```

Generate at <https://github.com/settings/tokens> (no scopes needed). Skip if you only want curated results.

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

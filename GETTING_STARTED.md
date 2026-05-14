# Getting Started

This guide covers installation and usage of agent-hunter.

---

## Overview

agent-hunter reads your project, searches for relevant skills, security-scans results, and shows the top 3 matches.

Time to results: under 30 seconds.

---

## Installation

### Step 1: Clone the Repository

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
```

This clones agent-hunter to your `.claude/skills/` directory where Claude Code looks for skills.

### Step 2: Run Setup

```bash
cd ~/.claude/skills/agent-hunter
./setup
```

This will:
1. Check that you have Python 3.10+
2. Create a local Python virtual environment
3. Install required dependencies (PyYAML, requests, rich)
4. Register agent-hunter in your global `~/.claude/CLAUDE.md`
5. Create a `~/.local/bin/agent-hunter` symlink so you can run it from anywhere

**It takes < 1 minute.**

### Step 3: Verify Installation

Run from any directory:

```bash
agent-hunter --help
```

You should see the help output. If you get "command not found", add `~/.local/bin` to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## First Use

### In Claude Code

Open **any** Claude Code session (new or existing project) and type:

```
/agent-hunter
```

Claude Code will run the hunt and show you the top 3 skills for your project.

### From the Command Line

```bash
agent-hunter hunt /path/to/your/project
```

Or in your project directory:

```bash
cd /path/to/your/project
agent-hunter hunt .
```

---

## What Happens

When you run `/agent-hunter`:

```
Found: FastAPI, PostgreSQL, pytest, Docker

Top 3 recommendations:

1. [SAFE] fastapi-backend-testing
 Your repo uses FastAPI, pytest, and Docker. Provides test and
 deployment workflow helpers.

2. [SAFE] postgres-mcp-server
 PostgreSQL detected. Provides database query and schema tools.

3. [REVIEW] api-security-scanner
 REST API security audits. Flagged for filesystem access.
 Review SKILL.md before installing.

Blocked (security): 2 results
```

Status meanings:
- [SAFE] - No security issues
- [REVIEW] - Minor flags, requires review
- [BLOCKED] - Failed security scan, not shown

---

## Installing Recommended Skills

If you want to install a recommended skill:

```bash
cd ~/.claude/skills
git clone https://github.com/owner/skill-name
```

Then restart Claude Code and the new skill will be available.

**Important:** We never auto-install. You always decide what to install.

---

## Brownfield Projects (Existing Codebases)

**agent-hunter is for any project-new or existing.**

If you have an existing codebase, run agent-hunter to discover skills that enhance your current work:

```bash
cd /path/to/existing/project
agent-hunter hunt .
```

**Examples of brownfield value:**

- **Refactoring:** Hunt for skills that help refactor your architecture
- **Performance:** Hunt for profiling/optimization skills for your stack
- **Testing:** Hunt for testing frameworks and tools
- **Deployment:** Hunt for deployment and CI/CD skills
- **Security:** Hunt for security scanning and hardening skills
- **Documentation:** Hunt for documentation and code analysis skills

**Result:** Discover skills you didn't know existed to accelerate your existing work.

---

## Proactive Mode (Optional)

By default, agent-hunter runs when you ask (`/agent-hunter`). To make it **automatically activate on new projects**:

```bash
export AGENT_HUNTER_AUTO=1
```

Add this line to your `~/.zshrc` or `~/.bash_profile` to make it permanent.

With proactive mode enabled:
- Runs automatically when opening a new project
- Shows top 3 skills without requiring explicit request
- One hunt per session per project
- Can still run `/agent-hunter` manually anytime

---

## GitHub Token (Optional but Recommended)

agent-hunter works **without** a token using the curated index (100+ verified skills).

To enable **GitHub API search** (discovers 5,000+ more skills):

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

Generate a token at https://github.com/settings/tokens (no scopes needed).

**Coverage:**
- **Without token**: ~100 verified skills (curated index) + web search
- **With token**: All 3 tiers - verified + GitHub search + web search

---

## Other Commands

### Audit Installed Skills

Check all installed skills for security issues:

```bash
agent-hunter audit
# or
/agent-hunter audit
```

### Rollback to Last Good State

Restore your skills registry to the previous snapshot (before last audit/update):

```bash
agent-hunter rollback
# or
/agent-hunter rollback
```

---

## Troubleshooting

### `/agent-hunter` command not found

**Check 1:** Verify setup completed

```bash
ls ~/.claude/skills/agent-hunter/
```

**Check 2:** Reload your shell

```bash
source ~/.zshrc # or ~/.bash_profile
```

**Check 3:** Verify `~/.local/bin` is in PATH

```bash
echo $PATH | grep -o "$HOME/.local/bin"
```

If not, add it:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### No results found

**Possible reasons:**

1. **GitHub rate limit hit** - GitHub API resets every hour
 - Set `GITHUB_TOKEN` for higher quota
 - Or try again in an hour

2. **Your stack is very niche** - Less likely to have existing skills
 - Check the detected tech stack
 - Try again and agent-hunter will offer web search for broader discovery

3. **Detection missed your stack** - Tech keywords weren't detected correctly
 - Check what was detected in the output
 - File an issue on GitHub if detection is wrong

### Security warning on a skill ([REVIEW])

Yellow flags usually indicate minor patterns like:
- Filesystem access (common for file manipulation skills)
- Network calls (common for API skills)
- Code modification (expected for refactoring tools)

**What to do:**
1. Read the SKILL.md from the recommended repo
2. Decide if the pattern fits your use case
3. Install manually if you're comfortable with it

---

## Privacy & Security

Collected:
- Framework names (FastAPI, React, Django)
- Library names (pytest, numpy, tailwindcss)
- Tool names (Docker, PostgreSQL, Redis)

Not collected:
- File paths
- Variable or function names
- Code content
- Project names
- Commit messages
- Secrets or sensitive data

Security measures:
- All results scanned before showing
- Failed scans (RED) blocked entirely
- No telemetry sent

---

## Next Steps

1. **Already installed?** Type `/agent-hunter` in any Claude Code session
2. **Want proactive mode?** `export AGENT_HUNTER_AUTO=1`
3. **Want broader discovery?** Set `GITHUB_TOKEN` for GitHub API access
4. **Questions?** See [INSTALL.md](./INSTALL.md) for detailed setup, or [README.md](./README.md) for overview

---

## Learning More

| Document | Purpose |
|----------|---------|
| [README.md](./README.md) | Overview, quick start, why agent-hunter exists |
| [INSTALL.md](./INSTALL.md) | Detailed setup, proactive mode, troubleshooting |
| [SKILL.md](./SKILL.md) | Complete workflow reference (for Claude) |
| [DISTRIBUTION.md](./DISTRIBUTION.md) | How to package and distribute agent-hunter |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Privacy, security, how to contribute |

---

## Questions or Issues?

- [Issue] **Found a bug?** [GitHub Issues](https://github.com/indhra/agent-hunter/issues)
- 💬 **Have a question?** [GitHub Discussions](https://github.com/indhra/agent-hunter/discussions)
- **Want to contribute?** See [CONTRIBUTING.md](./CONTRIBUTING.md)

---

****

Happy hunting!

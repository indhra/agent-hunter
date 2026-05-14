# Installation & Setup Guide

**agent-hunter** is a Claude Code SKILL that discovers and ranks the best skills and MCP servers for your projects.

> **New to Claude Code?** agent-hunter is designed as a first-install skill. Install it right after Claude Code itself.

---

## Installation (One-Time)

### Step 1: Clone to your skills directory

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
```

### Step 2: Run setup

```bash
./setup
```

The setup script will:
- ✅ Check Python 3.10+
- ✅ Create a local virtual environment
- ✅ Install dependencies (PyYAML, requests, rich)
- ✅ Register `/agent-hunter` in your global `~/.claude/CLAUDE.md`
- ✅ Symlink sub-skills
- ✅ Create `~/.local/bin/agent-hunter` for CLI access

**That's it.** `/agent-hunter` is now available in every Claude Code session.

---

## First Use

Open **any** Claude Code session (brand new project or existing repo) and type:

```
/agent-hunter
```

Or ask Claude directly:
```
What skills or tools should I install for this project?
```

agent-hunter will automatically:
1. Read your project's tech stack (framework names only, no code)
2. Hunt curated skills + GitHub results
3. Security-scan every result
4. Show top 3 recommendations
5. Guide you through installation if useful

---

## Proactive Mode (Optional)

By default, agent-hunter runs when you call `/agent-hunter` or ask Claude. To make it **automatically activate** when you start work on a new project:

### Enable Proactive Hunting

Add this to your project's `.claude/settings.json`:

```json
{
  "autoActivateSkills": ["agent-hunter"],
  "onSessionStart": {
    "if": "currentProject !== lastProject",
    "then": "/agent-hunter"
  }
}
```

**What this does:**
- Detects when you open a new project (by comparing current directory path with last session)
- Automatically runs `/agent-hunter` on session start
- Shows top 3 recommendations without waiting for you to ask

### Or Use Environment Variable

For team-wide activation, add to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export AGENT_HUNTER_AUTO=1
```

Then in Claude Code, agent-hunter will auto-run once per session per unique project path.

---

## GitHub Token Setup (Recommended for Brownfield Projects)

### For Existing/Brownfield Projects: Set GitHub Token

If you're hunting on **existing projects** (not just new ones), GitHub token is **highly recommended**:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

Generate at https://github.com/settings/tokens (no scopes needed, public access only).

**Make permanent:**
```bash
echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

### Why Token for Brownfield?

Brownfield projects have very specific needs. With GitHub token:
- ✅ Searches 5,000+ skill repositories
- ✅ Finds niche tools for refactoring, optimization, testing
- ✅ Better matches for "existing project enhancement"
- ✅ Avoids GitHub API rate limit hits

### Coverage Comparison

| Tier | Token? | Coverage | Speed | Best For |
|---|---|---|---|---|
| **Tier 1 (Curated)** | ❌ No | ~100 verified | Instant | Quick, trusted skills |
| **Tier 2 (GitHub)** | ✅ Yes | 5,000+ repos | 2-5 sec | **Brownfield work** |
| **Tier 3 (Web)** | - | Unlimited | 5-15 sec | Novel discoveries |

**Recommendation:**
- **Without token**: Works fine, uses verified index + web search
- **With token** (recommended): Full access to all 5,000+ GitHub skills, best for brownfield projects

---

## Commands

### Main Hunt

```bash
/agent-hunter
# or
agent-hunter hunt .
```

Discovers the top 3 skills/MCPs relevant to your current project.

### Audit Installed Skills

```bash
/agent-hunter audit
# or
agent-hunter audit
```

Checks all installed skills for:
- Security issues
- Tampering (SHA mismatch)
- Dependency conflicts

### Rollback to Previous State

```bash
/agent-hunter rollback
# or
agent-hunter rollback
```

Restores your skill registry to the last known good snapshot (created before the last audit/update).

---

## Configuration

### Environment Variables

```bash
# Enable automatic hunting on new projects
export AGENT_HUNTER_AUTO=1

# GitHub API access (for broader discovery)
export GITHUB_TOKEN=ghp_...

# Debug output
export DEBUG=1
```

### Project-Level Config

Create or edit `.claude/CLAUDE.md` in your project:

```markdown
## agent-hunter

Proactively discover, security-scan, and install SKILL.md files and MCP servers
relevant to this project. Invoke /agent-hunter when:
- Starting a new feature that might have existing tools
- Asking "what should I install"
- Need to audit installed skills

Available skills: /agent-hunter, /agent-hunter-update
```

Then add to `.claude/settings.json`:

```json
{
  "autoActivateSkills": ["agent-hunter"],
  "proactiveTriggers": {
    "newProject": true,
    "beforeFeatureBuild": true
  }
}
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
source ~/.zshrc  # or ~/.bash_profile
```

**Check 3:** Verify global CLAUDE.md
```bash
grep -i "agent-hunter" ~/.claude/CLAUDE.md
```

### No results found

**Reason 1:** GitHub rate limit hit
- Set `GITHUB_TOKEN` for higher quota

**Reason 2:** Tech stack not detected
- Try again and agent-hunter will show what was detected
- File an issue if detection is missing for your stack

**Reason 3:** Your stack is very niche
- Use web search: agent-hunter will offer to search broader when < 3 results

### Security warning on a skill

If agent-hunter flags a skill as 🟡 (review before installing):
1. Read the SKILL.md file from the recommended repo
2. Check the flagged patterns (usually filesystem access, network calls)
3. Decide if it fits your use case
4. Install manually if appropriate

RED (🔴) flagged skills are never shown — they're blocked entirely.

---

## Update & Uninstall

### Update to Latest

```bash
cd ~/.claude/skills/agent-hunter && git pull && ./setup
```

### Uninstall

```bash
rm -rf ~/.claude/skills/agent-hunter
```

Then remove the `## agent-hunter` section from `~/.claude/CLAUDE.md`.

---

## Privacy & Security

✅ **Only tech keywords** (framework names, library names) are extracted
✅ **No code, no paths, no secrets** ever leave your machine
✅ **All results security-scanned** before showing
✅ **RED results blocked entirely** — never shown to you

See [CONTRIBUTING.md](./CONTRIBUTING.md#privacy) for full details.

---

## Next Steps

1. **Install:** `~/.claude/skills/agent-hunter && ./setup`
2. **First hunt:** Open a project and type `/agent-hunter`
3. **Token (optional):** Set `GITHUB_TOKEN` for broader discovery
4. **Proactive (optional):** Enable `AGENT_HUNTER_AUTO=1` for auto-activation

**Questions?**
- 🐛 [GitHub Issues](https://github.com/indhra/agent-hunter/issues)
- 💬 [Discussions](https://github.com/indhra/agent-hunter/discussions)

---

**Built to save time and block the bad stuff.**

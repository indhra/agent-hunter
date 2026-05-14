# agent-hunter Project Configuration

This file shows how agent-hunter integrates into this project and can be used as a template for other projects.

---

## About agent-hunter

**agent-hunter** is a Claude Code SKILL that:
- Discovers relevant skills and MCP servers for your project
- Security-scans every result before showing it
- Shows top 3 recommendations with clear explanations
- Works across all three discovery tiers (curated index, GitHub API, web search)

**It's designed to be the first skill you install** after Claude Code itself.

---

## When to Use agent-hunter

Invoke `/agent-hunter` when:
- Starting a new project and wondering "what tools should I use?"
- Asking "what skills exist for my tech stack?"
- Before building something that might already exist as a skill/MCP
- You want to audit installed skills for security/tampering
- You need to discover MCP servers for your project

**Maximum 1 automatic hunt per session** to save tokens and avoid redundant searches.

---

## Usage

### Main Hunt (Find Top 3 Skills)

```
/agent-hunter
```

or from the command line:

```bash
agent-hunter hunt .
```

Shows top 3 skills/MCPs ranked by relevance to your project.

### Audit Installed Skills

```
/agent-hunter audit
```

or:

```bash
agent-hunter audit
```

Checks all installed skills for security issues, tampering, and dependency conflicts.

### Rollback to Last Good State

```
/agent-hunter rollback
```

Restores your skill registry to the last snapshot (created before the previous audit/update).

---

## Configuration for This Project

### Environment Variables

Set in your shell or `.env`:

```bash
# Optional: Enable GitHub API search (5000+ skills)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Optional: Enable automatic hunting on new projects
export AGENT_HUNTER_AUTO=1

# Optional: Show debug output
export DEBUG=1
```

See [INSTALL.md](../INSTALL.md) for detailed setup.

### Claude Code Settings

In `.claude/settings.json`, you can configure:

```json
{
  "autoActivateSkills": ["agent-hunter"],
  "proactiveTriggers": {
    "newProject": true,
    "beforeFeatureBuild": false
  }
}
```

---

## Session Behavior

**Guard:** `AGENT_HUNTER_RAN`

agent-hunter uses a session guard to prevent multiple automatic hunts in one session:

- ✅ First `/agent-hunter` call in a session → runs hunt
- ✅ User explicitly requests another hunt → runs hunt
- ⏭️ Automatic hunt requested but guard is set → skipped silently

This prevents token waste and redundant searches while still allowing explicit re-runs.

---

## Discovery Modes

agent-hunter uses a **three-tier discovery system**:

### Tier 1: Curated Index (Always Active)
- **Speed:** Instant (offline)
- **Coverage:** ~100 verified, human-reviewed skills
- **Trust:** Highest
- **Setup:** None needed

### Tier 2: GitHub API (Optional, Requires GITHUB_TOKEN)
- **Speed:** 2-5 seconds
- **Coverage:** 5,000+ repositories with SKILL.md
- **Trust:** Medium (automated filtering)
- **Setup:** `export GITHUB_TOKEN=...`

### Tier 3: LLM Web Search (On-Demand)
- **Speed:** 5-15 seconds
- **Coverage:** Unlimited (discovers novel skills, MCPs, marketplaces)
- **Trust:** Variable (security-scanned before showing)
- **Activation:** User prompt or auto-trigger when < 3 results

---

## How Results Are Ranked

Results are scored on 4 signals:

```
score = (
  stack_match   × 0.40   # Does it match my tech stack?
  trust_score   × 0.30   # Is it safe? (security scan)
  recency_score × 0.15   # Is it maintained?
  star_score    × 0.15   # Is it popular?
) × yagni_multiplier
```

**YAGNI multiplier** (penalizes dormant projects):
- Active (commits < 7d): 2.0×
- Recent (commits < 30d): 1.0×
- Dormant (commits > 90d): 0.5×

---

## Privacy & Security

✅ **Only tech keywords extracted** (framework names, library names)
✅ **No code, no paths, no secrets** ever leave your machine
✅ **All results security-scanned** before showing
✅ **RED results blocked entirely** — never shown

---

## Team Sharing

To enable agent-hunter for your entire team:

1. **Commit this file** (`.claude/CLAUDE.md`) to your repo
2. **Set environment variables** in your team's `.env` or CI/CD
3. **Document in README** that team members should install agent-hunter globally first

Example README section:

```markdown
### Setup (First Time)

1. Install agent-hunter (required):
   ```bash
   git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
   cd ~/.claude/skills/agent-hunter && ./setup
   ```

2. (Optional) Set GitHub token for broader discovery:
   ```bash
   export GITHUB_TOKEN=your_token
   ```

3. Open this repo in Claude Code and type:
   ```
   /agent-hunter
   ```
```

---

## Troubleshooting

**Q: No results found**
A: This means your stack is very niche or GitHub rate limit was hit. Set `GITHUB_TOKEN` for higher quota, or ask agent-hunter to search web for broader discovery.

**Q: What if I see a 🟡 (Review Before Installing) result?**
A: Read the SKILL.md file from the recommended repo. Usually it has minor security flags that are safe for your use case. Decide if you want to install.

**Q: /agent-hunter command not found**
A: Run the setup script again: `~/.claude/skills/agent-hunter/setup`

---

## Learning More

- **[INSTALL.md](../INSTALL.md)** — Detailed installation and proactive mode setup
- **[SKILL.md](../SKILL.md)** — Complete skill workflow and constraints
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Privacy, security, contribution guidelines
- **[README.md](../README.md)** — Overview and quick start

---

**Built to save time and block the bad stuff.**

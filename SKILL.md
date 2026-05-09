---
name: "agent-hunter"
description: "Repo-aware skill package manager for Claude Code. Reads your project context, finds the best skills and MCPs for it, explains why they fit, and blocks risky ones."
version: "1.0.0-alpha"
license: "MIT"
author: "Indhra Kiranu N A"
compatibility:
  claude: ">=1.0.0"
triggers:
  - "hunt for skills"
  - "find relevant skills"
  - "what skills exist for this project"
  - "what skills should I install"
  - "are there any skills I should install"
  - "agent-hunter hunt"
  - "agent-hunter audit"
  - "agent-hunter rollback"
mcp_dependencies: []
---

# agent-hunter

**Repo-aware skill package manager for Claude Code.**

Given your repo, tells you the top 3 skills or MCPs you should use now, why they fit, and which ones to avoid.
Security-scans every result. Never installs without confirmation.

---

## When to Use

Use agent-hunter when:
- Starting a new project and deciding what tools to install
- User asks "what skills should I install for this?"
- Before building a feature that might already exist as a skill/MCP
- User mentions exploring or discovering skills

**Maximum 1 automatic hunt per session** (loop guard below).

---

## Session Loop Guard

**CRITICAL — CHECK THIS FIRST:**

Check if `AGENT_HUNTER_RAN` is set in this session:

- **Already set to `true`**: Do NOT run another automatic hunt. If user explicitly requests it, proceed. Otherwise skip silently.
- **Not set**: Proceed with hunt, then set `AGENT_HUNTER_RAN = true`

This prevents infinite loops and token waste.

---

## Privacy Contract

**You may ONLY extract tech keywords from the user's project.**

**ALLOWED:**
- Framework names (FastAPI, React, Django)
- Library names (pytest, numpy, tailwindcss)
- Tool names (Docker, PostgreSQL, Redis)

**NEVER extract:**
- File paths
- Variable names, function names, class names
- Commit message text
- Repository name
- Any project-specific strings

Before extracting context:
> "I'll read your project files to identify your tech stack. Only framework/library names will be used — no file paths, variable names, or project-specific code."

After extraction, SHOW the user the tech signals:
> "Found: FastAPI, PostgreSQL, pytest, Docker"
>
> "Does this look right? I'll use these to hunt for relevant skills."

---

## The Hunt Workflow

### Step 1: Run the Hunt

```bash
agent-hunter hunt .
```

This command:
1. Extracts tech stack from project files (privacy-safe)
2. Searches curated index + GitHub (if GITHUB_TOKEN set)
3. Security-scans every result
4. Ranks by relevance to your project
5. Shows top 3 recommendations

### Step 2: Review Results

The hunt prints a report like this:

```
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

### Trust Signals

- 🟢 **Safe to install** — Verified or clean security scan
- 🟡 **Review before installing** — Minor security flags, user should review
- 🔴 **Blocked** — Failed security scan, not shown to user

**RED results are NEVER shown.** Only counted.

### Step 3: Explain Each Recommendation

For each result in the top 3, provide ONE specific sentence explaining why it fits this project.

**Good:**
> "Ranked #1 because your project uses FastAPI and PostgreSQL, and this skill handles exactly the migration workflow you need."

**Bad:**
> "This is a good skill for Python projects."

Reference something specific from the user's context.

### Step 4: Install (If User Confirms)

If the user wants to install any recommended skills, guide them:

```bash
# For each skill they want:
cd ~/.claude/skills && git clone https://github.com/owner/skill-name
```

Or use the suggested command from the hunt report.

**Never auto-install.** User must confirm first.

---

## Audit Command

Run when user says "audit installed skills" or "check skill health":

```bash
agent-hunter audit
```

This command:
1. Creates a pre-audit snapshot (for rollback)
2. Checks all installed skills for:
   - Security issues
   - Tamper detection (SHA mismatch)
   - Dependency conflicts
3. Reports health status

Show the results in a table:

```
Skill Health Check:

🟢 skill-a          Healthy
🟢 skill-b          Healthy
🟡 skill-c          Warning: SHA mismatch (may have been modified)
🔴 skill-d          BLOCKED: Security scan failed

Recommendation: Disable skill-d immediately
```

For any 🔴 or 🟡 issues:
- Explain what was detected
- Recommend action (disable, rollback, review)
- Show the command to fix it

---

## Rollback Command

Run when audit detects tampered skills or user wants to restore previous state:

```bash
agent-hunter rollback
```

This restores the registry to the last known good snapshot (created before audit/update).

**Always confirm with user before rolling back:**
> "This will restore your skill registry to the state before the last audit/update. Continue? [y/N]"

---

## If No Results Found

If hunt returns 0 results:

1. Explain why:
   > "No results found. This could mean:
   > - Your stack is very specialized
   > - GitHub rate limit hit (set GITHUB_TOKEN for more quota)
   > - Tech keywords weren't detected correctly"

2. Show what was detected:
   > "I detected: [tech signals]"

3. Suggest next steps:
   > "You can manually search GitHub for 'filename:SKILL.md <your-tech>' or build something new."

---

## GitHub Token (Optional)

For broader discovery beyond the curated index:

```bash
export GITHUB_TOKEN=your_token_here
```

Generate at https://github.com/settings/tokens (no scopes needed).

Without a token, agent-hunter only searches the curated verified skills index.

---

## Error Handling

| Error | Action |
|---|---|
| GitHub API 401 | Tell user to set GITHUB_TOKEN |
| GitHub API 429 (rate limit) | Wait 60s, retry once, then fail gracefully |
| GitHub API 503 | Tell user GitHub is down, try later |
| Context extraction fails | Continue with empty context, explain what's missing |
| Security scan fails on a result | Skip that result silently |
| Registry corrupt | Offer to reset registry |
| `AGENT_HUNTER_RAN` already set | Skip automatic hunt silently |

**Never show partial/unscanned results.** Fail clearly instead.

---

## Core Constraints

1. **No auto-install.** Show the command, user runs it.
2. **No LLM calls from Python scripts.** All reasoning happens in this SKILL.md.
3. **Top 3 focus.** Show best 3 by default, not 5-10.
4. **Privacy first.** Only tech keywords, never code or paths.
5. **Security first.** RED results are not shown, period.
6. **Human in the loop.** Every action requires user confirmation.
7. **Fail loudly.** Clear error messages, not silent failures.

---

## Scoring (For Reference)

Results are ranked by 4 signals:

```
total_score = (
    stack_match   × 0.40   # Does it match my tech stack?
  + trust_score   × 0.30   # Is it safe?
  + recency_score × 0.15   # Is it maintained?
  + star_score    × 0.15   # Is it popular?
) × yagni_multiplier
```

**YAGNI multiplier:**
- Active (commits <7d): 2.0×
- Recent (commits <30d): 1.0×
- Dormant (commits >90d): 0.5×

**Trust tiers:**
- Verified: 1.0 (in curated index)
- Community: 0.7 (GitHub, >50 stars)
- Raw: 0.4 (GitHub, new/unknown)

This is handled automatically by the Python scripts. You don't need to calculate scores manually.

---

## Commands Summary

```bash
# Main command — hunt for relevant skills/MCPs
agent-hunter hunt .

# Health check — audit all installed skills
agent-hunter audit

# Restore — rollback to last known good state
agent-hunter rollback
```

That's it. Three commands. Stay focused on the core value: **top 3 recommendations that save time and block bad stuff.**

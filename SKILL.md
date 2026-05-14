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

## Installation & Proactive Mode

### First-Time Installation

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter && ./setup
```

The setup script:
- Checks Python 3.10+
- Installs dependencies into local venv
- Registers `/agent-hunter` in global `~/.claude/CLAUDE.md`
- Symlinks sub-skills
- Creates `~/.local/bin/agent-hunter` for CLI access

After setup, `/agent-hunter` works in every Claude Code session.

### Proactive Activation (Optional)

To make agent-hunter **automatically hunt for skills when you start a new project**:

**Option 1: Environment Variable**
```bash
export AGENT_HUNTER_AUTO=1
```

**Option 2: Claude Code Settings**
Add to `.claude/settings.json`:
```json
{
 "autoActivateSkills": ["agent-hunter"],
 "onSessionStart": {
 "if": "projectChanged",
 "then": "/agent-hunter"
 }
}
```

With proactive mode enabled:
- [YES] When you open a new project → agent-hunter automatically runs
- [YES] Top 3 skills surface without waiting for you to ask
- [YES] One hunt per session per project (guard prevents redundant runs)

See [INSTALL.md](./INSTALL.md) for full setup details.

---

## When to Use

Use agent-hunter when:

**New Projects:**
- Starting fresh and deciding what tools to install
- Want top 3 skill recommendations before building

**Existing / Brownfield Projects:**
- **IMPORTANT:** You can use agent-hunter on ANY existing project to discover skills that enhance your current work
- Already have a codebase? Hunt for skills that complement your tech stack
- Refactoring? Hunt for skills that help the refactor
- Adding features? Hunt for skills that accelerate feature development
- Performance issues? Hunt for skills that profile/optimize your stack

**Any Time:**
- User asks "what skills should I install for this?"
- Before building a feature that might already exist as a skill/MCP
- User mentions exploring or discovering skills
- **Proactive mode**: automatically on new projects (if enabled)

**Maximum 1 automatic hunt per session** (loop guard below).

---

## Session Loop Guard

**CRITICAL - CHECK THIS FIRST:**

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
> "I'll read your project files to identify your tech stack. Only framework/library names will be used - no file paths, variable names, or project-specific code."

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
 Found: FastAPI, PostgreSQL, pytest, Docker

Top 3 recommendations:

1. [SAFE] fastapi-backend-testing
 Safe to install.
 Why: Your repo uses FastAPI, pytest, and Docker. This skill targets
 backend test and deployment workflows directly.

2. [SAFE] postgres-mcp-server
 Safe to install.
 Why: Your project connects to PostgreSQL. This MCP gives Claude direct
 database query and schema inspection tools.

3. [REVIEW] api-security-scanner
 Review before installing.
 Why: Useful for REST API security audits, but flagged for filesystem
 access patterns. Review SKILL.md before proceeding.

[BLOCKED] 2 results blocked (security scan)
```

### Trust Signals

- [SAFE] **Safe to install** - Verified or clean security scan
- [REVIEW] **Review before installing** - Minor security flags, user should review
- [BLOCKED] **Blocked** - Failed security scan, not shown to user

**RED results are NEVER shown.** Only counted.

### Step 2.5: Web Search Enrichment (Optional)

**Three-tier discovery system:**

```
Tier 1: Curated Index (always runs, instant, verified)
 ↓
Tier 2: GitHub API (runs if GITHUB_TOKEN set)
 ↓
Tier 3: LLM Web Search (optional enrichment)
```

**Activate web search when:**
1. User explicitly requests: "find more", "search broader", "web search"
2. Auto-trigger if initial results < 3 skills
3. User asks about discovery beyond GitHub

**When to offer web search:**

After showing initial hunt results, assess:
- If **3+ good results** ([SAFE] or [REVIEW]): Continue to Step 3, don't offer web search
- If **< 3 results** OR user seems unsatisfied: Offer web search

**Offer prompt:**
> "Found {N} skills from curated index + GitHub. Want to search broader?
>
> Web search can discover 5000+ MCP servers and community skills not in GitHub's index.
>
> Search now? [y/n/auto]"

**If user says yes or auto (when < 3 results):**

1. **Construct search query:**
 ```
 "GitHub SKILL.md {tech_stack} {domain} development agent skills 2026"

 Examples:
 - "GitHub SKILL.md FastAPI Python REST API development agent skills 2026"
 - "GitHub SKILL.md React TypeScript frontend development agent skills 2026"
 - "GitHub SKILL.md Django PostgreSQL backend development MCP 2026"
 ```

2. **Execute web search** using `vscode-websearchforcopilot_webSearch` tool

3. **Parse results for:**
 - GitHub repository URLs (github.com/owner/repo)
 - SKILL.md file references
 - MCP server mentions
 - Skill marketplace links (Smithery, Agensi.io, MCP Market, etc.)

4. **Extract candidate repos:**
 - Filter for GitHub URLs only
 - Remove duplicates already in hunt results
 - Limit to top 5 new discoveries

5. **For each new repo:**
 - Attempt to fetch SKILL.md from standard locations:
 - `/SKILL.md`
 - `/.claude/skills/*/SKILL.md`
 - `/skills/*/SKILL.md`
 - If found: Add to candidates for security scan
 - If marketplace link: Note as reference for user

6. **Security scan** new discoveries (same as GitHub results)
 - Run through security_scan.py
 - Block RED results
 - Flag YELLOW for review

7. **Merge and re-rank:**
 - Combine web search results with initial hunt results
 - Re-run scorer.py on combined set
 - Show updated top 3

8. **Show updated report:**
 ```
 Web search found 3 additional skills:

 Top 3 recommendations (updated):

 1. [SAFE] fastapi-official-skill (NEW - web search)
 Safe to install.
 Why: Official FastAPI skill from fastapi/fastapi repo
 Source: Web search

 2. [SAFE] postgres-mcp-server
 Safe to install.
 Why: [original explanation]
 Source: Curated index

 3. [SAFE] fastapi-ddd-pattern (NEW - web search)
 Safe to install.
 Why: Domain-driven design patterns for FastAPI
 Source: Web search via github.com/iktakahiro
 ```

**If web search fails:**
> "Web search timed out or returned no results. Continuing with {N} skills from curated index + GitHub."

**Performance notes:**
- Web search typically takes 5-15 seconds
- Show progress: " Searching web for additional skills..."
- Timeout after 30 seconds
- Cache results in session to avoid duplicate searches

**Marketplace references:**
If web search finds skill marketplaces (Agensi.io, Smithery, MCP Market), mention them:
> " Also found these skill marketplaces you can browse manually:
> - Smithery: https://smithery.ai/
> - Agensi: https://agensi.io/
> - MCP Market: https://mcpmarket.com/"

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

[SAFE] skill-a Healthy
[SAFE] skill-b Healthy
[REVIEW] skill-c Warning: SHA mismatch (may have been modified)
[BLOCKED] skill-d BLOCKED: Security scan failed

Recommendation: Disable skill-d immediately
```

For any [BLOCKED] or [REVIEW] issues:
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

## Discovery Modes

agent-hunter uses a **three-tier discovery system** for maximum coverage:

### Tier 1: Curated Index (Always Active)
- **Source:** `references/VERIFIED_SKILLS.md`
- **Count:** ~100 verified, security-scanned skills
- **Speed:** Instant (offline)
- **Trust:** Highest (human-reviewed)
- **No setup needed**

### Tier 2: GitHub API Search (Optional)
- **Source:** GitHub Code Search API
- **Count:** 5,000+ repositories with SKILL.md
- **Speed:** 2-5 seconds
- **Trust:** Medium (automated filtering)
- **Setup:** Requires GITHUB_TOKEN

To enable Tier 2:
```bash
export GITHUB_TOKEN=your_token_here
```

Generate at https://github.com/settings/tokens (no scopes needed).

### Tier 3: LLM Web Search (On-Demand)
- **Source:** Web search across GitHub, marketplaces, documentation
- **Count:** Unlimited (discovers novel skills)
- **Speed:** 5-15 seconds
- **Trust:** Variable (security-scanned before showing)
- **Activation:** User prompt or auto-trigger when < 3 results

**Recommended setup:**
- Casual use: Tier 1 only (no token needed)
- Active development: Tier 1 + 2 (set GITHUB_TOKEN)
- Exploration: All 3 tiers (web search on demand)

---

## Error Handling

| Error | Action |
|---|---|
| GitHub API 401 | Tell user to set GITHUB_TOKEN for Tier 2 discovery |
| GitHub API 429 (rate limit) | Wait 60s, retry once, then fall back to Tier 1 + 3 |
| GitHub API 503 | Tell user GitHub is down, offer Tier 3 (web search) |
| Web search timeout | Continue with Tier 1 + 2 results, explain timeout |
| Web search no results | Continue with Tier 1 + 2 results |
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
 stack_match × 0.40 # Does it match my tech stack?
 + trust_score × 0.30 # Is it safe?
 + recency_score × 0.15 # Is it maintained?
 + star_score × 0.15 # Is it popular?
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
# Main command - hunt for relevant skills/MCPs
agent-hunter hunt .

# Health check - audit all installed skills
agent-hunter audit

# Restore - rollback to last known good state
agent-hunter rollback
```

 Three commands. Stay focused on the core value: **top 3 recommendations that save time and block bad stuff.**

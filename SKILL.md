---
name: "agent-hunter"
description: "Proactively hunts for relevant, security-vetted SKILL.md files and MCP servers that match the current project's tech stack. Prevents reinventing existing tools. The immune system of an AI agentic system."
version: "0.1.0"
license: "MIT"
author: "indhra"
compatibility:
  claude: ">=1.0.0"
triggers:
  - "hunt for skills"
  - "find relevant skills"
  - "what skills exist for this project"
  - "are there any skills I should install"
  - "agent-hunter hunt"
  - "agent-hunter audit"
  - "agent-hunter rollback"
  - "agent-hunter context"
  - "agent-hunter scaffold"
  - "agent-hunter update"
mcp_dependencies: []
---

# agent-hunter

**The immune system of your AI agentic system.**
Finds proven skills and MCP servers that match what you're actually building.
Security-scans every result before showing it. Never installs without your confirmation.

---

## Session Loop Guard

**CRITICAL — READ FIRST:**

Before doing anything, check whether `AGENT_HUNTER_RAN` is set in this session.

If it is already set to `true`:
- Do NOT run another automatic hunt.
- If the user explicitly asked for a hunt (typed a trigger phrase), run it.
- If this is a background proactive trigger, skip silently.

If it is NOT set:
- Proceed with the hunt below.
- Set `AGENT_HUNTER_RAN = true` after completing.

Maximum 1 automatic hunt per session. This prevents infinite loops and token waste.

---

## Privacy Contract — Read Before Extracting Any Context

You may ONLY extract and transmit the following from the user's project:

**ALLOWED:** Framework names, library names, tool names from the explicit tech allowlist
(e.g. "fastapi", "postgres", "react"). These are tech signal keywords only.

**NEVER ALLOWED:**
- File paths
- Variable names, function names, class names
- Commit message text (extract tech keywords only, not the message itself)
- Repository name
- Project-specific strings of any kind
- Anything that could identify the user's specific project or code

Before running context extraction, tell the user:
> "I'll read your project files to identify your tech stack. Only framework/library names
> will be used — no file paths, variable names, or project-specific code."

After extraction, SHOW the user the extracted signals and confirm before proceeding:
> "Found these tech signals: [list]. Does this look right? I'll use these to hunt for relevant skills."

---

## Step 1 — Extract Project Context

Run:
```bash
python scripts/context_extractor.py .
```

This reads: `CLAUDE.md`, `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `git log --oneline -50`.

The script prints extracted signals to stdout. Show them to the user.

If context extraction fails (no supported files found), tell the user:
> "I couldn't find dependency files or CLAUDE.md. I'll do a broader hunt based on what I can
> observe from our current session."

---

## Step 2 — Hunt for Skills and MCP Servers

Run:
```bash
python scripts/hunter.py .
```

This queries GitHub Search API for SKILL.md files and MCP server configs matching your tech stack.

**If GITHUB_TOKEN is not set**, warn the user:
> "No GITHUB_TOKEN found. Hunting without authentication: limited to 60 requests/hour.
> Set GITHUB_TOKEN for 5,000 requests/hour:
> export GITHUB_TOKEN=your_token_here"

**Trust tier order (consult in this order):**
1. **Verified** — entries in `references/VERIFIED_SKILLS.md`. Show as `[VERIFIED]`.
2. **Community-reviewed** — coming in v0.2.1. Show as `[COMMUNITY]`.
3. **Raw GitHub** — unvetted search results. Show as `[RAW]`. Apply higher scrutiny.

---

## Step 3 — Security Scan Every Result

**Non-negotiable: NEVER show a result without scanning it first.**

For each result from Step 2:

```bash
python scripts/security_scan.py <path_to_SKILL.md>
```

Or, if you have the raw content, pass it directly to `scan_skill()`.

**Severity rules (hard):**
- 🔴 **RED** — EXCLUDE from results entirely. Count only. Do not show the skill.
  Tell the user at the bottom of the report: "N result(s) were blocked by security scan."
- 🟡 **YELLOW** — INCLUDE with a prominent warning. Explain what was flagged. Let user decide.
- 🟢 **GREEN** — Include normally.

**Never rationalize showing a RED result.** If the security scan says RED, it does not appear
in the results, no matter how relevant it seems. Full stop.

---

## Step 4 — Score and Rank

For each result that passed security scan (GREEN or YELLOW only):

The scoring is handled by `scripts/scorer.py`. The key formula:

```
total_score = (
    stack_match  × 0.30
  + domain_match × 0.20
  + star_score   × 0.15
  + recency      × 0.15
  + trust_score  × 0.20
) × yagni_multiplier
```

YAGNI multiplier:
- Tech area with commits in last 7 days → 2.0×
- Tech area with commits in last 30 days → 1.0×
- Tech area dormant for 90+ days → 0.5×

Trust score: verified=1.0, community=0.7, raw=0.4

---

## Step 5 — Generate "Why This For You" Explanation

For each of the top 5–10 results, write ONE sentence explaining why this specific skill
is relevant to this specific project. Use the context profile to make it personal.

Good example: "Ranked #1 because your project actively uses FastAPI and Postgres,
this skill handles exactly the migration workflow you'll need."

Bad example: "This is a good skill for Python projects."

The explanation must reference something specific from the user's context profile.

---

## Step 6 — Render the Hunt Report

Call `scripts/reporter.py` or format the report as follows:

### Terminal format:

```
══════════════════════════════════════════════════════════════════════
  agent-hunter · Hunt Report · YYYY-MM-DD HH:MM
  Project: [project root]
══════════════════════════════════════════════════════════════════════

  RECOMMENDED SKILLS

  1. 🟢 skill-name                          [VERIFIED]
     ████████░░  0.82  · 342⭐ · github.com/owner/skill-name
     → Why this for you: [one sentence]

  2. 🟡 another-skill                       [RAW]
     ██████░░░░  0.61  · 89⭐ · github.com/owner/another-skill
     🟡 Contains eval() — review before installing
     → Why this for you: [one sentence]

  ──────────────────────────────────────────────────────────────────

  DANGEROUS INSTALLED SKILLS (flagged by security scan)

  🔴 suspicious-skill  →  will be DISABLED (renamed to _suspicious-skill)

  ──────────────────────────────────────────────────────────────────

  ⚠️  2 result(s) blocked by security scan and excluded from recommendations.
══════════════════════════════════════════════════════════════════════
```

Save the report:
```bash
python scripts/reporter.py
# saves to ~/.agent-hunter/reports/hunt_report_YYYY-MM-DD.md
```

---

## Step 7 — Build Action Summary and Ask for Confirmation

After showing the report, build the action list and ask the user to confirm ONCE before acting.

Call `scripts/installer.py build_action_list` or construct it yourself from the scan results.

**Format the action summary like this:**

```
──────────────────────────────────────────────────────────────────
  READY TO ACT — here's what I'll do:

  INSTALL  (3 skills → ~/.claude/skills/)
    ✦  skill-name        [VERIFIED · score 0.82]  owner/skill-name
    ✦  another-skill     [RAW · score 0.61]        owner/another-skill
    ✦  third-skill       [COMMUNITY · score 0.55]  owner/third-skill

  DISABLE  (1 dangerous skill — soft-disable, reversible)
    ✦  suspicious-skill  [🔴 security scan failed]

  Note: YELLOW skills are included — review the security findings
  above before confirming. You can remove any from the list.

  Proceed? [y/N] or type the numbers to exclude (e.g. "skip 2,3"):
──────────────────────────────────────────────────────────────────
```

**Rules for building the action list:**
- Include skills ranked in top N that are GREEN or YELLOW and NOT already installed
- Include DISABLE for any installed skill that returned RED in the most recent audit re-scan
- NEVER include a RED result from the hunt as an install action
- Default scope: `~/.claude/skills/` (personal, available in all Claude Code sessions)

**Wait for the user's response before proceeding to Step 8.**

If the user types `n` or `N`: stop. Tell them what commands to run manually if they change their mind.
If the user types `y` or `Y`: proceed to Step 8.
If the user excludes items (e.g. "skip 2,3"): remove those from the action list, confirm the reduced list, then proceed.

---

## Step 8 — Execute Actions

After user confirms, execute the action list:

```bash
python scripts/installer.py <action> <args>
```

For each action in sequence:
- **install**: `python scripts/installer.py install <owner> <repo> [--sha <sha>]`
- **disable**: `python scripts/installer.py disable <skill_name>`
- **rollback**: `python scripts/installer.py rollback <owner> <repo> <sha>`
- **uninstall**: `python scripts/installer.py uninstall <skill_name>` (only if user explicitly asked)

**Print each result as it completes:**
```
  ✅  install       skill-name        Installed owner/skill-name via gh skill install
  ✅  install       another-skill     Installed owner/another-skill to ~/.claude/skills/
  ✅  disable       suspicious-skill  Disabled: suspicious-skill → _suspicious-skill
  ❌  install       third-skill       git clone timed out — run manually: gh skill install owner/third-skill
```

**After all actions complete, print a summary:**
```
══════════════════════════════════════════════════════════════════════
  agent-hunter · Actions Complete
  ✅ 2 installed  ✅ 1 disabled  ❌ 1 failed
  Your skill set is now updated. Run /agent-hunter audit anytime to check health.
══════════════════════════════════════════════════════════════════════
```

**On any failure:** Do NOT stop mid-list. Complete all remaining actions. Report failures at the end. Tell the user the manual command they can run for anything that failed.

---

## Audit Command

When triggered by "agent-hunter audit" or "audit installed skills":

1. Write a pre-audit snapshot first (enables rollback):
   ```bash
   python scripts/registry.py snapshot
   ```

2. Run the audit:
   ```bash
   python scripts/audit.py
   ```

3. Show the health table. For any 🔴 issue:
   - SHA tamper → tell user to run `agent-hunter rollback` to restore
   - Security issue → advise uninstalling the affected skill
   - Conflict → show which two skills conflict and suggest resolution

---

## Rollback Command

When triggered by "agent-hunter rollback" or after a tamper flag:

```bash
python scripts/rollback.py
```

This restores the registry to the pre-audit/pre-update state.
Confirm with the user before running — show them what will be restored.

---

## Context Command

When triggered by "agent-hunter context":

```bash
python scripts/context_extractor.py .
```

Show the full ContextProfile in a readable format:
- Tech stack detected
- Domain tags inferred
- Active / recent / dormant breakdown
- Source files read

This is a transparency command — the user should be able to verify exactly what
agent-hunter knows about their project before it hunts.

---

## Scaffold Command

When triggered by "agent-hunter scaffold <name>" or when hunt returns 0 results:

1. Tell the user: "No existing skills found for your stack. I'll scaffold a stub for you."

2. Run:
   ```bash
   python scripts/scaffold.py <name> --project .
   ```

3. Show the user the generated stub and walk them through customizing it.

4. Remind them: "When you're happy with it, share it back to the community:
   open a PR to add it to references/VERIFIED_SKILLS.md so others can find it."

---

## Update Command

When triggered by "agent-hunter update":

1. Run audit first (Step 1 of audit command above).
2. For each skill with `update_available` status, show:
   - What version is installed vs. available
   - What changed (if detectable from commit messages)
   - Confirm before each update
3. Run install commands individually, one skill at a time.
4. Never batch-update without confirmation.

---

## Zero Results Handling

If the hunt returns 0 results after pre-filtering and security scan:

1. Tell the user exactly why: "No results found. This could mean:
   - Your stack is very specialized (good — less reinventing needed)
   - The tech keywords weren't specific enough
   - GitHub rate limit was hit (set GITHUB_TOKEN to increase limit)"

2. Offer to scaffold:
   "Would you like me to scaffold a SKILL.md stub for your stack?
   You'd be building something new that others will benefit from."

3. If they say yes → run scaffold command.

---

## Error Handling

| Error | What to do |
|---|---|
| GitHub API 401 | Tell user: set GITHUB_TOKEN. Show how. |
| GitHub API 429 (rate limit) | Tell user: hit rate limit. Wait 60s and retry once. |
| GitHub API 503 | Tell user: GitHub is down. Try again later. |
| context_extractor.py fails | Continue with empty context. Tell user what was missing. |
| security_scan.py fails | Skip the result — do not show an unscanned skill. |
| registry.json corrupt | Tell user: registry is corrupt, offer to reset it. |
| AGENT_HUNTER_RAN already set | Skip automatic hunt silently. |

---

## Important Constraints

1. **No auto-install.** Ever. Show the install command. User runs it.
2. **No LLM API calls from scripts.** All reasoning happens here (in this SKILL.md), not in Python.
3. **No silent failures.** If a step fails, say so. Partial results are worse than clear errors.
4. **Privacy first.** Re-read the Privacy Contract before every hunt. When in doubt, don't extract.
5. **Security first.** A RED result is not shown. Not for any reason.
6. **Human in the loop.** Every action that changes the user's environment requires explicit confirmation.

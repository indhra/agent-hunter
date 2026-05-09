# Demo Guide: agent-hunter v1.0.0-alpha

**Purpose:** Complete walkthrough of agent-hunter's three core workflows
**Duration:** ~5 minutes
**Audience:** New users, contributors, stakeholders

---

## 🎬 Demo Script

### Setup (30 seconds)

**Narration:**
> "agent-hunter is a repo-aware skill package manager for Claude Code. It finds the top 3 most relevant skills for your project by analyzing your tech stack, then security-scans every result before showing recommendations."

**Screen:**
```bash
# Start in a sample project
cd ~/projects/my-fastapi-app

# Show project structure
ls -la
# (Show typical FastAPI structure: app/, requirements.txt, etc.)
```

---

## 🔍 Workflow 1: Hunt (2 minutes)

### Demo: Find Relevant Skills

**Narration:**
> "Let's say I'm working on a FastAPI project and want to see what skills already exist before building my own helpers. I'll run agent-hunter hunt."

**Screen:**
```bash
# Run hunt command
agent-hunter hunt .

# (Wait for results to appear)
```

**Expected Output:**
```
🔍 Analyzing project context...
   Tech stack: fastapi, pydantic, uvicorn, sqlalchemy, python

🔎 Searching for relevant skills...
   Curated index: 3 matches
   GitHub: 27 matches

🔒 Security scanning 30 results...
   ✅ 28 clean
   ⚠️  2 warnings
   ❌ 0 critical (blocked)

📊 Top 3 Recommendations:

1. fastapi-crud-helper (Score: 8.2/10)
   Source: github.com/awesome-skills/fastapi-crud
   Trust: ✅ Verified
   Stack match: 95% | Updated: 2 weeks ago | ⭐ 342

2. pydantic-validator-collection (Score: 7.8/10)
   Source: github.com/validators/pydantic-extra
   Trust: 🟡 Community
   Stack match: 88% | Updated: 1 month ago | ⭐ 128

3. sqlalchemy-migrations-skill (Score: 7.1/10)
   Source: github.com/db-tools/migration-helper
   Trust: 🟡 Community
   Stack match: 82% | Updated: 3 months ago | ⭐ 89

Would you like to:
  [i] Install top recommendation
  [a] View all 30 results
  [s] Skip
```

**Narration:**
> "Notice it shows the top 3 skills ranked by relevance. Each has a trust tier (verified, community, or raw GitHub), stack match percentage, recency, and star count. The scoring algorithm weighs technical fit at 40%, trust at 30%, and recency + stars at 15% each."

**Action:**
```bash
# User types: i
```

**Expected Output:**
```
📦 Installing: fastapi-crud-helper

✅ Cloned to: ~/.claude/skills/fastapi-crud-helper
✅ Added to registry
✅ Logged to install history

Next steps:
  - Restart Claude Code to load the skill
  - Trigger: "fastapi crud", "create endpoint", "REST resource"

Install complete!
```

**Narration:**
> "The skill is now installed and ready to use. agent-hunter logged this to the registry so we can audit it later."

---

## 🔍 Workflow 2: Audit (1.5 minutes)

### Demo: Health Check Installed Skills

**Narration:**
> "A week later, I want to make sure my installed skills haven't been tampered with or gone stale. I'll run audit."

**Screen:**
```bash
agent-hunter audit
```

**Expected Output:**
```
🔍 Auditing 3 installed skills...

📸 Creating pre-audit snapshot...
   Saved to: ~/.agent-hunter/backups/pre-audit-2026-05-09-143022.json

🔎 Checking each skill...

1. fastapi-crud-helper
   SHA: abc123def... ✅ (matches registry)
   Security: ✅ Clean (re-scanned remote)
   Updated: 2 weeks ago
   Status: 🟢 Healthy

2. pydantic-validator-collection
   SHA: def456ghi... ⚠️  MISMATCH
   Security: ✅ Clean
   Updated: 1 month ago → NOW: 2 days ago (update available)
   Status: 🟡 Update Available

3. old-django-skill
   SHA: ghi789jkl... ✅
   Security: ✅ Clean
   Installed: 45 days ago, last used: never
   Status: 🟡 Dormant (consider removing)

Summary:
  ✅ 1 healthy
  🟡 2 need attention
  ❌ 0 critical issues

Recommendations:
  - Update pydantic-validator-collection (remote changed)
  - Consider removing old-django-skill (unused for 45 days)

Would you like to:
  [u] Update flagged skills
  [r] Remove dormant skills
  [s] Skip
```

**Narration:**
> "Audit re-scans remote content, checks for SHA tampering, and flags dormant skills. It also creates a pre-audit snapshot so we can rollback if something goes wrong."

**Action:**
```bash
# User types: u
```

**Expected Output:**
```
📦 Updating: pydantic-validator-collection

✅ Pulled latest changes (def456ghi → jkl012mno)
✅ Updated registry
✅ Re-scanned security: Clean

Update complete!
```

---

## 🔄 Workflow 3: Rollback (1 minute)

### Demo: Restore to Safe State

**Narration:**
> "Oh no, the update broke something. Let's rollback to the pre-audit state."

**Screen:**
```bash
agent-hunter rollback
```

**Expected Output:**
```
🔙 Available snapshots:

1. pre-audit-2026-05-09-143022.json (2 minutes ago)
   - 3 skills
   - Created by: audit command

2. pre-update-2026-05-08-091500.json (1 day ago)
   - 3 skills
   - Created by: update command

3. pre-install-2026-05-07-153000.json (2 days ago)
   - 2 skills
   - Created by: install command

Which snapshot to restore? [1-3 or 'q' to quit]:
```

**Action:**
```bash
# User types: 1
```

**Expected Output:**
```
📸 Restoring snapshot: pre-audit-2026-05-09-143022.json

Preview of changes:
  pydantic-validator-collection: jkl012mno → def456ghi (rollback)

Confirm rollback? [y/N]:
```

**Action:**
```bash
# User types: y
```

**Expected Output:**
```
🔄 Rolling back registry...
   ✅ Restored ~/.agent-hunter/registry.json

🔄 Rolling back skill files...
   pydantic-validator-collection:
     ✅ git reset --hard def456ghi

✅ Rollback complete!

Registry and skill files restored to pre-audit state.
```

**Narration:**
> "Rollback restored both the registry and the actual skill files to the pre-audit state. We're back to a known-good configuration."

---

## 🎯 Key Features Highlighted

### Security-First Design
- ✅ All skills scanned for 10 OWASP LLM security patterns
- ✅ RED results automatically blocked
- ✅ SHA tamper detection on audit
- ✅ Pre-action snapshots for rollback

### Repo-Aware Intelligence
- ✅ Reads tech stack from project files
- ✅ Privacy-preserving (only tech keywords extracted)
- ✅ Context-aware scoring (4 signals)
- ✅ Position-aware ranking (top 3 only)

### User Experience
- ✅ One-command discovery (`hunt`)
- ✅ Automatic health checks (`audit`)
- ✅ One-click rollback (`rollback`)
- ✅ Interactive confirmations
- ✅ Clear trust indicators (verified/community/raw)

---

## 📹 Recording Tips

### Screen Recording Setup
- **Resolution:** 1920×1080 minimum
- **Font size:** Increase terminal font to 16-18pt
- **Color scheme:** High contrast (light background recommended for visibility)
- **Speed:** Natural pace, pause 2-3 seconds after each result screen

### Narration Tips
- **Tone:** Conversational, not scripted
- **Pace:** Speak clearly, pause between sections
- **Focus:** Explain *why* features matter, not just *what* they do
- **Length:** Aim for 4-5 minutes total

### Post-Processing
- **Add text overlays** at key moments:
  - "Security scanning 30 results..."
  - "Top 3 ranked by 4 signals"
  - "Pre-audit snapshot created"
- **Highlight cursor** for clarity
- **Add chapter markers** for hunt/audit/rollback sections

---

## 🔗 What to Say at the End

> "That's agent-hunter v1.0.0-alpha — a focused, security-first skill package manager for Claude Code.
>
> Three commands: hunt finds the top 3 relevant skills for your project. Audit health-checks what you've installed. Rollback restores to a known-good state.
>
> It's open source on GitHub, built with test-driven development, and has 92% code coverage.
>
> Try it: `pip install agent-hunter`, then run `agent-hunter hunt .` in your project.
>
> Link in description. Thanks for watching!"

---

## 📊 Metrics to Mention

- **Code coverage:** 92%
- **Test pass rate:** 100% (634 tests)
- **Security patterns:** 10 OWASP LLM checks
- **Default recommendations:** Top 3
- **Scoring signals:** 4 (stack, trust, recency, stars)
- **Commands:** 3 (hunt, audit, rollback)

---

## 🎨 Visual Assets

### Terminal Color Scheme
Recommended: **Solarized Light** or **GitHub Light**
- Better visibility in recordings
- Professional appearance
- Good contrast for text overlays

### Font
Recommended: **JetBrains Mono** or **Fira Code**
- Clear, readable
- Programmer-friendly
- Good at small sizes

---

## 🚀 Call to Action

**Primary CTA:**
> "Try it now: `pip install agent-hunter`"

**Secondary CTAs:**
- Star the repo: github.com/indhra/agent-hunter
- Read the docs: Full spec in SPEC.md
- Contribute: See CONTRIBUTING.md

---

**Ready to record!** Follow this script for a comprehensive, professional demo.

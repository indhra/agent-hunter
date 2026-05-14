# agent-hunter Demo Script

**Purpose:** Demonstrate the complete hunt → audit → rollback workflow for v1.0.0-alpha

**Duration:** ~5 minutes

**Audience:** Developers using Claude Code who want to discover relevant skills

---

## 🎬 Demo Flow

### Part 1: Hunt for Skills (2 minutes)

**Scenario:** You're building a FastAPI backend with PostgreSQL and need skill recommendations.

**Setup:**
```bash
# Navigate to a sample FastAPI project
cd ~/projects/sample-fastapi-app

# Verify project structure
ls
# Output: main.py requirements.txt models/ routes/ tests/
```

**Demo:**

```bash
# Run agent-hunter hunt
python /path/to/agent-hunter/scripts/main.py hunt .
```

**Expected output:**

```
 Analyzing your project...
 Tech stack: FastAPI, PostgreSQL, Pydantic, SQLAlchemy, pytest
 Searching GitHub for relevant skills...

Top 3 Skills for Your Project:

1. fastapi-expert (95/100)
 📦 github.com/awesome-skills/fastapi-expert
 [YES] Verified • 234 ⭐ • Updated 2 days ago

 Expert patterns for FastAPI development: dependency injection,
 background tasks, WebSocket support, testing strategies.

 Perfect match: FastAPI (40 points) + PostgreSQL (25 points) + pytest (15 points)

2. api-testing-suite (87/100)
 📦 github.com/testing/api-suite
 [SAFE] Community • 156 ⭐ • Updated 1 week ago

 Comprehensive API testing patterns: integration tests, contract
 testing, performance benchmarks, mock strategies.

 Strong match: FastAPI (35 points) + pytest (20 points)

3. database-migration-helper (82/100)
 📦 github.com/data/migrations
 [SAFE] Community • 89 ⭐ • Updated 3 weeks ago

 Database migration patterns for Alembic and SQLAlchemy: version
 control, rollback strategies, seed data management.

 Good match: PostgreSQL (30 points) + SQLAlchemy (25 points)

Security scan complete: 0 [BLOCKED] dangerous, 2 [REVIEW] warnings, 28 [SAFE] clean

Would you like to install these skills? [y/N]: y

[YES] Installed: fastapi-expert
[YES] Installed: api-testing-suite
[YES] Installed: database-migration-helper

Skills installed to: ~/.claude/skills/
```

**Talking points:**
- Notice the **scoring breakdown** - stack match is 40% of total score
- **Trust tiers** - Verified ([YES]) vs Community ([SAFE]) vs Raw
- **Recency signals** - "Updated 2 days ago" gets priority
- **Security scanning** - 0 dangerous skills shown, 2 warnings flagged
- **Top 3 only** - Not overwhelming with 50 options

---

### Part 2: Audit Installed Skills (1.5 minutes)

**Scenario:** A week later, you want to check if your installed skills are healthy.

**Demo:**

```bash
# Run audit command
python /path/to/agent-hunter/scripts/main.py audit
```

**Expected output:**

```
 Auditing installed skills...
 Pre-audit snapshot: ~/.agent-hunter/backups/pre-audit-2026-05-09-14-23-15.json

Installed Skills Health Check:

┌─────────────────────────┬────────┬──────────────┬─────────────────┐
│ Skill │ Status │ Last Updated │ Notes │
├─────────────────────────┼────────┼──────────────┼─────────────────┤
│ fastapi-expert │ [YES] OK │ 2 days ago │ SHA verified │
│ api-testing-suite │ [REVIEW] Old │ 1 week ago │ Update available│
│ database-migration-help │ [YES] OK │ 3 weeks ago │ SHA verified │
└─────────────────────────┴────────┴──────────────┴─────────────────┘

📊 Summary:
 2 healthy, 1 update available, 0 tampered, 0 security issues

[REVIEW] api-testing-suite has an update available:
 Current: v1.2.3 (commit abc1234)
 Latest: v1.3.0 (commit def5678)
 Changelog: Added contract testing support

Would you like to update api-testing-suite? [y/N]: y

[YES] Updated: api-testing-suite (v1.2.3 → v1.3.0)
 SHA verified, security scan passed
```

**Talking points:**
- **Pre-audit snapshot** - Automatic backup before any changes
- **SHA verification** - Detects if skill was tampered with
- **Update detection** - Compares installed vs latest remote version
- **Health table** - Clear status for each skill
- **Safe updates** - Security scan re-runs before update

---

### Part 3: Rollback (1 minute)

**Scenario:** The update broke something. You want to rollback to the previous state.

**Demo:**

```bash
# Run rollback command
python /path/to/agent-hunter/scripts/main.py rollback
```

**Expected output:**

```
 Available rollback points:

1. pre-audit-2026-05-09-14-23-15 (5 minutes ago)
 Before: Updated api-testing-suite

2. pre-audit-2026-05-08-10-15-42 (1 day ago)
 Before: Installed 3 skills

3. pre-audit-2026-05-07-16-30-21 (2 days ago)
 Before: Initial setup

Select snapshot to restore [1-3]: 1

📋 Rollback preview:
 api-testing-suite: v1.3.0 → v1.2.3 (revert update)

This will restore your registry to the state before the last audit.
Proceed? [y/N]: y

🔄 Rolling back...
 [YES] Registry restored
 [YES] api-testing-suite: Reset to commit abc1234 (v1.2.3)

[YES] Rollback complete!
 Your skills are now in the same state as 5 minutes ago.
```

**Talking points:**
- **Automatic snapshots** - Taken before any audit/update operation
- **Time-based selection** - Easy to pick the right restore point
- **Preview before restore** - See what will change
- **Git-based rollback** - Uses `git reset --hard` to restore exact SHA
- **Instant recovery** - No re-downloading, just git operations

---

## 🎨 Visual Demo Tips

### Terminal Setup

1. **Use a clean terminal** - No clutter, easy to read
2. **Increase font size** - 18-20pt for screen recording
3. **Use colors** - agent-hunter uses rich terminal formatting
4. **Full screen** - Hide desktop distractions

### Pacing

1. **Slow down** - Let viewers read output before continuing
2. **Pause after key points** - Give time to absorb
3. **Highlight important lines** - Point with cursor or annotation

### Sample Project Setup

Create a realistic FastAPI project:

```bash
mkdir -p ~/demo-projects/sample-fastapi-app
cd ~/demo-projects/sample-fastapi-app

# Create minimal FastAPI structure
cat > main.py << 'PYTHON'
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
 return {"Hello": "World"}

if __name__ == "__main__":
 uvicorn.run(app, host="0.0.0.0", port=8000)
PYTHON

cat > requirements.txt << 'TXT'
fastapi==0.109.0
uvicorn==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pydantic==2.5.3
pytest==7.4.4
TXT

mkdir -p models routes tests

cat > models/user.py << 'PYTHON'
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
 __tablename__ = "users"

 id = Column(Integer, primary_key=True)
 name = Column(String)
 email = Column(String, unique=True)
PYTHON
```

---

## 📝 Narration Script

### Opening (15 seconds)

> "Hi, I'm [name]. Today I'll show you agent-hunter - a package manager for Claude Code skills. Instead of building everything from scratch, let's find what already exists."

### Hunt Demo (90 seconds)

> "I'm working on a FastAPI backend with PostgreSQL. Let me run agent-hunter hunt to see what skills are available."
>
> [Run command, wait for output]
>
> "Notice it detected my tech stack automatically - FastAPI, PostgreSQL, Pydantic. And it found three relevant skills."
>
> [Point to results]
>
> "The top result is fastapi-expert with a 95/100 score. It's Verified, has 234 stars, and was updated 2 days ago. The scoring breakdown shows it matched on FastAPI, PostgreSQL, and pytest."
>
> [Point to security scan]
>
> "Security scan ran automatically - 0 dangerous skills, 2 warnings. Safe to install."
>
> [Confirm installation]
>
> "Let's install all three. Done. They're now in my Claude Code skills directory."

### Audit Demo (60 seconds)

> "A week later, I want to check if my skills are still healthy."
>
> [Run audit command]
>
> "agent-hunter created a pre-audit snapshot first - that's my rollback point if something goes wrong."
>
> [Point to health table]
>
> "Two skills are healthy, one has an update available. Let me update it."
>
> [Confirm update]
>
> "Updated to v1.3.0. Security scan passed, SHA verified. Good to go."

### Rollback Demo (45 seconds)

> "Oops, the update broke my workflow. Let's rollback."
>
> [Run rollback command]
>
> "Here are my rollback points. I want the one from 5 minutes ago, before the update."
>
> [Select snapshot]
>
> "Preview shows it will revert api-testing-suite back to v1.2.3. Exactly what I want."
>
> [Confirm rollback]
>
> "Done. My skills are back to the working state. Problem solved."

### Closing (15 seconds)

> "That's agent-hunter: hunt for the best skills, audit them regularly, rollback if needed. Three commands, focused on the core value - finding skills you don't have to build yourself."
>
> "Try it out at github.com/indhra/agent-hunter. Thanks for watching!"

---

## 🎥 Recording Checklist

### Before Recording

- [ ] Install agent-hunter from clean state
- [ ] Set up sample FastAPI project
- [ ] Clear terminal history
- [ ] Set GITHUB_TOKEN environment variable
- [ ] Test run all three commands (hunt, audit, rollback)
- [ ] Prepare narration script on second monitor
- [ ] Check audio levels
- [ ] Close distracting applications

### During Recording

- [ ] Start with clean terminal
- [ ] Introduce yourself and the tool
- [ ] Demo hunt command with real output
- [ ] Demo audit command showing health check
- [ ] Demo rollback command showing restore
- [ ] Keep pace slow and deliberate
- [ ] Pause after key points

### After Recording

- [ ] Edit for clarity (cut mistakes, add annotations)
- [ ] Add title screen with agent-hunter logo
- [ ] Add captions/subtitles
- [ ] Export in 1080p
- [ ] Upload to YouTube with good title/description
- [ ] Share on GitHub README

---

## 📊 Expected Demo Metrics

**Timing:**
- Hunt: ~12 seconds (well under 30s target)
- Audit: ~3 seconds (local operation)
- Rollback: ~2 seconds (git reset is instant)

**User experience:**
- Clear output with emoji indicators
- Progress feedback during GitHub search
- Confirmation prompts before destructive actions
- Helpful error messages if something fails

---

## Variations for Different Audiences

### For Developers

Focus on:
- Technical stack matching accuracy
- Security scanning details
- Performance metrics
- Testing infrastructure

### For Product Managers

Focus on:
- Time saved vs building from scratch
- Discovery of high-quality existing skills
- Risk mitigation via security scanning
- Rollback safety net

### For Security Teams

Focus on:
- OWASP LLM Top 10 coverage
- RED result filtering (never shown)
- SHA verification for tamper detection
- Sandbox isolation capabilities

---

## [YES] Success Criteria

Demo is successful if viewers:

1. **Understand the value** - Find skills instead of building them
2. **See it working** - Real output, not mockups
3. **Trust the security** - Automatic scanning, not manual review
4. **Feel confident** - Rollback exists if something breaks
5. **Want to try it** - Clear next steps (GitHub link)

Ready to record! 🎬

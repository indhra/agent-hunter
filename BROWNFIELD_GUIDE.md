# Brownfield Projects: Using agent-hunter on Existing Codebases

**agent-hunter works on ANY project-new or existing.**

This guide shows how to use agent-hunter to enhance and accelerate work on brownfield (existing) projects.

---

## What Is a Brownfield Project?

**Brownfield** = existing production code with:
- [YES] Established tech stack
- [YES] Working features
- [YES] Real users or business value
- [YES] Technical debt (usually)
- [YES] Team knowledge and conventions

**vs. Greenfield** = brand new project from scratch

---

## Why Use agent-hunter on Brownfield Projects?

You have working code. You want to:
- **Accelerate** feature development
- 🔧 **Refactor** with confidence
- ⚡ **Optimize** performance
- 🛡️ **Harden** security
- **Document** existing code
- 🧪 **Test** more thoroughly
- 🚢 **Deploy** better
- 🪵 **Pay down** technical debt

**Solution:** Hunt for existing skills that already solve these problems instead of building from scratch.

---

## Setup for Brownfield Success

### 1. Install agent-hunter (1 minute)

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter
./setup
```

### 2. Add GitHub Token (Highly Recommended for Brownfield)

For brownfield projects, GitHub token is **strongly recommended** because:
- Searches 5,000+ skills on GitHub (vs. ~100 curated)
- Finds niche tools for your specific tech stack
- Discovers refactoring, performance, and testing helpers

```bash
# Quick setup
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Permanent (add to ~/.zshrc)
echo 'export GITHUB_TOKEN=ghp_xxxxxxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

**Generate token:** https://github.com/settings/tokens (no scopes needed)

### 3. Optional: Enable Session Hunting

To hunt automatically when you open the project:

```bash
export AGENT_HUNTER_AUTO=1
```

Or add to `.claude/settings.json`:
```json
{
 "autoActivateSkills": ["agent-hunter"]
}
```

---

## Brownfield Workflow Examples

### Example 1: Refactoring Python Backend

**Your situation:**
```
Project: FastAPI microservice
Tech: FastAPI, PostgreSQL, pytest, Docker
Goal: Refactor to clean architecture
```

**Hunt:**
```bash
cd /path/to/fastapi-project
/agent-hunter
```

**What you might find:**
```
Top 3 recommendations:

1. [SAFE] fastapi-clean-architecture
 Safe to install.
 Why: Your repo uses FastAPI with PostgreSQL. This skill provides
 clean architecture patterns, service layers, and repository patterns.

2. [SAFE] database-migration-helper
 Safe to install.
 Why: PostgreSQL migrations are critical during refactoring. This skill
 helps manage schema changes safely.

3. [REVIEW] async-performance-profiler
 Review before installing.
 Why: Great for checking if your FastAPI async patterns are optimal
 during refactoring. Review for permissions first.
```

**Action:** Install skills 1 and 2. Review 3 before installing.

---

### Example 2: Performance Optimization

**Your situation:**
```
Project: React web app
Tech: React, Node.js, MongoDB, Redis
Goal: Improve page load time from 4.2s to < 2s
```

**Hunt:**
```bash
cd /path/to/react-app
/agent-hunter
```

**What you might find:**
```
Top 3 recommendations:

1. [SAFE] react-bundle-analyzer
 Safe to install.
 Why: Your repo uses React. This skill analyzes bundle size and finds
 bloated dependencies slowing your load time.

2. [SAFE] lighthouse-automated-audits
 Safe to install.
 Why: Perfect for measuring Web Vitals improvements. Runs automated
 lighthouse checks on every build.

3. [SAFE] redis-cache-optimizer
 Safe to install.
 Why: You're using Redis. This skill finds optimization opportunities
 in your cache strategy.
```

**Action:** Install all three. Run analyzer, optimize bundle, measure with lighthouse.

---

### Example 3: Adding Security Testing

**Your situation:**
```
Project: Go gRPC service
Tech: Go, gRPC, PostgreSQL, Kubernetes
Goal: Add security scanning before next release
```

**Hunt:**
```bash
cd /path/to/grpc-service
/agent-hunter
```

**What you might find:**
```
Top 3 recommendations:

1. [SAFE] grpc-security-validator
 Safe to install.
 Why: Your project uses gRPC. This skill validates gRPC security best
 practices: TLS, auth, permission checks.

2. [SAFE] dependency-vulnerability-scanner
 Safe to install.
 Why: Scans Go dependencies for known CVEs. Essential before release.

3. [REVIEW] container-image-scanner
 Review before installing.
 Why: Kubernetes deployment detected. Scans container images for
 vulnerabilities. Review filesystem access first.
```

**Action:** Install 1 and 2. Review 3 before container scanning.

---

### Example 4: Documenting Legacy Code

**Your situation:**
```
Project: 5-year-old Rails monolith
Tech: Ruby on Rails, PostgreSQL, Sidekiq, Redis
Goal: Document existing code to onboard new team members
```

**Hunt:**
```bash
cd /path/to/rails-app
/agent-hunter
```

**What you might find:**
```
Top 3 recommendations:

1. [SAFE] rails-codebase-mapper
 Safe to install.
 Why: Your Rails monolith needs visibility. This skill auto-generates
 dependency graphs, controller/model documentation, and flow diagrams.

2. [SAFE] sidekiq-job-documenter
 Safe to install.
 Why: Background jobs with Sidekiq are hard to document. This skill
 auto-documents job flows, retries, and dependencies.

3. [SAFE] database-schema-visualizer
 Safe to install.
 Why: PostgreSQL schema visualization helps new developers understand
 data relationships without reading migration files.
```

**Action:** Install all three. Generate documentation, commit to repo.

---

## Common Brownfield Scenarios

### Scenario: Microservices Architecture

**Goal:** Add distributed tracing to 10 microservices

```bash
/agent-hunter
# Expected: Find distributed-tracing skills, OpenTelemetry helpers
```

### Scenario: Monolith to Microservices

**Goal:** Identify candidates for extraction

```bash
/agent-hunter
# Expected: Find code dependency analyzers, service boundary tools
```

### Scenario: Legacy Database Migration

**Goal:** Move from MySQL to PostgreSQL safely

```bash
/agent-hunter
# Expected: Find migration helpers, data validation skills
```

### Scenario: Add CI/CD Pipeline

**Goal:** Set up automated testing and deployment

```bash
/agent-hunter
# Expected: Find GitHub Actions skills, Docker best practices
```

### Scenario: TypeScript Migration

**Goal:** Gradually migrate JavaScript to TypeScript

```bash
/agent-hunter
# Expected: Find TypeScript conversion tools, type inference helpers
```

---

## Tips for Brownfield Success

### 1. Run Hunts Regularly

- **Monthly**: Check for new tools matching your current focus
- **Before major refactors**: Hunt for tools that help the refactor
- **After big changes**: Hunt for tools to validate or optimize

### 2. Set GitHub Token

Brownfield projects benefit **most** from the full 5,000+ GitHub skill search. Set `GITHUB_TOKEN` for best results.

### 3. Focus on Your Pain Points

Hunt when:
- You have a specific goal (performance, security, documentation)
- You're about to spend days/weeks on something
- You have recurring pain (deployments, testing, monitoring)

### 4. Review Yellow ([REVIEW]) Results

Brownfield projects often need tools that require permissions (filesystem access, network calls). Review these carefully-they're often exactly what you need.

### 5. Commit Decisions

When you install a new skill:
```bash
cd ~/.claude/skills
git add .
git commit -m "Add fastapi-clean-architecture skill for refactoring"
git push
```

Keep your team aligned on what tools are being used.

---

## Team Usage in Brownfield Projects

### Share agent-hunter with Your Team

Add to `.claude/CLAUDE.md` in your brownfield project:

```markdown
## agent-hunter

Use to discover skills that enhance our development:
- Refactoring helpers
- Performance tools
- Testing frameworks
- Security scanners
- Documentation generators

Run: `/agent-hunter`

GitHub token should be set for optimal discovery of skills for our stack.
```

Then commit:
```bash
git add .claude/CLAUDE.md
git commit -m "Add agent-hunter guide to team CLAUDE configuration"
git push
```

### Create Team Hunt Guidelines

Document what skills your team has vetted:

```markdown
# Approved Skills for This Project

## Reviewed & Installed
- fastapi-clean-architecture [YES]
- database-migration-helper [YES]
- async-performance-profiler [YES]

## Reviewed & Not Needed
- kubernetes-helm-advanced (we use kustomize)
- graphql-federation (we use REST)

## To Review
- new-skill-x
- new-skill-y
```

---

## Measuring Brownfield Impact

### Before Hunting

Track your baseline:
```bash
# Time to add a feature: X days
# Code test coverage: Y%
# Performance metrics: Z
```

### After Installing Skills

```bash
# Time to add a feature: X - 20% days
# Code test coverage: Y + 10%
# Performance metrics: Z improved
```

---

## FAQ: Brownfield & agent-hunter

### Q: Will agent-hunter work on my 10-year-old codebase?

**A:** Yes! As long as you can identify the tech stack (Python, Node, Go, etc.), agent-hunter finds relevant skills. Even if some skills are for newer patterns, they often apply to legacy code.

### Q: Should I set GitHub token for brownfield projects?

**A:** **Yes, strongly recommend it.** Brownfield projects have very specific needs (refactoring, optimization, security), and the full 5,000+ GitHub search helps find niche tools.

### Q: Can agent-hunter help with technical debt?

**A:** Absolutely. Hunt for: debt analysis tools, refactoring helpers, test coverage improvers, performance profilers.

### Q: What if agent-hunter finds skills I don't want to use?

**A:** No problem. You choose what to install. If a skill isn't right, skip it. The recommendation is just a starting point.

### Q: Should my team use agent-hunter together?

**A:** Yes! Add to your project's `.claude/CLAUDE.md` so everyone can discover skills. Align on what you install.

---

## Next Steps

1. **Install agent-hunter** (if not done)
2. **Set GITHUB_TOKEN** (recommended for brownfield)
3. **Open your existing project**
4. **Run `/agent-hunter`**
5. **Review top 3 recommendations**
6. **Install what fits your current goal**
7. **Repeat** as you work on new features/refactors

---

**agent-hunter: Accelerate your brownfield projects.**

---

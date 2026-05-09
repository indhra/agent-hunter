# Real-World Validation Plan for v1.0.0-alpha

**Goal:** Test agent-hunter on 10 different repository types to validate scoring accuracy, performance, and recommendation quality.

---

## 📋 Test Repositories

### 1. Python FastAPI Backend
- **Tech stack:** FastAPI, PostgreSQL, Redis, Pydantic, SQLAlchemy
- **Expected skills:** API development, database patterns, caching, testing
- **Success criteria:** Top 3 recommendations all relevant to API development

### 2. React Frontend (TypeScript)
- **Tech stack:** React, TypeScript, Vite, TailwindCSS, React Query
- **Expected skills:** Component patterns, state management, styling, testing
- **Success criteria:** Top 3 recommendations all relevant to React/TS

### 3. Django Monolith
- **Tech stack:** Django, PostgreSQL, Celery, Redis, Django REST Framework
- **Expected skills:** Django patterns, async tasks, REST APIs, ORM
- **Success criteria:** Top 3 recommendations all relevant to Django

### 4. Vue.js SPA
- **Tech stack:** Vue 3, Composition API, Pinia, Vite, Vitest
- **Expected skills:** Vue patterns, state management, testing, build tools
- **Success criteria:** Top 3 recommendations all relevant to Vue

### 5. Ruby on Rails App
- **Tech stack:** Rails, PostgreSQL, Sidekiq, RSpec, Hotwire
- **Expected skills:** Rails patterns, background jobs, testing, Hotwire
- **Success criteria:** Top 3 recommendations all relevant to Rails

### 6. Go Microservice
- **Tech stack:** Go, gRPC, PostgreSQL, Docker, Kubernetes
- **Expected skills:** Go patterns, gRPC, containerization, orchestration
- **Success criteria:** Top 3 recommendations all relevant to Go/microservices

### 7. Rust CLI Tool
- **Tech stack:** Rust, Clap, Tokio, Serde, SQLite
- **Expected skills:** CLI patterns, async Rust, serialization, testing
- **Success criteria:** Top 3 recommendations all relevant to Rust/CLI

### 8. Next.js Full-Stack
- **Tech stack:** Next.js, TypeScript, Prisma, NextAuth, Vercel
- **Expected skills:** SSR patterns, auth, database, deployment
- **Success criteria:** Top 3 recommendations all relevant to Next.js

### 9. Elixir Phoenix
- **Tech stack:** Elixir, Phoenix, PostgreSQL, LiveView, Ecto
- **Expected skills:** Phoenix patterns, real-time, ORM, testing
- **Success criteria:** Top 3 recommendations all relevant to Elixir/Phoenix

### 10. Jupyter Data Science
- **Tech stack:** Python, Jupyter, Pandas, NumPy, Matplotlib, Scikit-learn
- **Expected skills:** Data analysis, visualization, ML patterns, notebooks
- **Success criteria:** Top 3 recommendations all relevant to data science

---

## 🎯 Validation Metrics

### Per-Repository Checks

For each repository, measure:

1. **Relevance Score (0-10)**
   - How relevant are the top 3 recommendations?
   - Do they match the tech stack?
   - Would a developer actually use them?

2. **Performance**
   - Total hunt time (target: <30 seconds)
   - Number of GitHub API calls
   - Cache hit rate

3. **Security Flags**
   - Number of RED results filtered
   - Number of YELLOW warnings
   - False positive rate

4. **Ranking Quality**
   - Is #1 actually the best match?
   - Are there better skills ranked lower?
   - Position-aware relevance (top 3 get most attention)

### Aggregate Metrics

Across all 10 repositories:

1. **Average relevance score** - Target: ≥8.0/10
2. **Average hunt time** - Target: <30 seconds
3. **Recommendation diversity** - Are we surfacing different skills per repo type?
4. **False positive rate** - Target: <5% RED flags that are actually safe
5. **Coverage** - Do all major frameworks have relevant skills?

---

## 📊 Data Collection Template

For each test run, record:

```json
{
  "repo_name": "example-fastapi-app",
  "repo_type": "Python FastAPI Backend",
  "tech_stack": ["FastAPI", "PostgreSQL", "Redis", "Pydantic"],
  "hunt_time_sec": 12.4,
  "recommendations": [
    {
      "rank": 1,
      "name": "fastapi-expert",
      "score": 95,
      "relevance": 10,
      "would_use": true,
      "notes": "Perfect match, exactly what I needed"
    },
    {
      "rank": 2,
      "name": "api-testing-suite",
      "score": 87,
      "relevance": 8,
      "would_use": true,
      "notes": "Useful for API testing patterns"
    },
    {
      "rank": 3,
      "name": "docker-compose-helper",
      "score": 82,
      "relevance": 6,
      "would_use": false,
      "notes": "Not specific to FastAPI, generic Docker help"
    }
  ],
  "security_flags": {
    "red": 2,
    "yellow": 5,
    "green": 23
  },
  "github_api_calls": 15,
  "overall_quality": 8.0
}
```

---

## 🔧 Testing Procedure

### Preparation

1. **Clear cache** between runs to simulate fresh installs:
   ```bash
   rm -rf ~/.agent-hunter/cache
   ```

2. **Set GitHub token** for consistent rate limits:
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   ```

3. **Enable timing output** for performance measurement:
   ```bash
   export AGENT_HUNTER_TIMING=1
   ```

### Execution

For each test repository:

```bash
# 1. Navigate to repo
cd /path/to/test-repo

# 2. Run hunt command
time python /path/to/agent-hunter/scripts/main.py hunt . > hunt_output.txt

# 3. Record results in validation_results.json

# 4. Manual review: Would you actually use these skills?

# 5. Take screenshot of output for documentation
```

### Analysis

After collecting all 10 data points:

1. **Calculate aggregate metrics**
   ```bash
   python scripts/analyze_validation.py validation_results.json
   ```

2. **Identify patterns**
   - Which repo types get the best recommendations?
   - Which scoring signals matter most?
   - Are there false positives/negatives?

3. **Tune weights if needed**
   - Adjust `config/defaults.json` scoring weights
   - Re-run validation to verify improvements
   - Document weight changes with rationale

---

## 🎛️ Weight Tuning Process

### Current Weights (v1.0.0-alpha)

```python
stack_match: 0.40  # Technical fit
trust_score: 0.30  # Trust tier
recency: 0.15      # Recent activity
stars: 0.15        # Popularity
```

### Tuning Scenarios

**If recommendations are too generic:**
- Increase `stack_match` (0.40 → 0.50)
- Decrease `trust_score` (0.30 → 0.25)

**If too many dormant skills appear:**
- Increase `recency` (0.15 → 0.20)
- Decrease `stars` (0.15 → 0.10)

**If trust tier matters more than we thought:**
- Increase `trust_score` (0.30 → 0.35)
- Decrease `stack_match` (0.40 → 0.35)

**If popularity signals quality:**
- Increase `stars` (0.15 → 0.20)
- Decrease `recency` (0.15 → 0.10)

### Validation Loop

1. Run validation with current weights
2. Analyze quality scores
3. Adjust one weight at a time
4. Re-run validation
5. Compare before/after metrics
6. Keep change if improvement >5%
7. Repeat until no more improvements

---

## 📝 Deliverables

### After validation is complete:

1. **validation_results.json** - Raw data for all 10 repos
2. **validation_report.md** - Summary with charts and findings
3. **config/defaults.json** - Updated with tuned weights (if changed)
4. **CHANGELOG.md** - Document any weight changes
5. **Screenshots/** - Visual evidence of recommendations

### Success Criteria for v1.0.0 Launch

- ✅ Average relevance score ≥8.0/10
- ✅ Average hunt time <30 seconds
- ✅ 0 critical bugs found
- ✅ Security scanning working (no false negatives)
- ✅ All 10 repo types get relevant recommendations

If criteria not met → fix issues → re-validate → repeat.

---

## 🚨 Known Edge Cases to Test

1. **Empty repository** - No tech stack detected
2. **Mixed languages** - Python + TypeScript + Go in one repo
3. **Legacy codebase** - Old frameworks (Django 1.x, React 15)
4. **Monorepo** - Multiple apps in subdirectories
5. **No dependencies** - Simple script with no requirements.txt
6. **Obfuscated code** - Minified JS, compiled artifacts
7. **Private skills** - Skills not on GitHub
8. **Rate limit hit** - Simulate 429 responses
9. **Network failure** - Simulate connection timeout
10. **Malformed SKILL.md** - Invalid YAML frontmatter

---

## 📊 Example Validation Report

```markdown
# Validation Results Summary

**Date:** May 9, 2026
**Version:** v1.0.0-alpha
**Repos tested:** 10/10

## Aggregate Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Avg relevance | ≥8.0/10 | 8.4/10 | ✅ |
| Avg hunt time | <30s | 14.2s | ✅ |
| False positives | <5% | 2.1% | ✅ |
| Coverage | 100% | 100% | ✅ |

## Per-Repository Results

1. FastAPI: 9.3/10 (12s) ✅
2. React: 8.7/10 (11s) ✅
3. Django: 8.9/10 (15s) ✅
4. Vue: 8.1/10 (13s) ✅
5. Rails: 7.8/10 (18s) ⚠️
6. Go: 8.6/10 (10s) ✅
7. Rust: 8.2/10 (16s) ✅
8. Next.js: 9.0/10 (9s) ✅
9. Elixir: 7.5/10 (21s) ⚠️
10. Jupyter: 8.3/10 (14s) ✅

## Findings

**Strong areas:**
- Python/JS ecosystems: Excellent recommendations
- Performance: Well under 30s target
- Security: No false negatives

**Improvement areas:**
- Rails/Elixir: Fewer skills available (ecosystem issue)
- Scoring: Consider increasing recency weight

**Recommendation:** Launch v1.0.0 with current weights. Rails/Elixir coverage will improve as ecosystem grows.
```

---

## ✅ Next Steps After Validation

1. **Document findings** in validation_report.md
2. **Update weights** in config/defaults.json (if needed)
3. **Fix critical bugs** (if any found)
4. **Update CHANGELOG.md** with validation summary
5. **Proceed to demo video** recording
6. **Prepare v1.0.0 stable release**

Ready to launch when all criteria met! 🚀

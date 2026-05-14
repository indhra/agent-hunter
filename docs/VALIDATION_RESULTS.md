# Real-World Validation Results - v1.0.0-alpha

**Test Date:** May 9, 2026
**Tester:** GitHub Copilot (automated testing)
**Status:** ⚠️ **CRITICAL BUGS FOUND** - Cannot proceed to stable release

---

## 🚨 Critical Bugs Discovered

### Bug #1: Invalid Skill Name Extraction (BLOCKER)
**Severity:** CRITICAL (prevents installation)

**Error:**
```
installer.InstallerError: Invalid skill name ''. Only alphanumeric characters, hyphens, underscores, and dots are allowed.
```

**Root Cause:**
When hunter.py returns results, the `skill_name` field is empty for some repos. The installer then crashes when trying to validate an empty string.

**Reproduction:**
```bash
cd /tmp/agent-hunter-validation/fastapi-example
agent-hunter hunt .
# Select "y" to install → CRASHES
```

**Impact:** Users cannot install ANY discovered skills. Complete failure of core workflow.

**Fix Required:** hunter.py must extract skill_name from repo URL or SKILL.md frontmatter. If missing, use repo name as fallback.

---

### Bug #2: Recommendation Relevance Failure (BLOCKER)
**Severity:** CRITICAL (defeats core product promise)

**Test Case 1: FastAPI Backend**
- **Expected:** FastAPI patterns, async Python, API development skills
- **Actual Results:**
 1. `@cyanheads/mcp-ts-core` (TypeScript MCP framework) [NO]
 2. `@delorenj/mcp-server-trello` (Trello integration) [NO]
 3. `is-bun-module` (Bun runtime checker) [NO]
- **Relevance Rate:** 0/3 (0%) - FAIL

**Test Case 2: Django REST Framework**
- **Expected:** Django patterns, DRF, ORM, REST API skills
- **Actual Results:**
 1. `@cspell/dict-django` (spell checker dictionary) [NO]
 2. `storybook-django` (UI component docs) ⚠️ (marginal)
 3. `figma-mcp` (Figma design tool) [NO]
- **Relevance Rate:** 0/3 (0%) - FAIL

**Root Cause:** Scoring algorithm matches on TECH KEYWORDS ONLY (e.g., "bun", "django") but doesn't understand CONTEXT. A Django spell checker dictionary != Django backend development patterns.

**Impact:** Core product promise broken. "Top 3 recommendations" are useless noise.

**Fix Required:** Either:
1. Curated verified skills index with human-reviewed quality (fastest fix)
2. Better scoring that understands skill PURPOSE vs tech stack mention
3. Both

---

### Bug #3: GitHub API Authentication Failure
**Severity:** MODERATE (degraded UX but has workaround)

**Error:**
```
[agent-hunter] Note: GITHUB_TOKEN not set - using unauthenticated rate limit (60/hr).
[agent-hunter] GitHub API error 401 for query: filename:SKILL.md django
```

**Root Cause:** GitHub Code Search API changed in Feb 2024 to REQUIRE authentication. Unauthenticated requests return 401, not 403.

**Impact:**
- User sees "unauthenticated rate limit" message but actually gets NO results from GitHub
- Falls back to `references/VERIFIED_SKILLS.md` (if it exists)
- Misleading error messaging

**Fix Required:**
1. Update error message: "GitHub Code Search requires authentication. Set GITHUB_TOKEN or results will be limited to curated index."
2. Check for 401 specifically and explain the token requirement clearly

---

## 📊 Validation Testing Results

### Test Coverage
| Repo Type | Status | Relevance | Notes |
|-----------|--------|-----------|-------|
| FastAPI Backend | [NO] FAIL | 0/3 (0%) | Bug #1 blocks install; Bug #2 shows irrelevant results |
| Django REST | [NO] FAIL | 0/3 (0%) | Same issues as FastAPI |
| React TypeScript | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Vue.js SPA | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Rails App | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Go Microservice | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Rust CLI | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Next.js | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Elixir Phoenix | ⏸️ SKIPPED | - | Blocked by critical bugs |
| Data Science | ⏸️ SKIPPED | - | Blocked by critical bugs |

**Overall Relevance:** 0/6 (0%) - Target was ≥80%

**Decision:** **CANNOT PROCEED TO v1.0.0 STABLE**

---

## Root Cause Analysis

### Why Relevance Failed

**Problem:** The scoring formula optimizes for KEYWORD MATCH, not USEFULNESS.

**Current behavior:**
- Sees "django" in tech stack
- Searches GitHub for `filename:SKILL.md django`
- Matches ANY repo mentioning "django" (spell checkers, UI tools, etc.)
- Ranks by stack_match score (0.40 weight) + trust score (0.30 weight)
- No understanding of SKILL PURPOSE

**What's missing:**
1. **Intent/domain matching** was removed in Week 2 simplification (folded into stack_match)
2. **Curated verified skills** - `references/VERIFIED_SKILLS.md` exists but is likely empty
3. **Natural language descriptions** - skills need "I help you build REST APIs" not just "uses FastAPI"
4. **Quality signal** - stars/recency/trust don't measure "does this solve my problem?"

---

## Recommendations

### Option A: Quick Fix (Curated Index Only)
**Time:** 2-3 hours
**Approach:**
1. Populate `references/VERIFIED_SKILLS.md` with 20-30 high-quality, human-reviewed skills
2. Disable GitHub Code Search for v1.0.0 (too noisy)
3. Ship with "curated recommendations only" model
4. Revisit GitHub search in v1.1.0 after quality improvements

**Pros:**
- Can ship v1.0.0 in 1-2 days
- 100% relevance guaranteed (human curated)
- Simpler, more focused

**Cons:**
- Limited coverage (30 skills vs thousands on GitHub)
- Not "discovering" skills, just recommending from list

---

### Option B: Fix Scoring Algorithm
**Time:** 1-2 weeks
**Approach:**
1. Re-add intent/domain matching with better implementation
2. Add skill PURPOSE field to SKILL.md frontmatter schema
3. Semantic similarity scoring on description text
4. Machine learning ranking model (if needed)

**Pros:**
- Scales to GitHub's full catalog
- True "discovery" engine
- Long-term better solution

**Cons:**
- Delays v1.0.0 release by 1-2 weeks
- Higher complexity
- May still have false positives

---

### Option C: Hybrid (RECOMMENDED)
**Time:** 3-4 days
**Approach:**
1. Ship v1.0.0 with curated index ONLY (disable GitHub search)
2. Add disclaimer: "v1.0 uses curated skills. GitHub discovery coming in v1.1"
3. Implement Option B scoring improvements in parallel for v1.1.0
4. Re-enable GitHub search after validation passes

**Pros:**
- Can ship v1.0.0 this week
- Guaranteed quality for v1.0
- Roadmap for improvement clear

**Cons:**
- Two-phase release
- Users may expect GitHub discovery in v1.0

---

## 🚦 Decision Gates

### Can we ship v1.0.0-alpha as-is?
**NO.** Installation is broken (Bug #1). Recommendations are useless (Bug #2).

### Can we ship v1.0.0 this week?
**YES, if we choose Option A or C** - disable GitHub search, use curated index only.

### What needs to happen before v1.0.0?
**MUST FIX:**
1. Bug #1 (skill name extraction)
2. Bug #2 (relevance) via curated index OR scoring improvements
3. Update messaging to set correct expectations

**SHOULD FIX:**
- Bug #3 (better GitHub auth error messaging)

**CAN DEFER:**
- GitHub Code Search improvements (ship in v1.1.0)

---

## 📝 Next Steps

### Immediate (Today)
1. ⏸️ **PAUSE v1.0.0 release** - critical bugs block stable release
2. 📋 **Decide on approach:** Option A, B, or C
3. [Issue] **Fix Bug #1** (skill name extraction) - takes 30 minutes
4. 📄 **Document decision** in ROADMAP.md

### Short-term (This Week)
- If Option A/C: Populate curated skills index, disable GitHub search, ship v1.0.0
- If Option B: Implement scoring improvements, re-test, then ship v1.0.0

### Medium-term (v1.1.0)
- Implement proper scoring with intent/domain matching
- Re-enable GitHub Code Search with quality filters
- Expand curated index to 100+ skills

---

## Lessons Learned

1. **Simplification has limits** - Removing intent/domain matching in Week 2 went too far
2. **Keyword matching ≠ relevance** - Need semantic understanding of skill PURPOSE
3. **Curated > Algorithmic for v1.0** - Better to ship small but high-quality
4. **Test on real repos** - Internal tests passed but real-world usage revealed critical gaps
5. **GitHub API changed** - External dependencies require monitoring (Feb 2024 auth requirement)

---

## [YES] Validation Checklist

- [x] Test on FastAPI backend → FAILED (0% relevance)
- [x] Test on Django REST → FAILED (0% relevance)
- [ ] Test on React TypeScript → BLOCKED (bugs found)
- [ ] Test on Vue.js SPA → BLOCKED
- [ ] Test on Rails app → BLOCKED
- [ ] Test on Go microservice → BLOCKED
- [ ] Test on Rust CLI → BLOCKED
- [ ] Test on Next.js full-stack → BLOCKED
- [ ] Test on Elixir Phoenix → BLOCKED
- [ ] Test on data science project → BLOCKED

**Status:** Testing stopped after 2/10 repos due to critical bugs.

---

**Conclusion:** v1.0.0-alpha validation FAILED. Critical bugs found. Recommend Option C (curated index for v1.0, GitHub search in v1.1). Cannot proceed to stable release without fixes.

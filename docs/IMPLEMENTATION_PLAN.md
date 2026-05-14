# agent-hunter Core Implementation Plan

**Version:** 1.0 (PLAN.md aligned)
**Goal:** Ship a focused, 10/10 repo-aware skill package manager for Claude Code
**Test Coverage Target:** 100%
**Speed Target:** <30 seconds for meaningful results

---

## I. Core Product Truth

### What we're building
> **"A repo-aware skill package manager for Claude Code that tells you the top 3 skills/MCPs you should use now, why they fit, and which ones to avoid."**

### What we're NOT building
- A broad discovery catalog
- A feature-rich ecosystem control plane
- A self-evolving AI system
- A security research platform

### Success metric
Users feel: **"I should run this before building anything non-trivial"**

---

## II. Hard Requirements (from PLAN.md)

### 4.0 New project onboarding
- [YES] Must work with NO local CLAUDE.md
- [YES] Global `~/.claude/CLAUDE.md` activation
- [YES] Project CLAUDE.md is optional, comes after first value

### 4.1 One-command install
```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter && ./setup
```

### 4.2 One-command run
```bash
/agent-hunter
# or
agent-hunter hunt .
```

### 4.3 Top 3 by default
- Show best 3 recommendations
- More on explicit request only
- Avoid result floods

### 4.4 Strong "why this for you"
Each result must explain:
- Why this repo
- Why now
- Why this over others

### 4.5 Trust communication
- Safe to install
- Review before installing
- Blocked

### 4.6 Speed
- Target: <30 seconds
- Never feel "slow but smart"

### 4.7 Real proof
- One real demo video
- Three real repo examples
- Actual useful finds

### 4.8 Full credibility
- All docs say the same thing
- No contradictions
- No placeholder media
- No stale examples

---

## III. What to Keep vs Cut

### KEEP (core to product promise)
1. **hunt command** - the main workflow
2. **Context extraction** - privacy-safe tech stack detection
3. **GitHub search** - curated index + optional API
4. **Security scanning** - simplified, clear trust tiers
5. **Ranking** - top 3 focus, strong explanations
6. **Registry** - track installs
7. **Install flow** - guided, safe
8. **Audit** - health check installed skills
9. **Rollback** - restore to known good

### CUT/SIMPLIFY (not core to v1)
1. [NO] `update` command → merge into audit workflow
2. [NO] `scaffold` command → separate tool, not package manager
3. [NO] `resolve-deps` command → fold into install
4. [NO] Complex self-evolving language in docs
5. [NO] Over-detailed security marketing
6. [NO] Too many metadata fields in results
7. [NO] Dependency resolution complexity → v2

### SIMPLIFY
1. **Security scan** - keep 10 core patterns, remove noise
2. **Trust tiers** - verified, community, raw (3 only)
3. **Scoring** - 4 signals max (stack, trust, recency, stars)
4. **Output** - markdown table, 3 rows default
5. **Config** - minimal, paths only

---

## IV. Architecture (Simplified)

```
User runs: /agent-hunter
 ↓
1. context_extractor.py
 → Reads repo files
 → Extracts ONLY tech keywords (privacy-safe)
 → Returns ContextProfile
 ↓
2. hunter.py
 → Queries curated index first
 → Optional: GitHub API if token present
 → Returns List[HuntResult]
 ↓
3. security_scan.py (per result)
 → 10 core patterns
 → Returns trust tier: verified/community/raw
 ↓
4. scorer.py
 → 4-signal scoring: stack_match, trust, recency, stars
 → Returns top 3 ScoredResult
 ↓
5. reporter.py
 → Markdown table output
 → Show top 3, count blocked
 → Clear next actions
 ↓
6. installer.py (on user confirm)
 → Git clone to ~/.claude/skills/
 → Update registry
 → Success message
```

**No LLM calls from scripts. All reasoning in SKILL.md.**

---

## V. File Structure (Minimal)

```
agent-hunter/
├── SKILL.md # Claude's brain (routing + workflow)
├── README.md # User-facing docs (aligned with SKILL.md)
├── VERSION # Single source of truth
├── setup # Install script
├── pyproject.toml # Project metadata
├── requirements.txt # Python deps
├── bin/
│ ├── hunt # Main entry point
│ ├── audit # Health check
│ └── rollback # Restore registry
├── scripts/
│ ├── main.py # CLI orchestrator
│ ├── context_extractor.py
│ ├── hunter.py
│ ├── security_scan.py
│ ├── scorer.py
│ ├── reporter.py
│ ├── installer.py
│ ├── registry.py
│ ├── audit.py
│ └── rollback.py
├── config/
│ └── defaults.json # Minimal config
├── references/
│ ├── VERIFIED_SKILLS.md # Curated index
│ └── SECURITY_PATTERNS.md # 10 core patterns
└── tests/
 ├── test_context_extractor.py
 ├── test_hunter.py
 ├── test_security_scan.py
 ├── test_scorer.py
 ├── test_reporter.py
 ├── test_installer.py
 ├── test_registry.py
 ├── test_audit.py
 ├── test_rollback.py
 └── test_main.py
```

**Remove:**
- [NO] `scripts/scaffold.py`
- [NO] `scripts/dep_resolver.py` (v2)
- [NO] `scripts/mcp_parser.py` (merge into hunter)
- [NO] `scripts/typo_detect.py` (v2)
- [NO] `scripts/verify_sig.py` (v2)
- [NO] `scripts/update.py` (merge into audit)
- [NO] `scripts/release.py` (not user-facing)

---

## VI. Scoring Algorithm (Simplified)

### Research-based design
From web research, recommendation systems use:
- Multiple candidate generators
- Scoring function for relevance
- Position-aware ranking (NDCG, MAP)
- Contextual signals (time, location, behavior)

### Our 4-signal scoring

```python
total_score = (
 stack_match × 0.40 # Does it match my tech stack?
 + trust_score × 0.30 # Is it safe?
 + recency_score × 0.15 # Is it maintained?
 + star_score × 0.15 # Is it popular?
) × yagni_multiplier

# YAGNI multiplier
active (commits <7d): 2.0×
recent (commits <30d): 1.0×
dormant (commits >90d): 0.5×

# Trust tiers
verified: 1.0 # In curated index
community: 0.7 # GitHub, >50 stars
raw: 0.4 # GitHub, new/unknown
```

**Simplified from 6 signals to 4.** Intent and domain folded into stack_match.

---

## VII. Security Scanning (10 Core Patterns)

Based on OWASP Top 10 for LLM/AI research:

1. **Prompt injection** - `os.system()`, `subprocess`, `eval()`
2. **Data exfiltration** - `requests.post()`, `urllib.request`
3. **Filesystem access** - `open()`, `write()`, `Path().unlink()`
4. **Environment leaks** - `os.environ`, `getenv()`
5. **Code execution** - `exec()`, `compile()`, `__import__()`
6. **Shell injection** - backticks, `$()`, shell=True
7. **Credential access** - `.env`, `config.json`, `secrets/`
8. **Network access** - `socket`, `http.client`
9. **Obfuscation** - base64, hex, rot13
10. **Suspicious domains** - known malicious patterns

**Remove:**
- SEO poisoning detection (low signal)
- Typo-squat detection (v2)
- Crypto signature verification (v2)

---

## VIII. Test Strategy (100% Coverage)

### TDD approach (from research)
1. **Red** - Write failing test
2. **Green** - Minimal code to pass
3. **Refactor** - Clean up, tests stay green

### Test patterns

#### Unit tests (pytest)
```python
# tests/test_scorer.py
def test_score_results_top_3_only():
 results = [mock_result(i) for i in range(10)]
 profile = ContextProfile(stack=["fastapi"])
 scored = score_results(results, profile)
 assert len(scored) == 3 # Top 3 only
 assert scored[0].total_score >= scored[1].total_score
```

#### Integration tests
```python
# tests/test_integration.py
def test_full_hunt_workflow(tmp_path):
 project_root = tmp_path / "test_project"
 project_root.mkdir()
 (project_root / "requirements.txt").write_text("fastapi==0.100.0")

 # Run full pipeline
 ctx = extract_context(str(project_root))
 results = hunter.search(ctx)
 scanned = [scan_skill(r) for r in results]
 scored = score_results(scanned, ctx)

 assert len(scored) >= 1
 assert scored[0].trust_tier in ["verified", "community", "raw"]
```

#### CLI tests
```python
# tests/test_main.py
def test_hunt_command_success(tmp_path, monkeypatch):
 monkeypatch.setenv("AGENT_HUNTER_REGISTRY", str(tmp_path / "registry.json"))
 result = subprocess.run(["python", "scripts/main.py", "hunt", "."], capture_output=True)
 assert result.returncode == 0
 assert "Top 3 recommendations" in result.stdout.decode()
```

#### Fixture-based tests
```python
# tests/conftest.py
@pytest.fixture
def mock_github_response():
 return {
 "items": [
 {"name": "SKILL.md", "repository": {"html_url": "...", "stargazers_count": 100}}
 ]
 }
```

### Coverage targets
- **Unit tests:** 100% of scripts/
- **Integration tests:** End-to-end workflows
- **CLI tests:** All commands
- **Edge cases:** Error handling, empty results, network failures

---

## IX. Path Injection (Testability)

**Problem:** Current code hard-codes `~/.agent-hunter/`, making tests fragile.

**Solution:** Inject paths via env vars or config.

```python
# Before
REGISTRY_PATH = Path.home() / ".agent-hunter" / "registry.json"

# After
REGISTRY_PATH = Path(os.getenv("AGENT_HUNTER_REGISTRY",
 str(Path.home() / ".agent-hunter" / "registry.json")))
```

**Benefit:** Tests can use tmp_path, no side effects on user system.

---

## X. Implementation Phases (Week-by-Week)

### Week 1: Truth restoration (PLAN.md Phase 1)
**Goal:** Remove contradictions, align messaging

Tasks:
1. [YES] Sync VERSION to 0.9.0 across all files
2. [YES] Rewrite README.md positioning (1-liner from PLAN.md)
3. [YES] Simplify SKILL.md (remove self-evolving language)
4. [YES] Remove placeholder media mentions
5. [YES] Align pyproject.toml metadata
6. [YES] Remove stale SPEC.md/ROADMAP.md sections

Deliverable: All docs say the same thing, no contradictions.

### Week 2: Core simplification (PLAN.md Phase 2+3)
**Goal:** Cut non-core features, improve recommendation quality

Tasks:
1. [YES] Remove scripts: scaffold.py, dep_resolver.py, typo_detect.py, verify_sig.py, update.py, release.py
2. [YES] Simplify scorer.py to 4 signals
3. [YES] Reduce security_scan.py to 10 core patterns
4. [YES] Path injection for testability
5. [YES] Top 3 default output in reporter.py
6. [YES] Improve "why this for you" explanations

Deliverable: Simplified codebase, ready for 100% test coverage.

### Week 3: Test coverage (PLAN.md Phase 3)
**Goal:** 100% test coverage, TDD for new code

Tasks:
1. [YES] Write unit tests for all scripts/ (pytest)
2. [YES] Integration tests for full hunt workflow
3. [YES] CLI tests for main.py commands
4. [YES] Edge case tests (errors, empty, failures)
5. [YES] Fixtures for mock data
6. [YES] Coverage report (pytest-cov)

Deliverable: All tests green, 100% coverage.

### Week 4: Real-world validation (PLAN.md Phase 4+5)
**Goal:** Prove it works on real repos

Tasks:
1. [YES] Test on 10 real repos (FastAPI, React, ML, CLI, etc.)
2. [YES] Collect weak recommendation cases
3. [YES] Tune ranking for quality
4. [YES] Record demo video
5. [YES] Prepare 3 example runs
6. [YES] Screenshots for README

Deliverable: Proof of value, ready to launch.

---

## XI. Success Criteria (Launch Gate)

From PLAN.md §14B:

### Product gate
- [ ] Install works cleanly
- [ ] Global CLAUDE.md activation works
- [ ] New-project flow (no local CLAUDE.md) works
- [ ] Top 3 output feels high-signal
- [ ] Next step obvious from result screen

### Quality gate
- [ ] README matches reality
- [ ] SKILL.md, setup, versioning aligned
- [ ] No placeholder media
- [ ] No inflated feature claims

### Engineering gate
- [ ] All tests green
- [ ] 100% coverage (pytest-cov)
- [ ] Path/config behavior reliable
- [ ] Failure states understandable

### Proof gate
- [ ] Real demo recorded
- [ ] 3 strong repo examples
- [ ] Top 3 quality proven on real runs
- [ ] ≥3 external users tried it
- [ ] Clear saved time reported

---

## XII. Key Research Insights Applied

### From package manager research
- **One version model** (Homebrew) - we keep latest only
- **Source distribution** - git clone, auditable
- **Security first** - prevent dependency confusion

### From recommendation systems research
- **Multiple signals** - stack, trust, recency, popularity
- **Position matters** - top 3 get most attention
- **Context-aware** - repo-specific explanations

### From OWASP AI security research
- **Prompt injection** - #1 risk, detect `eval()`, `exec()`
- **Semantic firewall** - scan before showing to user
- **Least privilege** - never auto-install

### From TDD research
- **Red-Green-Refactor** - write tests first
- **Pytest > unittest** - more expressive
- **Fixtures** - reusable test data
- **Balance** - 100% coverage is good, but focus on quality

---

## XIII. Documentation Strategy

### User-facing (README.md)
- **Hero:** ""
- **One-liner:** "Repo-aware skill package manager for Claude Code"
- **Install:** 30 seconds, one command
- **First run:** Obvious, fast, valuable
- **Examples:** Real repos, real results

### Developer-facing (CLAUDE.md)
- **Architecture:** Simple diagram
- **Coding rules:** No LLM calls, privacy-safe
- **Test strategy:** TDD, 100% coverage
- **Contribution:** How to add patterns, skills

### Product-facing (SKILL.md)
- **Workflow:** Step-by-step Claude instructions
- **Routing:** When to activate (not aggressive)
- **Privacy:** Clear contract
- **Output:** Structured, actionable

---

## XIV. Decision Rules

From PLAN.md §15:

### Build it if
- [YES] Improves top 3 recommendation quality
- [YES] Improves trust
- [YES] Improves first-run clarity
- [YES] Improves install success
- [YES] Improves speed meaningfully

### Delay it if
- [NO] Adds complexity without user value
- [NO] Expands scope before quality is high
- [NO] Is mostly infrastructure vanity
- [NO] Is hard to explain in one sentence

### Cut it if
- [NO] Weakens product story
- [NO] Adds maintenance burden but no user pull
- [NO] Creates more claims than proof

---

## XV. Next Steps

1. [YES] Review this plan
2. [YES] Create new branch: `feat/plan-aligned-core`
3. [YES] Week 1: Truth restoration
4. [YES] Week 2: Core simplification
5. [YES] Week 3: Test coverage
6. [YES] Week 4: Real-world validation
7. [YES] Launch gate check
8. [YES] Ship v1.0

**The goal is not to make agent-hunter bigger.
The goal is to make it feel inevitable.**

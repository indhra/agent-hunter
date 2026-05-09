# agent-hunter v1.0.0-alpha Release Notes

**Release Date:** May 2026
**Type:** Alpha Release
**Focus:** Core functionality, simplified architecture, production-ready testing

> **Repo-aware skill package manager for Claude Code.**
> Before you build it again, check what already exists.

---

## 🎯 What is agent-hunter?

agent-hunter is a focused package manager for Claude Code skills and MCP servers. It reads your project context, hunts GitHub for the top 3 most relevant skills, security-scans every result, and surfaces ranked recommendations.

**Three core commands:**
1. `agent-hunter hunt` - Find the top 3 skills for your project
2. `agent-hunter audit` - Health check installed skills
3. `agent-hunter rollback` - Restore to last known good state

**Key principle:** One version of the truth. Like Homebrew, we show you the best match — not a marketplace.

---

## 🚀 What's New in v1.0.0-alpha

### Simplified Architecture

**Before (v0.8.0):**
- 11 commands (hunt, context, scaffold, install, remove, enable, update, audit, rollback, contribute, resolve-deps)
- 6 scoring signals (intent_match, domain_match, stack_match, stars, recency, trust)
- Default top 5 recommendations
- 15+ Python modules
- ~4,800 lines of code

**After (v1.0.0-alpha):**
- **3 core commands** (hunt, audit, rollback)
- **4 scoring signals** (stack_match, trust, recency, stars)
- **Top 3 recommendations** (position-aware ranking)
- **8 core modules** (hunter, scorer, security_scan, context_extractor, registry, installer, audit, rollback)
- **~2,750 lines of code** (-43% reduction)

### Scoring Algorithm Improvements

Simplified from 6 to 4 signals with research-backed weights:

```python
total_score = (
    stack_match × 0.40 +    # Technical fit (40%)
    trust_score × 0.30 +    # Trust tier (30%)
    recency × 0.15 +        # Recent activity (15%)
    stars × 0.15            # Popularity (15%)
) × yagni_multiplier
```

**YAGNI multipliers** (You Aren't Gonna Need It):
- Active domain (last 30 days): 2.0×
- Recent domain (31-180 days): 1.0×
- Dormant domain (>180 days): 0.5×

**Trust tiers:**
- Verified: 1.0 (curated index + signature validation)
- Community: 0.7 (GitHub with >50 stars)
- Raw: 0.4 (any GitHub result)

### Security Enhancements

**10 core OWASP LLM security patterns:**
1. Prompt injection (LLM01)
2. Shell command execution
3. Eval/exec code execution
4. Data exfiltration (network, filesystem)
5. Environment variable leaks
6. Credential access
7. Suspicious domains
8. Obfuscation patterns
9. Unicode homoglyphs
10. Path traversal

**RED results policy:** Never shown to user. Count only. Dangerous skills are disabled (reversible rename), not deleted.

### Testing Infrastructure

**Coverage:** 92% (2,014 statements, 166 missing)

**Per-module coverage:**
- security_scan.py: 100%
- reporter.py: 99%
- main.py: 98%
- audit.py: 97%
- scorer.py: 97%
- context_extractor.py: 96%

**Path injection for isolated testing:**
- `AGENT_HUNTER_REGISTRY` - registry.json location
- `AGENT_HUNTER_SKILLS_DIR` - skills installation directory
- `AGENT_HUNTER_INSTALL_LOG` - install log path
- `AGENT_HUNTER_BACKUPS` - backups directory

Tests run in isolation without touching `~/.claude/skills/` or `~/.agent-hunter/`.

### Privacy Guarantees

Context extraction transmits **only tech keywords** from an explicit allowlist:
- Framework names: fastapi, django, react, vue, rails, spring, etc.
- Library names: pandas, numpy, sqlalchemy, etc.

**Never transmitted:**
- File paths
- Variable names
- Function names
- Class names
- Commit messages
- Repository name
- Any project-specific strings

### Performance

**Target:** <30 seconds for meaningful results

**Actual (internal testing):**
- Cold start (no cache): ~8-12 seconds
- Warm start (with cache): ~3-5 seconds
- GitHub API rate limit: 30 requests/minute (authenticated)

---

## 📦 Installation

### Prerequisites

- Python 3.10+
- Git
- GitHub personal access token (optional, enables broader discovery)

### Install

```bash
# Clone the repository
git clone https://github.com/indhra/agent-hunter.git
cd agent-hunter

# Install dependencies
pip install -r requirements.txt

# Optional: Set GitHub token for broader search
export GITHUB_TOKEN="ghp_your_token_here"
```

### Verify Installation

```bash
python scripts/main.py --help
```

---

## 🎯 Usage

### Hunt for Skills

```bash
# From your project directory
python scripts/main.py hunt .

# Output:
# Top 3 Skills for Your Project
#
# 1. fastapi-expert (95/100)
#    📦 github.com/awesome/fastapi-expert
#    ✅ Verified • 234 ⭐ • Updated 2 days ago
#    Perfect match for FastAPI + PostgreSQL + Redis
#
# 2. api-testing-suite (87/100)
#    📦 github.com/testing/api-suite
#    🟢 Community • 156 ⭐ • Updated 1 week ago
#    API testing patterns for REST endpoints
#
# 3. docker-compose-helper (82/100)
#    📦 github.com/devops/docker-compose
#    🟢 Community • 89 ⭐ • Updated 3 weeks ago
#    Docker Compose workflow automation
```

### Audit Installed Skills

```bash
python scripts/main.py audit

# Output:
# Installed Skills Health Check
#
# ✅ fastapi-expert - Healthy
# ✅ api-testing-suite - Healthy
# 🟡 docker-compose-helper - Update available
```

### Rollback to Safe State

```bash
python scripts/main.py rollback

# Output:
# Available snapshots:
# 1. pre-audit-2026-05-08-14-23-15
# 2. pre-audit-2026-05-07-09-45-32
#
# Select snapshot to restore: 1
# ✅ Restored registry to pre-audit-2026-05-08-14-23-15
```

---

## 🔧 Configuration

Default config: `config/defaults.json`

User config: `~/.agent-hunter/config.json`

**Key settings:**

```json
{
  "hunt": {
    "top_n_shown": 3,
    "timeout_sec": 30,
    "phase": "launch"
  },
  "scoring": {
    "weights": {
      "stack_match": 0.40,
      "trust_score": 0.30,
      "recency_score": 0.15,
      "star_score": 0.15
    }
  },
  "security": {
    "scan_enabled": true,
    "red_count_only": true
  }
}
```

---

## 📊 What Changed from v0.8.0

### Removed Features

**Commands:**
- `context` - Folded into hunt workflow
- `scaffold` - Out of scope for package manager
- `install` - Automatic via hunt confirmation
- `remove` - Use standard tools (rm -rf)
- `enable` - Use standard tools (mv)
- `update` - Folded into audit workflow
- `contribute` - Out of scope

**Modules:**
- `scaffold.py` - Skill creation helper (out of scope)
- `dep_resolver.py` - Dependency conflict detection (deferred to v2)
- `mcp_parser.py` - MCP config parsing (inlined into hunter.py)
- `typo_detect.py` - Typo-squat detection (deferred to v2)
- `verify_sig.py` - Cryptographic signatures (deferred to v2)
- `update.py` - Skill update command (folded into audit)
- `release.py` - Release automation (out of scope)

**Scoring signals:**
- `intent_match` - Folded into stack_match
- `domain_match` - Folded into stack_match

### Why These Changes?

**Focus on core value:** Package manager that finds the best skill, not a skill development IDE.

**Simplicity:** 3 commands are easier to learn and maintain than 11.

**Performance:** 4 scoring signals are faster to compute than 6.

**Trust:** Security scanning is mandatory, not optional.

**Reliability:** 92% test coverage with isolated tests.

---

## 🐛 Known Limitations (Alpha)

### Expected Behaviors

1. **GitHub token recommended** - Unauthenticated requests have lower rate limits
2. **English-only** - Tech keywords extracted from English project files
3. **GitHub-only** - No GitLab, Bitbucket, or custom Git servers yet
4. **SKILL.md format** - Only scans for Claude Code SKILL.md files
5. **Personal install only** - Always installs to `~/.claude/skills/`, not project-level

### Deferred to v1.1.0+

1. **Dependency conflict detection** - Currently no cross-skill dependency analysis
2. **Typo-squat detection** - No Levenshtein distance checks on package names
3. **Cryptographic signatures** - No GPG signature verification
4. **MCP marketplace** - Currently limited to GitHub search
5. **Docker sandbox testing** - Subprocess isolation only (Docker opt-in not wired)

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=scripts --cov-report=term-missing

# Isolated tests (won't touch your actual skills)
export AGENT_HUNTER_SKILLS_DIR="/tmp/test-skills"
export AGENT_HUNTER_REGISTRY="/tmp/test-registry.json"
pytest tests/ -v
```

### Test Results (v1.0.0-alpha)

```
634 tests passing
0 tests failing
92% code coverage
100% pass rate
```

---

## 📚 Documentation

- [SPEC.md](SPEC.md) - Full technical specification
- [ROADMAP.md](ROADMAP.md) - Version roadmap v0.4.0 → v1.0.0
- [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) - 4-week execution plan
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) - Security scan patterns

---

## 🙏 Acknowledgments

**Inspiration:**
- Homebrew (one-version package manager model)
- OWASP LLM Top 10 (security patterns)
- Claude Code (skill ecosystem)

**Research:**
- Position-aware ranking (top 3 vs top 5)
- YAGNI multipliers (active vs dormant projects)
- Trust tier scoring (verified > community > raw)

---

## 🚀 What's Next?

### v1.0.0 (Stable)

- Real-world validation on 10+ repo types
- Scoring weight tuning based on user feedback
- Performance benchmarks
- Demo video
- Public launch

### v1.1.0 (Enhanced)

- Dependency conflict detection
- Typo-squat protection
- Cryptographic signature verification
- MCP marketplace integration
- Docker sandbox testing

### v2.0.0 (Enterprise)

- GitLab/Bitbucket support
- Private registry support
- Team collaboration features
- Usage analytics
- CVE index integration

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---

## 🐛 Bug Reports

Found a bug? [Open an issue](https://github.com/indhra/agent-hunter/issues)

**Include:**
1. Command you ran
2. Expected behavior
3. Actual behavior
4. Error message (if any)
5. Your Python version (`python --version`)

---

## 💬 Feedback

We'd love to hear from you:

- What skills did agent-hunter recommend?
- Were the recommendations relevant?
- What could be better?

Share feedback: [GitHub Discussions](https://github.com/indhra/agent-hunter/discussions)

---

**Thank you for trying agent-hunter v1.0.0-alpha!**

The best skills are the ones you don't have to build yourself. 🚀

# ROADMAP.md Update for v1.0.0-alpha

**Changes needed:** ROADMAP.md currently describes the old incremental v0.1.0 → v1.0.0 plan. It needs to be updated to reflect the actual path taken (simplified architecture).

---

## Current Status (Reality)

**Version:** v1.0.0-alpha
**Architecture:** Simplified 3-command package manager
**Code:** 2,750 lines (down from 4,800)
**Commands:** hunt, audit, rollback (down from 11)
**Scoring:** 4 signals (down from 6)
**Test coverage:** 92%
**Status:** Ready for real-world validation

---

## Proposed ROADMAP.md Structure

### Section 1: Version History (What Actually Happened)

```markdown
## v0.1.0 - v0.8.0 (Archive)

Early development explored maximum feature set:
- 11 commands (hunt, context, scaffold, install, remove, enable, update, audit, rollback, contribute, resolve-deps)
- 6 scoring signals
- 15+ Python modules
- Dependency conflict detection
- Typo-squat protection
- Cryptographic signatures
- MCP marketplace integration

**Learning:** Feature bloat obscured core value. Users wanted simplicity.

## v1.0.0-alpha (Current - May 2026)

**Mission:** Be the Homebrew of Claude Code skills.

Complete architecture reset focused on package manager core:
- **3 commands:** hunt, audit, rollback
- **4 signals:** stack_match (40%), trust (30%), recency (15%), stars (15%)
- **Top 3 recommendations** (position-aware ranking)
- **92% test coverage** with isolated testing
- **OWASP LLM security** (10 core patterns)
- **Privacy-preserving** context extraction

**Code reduction:** -43% (4,800 → 2,750 lines)

**Status:** [YES] Ready for real-world validation

**Remaining for v1.0.0 stable:**
- Real-world validation on 10+ repo types
- Scoring weight tuning based on user feedback
- Demo video
- Public launch
```

### Section 2: Future Roadmap (What's Next)

```markdown
## v1.0.0 Stable (Target: June 2026)

**Gate:** Real-world validation complete + demo video recorded

Deliverables:
- [YES] Validated on 10+ different repo types
- [YES] Scoring weights tuned based on actual results
- [YES] Demo video published
- [YES] Release notes finalized
- [YES] Public GitHub launch

No new features. Stabilization only.

---

## v1.1.0 (Target: Q3 2026)

**Theme:** Enhanced Trust & Safety

Features:
- Dependency conflict detection (restore from v0.7.0 research)
- Typo-squat protection (Levenshtein distance checks)
- Cryptographic signature verification (GPG)
- Enhanced MCP server discovery
- Docker sandbox integration (opt-in)

**Requirement:** v1.0.0 must be stable first.

---

## v1.2.0 (Target: Q4 2026)

**Theme:** Enterprise Features

Features:
- Private registry support
- GitLab/Bitbucket skill discovery
- Team collaboration (shared registries)
- Usage analytics dashboard
- Skill dependency trees

**Requirement:** v1.1.0 trust features proven.

---

## v2.0.0 (Target: 2027)

**Theme:** Platform Integration

Features:
- Native Claude Desktop integration
- MCP marketplace (official)
- CVE index integration
- Skill health monitoring service
- Community skill ratings

**Breaking change:** New registry schema, new SKILL.md format.

---

## Features NOT on Roadmap

Explicitly out of scope:

1. **Skill development IDE** - Use your editor, not agent-hunter
2. **Skill scaffolding** - Templates obscure learning
3. **Skill contribution workflow** - Use GitHub directly
4. **Marketplace hosting** - GitHub is the source of truth
5. **Paid skill directory** - Open source only

**Why:** Package manager should find skills, not create them.
```

---

## Recommendation

Replace current ROADMAP.md with this updated version that:
1. Acknowledges the simplification from v0.8.0
2. Documents v1.0.0-alpha as current state
3. Shows clear path to v1.0.0 stable
4. Maps future versions (v1.1.0, v1.2.0, v2.0.0)
5. Explicitly lists out-of-scope features

This gives users realistic expectations and shows the project's maturity trajectory.

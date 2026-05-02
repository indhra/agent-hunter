# Verified Skills

Community-curated list of skills that have been manually reviewed, security-scanned, and vouched for by a maintainer or trusted contributor.

**Trust tier:** These skills receive a `+0.25` score bonus in agent-hunter's relevance ranking because a human has done the due diligence you'd otherwise have to do yourself.

**What "verified" means:**
- Full SKILL.md was read (not just the description)
- Repo history checked for sudden ownership changes
- security_scan.py returned 🟢 (no RED flags)
- Reviewed by someone who is NOT the skill's author
- Skill was tested in a real project

To contribute a verified skill, see [CONTRIBUTING.md](../CONTRIBUTING.md#type-3-verified-skills).

---

## Format

```markdown
### skill-name
- **Repo:** https://github.com/owner/repo
- **Version reviewed:** vX.Y.Z
- **SHA at review:** [full git tree SHA]
- **License:** [SPDX identifier]
- **Reviewer:** @github-handle
- **Review date:** YYYY-MM-DD
- **Stack:** [comma-separated tech it's designed for]
- **Why verified:** [one sentence]
```

---

## Verified Skills

<!--
████████████████████████████████████████████████████
  PLACEHOLDER — VERIFIED SKILLS
  Target: 25+ entries by v1.0.0 release.
  First entries will be added by maintainer after
  manual review of top GitHub SKILL.md results.
  Contributors: use the format above and open a PR.
████████████████████████████████████████████████████
-->

*No verified skills yet — this list is seeded during v0.2.0 development.*

*Want to be first? Review a skill you've used in production and [open a PR](https://github.com/indhra/agent-hunter/pulls).*

---

## Known Malicious Skills

Skills that have been identified as malicious, containing prompt injection, hidden code, or supply-chain compromise. These are **permanently blocked** — they will never appear in hunt results regardless of score.

| Repo | Reason | Source | Date flagged |
|---|---|---|---|
| *(seeded from Snyk ToxicSkills report during v0.2.1 development)* | — | — | — |

To report a malicious skill, open a [Security Pattern issue](https://github.com/indhra/agent-hunter/issues/new?template=security_pattern.md).

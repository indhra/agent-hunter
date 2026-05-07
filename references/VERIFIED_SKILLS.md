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

### browse
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `browse/SKILL.md`
- **Version reviewed:** v1.1.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (browser automation, QA)
- **Why verified:** Headless browser control for QA and dogfooding; GREEN security scan, no shell exec or prompt injection patterns; widely used gstack core skill.

### qa
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `qa/SKILL.md`
- **Version reviewed:** v2.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (testing, QA, bug reproduction)
- **Why verified:** Iterative QA loop that finds and fixes bugs with browser evidence; GREEN scan, no dangerous patterns.

### review
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `review/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (code review, diff analysis)
- **Why verified:** Code review skill checking boundary violations, conditional side effects, and structural issues; GREEN scan, no shell exec.

### autoplan
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `autoplan/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (planning, CEO/eng/design review automation)
- **Why verified:** Runs CEO, design, eng, and DX review skills sequentially with auto-decisions; GREEN scan; orchestration-only with no direct shell/file writes.

### codex
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `codex/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (code review, adversarial testing, second opinion)
- **Why verified:** OpenAI Codex CLI wrapper for independent diff review and adversarial testing; GREEN scan; does not write files directly.

### canary
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `canary/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (monitoring, post-deploy verification)
- **Why verified:** Post-deploy canary monitoring using browse daemon; GREEN scan; read-only observation pattern, no writes or shell exec.

### health
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `health/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (code quality, linting, test coverage)
- **Why verified:** Code quality dashboard wrapping existing project tools; GREEN scan; does not modify files, orchestration-only.

### retro
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `retro/SKILL.md`
- **Version reviewed:** v2.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (retrospective, code quality metrics, trend tracking)
- **Why verified:** Sprint retrospective with persistent quality metric history; GREEN scan; reads project state, writes only to `.retro/` local directory.

### document-release
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `document-release/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (documentation, changelog, README sync)
- **Why verified:** Post-ship doc updater that reads diff and updates project docs; GREEN scan; no network writes or shell exec beyond git.

### learn
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `learn/SKILL.md`
- **Version reviewed:** v1.0.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (session memory, lessons learned, knowledge management)
- **Why verified:** Records and retrieves lessons learned across sessions; GREEN scan; writes only to designated session log files, no exec patterns.

### freeze
- **Repo:** https://github.com/garrytan/gstack
- **Path:** `freeze/SKILL.md`
- **Version reviewed:** v0.1.0
- **SHA at review:** b512be7117eda1016f3ebf1fef0687f2c6b1cc37
- **License:** MIT
- **Reviewer:** @indhra
- **Review date:** 2026-05-06
- **Stack:** any (safety, edit scoping, debugging guardrails)
- **Why verified:** Restricts Claude edits to a specified directory for the session; GREEN scan; safety guardrail with no shell exec.

---

## Known Malicious Skills

Skills that have been identified as malicious, containing prompt injection, hidden code, or supply-chain compromise. These are **permanently blocked** — they will never appear in hunt results regardless of score.

| Repo | Reason | Source | Date flagged |
|---|---|---|---|
| *(seeded from Snyk ToxicSkills report during v0.2.1 development)* | — | — | — |

To report a malicious skill, open a [Security Pattern issue](https://github.com/indhra/agent-hunter/issues/new?template=security_pattern.md).

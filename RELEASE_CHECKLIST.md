# v1.0.0 Release Checklist

This checklist ensures agent-hunter is ready for public release as the "first skill to install after Claude Code."

---

## Pre-Release (This Week)

### Code Quality
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Linting clean (`ruff check .`)
- [ ] No unhandled exceptions in core workflows
- [ ] Hunt, audit, rollback commands all working
- [ ] Proactive detection mechanism (bin/detect-project) tested

### Documentation
- [ ] [x] SKILL.md - Complete with all workflows
- [ ] [x] README.md - Updated with goal and quick start
- [ ] [x] GETTING_STARTED.md - Step-by-step install guide
- [ ] [x] INSTALL.md - Detailed setup + proactive mode
- [ ] [x] DISTRIBUTION.md - How to package and distribute
- [ ] [x] .claude/CLAUDE.md - Project-level configuration
- [ ] [ ] CONTRIBUTING.md - Updated with v1.0.0 info
- [ ] [ ] CHANGELOG.md - Final v1.0.0 entry
- [ ] [ ] bin/detect-project - Proactive detection working

### Testing
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Test installation on clean machine
- [ ] Test `/agent-hunter` in new project
- [ ] Test `/agent-hunter` in existing project
- [ ] Test audit workflow
- [ ] Test rollback workflow
- [ ] Test proactive mode with `AGENT_HUNTER_AUTO=1`
- [ ] Test without `GITHUB_TOKEN` (uses curated index only)
- [ ] Test with `GITHUB_TOKEN` (all 3 tiers)
- [ ] Test security scanning blocks risky skills

### Package Preparation
- [ ] Version bumped to 1.0.0 in SKILL.md
- [ ] Version bumped to 1.0.0 in README.md
- [ ] Version bumped to 1.0.0 in setup script
- [ ] Version bumped to 1.0.0 in scripts/main.py
- [ ] All TODOs and FIXMEs resolved
- [ ] License file present and correct (MIT)
- [ ] .gitignore complete

---

## Release Day (v1.0.0 Tag)

### Git Operations
- [ ] All commits created and pushed
- [ ] Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0: First-install skill"`
- [ ] Push tag: `git push origin v1.0.0`
- [ ] Verify on GitHub: https://github.com/indhra/agent-hunter/tags

### Security & Signing (Optional for v1.0.0, Required for v1.0.1+)
- [ ] (Optional) Cryptographic signing of release artifacts
- [ ] (Optional) Create checksums for release binaries
- [ ] Document verification steps in README

### GitHub Release
- [ ] Create GitHub release for v1.0.0
- [ ] Title: "agent-hunter v1.0.0 - The first skill to install after Claude Code"
- [ ] Description:
 ```markdown
 **agent-hunter v1.0.0** is production-ready and recommended as the first skill for all new Claude Code users.

 ## What's new in v1.0.0
 - Production-ready hunt, audit, and rollback workflows
 - Security scanning with 3-tier trust model
 - Proactive detection for new projects
 - Complete documentation for installation and distribution

 ## Installation
 ```bash
 git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
 cd ~/.claude/skills/agent-hunter && ./setup
 ```

 Then type `/agent-hunter` in any Claude Code session.

 ## Links
 - 📖 [GETTING_STARTED.md](./GETTING_STARTED.md) - Installation guide
 - [INSTALL.md](./INSTALL.md) - Detailed setup + proactive mode
 - [README.md](./README.md) - Overview + why use agent-hunter
 - 📦 [DISTRIBUTION.md](./DISTRIBUTION.md) - How to distribute

 ## Changelog
 See [CHANGELOG.md](./CHANGELOG.md) for full details.
 ```
- [ ] Upload any artifacts (tar.gz, checksums)
- [ ] Mark as "Latest release"

---

## Marketing & Promotion (Week After Release)

### Internal Announcement
- [ ] Slack/Discord announcement to core team
- [ ] Include installation link
- [ ] Include screenshot of typical hunt output

### External Announcement
- [ ] [ ] Blog post on Anthropic blog (coordinate with team)
 - What agent-hunter solves
 - How to install
 - Real-world examples
 - Future roadmap

- [ ] [ ] GitHub release announcement via Twitter/LinkedIn
 - Short teaser (< 280 chars)
 - Installation link
 - Hero screenshot

- [ ] [ ] Add to Claude Code documentation
 - Link from "First Skills to Install" section
 - Brief description and link to GETTING_STARTED.md

- [ ] [ ] Skill Marketplace Listings (if applicable)
 - **Smithery:** https://smithery.ai/
 - **Agensi.io:** https://agensi.io/
 - **MCP Market:** (if applicable)

### Community Engagement
- [ ] [ ] Post in Claude Code Discord
- [ ] [ ] Post in AI/ML communities (Reddit r/MachineLearning, HackerNews, etc.)
- [ ] [ ] Share in relevant GitHub discussions
- [ ] [ ] Email newsletter (if applicable)

---

## Post-Release Validation (First 2 Weeks)

### Feedback Collection
- [ ] [ ] Monitor GitHub issues for bugs
- [ ] [ ] Monitor GitHub discussions for questions
- [ ] [ ] Collect feedback from 10+ beta users
- [ ] [ ] Gather NPS score (Net Promoter Score)
- [ ] [ ] Track download/star growth

### Support & Documentation
- [ ] [ ] Create TROUBLESHOOTING.md based on support requests
- [ ] [ ] Update FAQ if needed
- [ ] [ ] Add known issues to README if critical

### Analytics (if available)
- [ ] [ ] Track GitHub downloads/clones
- [ ] [ ] Track usage metrics (if any telemetry, respect privacy)
- [ ] [ ] Monitor skill discovery success rate

---

## Bug Fix & Polish (First Month)

### Critical Issues
- [ ] Fix any bugs preventing installation
- [ ] Fix any bugs causing security scanning to fail
- [ ] Fix any false-positive security flags

### Minor Issues
- [ ] Performance optimizations if needed
- [ ] UX improvements based on feedback
- [ ] Documentation clarifications

### v1.0.1 Release (If Needed)
- [ ] [ ] Tag and release v1.0.1 with bugfixes
- [ ] [ ] Update all documentation
- [ ] [ ] Promote v1.0.1 as "latest" if critical bugs fixed

---

## Success Metrics (3 Months Post-Release)

**Goals for v1.0.0 → v1.0.x maturity:**

- [ ] [ ] 1,000+ GitHub stars
- [ ] [ ] 100+ GitHub issues (indicates engagement)
- [ ] [ ] 50+ community contributions
- [ ] [ ] 5,000+ users (estimated from analytics)
- [ ] [ ] Featured in "best Claude Code skills" lists
- [ ] [ ] Used in team workflows (team CLAUDE.md adoption)
- [ ] [ ] Zero critical security issues
- [ ] [ ] < 5% installation failure rate

**Long-term vision (v1.0.0 → v2.0.0):**

- [ ] [ ] Default included in Claude Code installer
- [ ] [ ] Adopted by 50%+ of new users
- [ ] [ ] Proactive mode enabled by default (with opt-out)
- [ ] [ ] Community-driven skill discovery integration
- [ ] [ ] Framework-specific discovery plugins (FastAPI plugin, React plugin, etc.)

---

## Version Readiness

### Current Status
- Release Date Target: 2026-05-14 (tentative)
- Blocking Issues: None known
- Risk Level: Low (core features tested, documentatio complete)

### Sign-Off
- [ ] Lead Developer: Indhra Kiranu N A
- [ ] Product Owner: (if applicable)
- [ ] Security Review: (if applicable)

---

## Release Notes Template

```markdown
# agent-hunter v1.0.0

**The first skill you should install after Claude Code.**

## Goal

You waste time rebuilding skills that already exist. agent-hunter changes that:
- Discovers relevant skills for your project automatically
- 🛡️ Security-scans every result before showing
- ⚡ Shows top 3 recommendations in < 30 seconds
- 🚫 Blocks risky skills completely (RED results never shown)

## 📦 Installation

One command:
```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter && ./setup
```

Then: `/agent-hunter` in any Claude Code session.

## Features

- **Three-tier discovery**: Curated index (instant) + GitHub API (with token) + web search (on-demand)
- **Context-aware ranking**: Top 3 skills matched to YOUR tech stack
- **Security-first**: Every result scanned; RED results blocked
- **Proactive mode**: Auto-hunt on new projects (optional)
- **Audit & rollback**: Check installed skills for security issues and tampering

## 📖 Documentation

- [GETTING_STARTED.md](./GETTING_STARTED.md) - Installation guide
- [INSTALL.md](./INSTALL.md) - Detailed setup + proactive mode
- [README.md](./README.md) - Overview + why use agent-hunter

## [Issue] Known Issues

None. Report any issues at: https://github.com/indhra/agent-hunter/issues

## 🙏 Thanks

Built by Indhra Kiranu N A. Inspired by the need to save time and block bad stuff.

---

**Hunt well. **
```

---

## Next Actions

1. [YES] Complete all items in **Pre-Release** section
2. Execute **Release Day** section
3. Run **Marketing & Promotion** campaign
4. Monitor **Post-Release Validation** feedback
5. Plan v1.0.1 or v1.1 based on feedback

---

**Released:** 2026-05-14
**Target Status:** Production-Ready [YES]
**User Base:** All Claude Code users (recommended first-install)

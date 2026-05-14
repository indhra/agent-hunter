# Distribution & Implementation Guide

This guide explains how agent-hunter is distributed, installed, and made available to Claude Code users worldwide.

---

## Goal

**agent-hunter** is the recommended **first-install skill** for any new Claude Code user. After installing Claude Code:

```
1. Install Claude Code
2. Install agent-hunter (./setup)
3. Open any project → /agent-hunter auto-surfaces top 3 skills
4. Install recommended skills
```

The user **never searches for skills manually** or **rebuilds what exists**.

---

## Distribution Model

### Current: Direct GitHub Clone

Users install by cloning the repo:

```bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter && ./setup
```

**Advantages:**
- ✅ Full transparency (source code visible)
- ✅ Easy to fork and customize
- ✅ Self-contained (no external package registry required)
- ✅ Version-controlled updates

**How to distribute:**
1. **GitHub README** — Add installation badge + quick start link
2. **Claude Code official docs** — Link from "first skills to install" section
3. **Skill marketplaces** — List on Smithery, Agensi.io, MCP Market
4. **Word of mouth** — Share in Discord, forums, AI communities

### Future: Package Registry (v2.0+)

When Claude Code adds a native SKILL package registry:

```bash
claude-code install agent-hunter
```

Would automatically:
- Download from registry
- Verify signature
- Run setup
- Register globally

**Preparation now:**
- ✅ Sign releases with cryptographic keys
- ✅ Maintain changelog of all versions
- ✅ Keep SKILL.md compatibility across versions
- ✅ Test in isolated CI/CD environments

---

## Installation Roadmap

### Phase 1: Public Beta (v1.0.0-alpha → v1.0.0)

**Timeline:** Now

**Goals:**
- ✅ Core features working (hunt, audit, rollback)
- ✅ Top 3 recommendation workflow solid
- ✅ Security scanning verified
- ✅ Installation script robust

**Rollout:**
1. Open-source release on GitHub
2. Add to skill discovery lists (Smithery, etc.)
3. Share in Claude communities
4. Gather feedback from 100+ users

**Distribution channels:**
- GitHub releases with checksums
- Documentation site
- Word of mouth / social media
- AI communities (Discord, Reddit, forums)

### Phase 2: Production (v1.0.0)

**Timeline:** After public beta feedback

**Goals:**
- ✅ Proactive mode fully tested
- ✅ Real-world validation on diverse projects
- ✅ Performance optimized
- ✅ All known bugs fixed

**What changes:**
- Cryptographic signing of releases
- Automated install verification
- Performance benchmarks published
- Community contributions merged

**Promotion:**
- Official Claude Code documentation link
- Anthropic blog post
- Partner integrations (GitHub, frameworks)

### Phase 3: Ecosystem Integration (v1.1+)

**Goals:**
- ✅ Native registry support
- ✅ Cross-platform distribution
- ✅ Enterprise deployment guides
- ✅ Team-wide activation via CLAUDE.md

**What it enables:**
- Single-command installation
- Auto-update mechanism
- Centralized skill marketplace
- Corporate licensing (optional)

---

## How Proactive Mode Works

### Session-Based Detection

When agent-hunter is installed globally (`~/.claude/CLAUDE.md`):

```
Session 1: Open project /path/to/project-a
  → agent-hunter checks: Is this a new project?
  → YES → runs hunt (if AGENT_HUNTER_AUTO=1)
  → Sets AGENT_HUNTER_RAN=true (guard for this session)

Session 2: Same project /path/to/project-a
  → agent-hunter checks: Same project as last session?
  → YES → skip hunt (already recommended)

Session 3: New project /path/to/project-b
  → agent-hunter checks: Is this a new project?
  → YES → runs hunt again
  → Sets AGENT_HUNTER_RAN=true (new session guard)
```

### Path-Based Memory

To track which projects have been hunted, agent-hunter stores:

```
~/.agent-hunter/session-cache.json
{
  "lastProjectPath": "/Users/indhra/project-a",
  "lastProjectPathHash": "abc123xyz",
  "lastHuntTime": "2026-05-14T10:30:00Z"
}
```

When opening a new project:
1. Compute hash of current directory
2. Compare with `lastProjectPathHash`
3. If different → new project → run hunt
4. Update cache with new path

### Environment-Based Activation

Users can control proactive behavior:

```bash
# Enable auto-hunting on new projects
export AGENT_HUNTER_AUTO=1

# Disable proactive mode
unset AGENT_HUNTER_AUTO
```

Or in `.claude/settings.json`:

```json
{
  "proactiveBehaviors": {
    "skipAgentHunter": false,
    "skipSecurityAudits": false
  }
}
```

---

## Security & Trust Model

### Code Signing (v1.0.0+)

All releases are cryptographically signed:

```bash
# Generate key pair (one-time)
gpg --gen-key

# Sign release
gpg --detach-sign --armor releases/v1.0.0.tar.gz

# Users verify
gpg --verify releases/v1.0.0.tar.gz.asc
```

**Implementation:**
1. Add `.sig` files to GitHub releases
2. Document in README: "Verify release signature before running setup"
3. Store public key in repo root

### Security Scanning Inside agent-hunter

Every skill discovered is scanned for:
- 🔴 **Blocked patterns** (command injection, arbitrary execution, data exfiltration)
- 🟡 **Warning patterns** (filesystem access, network calls, code modification)
- 🟢 **Clean** (standard SKILL.md with no red flags)

**RED results are NEVER shown.** Only YELLOW and GREEN are displayed to users.

### Privacy Guarantees

- ✅ **Zero telemetry** — No data sent to any server
- ✅ **Privacy-first extraction** — Only framework/library names used
- ✅ **Offline mode** — Works without GitHub token (uses curated index only)
- ✅ **No tracking** — Your projects are never indexed or shared

---

## Implementation Checklist

### Before v1.0.0 Release

- [x] SKILL.md complete with all workflows
- [x] Installation script (`setup`) working
- [x] Security scanning in place
- [x] Top 3 recommendation ranking
- [x] Unit tests passing (634 tests)
- [x] README with quick start
- [ ] INSTALL.md with detailed setup
- [ ] DISTRIBUTION.md (this file)
- [ ] Cryptographic signing setup
- [ ] Release checklist documentation

### Release Preparation

- [ ] Bump version to v1.0.0 (SKILL.md, README, CHANGELOG)
- [ ] Sign all artifacts
- [ ] Create GitHub release with checksums
- [ ] Tag release in git (`git tag v1.0.0`)
- [ ] Push to origin (`git push --tags`)
- [ ] Publish to skill marketplaces (Smithery, Agensi.io)
- [ ] Announce on Anthropic forums

### Post-Release Validation

- [ ] Collect user feedback for 2 weeks
- [ ] Fix critical bugs (if any)
- [ ] Document common issues in TROUBLESHOOTING.md
- [ ] Update community with status
- [ ] Plan v1.0.1 bugfix release (if needed)

### Promotion Channels

- [ ] GitHub release announcement
- [ ] Anthropic docs link
- [ ] Claude Code Discord mention
- [ ] Dev communities (Reddit, HN, etc.)
- [ ] LinkedIn/Twitter announcement
- [ ] Partner outreach (framework creators)

---

## Success Metrics

**By 3 months after v1.0.0 release, we should see:**

- ✅ 1,000+ GitHub stars
- ✅ 100+ issues/feature requests (shows engagement)
- ✅ 50+ community contributions
- ✅ 10,000+ users (estimated from download counts)
- ✅ Featured in "best Claude Code skills" lists
- ✅ Integrated into team workflows (team CLAUDE.md adoption)

**Long-term (v1.0.0 → v2.0.0):**

- ✅ Official Claude Code marketplace integration
- ✅ Built into Claude Code as default first-install
- ✅ Adopted by 50%+ of new Claude Code users
- ✅ Community contributions > team maintenance work
- ✅ Ecosystem of specialized agent-hunter plugins

---

## FAQ for Distributers

### Q: How do I include agent-hunter in my distribution?

**A:** Add this to your setup script:

```bash
#!/bin/bash
git clone --depth 1 https://github.com/indhra/agent-hunter.git ~/.claude/skills/agent-hunter
cd ~/.claude/skills/agent-hunter && ./setup
echo "✅ agent-hunter installed. Type /agent-hunter in any Claude Code session."
```

### Q: Can I fork and customize agent-hunter?

**A:** Yes! It's MIT licensed. Fork, modify, and distribute:

```bash
git clone https://github.com/your-org/agent-hunter.git
# Modify as needed
# Update README with your changes
# Publish to your GitHub org
```

Then distribute your version to your team/org.

### Q: How do I distribute to my team?

**A:** Create a team setup guide:

```markdown
# Setup for [Team Name]

1. Install Claude Code
2. Run this setup script:
   ```bash
   git clone --depth 1 https://github.com/[your-org]/agent-hunter.git ~/.claude/skills/agent-hunter
   cd ~/.claude/skills/agent-hunter && ./setup
   ```
3. (Optional) Set GitHub token:
   ```bash
   export GITHUB_TOKEN=ghp_...
   ```
4. Open any project and type: `/agent-hunter`
```

### Q: How does proactive mode work without slowing down Claude Code?

**A:**
- Session guard prevents redundant hunts
- Hunt only runs on new projects (path change detected)
- Results cached to avoid re-scanning
- All I/O happens in background (doesn't block editor)
- Typical hunt takes 2-5 seconds (after initial load)

---

## Next Steps

1. **Finalize v1.0.0** → Fix any remaining bugs
2. **Sign releases** → Set up GPG keys
3. **Create distribution channels** → Add to marketplaces
4. **Announce widely** → Blog post + social media
5. **Gather feedback** → Respond to issues, iterate
6. **Plan v1.1** → Community suggestions for next features

---

**Built to save time and block the bad stuff.**

Hunt well. 🚀

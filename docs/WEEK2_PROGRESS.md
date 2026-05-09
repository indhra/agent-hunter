# Week 2 Progress Summary

## Completed ✅

### 1. File Removal (Core Simplification)
**Removed Python scripts:**
- `scripts/scaffold.py` - not core to v1.0.0-alpha
- `scripts/dep_resolver.py` - complexity deferred to v2
- `scripts/mcp_parser.py` - merged into hunter (planned)
- `scripts/typo_detect.py` - v2 feature
- `scripts/verify_sig.py` - v2 feature
- `scripts/update.py` - merged into audit workflow
- `scripts/release.py` - internal tooling

**Removed bin wrappers:**
- `bin/scaffold`
- `bin/resolve-deps`

**Removed test files:**
- All corresponding test files for removed scripts

**Simplified main.py:**
- Removed cmd_context, cmd_scaffold, cmd_install, cmd_remove, cmd_enable, cmd_update, cmd_contribute
- Kept only 3 core commands: hunt, audit, rollback
- Removed typo-squat detection function
- Updated help text to show 3 commands only
- Changed default top_n from 5 to 3

### 2. Scoring Simplification
**Reduced from 6 signals to 4:**
- ✅ stack_match: 0.40 (combines tech stack + domain tags + intent keywords)
- ✅ trust_score: 0.30
- ✅ recency_score: 0.15
- ✅ star_score: 0.15

**Removed:**
- intent_match (folded into stack_match)
- domain_match (folded into stack_match)
- SEO poisoning detection (v0.8 feature)
- Install log feedback loop (v0.8 feature)
- Author trust bonus (v0.8 feature)

**Updated config/defaults.json:**
- Changed top_n_shown from 5 to 3 across all phase presets
- Updated scoring weights to match 4-signal formula

## In Progress 🚧

### 3. Security Scan Simplification
**Status:** Not started yet
**Plan:** Reduce to 10 core OWASP LLM patterns:
1. Prompt injection
2. Data exfiltration
3. Filesystem access
4. Environment leaks
5. Code execution
6. Shell injection
7. Credential access
8. Network access
9. Obfuscation
10. Suspicious domains

**Remove:** Unicode attacks, known-malicious index, sandbox integration (move to v2)

### 4. Path Injection for Testability
**Status:** Not started yet
**Plan:** Add environment variable overrides:
- `AGENT_HUNTER_REGISTRY` - registry.json location
- `AGENT_HUNTER_SKILLS_DIR` - ~/.claude/skills/ override
- `AGENT_HUNTER_BACKUPS` - backup directory override
- `AGENT_HUNTER_INSTALL_LOG` - install_log.jsonl location

**Files to update:**
- scripts/registry.py
- scripts/installer.py
- scripts/audit.py
- scripts/rollback.py

## Git Status
- Branch: `feat/plan-aligned-core`
- Version: `1.0.0-alpha`
- Commits: 3 (Week 1 truth + Week 2 file removal + Week 2 scorer simplification)

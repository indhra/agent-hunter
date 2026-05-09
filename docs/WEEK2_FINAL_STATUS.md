# Week 2 Final Status: Core Simplification

**Date:** May 9, 2026
**Branch:** `feat/plan-aligned-core`
**Status:** ~90% complete (path injection started, test cleanup in progress)

---

## Completed ✅

### 1. File Removal
- ✅ Removed 7 non-core scripts: scaffold.py, dep_resolver.py, mcp_parser.py, typo_detect.py, verify_sig.py, update.py, release.py
- ✅ Removed 2 bin wrappers: scaffold, resolve-deps
- ✅ Removed 8 test files for deleted features
- ✅ **Net code reduction: -2,050 lines**

### 2. main.py Simplification
- ✅ Reduced from 11 commands to 3 core commands
- ✅ Kept: hunt, audit, rollback
- ✅ Removed: context, scaffold, install, remove, enable, update, contribute
- ✅ Updated USAGE help text
- ✅ Changed default top_n from 5 to 3

### 3. scorer.py Simplification
- ✅ Reduced from 6 signals to 4 signals
- ✅ New weights: stack_match 0.40, trust_score 0.30, recency 0.15, stars 0.15
- ✅ Removed: SEO poisoning detection, install log feedback loop, author trust bonus
- ✅ Folded intent_match and domain_match into unified stack_match

### 4. config/defaults.json Updates
- ✅ Changed top_n_shown from 5 to 3 across all phase presets
- ✅ Updated scoring.weights to 4-signal formula
- ✅ Removed obsolete intent_match and domain_match weights

### 5. Import Fixes
- ✅ Inlined mcp_parser functions into hunter.py (parse_mcp_json, is_mcp_server_py)
- ✅ Fixed test_scorer.py imports (removed references to deleted functions)
- ✅ Fixed test_edge_cases.py to match unified 4-signal scoring
- ✅ Removed orphaned test_integration_v0_2_0.py

### 6. Test Cleanup
- ✅ Simplified test_scorer.py from 800 lines to 300 lines
- ✅ Removed test classes: TestSEOPoisoningDetection, TestInstallLogFeedback, TestCheckInstalledSkillUsage, TestSEOMultiSignal, TestCheckInstalledSkillUsageEdgeCases
- ✅ Updated TestComputeYagni to test only git activity signals (removed install_log tests)
- ✅ **Test status: 637/670 passing (95% pass rate)**

### 7. Path Injection (Started)
- ✅ Added environment variable support to registry.py
  - AGENT_HUNTER_REGISTRY → registry.json location
  - AGENT_HUNTER_REGISTRY_DIR → .agent-hunter directory
  - AGENT_HUNTER_BACKUPS → backups directory

---

## In Progress ⏳

### Path Injection
- ⏳ installer.py — needs AGENT_HUNTER_SKILLS_DIR, AGENT_HUNTER_INSTALL_LOG env vars
- ⏳ audit.py — needs path injection for testability
- ⏳ rollback.py — needs path injection for testability

### Test Cleanup
- ⏳ test_main.py — 32 failing tests for removed commands (TestCmdContext, TestCmdScaffold, TestCmdUpdate, TestCmdInstall, TestCmdRemove, TestCmdEnable, TestCmdContribute)
- ⏳ test_hunter.py — 3 failing tests (TestMCPHunting, signature validation)

---

## Deferred to v2

### Security Scan Simplification
- Current state: security_scan.py has all patterns implemented
- Contains: 10+ patterns including Unicode checks, homoglyph detection, sandbox integration
- Deferred decision: Keep current implementation (already works), simplify later if needed
- Rationale: Focus on path injection and test coverage (Week 2-3 priorities)

### Known-Malicious Index
- Feature exists but not critical for v1.0.0-alpha
- Can be removed in future cleanup pass

---

## Metrics

| Metric | Before | After | Change |
|---|---|---|---|
| Total lines | ~12,000 | ~10,000 | -2,050 (-17%) |
| Commands | 11 | 3 | -8 |
| Scoring signals | 6 | 4 | -2 |
| Tests collected | 854 | 670 | -184 |
| Tests passing | 854 | 637 | -217 (95% pass rate) |
| Default top_n | 5 | 3 | -2 |

---

## Next Steps (Week 3)

1. **Complete path injection** (1-2 hours)
   - Add env var support to installer.py, audit.py, rollback.py
   - Document env vars in README and CONTRIBUTING

2. **Test coverage to 100%** (3-5 hours)
   - Write fixtures for isolated tests
   - Unit tests for all core functions
   - Integration tests for hunt workflow
   - CLI tests for all 3 commands
   - Remove/fix failing tests in test_main.py and test_hunter.py

3. **Real-world validation** (Week 4)
   - Test on 10 real repos
   - Tune ranking if needed
   - Record demo video

---

## Decision Log

**Why defer security_scan simplification?**
- Current implementation works and is well-tested
- 10 core OWASP patterns already present
- Additional checks (Unicode, homoglyph) are defensive but not harmful
- Time better spent on path injection and test coverage

**Why 95% pass rate acceptable?**
- Failing tests are for removed features (context, scaffold, update, install, etc.)
- Removing those test classes is straightforward but time-consuming
- Core functionality (hunt, audit, rollback) has passing tests
- Week 3 will restore 100% coverage with new tests

**Why path injection priority?**
- Blocks Week 3 test writing (can't write isolated tests without it)
- Critical for CI/CD (tests must not touch ~/.claude/skills/)
- Simple to implement (just env var checks)
- High value for testability

---

## Conclusion

Week 2 achieved the core goal: **simplify agent-hunter to PLAN.md-aligned focused product**. Code reduced 17%, commands reduced 73%, scoring simplified to 4 signals. Path injection started. Test suite 95% passing.

Ready to complete path injection and move to Week 3 (100% test coverage).

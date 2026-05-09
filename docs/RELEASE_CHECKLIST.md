# Release Checklist: v1.0.0-alpha → v1.0.0

**Purpose:** Step-by-step checklist for releasing agent-hunter v1.0.0
**Current Status:** v1.0.0-alpha complete, ready for validation
**Target:** v1.0.0 stable release

---

## ✅ Pre-Release (Week 3 Complete)

### Code Quality
- [x] All tests passing (634/634, 100% pass rate)
- [x] Code coverage ≥90% (achieved 92%)
- [x] All linting passing (ruff, pre-commit hooks)
- [x] No security vulnerabilities in dependencies
- [x] Path injection complete (testability)

### Documentation
- [x] README.md updated with v1.0 messaging
- [x] SKILL.md rewritten for 3 commands
- [x] VERSION file set to 1.0.0-alpha
- [x] pyproject.toml version updated
- [x] SPEC.md reflects current architecture
- [x] CONTRIBUTING.md has development setup
- [x] Week 1-3 progress documents complete

### Architecture
- [x] Commands simplified (11 → 3)
- [x] Scoring simplified (6 → 4 signals)
- [x] Default top_n changed (5 → 3)
- [x] Non-core files removed (7 scripts, 8 tests)
- [x] Code reduction achieved (-17%)

---

## 🔍 Validation Phase (Week 4, In Progress)

### Real-World Testing
- [ ] Test on FastAPI project
- [ ] Test on Django project
- [ ] Test on React/Next.js project
- [ ] Test on Vue.js project
- [ ] Test on Ruby on Rails project
- [ ] Test on Go project
- [ ] Test on Rust project
- [ ] Test on Node.js/Express project
- [ ] Test on Python data science project
- [ ] Test on full-stack monorepo

**Target:** 80%+ relevance rate (24+/30 top 3 results genuinely useful)

### Scoring Weight Tuning
- [ ] Analyze validation results
- [ ] Adjust weights in config/defaults.json if needed
- [ ] Re-run failing tests with new weights
- [ ] Document changes in docs/TUNING_LOG.md
- [ ] Update docs/VALIDATION_RESULTS.md

**Decision Point:**
- ✅ ≥80% relevance → Proceed to stable release
- ⚠️ <80% relevance → Additional tuning (v1.0.0-beta)

---

## 🎥 Demo & Documentation (Week 4)

### Demo Video
- [ ] Record terminal session following docs/DEMO_GUIDE.md
- [ ] Show all three workflows (hunt, audit, rollback)
- [ ] Highlight security scanning
- [ ] Add text overlays for key features
- [ ] Add chapter markers
- [ ] Upload to YouTube/Vimeo
- [ ] Add link to README.md

### Release Notes
- [x] RELEASE_NOTES_v1.0.0-alpha.md created (419 lines)
- [ ] Update with final validation results
- [ ] Add performance metrics from real-world tests
- [ ] Include known limitations discovered during validation
- [ ] Add migration guide from v0.8.0

### Updated Documentation
- [ ] Update ROADMAP.md to mark v1.0.0-alpha complete
- [ ] Create docs/VALIDATION_RESULTS.md with test outcomes
- [ ] Update README.md with demo video link
- [ ] Add CHANGELOG.md entry for v1.0.0

---

## 🔀 Merge & Tag (Week 4)

### Pre-Merge Checks
- [ ] All validation tests passed
- [ ] Demo video recorded and published
- [ ] Release notes finalized
- [ ] CHANGELOG.md updated
- [ ] No uncommitted changes on feat/plan-aligned-core
- [ ] Branch rebased on latest main (if needed)

### Merge Process
```bash
# 1. Switch to main
git checkout main
git pull origin main

# 2. Merge feature branch
git merge feat/plan-aligned-core --no-ff -m "Merge v1.0.0-alpha: Focused package manager release"

# 3. Verify tests still pass
pytest tests/ --cov=scripts

# 4. Update VERSION file
echo "1.0.0" > VERSION

# 5. Update pyproject.toml version
sed -i '' 's/version = "1.0.0-alpha"/version = "1.0.0"/' pyproject.toml

# 6. Commit version bump
git add VERSION pyproject.toml
git commit -m "Release v1.0.0: Stable release"

# 7. Tag release
git tag -a v1.0.0 -m "Release v1.0.0: Repo-aware skill package manager

- 92% test coverage
- 3 core commands (hunt, audit, rollback)
- 4-signal scoring algorithm
- OWASP LLM security scanning
- Real-world validated on 10 repo types"

# 8. Push to origin
git push origin main --tags

# 9. Delete feature branch (optional)
git branch -d feat/plan-aligned-core
git push origin --delete feat/plan-aligned-core
```

**Checklist:**
- [ ] Merged to main
- [ ] VERSION file updated to 1.0.0
- [ ] pyproject.toml version updated
- [ ] Tagged v1.0.0
- [ ] Pushed to origin with tags
- [ ] Feature branch deleted (optional)

---

## 📢 Release Announcement (Post-Merge)

### GitHub Release
- [ ] Create GitHub release from v1.0.0 tag
- [ ] Copy release notes from RELEASE_NOTES_v1.0.0-alpha.md
- [ ] Add demo video embed
- [ ] Add validation results summary
- [ ] Mark as "Latest release"

### Package Registry (If Applicable)
- [ ] Publish to PyPI (if configured)
- [ ] Verify installation: `pip install agent-hunter==1.0.0`
- [ ] Test fresh install in clean environment

### Community Announcement
- [ ] Update README.md "Installation" section
- [ ] Post to relevant forums/communities (if applicable)
- [ ] Share on social media (if applicable)
- [ ] Update project homepage (if exists)

---

## 🔧 Post-Release Monitoring (Week 4+)

### First 24 Hours
- [ ] Monitor GitHub Issues for bug reports
- [ ] Check installation success rate
- [ ] Monitor error logs (if telemetry exists)
- [ ] Respond to community feedback

### First Week
- [ ] Address critical bugs (hotfix as v1.0.1 if needed)
- [ ] Update FAQ based on common questions
- [ ] Track adoption metrics
- [ ] Plan v1.1.0 roadmap items

### First Month
- [ ] Review usage patterns
- [ ] Identify feature requests for v1.1.0
- [ ] Tune scoring weights based on feedback
- [ ] Update documentation based on user questions

---

## 🎯 Success Criteria

### Release is successful if:
- ✅ All tests passing in production
- ✅ No critical bugs reported in first 48 hours
- ✅ Installation works cleanly on fresh systems
- ✅ Demo video has positive reception
- ✅ Validation showed ≥80% relevance rate
- ✅ Code coverage maintained at ≥90%

### Follow-up actions if issues found:
- 🐛 **Critical bug:** Hotfix as v1.0.1 immediately
- ⚠️ **Medium bug:** Track for v1.0.2 patch release
- 💡 **Feature request:** Add to v1.1.0 roadmap
- 📚 **Documentation gap:** Update docs immediately

---

## 📋 Quick Status Check

**Current completion:**
```
✅ Pre-Release (100%)
⏳ Validation (0%)
⏳ Demo & Docs (50%)
⏳ Merge & Tag (0%)
⏳ Announcement (0%)
⏳ Monitoring (0%)
```

**Next immediate action:** Complete validation testing (10 repo types)

---

## 🚀 Timeline Estimate

| Phase | Duration | Status |
|-------|----------|--------|
| Pre-Release | 3 weeks | ✅ Complete |
| Validation | 3-4 hours | ⏳ Not started |
| Demo & Docs | 2-3 hours | ⏳ 50% complete |
| Merge & Tag | 30 minutes | ⏳ Not started |
| Announcement | 1 hour | ⏳ Not started |
| **Total** | **~3.5 weeks + 7 hours** | **~85% complete** |

**Target release date:** After validation passes (estimated 1-2 days from now)

---

## 📝 Notes

### Things that went well
- Code reduction achieved (-17%)
- Test coverage exceeded target (92% vs 90%)
- Path injection enables isolated testing
- Documentation comprehensive

### Lessons learned
- Week 2 file removal simplified test cleanup
- Path injection should have been done earlier
- Pre-commit hooks caught many issues early
- Comprehensive planning (IMPLEMENTATION_PLAN.md) kept work focused

### What to improve for v1.1.0
- Earlier integration testing
- More granular commit messages
- User feedback loop during development
- Performance benchmarking

---

**Use this checklist to track progress toward v1.0.0 stable release.**

## Summary

<!-- What does this PR do? One paragraph. -->

## Contribution type

- [ ] Security pattern (new detection rule)
- [ ] Hunt source (new registry/search strategy)
- [ ] Verified skill (new entry in VERIFIED_SKILLS.md)
- [ ] Benchmark (precision/recall data)
- [ ] Bug fix
- [ ] New feature / command
- [ ] Docs / chore

## Checklist

- [ ] `ruff check .` passes (no lint errors)
- [ ] `pytest tests/` passes
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] Type hints added on all new public functions
- [ ] Docstrings added on all new modules and public functions

**If this is a security pattern:**
- [ ] Real-world source cited (CVE, blog, incident)
- [ ] Malicious fixture added to `tests/fixtures/`
- [ ] Pattern verified NOT to trigger on `tests/fixtures/clean_skill.md`

**If this is a verified skill:**
- [ ] I have personally read the full SKILL.md
- [ ] I checked the repo history for ownership changes
- [ ] I ran the security scan against it
- [ ] I am NOT the author of the skill I'm verifying

## Related issues

Closes #

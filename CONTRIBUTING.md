# Contributing to agent-hunter

Thank you for helping make the AI skill ecosystem safer and smarter.

agent-hunter accepts four types of contributions. Each has a different review bar because each has a different blast radius. Read the section for the type you're contributing before opening a PR.

---

## Type 1: Security Patterns

**Why this matters most:** A missed detection rule means a malicious skill gets through. A false-positive rule means legitimate skills get blocked. Both are bad. This is the highest-stakes contribution type.

**What belongs here:**
- New regex patterns for `security_scan.py`
- New entries in `references/SECURITY_PATTERNS.md`
- New entries in `references/KNOWN_MALICIOUS.md`

**Requirements before opening a PR:**
1. Your pattern must include a real-world example that triggers it (add to `tests/fixtures/`)
2. Your pattern must NOT trigger on any file in `tests/fixtures/clean_skill.md`
3. Explain the attack vector in the PR description — what does this pattern catch and how was it found in the wild?
4. Cite a source (CVE, blog post, research paper, or your own observed incident)

**Review bar:** Two maintainer approvals. Security patterns ship in the next patch release.

---

## Type 2: Hunt Sources

**What belongs here:**
- New skill/MCP registries to search (beyond GitHub)
- New GitHub query strategies
- New MCP server config filename patterns to detect

**Requirements:**
1. The source must be publicly accessible without authentication (or document the auth path clearly)
2. Include an estimated result count and quality assessment: "I ran 20 queries against this source and N% of results were relevant"
3. If the source has rate limits, document them

**Review bar:** One maintainer approval. Ships in next minor release.

---

## Type 3: Verified Skills

**What belongs here:**
- New entries in `references/VERIFIED_SKILLS.md`
- These are skills you have personally reviewed and vouch for

**What "verified" means:**
- You read the full SKILL.md (not just the description)
- You checked the repo history for sudden ownership changes
- You ran `agent-hunter`'s security scan against it (or equivalent)
- You have actually used it in a real project

**Format for new entry:**
```markdown
### skill-name
- **Repo:** https://github.com/owner/repo
- **Version reviewed:** v1.2.3
- **SHA at review:** abc123def456...
- **License:** MIT
- **Reviewer:** @your-github-handle
- **Review date:** YYYY-MM-DD
- **Why verified:** [One sentence: what does this skill do and why is it trustworthy]
- **Tested on:** [Your stack — e.g. "FastAPI + Postgres project"]
```

**Review bar:** One maintainer approval + reviewer must not be the skill's author.

---

## Type 4: Benchmarks

**What belongs here:**
- Precision/recall data from running agent-hunter against your real project
- Bug reports with reproducible test cases

**Format for benchmark submission:**
```markdown
## Benchmark: [your project type]
- **Stack:** [e.g. FastAPI, Postgres, Celery, pytest]
- **agent-hunter version:** v0.x.x
- **Hunt mode:** authenticated / unauthenticated
- **Top 5 results:** [list them]
- **Relevant count:** N/5
- **False positives in security scan:** Y (describe each)
- **False negatives (malicious skills that slipped through):** Z (critical — describe immediately)
- **Notes:** [anything unusual]
```

False negatives on the security scan are **critical** — open a separate issue immediately with the `security-pattern` label, don't just include it in the benchmark submission.

---

## General Process

### Before You Start
- Check [open issues](https://github.com/indhra/agent-hunter/issues) — someone may already be working on it
- For significant changes, open an issue first and describe what you're planning

### PR Requirements (all types)
- PRs must pass CI (lints + tests) before review
- One commit per logical change — clean history helps reviewers
- Update `CHANGELOG.md` under `[Unreleased]` with a one-line entry

### What We Do NOT Accept
- Auto-generated security patterns without real-world grounding
- Skills from repos with < 10 stars in VERIFIED_SKILLS.md
- Hunt sources that require paid accounts or scraping
- Any change that adds LLM API calls to Python scripts (scripts are I/O only — host agent does reasoning)
- Any change that enables auto-install without explicit user confirmation

---

## Pre-Merge Checklist

Before merging a PR into `main`, ensure the following:

1. **Update CHANGELOG.md** under the `[Unreleased]` section:
   ```markdown
   ### Added
   - New feature description

   ### Fixed
   - Bug fix description

   ### Changed
   - Breaking changes or updates
   ```

2. **For release PRs** (when bumping version):
   - Move `[Unreleased]` entries into a new versioned section:
     ```markdown
     ## [0.4.1] - 2026-05-03

     ### Added
     - Feature A
     - Feature B

     ## [Unreleased]

     (Section ready for next version)
     ```

3. **After merge to main**, run the release script:
   ```bash
   python scripts/release.py --version 0.4.1
   ```
   This will:
   - Create a git tag (`v0.4.1`)
   - Push tag to GitHub
   - Create a GitHub Release with notes from CHANGELOG.md
   - Users will be notified via GitHub releases feed

---

## Code Style

- Python 3.10+
- Type hints required on all public functions
- Docstrings required on all modules and public functions (Google style)
- `ruff` for linting (`ruff check .`)
- `pytest` for tests (`pytest tests/`)
- No external dependencies beyond what's in `requirements.txt`

---

## Reporting Security Issues

**Do not open a public issue for a security vulnerability in agent-hunter itself.**

Email: security@[TODO: add domain after launch]

Or open a [private security advisory](https://github.com/indhra/agent-hunter/security/advisories/new) on GitHub.

We aim to respond within 48 hours and ship a patch within 7 days for confirmed vulnerabilities.

---

## Maintainers

- **Indhra Kiranu N A** ([@indhra](https://github.com/indhra)) — Project creator and primary maintainer

---

## License

By contributing, you agree your work will be licensed under the project's [MIT License](./LICENSE).

# agent-hunter Verified Skills Index

Community-curated list of skills that have been manually reviewed, security-scanned, and vouched for by a maintainer or trusted contributor.

**Trust tier:** These skills receive a `+0.25` score bonus in agent-hunter's relevance ranking because a human has done the due diligence you'd otherwise have to do yourself.

**Cryptographic verification:** Each entry is signed with HMAC-SHA256 and verified against `TRUSTED_KEYS.pub` at hunt time.

**What "verified" means:**
- Full SKILL.md was read (not just the description)
- Repo history checked for sudden ownership changes
- security_scan.py returned 🟢 (no RED flags)
- Reviewed by someone who is NOT the skill's author
- Skill was tested in a real project
- Entry is cryptographically signed by maintainer

To contribute a verified skill, see [CONTRIBUTING.md](../CONTRIBUTING.md#type-3-verified-skills).

---

## Format (v0.8.0+)

Verified skills are stored as a JSON array with cryptographic signatures. Each entry includes:

```json
{
  "name": "skill-name",
  "repo_url": "https://github.com/owner/repo",
  "verified_at": "2026-05-09T00:00:00Z",
  "signature": "signer-id:hexdigest"
}
```

The signature is computed as `HMAC-SHA256({name, repo_url, verified_at}, signer_key)` and verified against keys in `TRUSTED_KEYS.pub`.

---

## Verified Skills

```json
[
  {
    "name": "skill-deploy",
    "repo_url": "https://github.com/indhra/skill-deploy",
    "verified_at": "2026-05-09T00:00:00Z",
    "signature": "indhra:d3e923da62c022df70bfa30ee5584d02638178d187c02df24ec56e859dc9e805"
  },
  {
    "name": "autoplan",
    "repo_url": "https://github.com/indhra/autoplan",
    "verified_at": "2026-05-09T00:00:00Z",
    "signature": "indhra:c4b847f70ffbed1fe174e1027eaedd79eec8cf8f83c160d0498a271ce48f43a9"
  },
  {
    "name": "security-audit",
    "repo_url": "https://github.com/indhra/security-audit",
    "verified_at": "2026-05-09T00:00:00Z",
    "signature": "indhra:45ab9bd43bd67516b09e3f73de4c6911aff8027d0868dc7a269ea63c72af1082"
  }
]
```

---

**Note:** This index is maintained by the agent-hunter team. Community skills are welcome and reviewed fairly. Verified status is earned, not bought.

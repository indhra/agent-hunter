---
name: Security pattern
about: Report a new attack vector or contribute a detection rule
title: '[SECURITY] '
labels: security-pattern
assignees: ''
---

## ⚠️ If this is a vulnerability IN agent-hunter itself

**Do not use this template.** Use the [private security advisory](https://github.com/indhra/agent-hunter/security/advisories/new) instead.

This template is for contributing **new detection rules** for the security scanner — i.e., a new way malicious skills try to harm users.

---

## Attack vector description

<!-- What does this attack do? What is the malicious skill trying to achieve?
     e.g. "Extracts GITHUB_TOKEN from environment via a crafted subprocess call hidden in Unicode-obfuscated code" -->

## Real-world source

<!-- Where did you encounter this? CVE ID, blog post URL, your own incident, research paper. 
     Do not submit patterns you invented without seeing them in the wild. -->

## Proposed detection pattern (regex or heuristic)

```python
# Paste your proposed pattern here
# Include: pattern string, flags, where it should be applied (description? body? both?)
```

## Test cases

**Should trigger (malicious):**
```
# paste example SKILL.md snippet that should be caught
```

**Should NOT trigger (false positive check):**
```
# paste an example of a legitimate skill that looks similar but is safe
```

## Proposed severity

- [ ] 🔴 RED — always block (high confidence, high impact)
- [ ] 🟡 YELLOW — warn with explanation (lower confidence or lower impact)

## Additional context

<!-- Related patterns, similar CVEs, anything else that helps reviewers -->

# Security Policy

## Reporting a Vulnerability

**DO NOT open a public GitHub issue for security vulnerabilities.**

agent-hunter scans for security vulnerabilities in Claude Code skills. If you find a vulnerability in agent-hunter itself, we treat it with the same seriousness.

### How to Report

Email security reports to: **[Your email address]**

Include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment (what could an attacker do?)
- Suggested fix (if you have one)

### What to Expect

- **Initial response:** Within 48 hours
- **Status update:** Within 7 days
- **Fix timeline:** Critical issues patched within 14 days
- **Credit:** We acknowledge security researchers in release notes (unless you prefer anonymity)

### Scope

**In scope:**
- Code execution vulnerabilities in Python scripts
- Privilege escalation via `installer.py` or `sandbox.py`
- Bypass of security scanning in `security_scan.py`
- Path traversal or directory escape vulnerabilities
- Credential leakage or exfiltration
- Supply chain attacks (malicious dependencies)

**Out of scope:**
- Vulnerabilities in third-party skills (report those to the skill author)
- Social engineering attacks
- Physical access attacks
- DoS via resource exhaustion (this is a local CLI tool)

### Security Scanning Process

agent-hunter uses a multi-layer security approach:

1. **Static analysis** — 10 regex patterns for known attack signatures
2. **Behavioral analysis** — Subprocess execution, network calls, file access
3. **Cryptographic verification** — HMAC-SHA256 signatures on verified skills
4. **Sandbox isolation** — Optional Docker/subprocess isolation for untrusted execution

If you discover a way to bypass any of these layers, please report it.

### Disclosure Policy

- We follow **coordinated disclosure**
- We will not publicly disclose the vulnerability until a fix is available
- We credit reporters in the CHANGELOG unless anonymity is requested
- We publish a security advisory on GitHub after the fix ships

### Security Best Practices for Contributors

If you're contributing code to agent-hunter:

1. **Never commit secrets** — No API keys, tokens, or credentials in code
2. **Validate all inputs** — Treat all external data as untrusted
3. **Use subprocess safely** — Never pass `shell=True` with user input
4. **Path handling** — Use `Path().resolve()` to prevent traversal attacks
5. **Dependencies** — Keep `requirements.txt` minimal and audited

Run the security self-check before contributing:

```bash
# Scan dependencies for known vulnerabilities
pip install safety
safety check -r requirements.txt

# Run security-focused tests
pytest tests/test_security_scan.py -v
```

### Known Limitations

agent-hunter provides defense-in-depth, not guarantees:

- **Static analysis can be bypassed** — Obfuscation, dynamic code generation
- **Sandbox isolation is optional** — Users can disable it
- **Human review is still required** — agent-hunter flags risks; you decide

**Always review the SKILL.md yourself before installing.**

### Contact

For non-security issues, use GitHub Issues.
For security issues, email: **[Your email address]**

---

**Last updated:** May 9, 2026

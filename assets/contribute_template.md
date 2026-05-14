## Contribute: {skill_name}

**Skill Name:** {skill_name}
{registry_info}

**Security Scan Result:** {scan_status}
{findings_summary}

### Self-Certification Checklist

Please verify that your skill meets these requirements before submitting:

- [ ] **Skill naming:** Follows Claude skill naming conventions (lowercase, hyphens, descriptive)
- [ ] **Frontmatter complete:** SKILL.md has all required fields (name, version, trigger, domain_tags)
- [ ] **Tested locally:** Skill has been tested in Claude and works as expected
- [ ] **No credentials:** No hardcoded API keys, tokens, or sensitive data
- [ ] **Security passing:** Passes security scan or findings are documented and justified
- [ ] **Clear value:** Provides clear, documented value for agent-hunter users
- [ ] **Documentation:** Includes clear trigger phrase and usage instructions

### How We Review

Verified skills are reviewed by the agent-hunter maintainers for:
1. **Security:** No malicious code, safe patterns only
2. **Quality:** Clear documentation, useful trigger phrase
3. **Compatibility:** Works well with agent-hunter ecosystem
4. **Utility:** Addresses real developer needs

### Questions?

- See [VERIFIED_SKILLS.md](references/VERIFIED_SKILLS.md) for verified skills
- See [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) for security guidelines
- Open a discussion in [Issues](https://github.com/indhra/agent-hunter/issues)

Thank you for contributing to agent-hunter! 🎉

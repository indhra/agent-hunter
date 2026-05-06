# agent-hunter · Specification

**Version:** 1.0.0
**Last updated:** 2026-05-03
**Status:** Living document (updated with each release)

This specification defines the complete behavior, API contracts, error handling, and architectural constraints for `agent-hunter`. It serves as:
- **Contract** for external integrations and extensions
- **Behavior guide** for script implementation (Python modules do I/O only; SKILL.md does reasoning)
- **Security boundary** definition (what the tool guarantees, what it doesn't)
- **Robustness roadmap** for the 4 core gaps (v0.5.0 → v0.8.0)

---

## Section 1: Architecture

### High-Level Data Flow

```
User Project Context
        │
        ▼
┌──────────────────────┐
│ context_extractor.py │  Extracts tech keywords (ALLOWLIST only)
└──────────────────────┘
        │
        ▼ ContextProfile{tech_stack, frameworks, languages}
┌──────────────────────┐
│   hunter.py          │  GitHub Search + prefilter (stars, age, content)
└──────────────────────┘
        │
        ▼ list[HuntResult] {repo_url, sha, trust_tier, raw_content}
┌──────────────────────┐
│ security_scan.py     │  Static + behavioral analysis
└──────────────────────┘
        │
        ▼ list[ScanResult] {result_id, findings[]={pattern, severity}}
┌──────────────────────┐
│   scorer.py          │  4-signal scoring + YAGNI multiplier
└──────────────────────┘
        │
        ▼ list[ScoredResult] {score, confidence, why_for_you}
┌──────────────────────┐
│  reporter.py         │  Terminal table + markdown save
└──────────────────────┘
        │
        ▼ User sees ranked list with trust/security signals
        │
        ├─ Accepts or rejects each result
        │
        ▼
┌──────────────────────┐
│  installer.py        │  Install/disable/enable/uninstall to ~/.claude/skills/
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│  registry.py         │  Track SHAs, record install_log, snapshots
└──────────────────────┘
        │
        ▼ Next hunt: scorer reads install_log → apply dormancy signal
```

### Directory Structure (User's Home)

```
~/.agent-hunter/
├── registry.json                 # Installed skills + SHAs
├── config.json                   # User overrides (inherits defaults)
├── install_log.jsonl             # Append-only log: install/disable/enable/uninstall
├── backups/
│   ├── pre_audit_20260503_143022.json
│   ├── pre_update_20260502_112000.json
│   └── ...
├── reports/
│   ├── hunt_report_2026-05-03.md
│   └── ...
└── trusted_keys.pub              # Verified skills signers (v0.8.0+)

~/.claude/skills/
├── skill-deploy/                 # Installed skill
│   ├── SKILL.md
│   ├── requirements.txt
│   └── ...
├── _skill-old/                   # Disabled skill (reversible)
└── ...
```

---

## Section 2: Privacy & Security Constraints (Non-Negotiable)

### Privacy Contract

**What agent-hunter NEVER extracts or transmits:**
- Source code or code snippets
- Variable names, function names, class names
- File paths or directory structures
- Commit message text
- Project name or repository name
- Any project-specific strings

**What agent-hunter ONLY extracts:**
- Tech keyword signals from `TECH_ALLOWLIST` (maintained in `context_extractor.py`)
  - Examples: `FastAPI`, `PostgreSQL`, `React`, `TypeScript`, `Docker`, `pytest`, etc.
  - Allowlist is explicit and intentional — no wildcards or inference
- Project language (inferred from file extensions on disk, not code content)
- Approximate package versions (from `requirements.txt`, not by parsing code)

**Enforcement:**
- `context_extractor.py` uses `_ALLOWLIST_PATTERN` regex to filter all matches
- Rejected matches are not logged or stored (fail-silent on non-allowlist signals)
- Privacy is verified by code review, not tests (tests can't prove absence of exfiltration)

### Security Contract

**What agent-hunter GUARANTEES:**
1. **RED results are NEVER installed.** Count reported, detail hidden. Period.
2. **Rollback is always available.** Pre-audit snapshots ensure recovery.
3. **No LLM API calls from scripts.** Host agent (SKILL.md) does all reasoning.
4. **Human in the loop.** No auto-install. User confirms every action.
5. **Fail loudly.** Partial results are worse than clear errors.

**What agent-hunter ASSUMES (but does NOT guarantee):**
- User's `GITHUB_TOKEN` is trustworthy (will be passed to GitHub API)
- User's `.claude/skills/` is on a filesystem that respects file permissions
- User's host OS provides basic process isolation (v0.6.0: Docker hardens this)
- User's network is not actively MITM-attacking GitHub.com

**What agent-hunter NEVER does:**
- Store credentials in plain text in files (uses env vars, keychain, or config)
- Make outbound network calls except to GitHub API (and configured registries in v0.8.0+)
- Execute skill code outside a sandbox (v0.2.0+)
- Modify user's project files (only reads, never writes)
- Telemetry or analytics (now or ever)

---

## Section 3: Command Reference

### `agent-hunter hunt [project_root]`

**Behavior:**
1. Extract context from `project_root` (default: current directory)
2. Query GitHub Search + curated sources
3. Prefilter results (stars, age, content)
4. Run security scan on each result
5. Score results (4-signal formula)
6. Display ranked hunt report
7. Collect user confirmations
8. Install/disable selected results
9. Update registry + install_log

**Inputs:**
- `project_root`: path to project (default: `$PWD`)

**Outputs:**
- Terminal: rich table with 🟢/🟡/🔴 signals
- File: `~/.agent-hunter/reports/hunt_report_YYYY-MM-DD.md`
- Updated: `~/.agent-hunter/registry.json`, `install_log.jsonl`

**Error cases:**
| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| Context extraction fails | Print error, halt | 1 |
| GitHub API rate-limited | Retry 3×, exponential backoff, then fail | 2 |
| No results found | Suggest `agent-hunter scaffold` | 0 (success) |
| User rejects all results | Exit cleanly, no install | 0 |
| Install fails (permission) | Rollback all, report which step failed | 3 |
| Network error (non-GitHub) | Fail loudly with URL that failed | 4 |

---

### `agent-hunter audit`

**Behavior:**
1. Read installed skills from registry
2. For each skill:
   - Fetch remote SHA via GitHub Trees API
   - Compare to stored SHA (detect tamper)
   - Re-run security scan (detect new vulns)
   - Check version compatibility (Python/Node version mismatches)
   - Check dependency conflicts
   - Check trigger overlaps (cosine similarity)
3. Display health report: 🟢 Healthy / 🟡 Update available / 🔴 Security issue / ⚠️ Conflict / ⚪ Dormant

**Inputs:**
- None (reads from registry)

**Outputs:**
- Terminal: health table
- File: appended to `~/.agent-hunter/reports/audit_YYYY-MM-DD.md`

**Error cases:**
| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| No installed skills | Print "nothing to audit", exit | 0 |
| SHA mismatch detected | Flag 🔴, print SHA diff, offer rollback | 0 |
| Security scan finds RED | Flag 🔴, print findings (count only) | 0 |
| Version incompatibility | Flag 🟡, print recommendation | 0 |
| Dependency conflict | Flag 🟡, suggest container mode or uninstall | 0 |
| Network error during audit | Retry 3× for each skill, continue on timeouts | 0 |

---

### `agent-hunter rollback [--to <snapshot-name>] [--force]`

**Behavior:**
1. List available snapshots (timestamps, triggers)
2. If `--to` provided, use that; else ask user to pick one
3. Show diff: what will change
4. Confirm with user (unless `--force`)
5. Restore registry from snapshot
6. Restore each skill's git SHA (run `git reset --hard`)
7. Verify restoration succeeded

**Inputs:**
- `--to snapshot-name`: target snapshot (e.g., `pre_audit_20260503_143022.json`)
- `--force`: skip confirmation

**Outputs:**
- Terminal: status line per restored skill
- Updated: `~/.agent-hunter/registry.json`, skill git repos

**Error cases:**
| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| No snapshots available | Print "nothing to restore", exit | 0 |
| Snapshot corrupted (CRC mismatch) | Fail with error, don't restore | 5 |
| Git reset fails on skill | Continue other skills, report failures | 0 |
| Snapshot not found | Print available snapshots, fail | 1 |

---

### `agent-hunter update`

**Behavior:**
1. Read installed skills from registry
2. For each skill with available update:
   - Fetch new SHA from remote
   - Show diff (what changed: commits, files)
   - Ask user: "Update to new version?"
   - If yes: fetch, pull, update registry
3. Re-run audit after all updates (to detect new conflicts)

**Inputs:**
- User confirmations per skill

**Outputs:**
- Terminal: update progress
- Updated: registry, skill repos

---

### `agent-hunter context`

**Behavior:**
1. Extract context from current project
2. Pretty-print ContextProfile so user can verify signals

**Inputs:**
- None

**Outputs:**
- Terminal: JSON or YAML dump of extracted context (user's choice)

**Example output:**
```yaml
project_root: /Users/me/project
languages: [python, javascript]
frameworks: [FastAPI, React]
databases: [PostgreSQL]
testing: [pytest, Jest]
ci_cd: [GitHub Actions]
other_tools: [Docker, Terraform]
tech_signal_count: 12
allowlist_coverage: 100%
```

---

### `agent-hunter contribute <skill-name>`

**Behavior:**
1. Validate skill exists in `~/.claude/skills/<skill-name>/`
2. Run security scan on it (reject if RED)
3. Parse SKILL.md frontmatter (reject if incomplete)
4. Open GitHub issue on `indhra/agent-hunter` with:
   - Pre-filled template (name, version, repo URL, security summary)
   - Link to `assets/contribute_template.md`
5. Fall back to printing template to stdout if `gh` not installed

**Inputs:**
- `skill-name`: name of installed skill

**Outputs:**
- GitHub: new issue created (or template printed to stdout)
- Terminal: issue URL or template content

**Error cases:**
| Condition | Behavior | Exit Code |
|-----------|----------|-----------|
| Skill not found in ~/.claude/skills/ | Print error, list installed skills | 1 |
| Security scan finds RED | Block contribution, show findings (count) | 2 |
| Frontmatter incomplete (missing name, version, trigger, domain_tags) | Block contribution, show missing fields | 3 |
| `gh` not installed | Fall back to stdout template | 0 (success) |
| GitHub API error | Fail with error message | 4 |

---

## Section 4: Module Specifications

### `context_extractor.py`

**Public Functions:**

```python
def extract_context(project_root: str) -> ContextProfile:
    """
    Extract tech signal keywords from project.
    
    Args:
        project_root: Path to project root
        
    Returns:
        ContextProfile: {tech_stack: list[str], frameworks: list, languages: list}
        
    Raises:
        ContextExtractionError: if project_root doesn't exist or is unreadable
    """
```

**Behavior:**
1. Read `CLAUDE.md`, `requirements.txt`, `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`
2. Parse `git log --oneline -50` (last 50 commits)
3. Match tokens against `TECH_ALLOWLIST` (regex-safe)
4. Return ContextProfile with counts and confidence

**Privacy:** No code, paths, or names are extracted. Only allowlist-matched keywords.

---

### `hunter.py`

**Public Functions:**

```python
class Hunter:
    def hunt(self, profile: ContextProfile, config: Dict) -> list[HuntResult]:
        """
        Search GitHub + curated sources for relevant skills.
        
        Args:
            profile: Extracted context (tech_stack, etc.)
            config: Config dict (min_stars, max_age_days, etc.)
            
        Returns:
            list[HuntResult]: ranked by prefilter pass rate
            
        Raises:
            HunterError: if all queries fail
        """
```

**Prefilter criteria (applied in parallel):**
1. `stars >= config.min_stars` (default: 10)
2. `last_commit_date > (today - config.max_age_days)` (default: 180 days)
3. `repo_has_code_files` (check `language` in GitHub repo object)
4. `tech_name_in_raw_skill_content` (fetch raw SKILL.md and search)

**Rate limiting:**
- Authenticated (with `GITHUB_TOKEN`): 5,000 req/hr
- Unauthenticated: 60 req/hr
- On 429: exponential backoff (1s, 2s, 4s), retry 3 times, then fail with message

**Error cases:**
| Condition | Behavior | Exception |
|-----------|----------|-----------|
| GitHub API unreachable | Retry 3× with backoff, then fail | `HunterError` |
| No results found | Return empty list (user can scaffold) | (none) |
| Invalid config (negative stars) | Fail loudly with config error | `ConfigError` |

---

### `security_scan.py`

**Public Functions:**

```python
def scan_skill(raw_content: str) -> ScanResult:
    """
    Scan SKILL.md for security issues.
    
    Args:
        raw_content: Raw SKILL.md content from GitHub
        
    Returns:
        ScanResult: {id, findings: list[ScanFinding]}
        
    Raises:
        ScanError: if scan crashes (e.g., invalid YAML)
    """

class ScanFinding:
    pattern: str          # e.g., "PROMPT_INJECTION"
    severity: str         # "RED", "ORANGE", "YELLOW", "GREEN"
    description: str      # Human-readable explanation
    location: Dict        # {"line": int, "snippet": str}
    remediation: str      # How to fix it
```

**Detection patterns (v0.1.0):**
1. **PROMPT_INJECTION** (RED) — Common patterns: "ignore system prompt", "forget instructions", etc.
2. **UNGUARDED_EXEC** (RED) — `exec()`, `eval()`, `subprocess.run()` without input validation
3. **EMBEDDED_SECRETS** (RED) — API keys, tokens in SKILL.md body
4. **UNICODE_OBFUSCATION** (ORANGE) — U+202E (direction override), zero-width chars, homoglyphs
5. **SUSPICIOUS_IMPORTS** (YELLOW) — `os.system`, `urllib` without context
6. **MISSING_FRONTMATTER** (YELLOW) — No YAML frontmatter

**v0.6.0 additions:**
7. **OBFUSCATION_DETECTED** (ORANGE → RED if unpack reveals RED) — base64, marshal, pickle
8. **SANDBOX_ESCAPE_ATTEMPT** (RED) — Observed during execution
9. **SUSPICIOUS_ENV_READ** (ORANGE) — Attempts to read env vars during sandbox

**Behavioral analysis (v0.6.0):**
- High-suspicion skills run in sandbox during scan
- Captures: file writes outside `/tmp`, network attempts, env var reads
- Failures are non-blocking (skill still scores, but flagged)

---

### `scorer.py`

**Public Functions:**

```python
def score_results(
    hunt_results: list[HuntResult],
    scan_results: list[ScanResult],
    profile: ContextProfile,
    config: Dict
) -> list[ScoredResult]:
    """
    Score results using 4-signal formula + YAGNI multiplier.
    
    Returns:
        list[ScoredResult]: sorted by final_score descending
    """

class ScoredResult:
    result_id: str
    final_score: float       # 0.0 – 1.0
    signals: Dict            # {stack_score, domain_score, star_score, recency_score}
    yagni_multiplier: float  # 0.5x – 2.0x
    trust_tier: str          # "VERIFIED", "COMMUNITY", "RAW"
    why_for_you: str         # Human explanation
    blocked_reason: str      # If score < threshold
```

**Scoring formula (v0.4.0):**
```
total_score = (
    stack_score × 0.30 +
    domain_score × 0.20 +
    star_score × 0.15 +
    recency_score × 0.15 +
    trust_score × 0.20
) × yagni_multiplier

stack_score: Jaccard(result_tech, profile_tech) [0 – 1]
domain_score: String similarity between result domain + profile domains [0 – 1]
star_score: min(stars / 100, 1.0) [0 – 1]
recency_score: days_since_commit < 30 ? 1.0 : 0.5 [0.5 – 1.0]
trust_score: VERIFIED=1.0, COMMUNITY=0.7, RAW=0.4

yagni_multiplier:
  - Active domain (commits in last 7 days): 2.0×
  - Recent (commits in last 30 days): 1.0×
  - Dormant (install_log: >30 days, 0 session mentions): 0.5× (v0.4.0+)
```

**v0.4.0 feedback loop:**
- Read `~/.agent-hunter/install_log.jsonl` for installed skills
- If skill installed >30 days ago + 0 session mentions → dormant → apply 0.5× multiplier
- If skill has 5+ session mentions in last 30 days → boost 1.1× (capped)
- `context_extractor.extract_sessions()` mines `~/.claude/sessions/*.jsonl` for skill mentions

**Edge cases:**
| Case | Handling |
|------|----------|
| RED scan result | Score blocked at 0.0, exclude from results |
| 0 stars | Star score = 0.0, total still computed |
| No domain match | Domain score = 0.0, other signals carry score |
| Newly installed skill | Dormancy multiplier = 1.0 (no penalty yet) |

---

### `installer.py`

**Public Functions:**

```python
def build_action_list(
    scored_results: list[ScoredResult],
    scan_results: list[ScanResult],
    installed_skills: Dict,
    dangerous: bool = False
) -> list[PendingAction]:
    """
    Build list of actions (install/disable) for user confirmation.
    
    Args:
        dangerous: If True, include DISABLE actions for RED-flagged installed skills
        
    Returns:
        list[PendingAction]: [install/disable/enable/uninstall actions]
    """

def execute_actions(actions: list[PendingAction], dry_run: bool = False) -> list[ActionResult]:
    """
    Execute install/disable/enable/uninstall actions.
    
    Args:
        dry_run: If True, skip filesystem changes, print what would happen
        
    Returns:
        list[ActionResult]: per-action success/failure status
        
    Raises:
        InstallerError: if any action fails (rolls back all prior actions)
    """

class PendingAction:
    action_type: str      # "install", "disable", "enable", "uninstall"
    skill_name: str
    repo_url: str         # GitHub repo URL
    target_sha: str       # Git SHA to install
```

**Install flow:**
1. Try `gh skill install <owner>/<repo>` (requires `gh` CLI)
2. Fall back to `git clone <repo_url> ~/.claude/skills/<skill-name>` + `git checkout <sha>`
3. Validate directory exists and contains `SKILL.md`
4. Append to `install_log.jsonl`: `{action: "install", skill_name, sha, timestamp}`

**Disable flow:**
1. Rename `~/.claude/skills/<skill-name>` → `~/.claude/skills/_<skill-name>`
2. Append to `install_log.jsonl`: `{action: "disable", skill_name, timestamp}`

**Enable flow (undo disable):**
1. Rename `~/.claude/skills/_<skill-name>` → `~/.claude/skills/<skill-name>`
2. Append to `install_log.jsonl`: `{action: "enable", skill_name, timestamp}`

**Uninstall flow (permanent, requires user confirmation):**
1. Delete `~/.claude/skills/<skill-name>` directory
2. Remove from `registry.json`
3. Append to `install_log.jsonl`: `{action: "uninstall", skill_name, timestamp}`

**Rollback on failure:**
- If any action fails, undo all prior actions in reverse order
- Print status: "Rolled back 3 installs due to failure on step 4"

---

### `registry.py`

**Public Functions:**

```python
class Registry:
    def read(self) -> Dict:
        """Load registry from ~/.agent-hunter/registry.json"""
        
    def write(self, data: Dict) -> None:
        """Save registry to ~/.agent-hunter/registry.json"""
        
    def snapshot(self, trigger: str) -> str:
        """Write timestamped snapshot to backups/, return snapshot name"""
        
    def restore_from_snapshot(self, snapshot_name: str) -> None:
        """Restore registry from snapshot"""
        
    def get_installed_skills(self) -> list[str]:
        """Return list of currently installed skill names"""
        
    def get_skill_metadata(self, skill_name: str) -> Dict:
        """Return stored SHA, install_date, etc. for a skill"""
```

**Registry schema:**
```json
{
  "version": "0.1.0",
  "created_at": "2026-05-01T10:00:00Z",
  "last_updated_at": "2026-05-03T14:30:00Z",
  "skills": {
    "skill-deploy": {
      "repo_url": "https://github.com/owner/skill-deploy",
      "git_tree_sha": "abc123...",
      "install_date": "2026-05-03T10:00:00Z",
      "trust_tier": "VERIFIED",
      "version": "1.2.3"
    }
  }
}
```

**Snapshot schema:**
```json
{
  "snapshot_time": "2026-05-03T14:00:00Z",
  "trigger": "pre_audit",
  "git_branch": "main",
  "crc32": "deadbeef",
  "registry": { ... }
}
```

---

### `rollback.py`

**Public Functions:**

```python
def rollback(target_snapshot: str = None, force: bool = False) -> None:
    """
    Restore registry + skill repos to snapshot state.
    
    Args:
        target_snapshot: Snapshot name (default: most recent)
        force: Skip confirmation
    """
```

**Behavior:**
1. List available snapshots (if target_snapshot not provided)
2. Load target snapshot
3. Show diff (skills to be restored, installed to be removed, etc.)
4. Confirm with user (unless --force)
5. Restore registry.json
6. For each skill: `git reset --hard <stored-sha>`
7. Verify restoration succeeded

---

### `reporter.py`

**Public Functions:**

```python
def render_hunt_report(
    scored_results: list[ScoredResult],
    scan_results: list[ScanResult],
    config: Dict
) -> str:
    """
    Render terminal report of hunt results.
    
    Returns:
        Formatted string with rich table
    """

def save_hunt_report(report_str: str) -> str:
    """
    Save report to ~/.agent-hunter/reports/hunt_report_YYYY-MM-DD.md
    
    Returns:
        Path to saved file
    """
```

**Output format (terminal):**
```
╭─ Hunt Results (5 matches) ──────────────────────────────────╮
│                                                              │
│ 1. skill-deploy (4.2/5.0) ⭐⭐⭐⭐ [VERIFIED]               │
│    Why: 90% tech match + verified + 250 stars               │
│    🟢 Security scan clean                                   │
│    Install with: agent-hunter install indhra/skill-deploy   │
│                                                              │
│ 2. react-hooks-audit (3.8/5.0) ⭐⭐⭐ [COMMUNITY]           │
│    Why: 75% tech match + trusted author                     │
│    🟡 Unicode obfuscation (non-critical)                    │
│    Install with: ...                                        │
│                                                              │
│ 3. ... (RED-flagged, excluded from display)                 │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

**Markdown format (saved to file):**
```markdown
# Hunt Report — 2026-05-03

## Summary
- Searched for: [tech keywords]
- Found: 5 candidates
- Passed security: 4
- Blocked (RED): 1

## Top Results

### 1. skill-deploy (Score: 4.2/5.0)
**Repo:** https://github.com/indhra/skill-deploy
**Why this for you:** 90% tech stack match + Verified + 250 stars + active
**Security:** 🟢 Clean (0 findings)
**Install:** `agent-hunter install indhra/skill-deploy`

...
```

**Special rules:**
- RED results are never shown, only count: "1 result blocked by security policies"
- ORANGE findings are shown, but don't block
- Markdown report includes counts for all severity levels
- Terminal output limited to top 10 results (user can request more via `-v`)

---

### `sandbox.py`

**Public Functions:**

```python
class Sandbox:
    def run_code(self, code: str, timeout_seconds: int = 10) -> SandboxResult:
        """
        Execute code in isolated subprocess/container.
        
        Args:
            code: Python code to run
            timeout_seconds: Execution timeout
            
        Returns:
            SandboxResult: {stdout, stderr, return_code, observed_behaviors}
        """

class SandboxResult:
    stdout: str
    stderr: str
    return_code: int
    observed_behaviors: list[str]  # ["network_attempt", "env_read_GITHUB_TOKEN", ...]
```

**Subprocess mode (default, v0.2.0+):**
- Masked env vars (GITHUB_TOKEN, ANTHROPIC_API_KEY, etc. → `***`)
- Restricted working dir (temp dir, not project root)
- No network flag (where OS supports it)
- Capture stdout/stderr
- Kill if timeout exceeded

**Docker mode (v0.6.0+, opt-in):**
- Build Dockerfile on-the-fly: `FROM python:3.12-slim`
- Run in container: no network, read-only FS (except `/tmp`), 256MB memory, CPU share=1
- 10s execution timeout, killed if exceeded
- Container discarded after test (no layer reuse)
- Graceful fallback to subprocess if Docker not installed

---

### `skill_parser.py`

**Public Functions:**

```python
def parse_skill_frontmatter(raw_content: str) -> SkillFrontmatter:
    """
    Extract YAML frontmatter from SKILL.md.
    
    Args:
        raw_content: Raw SKILL.md content
        
    Returns:
        SkillFrontmatter: parsed frontmatter + body text
        
    Raises:
        SkillParseError: if YAML is malformed
    """

class SkillFrontmatter:
    name: str
    version: str
    description: str
    trigger: str
    domain_tags: list[str]
    license: str = None
    repo_url: str = None
    author: str = None
    body: str  # Full skill markdown after frontmatter
```

**Frontmatter format:**
```yaml
---
name: skill-deploy
version: 1.2.3
description: Deploy FastAPI apps to AWS Lambda
trigger: When I say "deploy this"
domain_tags: [DevOps, AWS, FastAPI]
license: MIT
---

# Skill: Deploy to AWS Lambda
... body ...
```

**Handling:**
- Missing `---` delimiters → treat entire content as body (SkillParseError)
- Malformed YAML → fail with error message
- Missing required fields (name, version, trigger) → empty values, warn in log

---

## Section 5: Robustness Gaps & Solutions (v0.5.0 → v0.8.0)

### Gap 1: Runtime Sandboxing (v0.6.0.0)

**Problem:**
- Current `security_scan.py` uses static regex analysis
- Obfuscated code bypasses regexes: base64-encoded exec, dynamic eval, bytecode
- Even perfect static scan can't catch all attacks

**Solution:**

**Phase A (v0.6.0):**
1. Dynamic unpacking in `security_scan.py`:
   - Detects base64, marshal, pickle patterns
   - Uses AST to safely identify decode-then-exec blocks
   - Controlled execution in sandbox to unpack
   - Re-scan unpacked code for RED patterns
   
2. Behavior analysis during sandbox:
   - Monitor file writes (reject outside /tmp)
   - Monitor network (reject all)
   - Monitor env reads (flag suspicious)
   - Report findings as `SANDBOX_ESCAPE_ATTEMPT` (RED) or `SUSPICIOUS_ENV_READ` (ORANGE)

3. Docker isolation (v0.6.0+):
   - Subprocess mode: masked env, restricted cwd, no network
   - Docker mode: `FROM python:3.12-slim`, no network, read-only FS, 256MB memory, 10s timeout
   - Auto-fallback to subprocess if Docker unavailable

**Phase B (v2.0.0+):**
- WASM sandbox option for truly untrusted code
- Real-time syscall monitoring (seccomp, strace)

**Verification:**
- Obfuscated code test case: base64 exec hidden malware → detected and blocked
- Sandbox escape test case: attempt `open("/etc/passwd")` → caught and flagged
- Network test case: `urllib.request.urlopen(...)` → blocked

---

### Gap 2: Safe-State Recovery (v0.5.0.0)

**Problem:**
- Current rollback only restores `registry.json`
- No pre-audit snapshots → no recovery point if audit installs poison
- No protection against silent SHA modifications

**Solution:**

**Phase A (v0.5.0):**
1. Pre-audit snapshots:
   - Before every `audit` or `update` command, write snapshot to `~/.agent-hunter/backups/pre_audit_*.json`
   - Snapshot includes: registry, installed skills list, SHA hashes, install_log tail
   - CRC32 checksum for tamper detection
   
2. Enhanced rollback:
   - List available snapshots with metadata
   - User picks target (or `--to` flag)
   - Show diff before restore
   - Restore registry + skill git SHAs (run `git reset --hard`)
   - Verify restoration succeeded

3. Recovery playbook (`docs/RECOVERY.md`):
   - "I think a skill was compromised" → steps
   - "My registry is corrupted" → steps
   - "How to detect a poisoned SHA" → steps (v0.8.0: sig verification)

**Phase B (v0.8.0+):**
- Ed25519 signing of snapshots (cryptographic verification)
- Automatic snapshot versioning in git
- Recovery incident template for users

**Verification:**
- Snapshot written before audit (check file exists)
- Snapshot contains correct metadata
- Rollback restores registry + skill SHAs correctly
- CRC32 validation detects corrupted snapshot
- Recovery playbook is clear and actionable

---

### Gap 3: Dependency Conflict Management (v0.7.0.0)

**Problem:**
- Skills can declare `requirements.txt`: Skill A wants `pydantic<2.0`, Skill B wants `pydantic>=2.0`
- Installing both breaks both
- Current code doesn't detect or resolve conflicts
- `pip install` would fail, leaving agent in broken state

**Solution:**

**Phase A (v0.7.0):**
1. Dependency resolver (`scripts/dep_resolver.py`):
   - Reads all installed skill `requirements.txt`, `pyproject.toml`, `package.json`, `Gemfile`
   - Builds conflict graph: which skills have incompatible dependencies
   - Attempts to find compatible semver range for each package
   - Output: list of conflicts + proposed resolutions (or "UNRESOLVABLE")
   
2. Audit --deps command:
   - Reports total unique dependencies
   - Lists conflicting pairs + severity
   - Recommends: uninstall, upgrade one skill, or use container mode
   - Completes in ≤ 5s for 50 skills

3. Version compatibility matrix:
   - Registry stores: `python_version_tested`, `node_version_tested` per skill
   - On audit: compare vs. host environment
   - Host Python 3.12, skill tested on 3.10 → 🟡 compatibility warning
   - Host Python 3.12, skill tested on 3.6 → 🔴 incompatible

4. Skill isolation options (config):
   - `"skill_isolation": "none" | "venv" | "container"` (default: none)
   - `venv`: each skill gets isolated Python venv
   - `container`: each skill runs in isolated Docker container

**Phase B (v2.0.0+):**
- Automatic conflict resolution via dependency pinning
- Multi-env testing (Python 3.10, 3.11, 3.12)
- Manifest.lock-style lock files for reproducibility

**Verification:**
- Resolver detects pydantic version conflict (fixture test)
- Resolver proposes valid semver range or UNRESOLVABLE flag
- Audit --deps completes in ≤ 5s
- Container mode: skill runs correctly in isolated env

---

### Gap 4: Web-of-Trust & Verified Indexing (v0.8.0.0)

**Problem:**
- Current hunt uses GitHub Search API only
- Search is rate-limited (60 req/hr unauthenticated, 5000/hr authenticated)
- Highly vulnerable to SEO poisoning: attacker registers `skll-deploy` (typo) to rank high
- No way to distinguish "popular among bots" from "genuinely useful"
- No curated index to bootstrap trust

**Solution:**

**Phase A (v0.8.0):**
1. Cryptographic signing:
   - Verified skills in `references/VERIFIED_SKILLS.md` are signed with Ed25519 key
   - Key in `references/TRUSTED_KEYS.pub`
   - Hunter verifies signature before showing result
   - Failed signature → 🔴 flag "Signature mismatch — tampered?"

2. Typo-squat detection:
   - For each hunt result, compute Levenshtein distance to verified skills
   - Distance ≤ 2 → flag as "⚠️ Similar to verified skill XXX"
   - Config: `"block_typo_results": true` to exclude typos entirely

3. Curated sources:
   - New data source: `references/CURATED_SOURCES.md` lists trusted registries
   - Examples: awesome-claude-skills org, private company index
   - Hunter consults curated sources BEFORE GitHub Search
   - Results labeled `[CURATED]` (higher trust tier than raw)

4. Verified index maintenance:
   - Contributing.md: process for submitting skills
   - Criteria: 50+ stars, active (commit in 60d), passing security scan, 2 maintainer sign-offs
   - Automated: weekly GitHub Actions re-scans all verified skills

5. Web-of-Trust graph (optional):
   - Users can endorse trusted authors: `~/.agent-hunter/trusted_authors.json`
   - Skills by trusted authors get `[AUTHOR_TRUSTED]` label + 0.15× score bonus
   - Community web-of-trust without central authority

**Phase B (v2.0.0+):**
- Formal threat model for Web-of-Trust (published in SECURITY.md)
- Integration with SBOM standards (SPDX)
- Decentralized trust via blockchain signatures (optional, research phase)

**Verification:**
- Verified skill signature validates correctly
- Signature verification fails (with clear error) for tampered entry
- Typo-squat detection flags `skll-deploy` as similar to `skill-deploy`
- Curated sources return results with `[CURATED]` label
- `CONTRIBUTING.md` is clear and actionable
- Weekly re-scan of verified skills executes successfully

---

## Section 6: Configuration

### `config/defaults.json`

```json
{
  "hunt": {
    "min_stars": 10,
    "max_age_days": 180,
    "phase": "growth",
    "timeout_seconds": 30
  },
  "sandbox": {
    "mode": "subprocess",
    "docker_fallback": true,
    "timeout_seconds": 10
  },
  "skill_isolation": "none",
  "snapshot_retention_days": 90,
  "max_snapshots_kept": 30,
  "freeze_mode": false,
  "min_trust_tier": "raw",
  "block_typo_results": false,
  "github_token": "<from env>",
  "log_level": "info"
}
```

### User Config (`~/.agent-hunter/config.json`)

User can override any defaults. Missing keys inherit from `defaults.json`.

---

## Section 7: Error Handling Matrix

All scripts must follow this matrix:

| Scenario | HTTP Status | Exit Code | User Message | Recovery |
|----------|-------------|-----------|--------------|----------|
| Context extraction fails | N/A | 1 | "Failed to read project files: [reason]" | Abort |
| GitHub API 404 | 404 | 2 | "Repo not found: [URL]" | Continue hunt with other results |
| GitHub API 429 (rate limit) | 429 | 2 | "Rate limited. Retrying with backoff..." | Retry 3× with exponential backoff |
| GitHub API 500+ | 5xx | 2 | "GitHub API error. Try again in 5 mins." | Abort |
| Network timeout | N/A | 4 | "Network timeout. Check internet connection." | Abort or retry |
| Disk full | N/A | 6 | "Disk full. Cannot save registry." | Abort |
| Permission denied (install) | N/A | 3 | "Permission denied: ~/.claude/skills/. Are permissions correct?" | Fail + rollback |
| Invalid JSON in registry | N/A | 7 | "Registry corrupted. Run `agent-hunter rollback`." | Fail |
| Git reset fails | N/A | 3 | "Failed to restore skill-name SHA. Git error: [reason]" | Fail + continue other skills |

---

## Section 8: Testing Strategy

### Fixture Files (`tests/fixtures/`)

| File | Purpose |
|------|---------|
| `clean_skill.md` | Valid SKILL.md (no findings) |
| `malicious_skill.md` | SKILL.md with RED findings (prompt injection + exec) |
| `obfuscated_skill.md` | SKILL.md with base64 obfuscation (v0.6.0+) |
| `version_conflict_skills.md` | Pydantic v1 vs v2 (v0.7.0+) |
| `typo_squat_skill.md` | Name similarity to known skill (v0.8.0+) |

### Test Categories

| Category | Coverage Goal | Examples |
|----------|---|---|
| Unit | Function level | `test_context_extractor.py`, `test_score.py` |
| Integration | Data flow | `test_hunter_to_scanner.py` |
| Regression | Attack patterns | `test_security_patterns.py` (50+ cases) |
| Performance | Benchmarks | `test_hunt_time_target.py` (must complete in 25s) |
| E2E | Full pipeline | `test_end_to_end_hunt.py` (real GitHub queries) |

---

## Section 9: Security Assumptions & Guarantees

### Assumptions (not guaranteed by agent-hunter)
1. User's GitHub token is not compromised
2. User's filesystem enforces Unix permissions
3. User's network is not MITM-attacking GitHub.com
4. User's host OS provides basic process isolation (v0.6.0: Docker hardens)
5. User's Python environment is not pre-compromised

### Guarantees (provided by agent-hunter)
1. RED results are NEVER installed
2. Rollback is always available
3. No LLM API calls from scripts
4. No telemetry or analytics
5. No credentials stored in plain text in files
6. Human confirmation required for all actions
7. Fail loudly on errors (no silent failures)

### Out of Scope (not the tool's responsibility)
- Detecting vulnerability in installed skills (that's the host agent's job via red-teaming)
- Detecting user's own malicious configurations
- Protecting against advanced persistent threats (APTs)
- Guaranteeing 100% malware detection (no tool does this)

---

## Section 10: Performance Targets (v1.0.0+)

| Operation | Target | Measured On |
|-----------|--------|-------------|
| Hunt (authenticated, 5 results) | ≤ 25s | 2-core machine, cold GitHub API |
| Hunt (unauthenticated, 3 results) | ≤ 60s | Public API rate limit |
| Audit (20 installed skills) | ≤ 45s | Parallel re-scan + SHA checks |
| Audit (50 skills, with --deps) | ≤ 5s | Dependency resolver |
| Rollback (restore registry + 10 skills) | ≤ 2s | Git reset for each skill |
| Sandbox execution (safe code) | ≤ 10s | Python 3.12 subprocess |
| Docker sandbox startup | ≤ 3s | Image pull + container start |
| Signature verification (100 skills) | ≤ 100ms | Ed25519 verification |
| Typo-squat detection (50 verified skills) | ≤ 50ms | Levenshtein distance |

---

## Section 11: Future Enhancements (v2.0.0+)

- Skill package bundles (e.g., "full-stack-dev": [react, node, postgres-helper])
- Dedicated MCP server registry (separate from SKILL.md)
- Automated conflict resolution + environment rebuilding
- Opt-in anonymized telemetry for scoring improvements
- Web dashboard for skill management
- Fleet deployment (team-wide skill provisioning)
- LLM marketplace (model version compatibility matrix)

---

*This specification is versioned alongside the tool. Updates are published on each MINOR/PATCH/BUILD release.*

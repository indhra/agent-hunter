# agent-hunter Recovery Playbook

**Version:** 0.5.0.0
**Last updated:** 2026-05-03

This is the step-by-step guide for recovering from incidents involving installed skills. It assumes agent-hunter v0.5.0+ with pre-audit snapshot support.

---

## Quick Reference

| Scenario | Command | Time |
|----------|---------|------|
| "I think a skill was compromised" | `agent-hunter rollback` + `agent-hunter audit` | 5 min |
| "My registry is corrupted" | `agent-hunter rollback` | < 1 min |
| "I want to see what changed" | `agent-hunter rollback` (shows diff) | 2 min |
| "I need to go back 5 updates" | `agent-hunter rollback --to <snapshot>` | < 1 min |
| "List all my recovery points" | `agent-hunter audit` (shows snapshots in report) | 1 min |

---

## Scenario 1: "I think a skill was compromised"

**Symptoms:**
- A skill suddenly behaves differently
- Error messages mention unexpected files or network calls
- Performance degradation
- Audit report shows RED security findings

**Recovery Steps:**

### Step 1: Isolate the Skill

```bash
# Disable the suspicious skill (reversible)
agent-hunter disable <skill-name>

# Verify it's disabled
ls -la ~/.claude/skills/ | grep "^d.*_skill-name"
```

### Step 2: Review Snapshots

```bash
# List available snapshots
agent-hunter audit --list-snapshots

# Pick the most recent snapshot BEFORE the suspected compromise
```

### Step 3: Rollback (Optional — only if you want to restore state)

```bash
# Start interactive rollback
agent-hunter rollback

# Or directly restore to a specific snapshot
agent-hunter rollback --to pre_audit_20260503_143022.json
```

### Step 4: Re-audit All Installed Skills

```bash
# Re-run security scan on all skills
agent-hunter audit

# Review any RED findings
```

### Step 5: Decision

**If audit shows no RED findings:**
- The skill may have been a false alarm. Re-enable it: `agent-hunter enable <skill-name>`
- Monitor its behavior closely

**If audit shows RED findings:**
- Remove the skill permanently: `agent-hunter remove <skill-name>`
- Uninstall command logs the uninstall to `install_log.jsonl`

---

## Scenario 2: "My registry is corrupted" (or I cannot read it)

**Symptoms:**
- `agent-hunter hunt` fails with "Registry corrupted"
- Files in `~/.agent-hunter/registry.json` are empty or malformed JSON
- Previous commands worked but now fail consistently

**Recovery Steps:**

### Step 1: Backup Current State

```bash
cp ~/.agent-hunter/registry.json ~/.agent-hunter/registry.json.corrupted
```

### Step 2: Restore from Snapshot

```bash
# This will list snapshots and let you pick one
agent-hunter rollback

# Or restore to the most recent snapshot automatically
agent-hunter rollback --force
```

### Step 3: Verify Restoration

```bash
# Check registry is readable
cat ~/.agent-hunter/registry.json | jq .

# Check all installed skills are listed
agent-hunter audit
```

### Step 4: If No Snapshots Exist

If rollback says "No snapshots available," the registry must be manually rebuilt:

```bash
# Manually list installed skills
ls -la ~/.claude/skills/

# Recreate registry by reinstalling each skill
# (This is a last resort; ask for help if unsure)
```

---

## Scenario 3: "I want to see what changed between two snapshots"

**Symptoms:**
- You want to audit changes made by a recent update
- You need to understand what changed in the registry

**Recovery Steps:**

### Step 1: List Snapshots

```bash
agent-hunter rollback  # (don't confirm; just view the list)
```

### Step 2: Compare Two Snapshots Manually

```bash
# Extract registry data from snapshot 1
jq '.registry' ~/.agent-hunter/backups/pre_audit_20260503_143022.json > /tmp/snap1.json

# Extract registry data from snapshot 2
jq '.registry' ~/.agent-hunter/backups/pre_audit_20260502_120000.json > /tmp/snap2.json

# Show the diff
diff -u /tmp/snap1.json /tmp/snap2.json | less
```

### Step 3: If You Want to Rollback

```bash
agent-hunter rollback --to pre_audit_20260503_143022.json
```

---

## Scenario 4: "I accidentally uninstalled a skill and want to restore it"

**Symptoms:**
- You ran `agent-hunter remove <skill-name>` by mistake
- The skill directory is gone from `~/.claude/skills/`
- You want to recover the exact version you had

**Recovery Steps:**

### Step 1: Find the Pre-Uninstall Snapshot

```bash
# Look for a snapshot BEFORE the uninstall happened
agent-hunter rollback  # (view the list; don't restore yet)

# Note the snapshot timestamp or name
```

### Step 2: Restore from Snapshot

```bash
agent-hunter rollback --to pre_audit_20260502_140000.json --force
```

### Step 3: Verify the Skill is Restored

```bash
ls -la ~/.claude/skills/<skill-name>

agent-hunter audit  # Should show the skill as "Healthy"
```

---

## Scenario 5: "I want to freeze my installation (prevent accidental changes)"

**Symptoms:**
- You have a stable set of skills and want to protect them
- You want snapshots to be written, but not allow install/disable/enable/uninstall

**Recovery Steps:**

### Step 1: Enable Freeze Mode

```bash
# Edit ~/.agent-hunter/config.json
{
  "freeze_mode": true
}
```

### Step 2: Now All Actions Require Explicit Confirmation

```bash
# Try to disable a skill — it will ask for extra confirmation
agent-hunter disable <skill-name>

# Disable is now blocked until you unset freeze_mode
```

### Step 3: Unfreeze When Ready

```bash
# Edit config.json again
{
  "freeze_mode": false
}
```

---

## Scenario 6: "I want to see the recovery history"

**Symptoms:**
- You want to know what changes were made to installed skills over time
- You need audit trail for compliance

**Recovery Steps:**

### Step 1: Review Snapshots

```bash
# List all snapshots with timestamps and triggers
ls -lh ~/.agent-hunter/backups/

# View metadata of each snapshot
jq '{snapshot_time, trigger, git_branch}' ~/.agent-hunter/backups/*.json
```

### Step 2: Review Install Log

```bash
# Install log records every action: install, disable, enable, uninstall
cat ~/.agent-hunter/install_log.jsonl | jq .

# Filter by action type
cat ~/.agent-hunter/install_log.jsonl | jq 'select(.action == "install")'
```

### Step 3: Generate Audit Report

```bash
# Audit report includes all skills, their status, and recovery info
agent-hunter audit

# Save to file for records
agent-hunter audit > audit_report_$(date +%Y%m%d).txt
```

---

## Incident Response Checklist

**If you suspect a security incident:**

- [ ] **Isolate**: Run `agent-hunter disable <skill-name>` to quarantine the skill
- [ ] **Snapshot**: Before any changes, note the current snapshot via `agent-hunter rollback --list`
- [ ] **Audit**: Run `agent-hunter audit` and review all findings (especially RED)
- [ ] **Decide**:
  - [ ] False alarm? Re-enable with `agent-hunter enable`
  - [ ] Real threat? Remove with `agent-hunter remove` and save findings
- [ ] **Investigate**: Run `agent-hunter context` to understand what the skill has access to
- [ ] **Recover**: If needed, rollback to pre-compromise state with `agent-hunter rollback`
- [ ] **Prevent**: After incident, review SECURITY.md for hardening recommendations

---

## Error Handling

### Rollback Fails with "Snapshot Integrity Check Failed"

**Cause:** Snapshot file is corrupted (CRC32 mismatch)

**Fix:**
1. Delete the corrupted snapshot: `rm ~/.agent-hunter/backups/<corrupted-snapshot>.json`
2. Try rollback again: `agent-hunter rollback`
3. If all snapshots are corrupted, reach out to maintainers for manual recovery

### Rollback Says "No Snapshots Available"

**Cause:** This is the first time you're trying to recover, or snapshots were deleted

**Fix:**
1. If you have no snapshots, you cannot rollback. Going forward:
   - Run `agent-hunter audit` to create a snapshot before your next operation
2. To manually rebuild from current state, list installed skills:
   - `ls ~/.claude/skills/` and note each skill name

### Git Reset Fails During Rollback

**Cause:** Skill's git repo is corrupted or has uncommitted changes

**Fix:**
1. Rollback completes but flags the failed skill with ✗
2. To repair the skill manually:
   ```bash
   cd ~/.claude/skills/<skill-name>
   git status  # to see what's broken
   git reset --hard HEAD  # to discard local changes
   ```

### Registry File Missing After Rollback

**Cause:** Rare — file system error during restore

**Fix:**
1. Check if backup is intact: `ls ~/.agent-hunter/backups/`
2. Manually copy a recent snapshot back: `cp ~/.agent-hunter/backups/pre_audit_*.json ~/.agent-hunter/registry.json`
3. Open an issue with agent-hunter team

---

## Prevention Checklist

**To avoid incidents in the future:**

- [ ] **Review audit reports regularly** — run `agent-hunter audit` weekly
- [ ] **Enable freeze mode during stable periods** — protects against accidental changes
- [ ] **Monitor install_log.jsonl** — check for unexpected actions
- [ ] **Use verified skills only** — hunt with `--min-trust-tier community` to raise the bar
- [ ] **Keep agent-hunter updated** — new versions have improved scanning
- [ ] **Test in staging** — before installing production skills in a shared environment
- [ ] **Set snapshot retention** — tune `snapshot_retention_days` and `max_snapshots_kept` in config.json

---

## Getting Help

**If recovery steps don't work:**

1. **Check logs:**
   ```bash
   cat ~/.agent-hunter/logs/*.log  # if logging is enabled
   ```

2. **Generate diagnostic bundle:**
   ```bash
   agent-hunter audit --verbose  # shows full details
   ls -lah ~/.agent-hunter/  # show all config and backup files
   ```

3. **Open an issue on GitHub:**
   - Include the diagnostic bundle
   - Describe what you were doing when the issue occurred
   - Paste the exact error message

4. **Manual recovery (last resort):**
   - Contact agent-hunter maintainers
   - Provide: corrupted registry.json, any available snapshots, install_log.jsonl

---

## Glossary

- **Snapshot**: Timestamped backup of registry.json + metadata (trigger, git branch, CRC32)
- **Rollback**: Restore registry and skill SHAs to a snapshot state
- **Freeze mode**: Config option to require extra confirmation for install/disable/enable/uninstall
- **SHA**: Git commit hash, stored per skill to detect tampering
- **CRC32**: Checksum used to detect snapshot file corruption
- **Install log**: Append-only JSONL file recording all actions (install, disable, enable, uninstall)

---

*Last updated: 2026-05-03. For the latest version, see https://github.com/indhra/agent-hunter/docs/RECOVERY.md*

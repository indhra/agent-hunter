---
name: "agent-hunter-update"
description: "Upgrade agent-hunter to the latest version. Pulls the latest code and re-runs setup to install new skills and dependencies."
version: "0.4.0"
license: "MIT"
author: "Indhra Kiranu N A"
compatibility:
  claude: ">=1.0.0"
triggers:
  - "agent-hunter update"
  - "update agent-hunter"
  - "upgrade agent-hunter"
  - "agent-hunter upgrade"
mcp_dependencies: []
skill_dependencies: []
---

# /agent-hunter-update

Upgrade agent-hunter to the latest version.

## Step 1 — Pull latest

Run this in the terminal:

```bash
cd ~/.claude/skills/agent-hunter && git pull && ./setup
```

## Step 2 — Show what changed

After the pull, show the user the git log summary:

```bash
cd ~/.claude/skills/agent-hunter && git log --oneline -10
```

Report: "agent-hunter updated. Here's what changed:" and summarize the log in plain English — no commit hashes, just the feature names and fixes.

## Step 3 — Done

Confirm the update is complete and remind the user they can run `/agent-hunter` to hunt for new skills relevant to their current project.

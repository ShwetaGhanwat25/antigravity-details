# Running with Antigravity Agent

How to run the PR Review Bot using the Antigravity agent platform instead of the Python scripts directly. In this approach, Antigravity orchestrates everything — it runs the agent, calls the skills, manages the MCP connections, and handles scheduling.

---

## How This Differs from the Python Approach

| | Python approach (`make` commands) | Antigravity approach |
|---|---|---|
| What runs the code | You run Python scripts manually | Antigravity runs the agent automatically |
| Scheduling | Python `schedule` library inside `runner.py` | Antigravity's built-in scheduler |
| GitHub + Chat connections | Direct API calls via `requests` | GitHub MCP + Google Chat MCP |
| PR review trigger | GitHub Actions or Flask + ngrok | Antigravity webhook listener |
| CLI trigger | `python src/test_reviewer.py --live` | `antigravity pr-review <repo> <PR#>` |

---

## Files Used in This Approach

```
agent.md                                   # defines the agent — its role, skills, and MCPs
skills/pr-diff-analyzer/SKILL.md           # Skill 1: fetch diff + run Gemini analysis
skills/review-commenter/SKILL.md           # Skill 2: post review + label + notify Chat
mcp/github-mcp/mcp_config.json             # connects the agent to GitHub API
mcp/google-chat-mcp/mcp_config.json        # connects the agent to Google Chat
scheduled-tasks/stale-pr-digest.json       # tells Antigravity: run digest weekdays 9 AM
scheduled-tasks/weekly-review-report.json  # tells Antigravity: run report Mondays 8 AM
plugin/plugin.json                         # registers the CLI command
plugin/skills/pr-review-trigger/SKILL.md   # defines how the CLI command runs the agent
```

---

## Prerequisites

- Antigravity 2.0 installed (CLI + IDE)
- A GitHub Personal Access Token with `repo` and `pull_requests:write` scopes
- A Gemini API key from [aistudio.google.com](https://aistudio.google.com)
- A Google Chat space with a webhook URL
- Your `.env` file filled in (see `SETUP_GUIDE.md` Step 2)

---

## Step 1 — Register the MCPs in Antigravity

MCPs are how the agent talks to GitHub and Google Chat. You register them once.

**GitHub MCP**
1. Open Antigravity IDE → MCP panel (sidebar or `Ctrl+Shift+M`)
2. Click **+ Add MCP** → **From file**
3. Select `mcp/github-mcp/mcp_config.json`
4. No authentication needed — it uses your `GITHUB_TOKEN` env var automatically

**Google Chat MCP**
1. In the MCP panel → **+ Add MCP** → **From file**
2. Select `mcp/google-chat-mcp/mcp_config.json`
3. Click **Authenticate** → sign in with your Google Workspace account
4. Approve permissions (Chat: create messages, read spaces)
5. Status should show ✅ Connected

---

## Step 2 — Load the Agent

1. Open Antigravity IDE
2. Click **+ New Agent** → **From file**
3. Select `agent.md`
4. The agent `pr-review-agent` should appear with both skills registered:
   - `pr-diff-analyzer`
   - `review-commenter`

---

## Step 3 — Set Up Scheduled Tasks

This replaces `make reports-scheduled` — Antigravity handles the cron scheduling.

**Via CLI:**
```bash
antigravity schedule load scheduled-tasks/stale-pr-digest.json
antigravity schedule load scheduled-tasks/weekly-review-report.json
```

**Via IDE:**
1. Open the **Scheduled Tasks** panel
2. Click **+ Import** → select `scheduled-tasks/stale-pr-digest.json`
3. Click **+ Import** → select `scheduled-tasks/weekly-review-report.json`
4. Both tasks appear as **Active** — stale digest weekdays 9 AM, weekly report Mondays 8 AM

To trigger either report immediately without waiting for the schedule:
```bash
antigravity schedule run stale-pr-digest
antigravity schedule run weekly-review-report
```

---

## Step 4 — Install the CLI Plugin

This gives you the `antigravity pr-review` terminal command.

```bash
# Windows
Copy-Item -Recurse "plugin" "$env:USERPROFILE\.gemini\antigravity-cli\pr-review"

# Mac/Linux
cp -r plugin ~/.gemini/antigravity-cli/pr-review
```

Verify:
```bash
antigravity --list-plugins
# Should show: pr-review — Manual PR review trigger
```

---

## Step 5 — Wire Up the PR Review Trigger

The agent needs to receive GitHub PR events. Point your GitHub repo's webhook at Antigravity's listener URL.

1. In Antigravity IDE, open the `pr-review-agent` → **Webhooks** tab
2. Copy the listener URL (format: `https://antigravity.run/webhooks/<your-id>`)
3. Go to your GitHub repo → **Settings → Webhooks → Add webhook**
   - Payload URL: the Antigravity listener URL
   - Content type: `application/json`
   - Events: **Pull requests** only
4. Click **Add webhook** — GitHub sends a ping and the agent activates

---

## How It Runs After Setup

```
PR opened/updated on GitHub
        ↓
GitHub sends event to Antigravity webhook listener
        ↓
Antigravity triggers pr-review-agent (agent.md)
        ↓
Agent runs Skill 1: pr-diff-analyzer
  → GitHub MCP fetches the diff
  → Gemini analyzes it and returns structured review
        ↓
Agent runs Skill 2: review-commenter
  → GitHub MCP posts comment + inline comments + label
  → Google Chat MCP sends notification
        ↓
Done — no manual action needed
```

---

## CLI Usage

Manually trigger a review from the terminal on any PR:

```bash
# Full review — posts comment, label, and Chat notification
antigravity pr-review org/my-repo 42

# Preview only — prints review to terminal, no GitHub or Chat writes
antigravity pr-review org/my-repo 42 --dry-run

# Review without Chat notification
antigravity pr-review org/my-repo 42 --no-chat
```

---

## Comparison: Which Approach to Use

| Situation | Use |
|---|---|
| Demo or test the reports right now | `make reports` |
| Run reports on a schedule without Antigravity | `make reports-scheduled` |
| Full production setup on Antigravity platform | This guide |
| PR review without a server | GitHub Actions (see `SETUP_GUIDE.md`) |

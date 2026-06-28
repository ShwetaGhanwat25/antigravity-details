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

## Exact References — Where Antigravity Is Wired In

Every place in the codebase where Antigravity reads a config, makes a decision, or takes over from the Python scripts.

**`agent.md`**
- Line 2 — `name: pr-review-agent` — the agent name Antigravity uses to identify and load this agent
- Lines 10–12 — `skills:` block — tells Antigravity which skill files to load and run in sequence (pr-diff-analyzer first, then review-commenter)
- Lines 13–15 — `mcps:` block — tells Antigravity which MCP connections to wire up before the agent runs
- Line 68 — lists the 6 GitHub MCP tools the agent is allowed to call by name
- Line 70 — lists the `send_message` Google Chat MCP tool

**`mcp/github-mcp/mcp_config.json`**
- Line 2 — `$schema` pointing to Antigravity's MCP schema — marks this file as an Antigravity-managed MCP config
- Line 5 — `transport: stdio` — Antigravity spawns the MCP as a subprocess and communicates over stdin/stdout
- Line 9 — `"GITHUB_TOKEN": "${GITHUB_TOKEN}"` — Antigravity injects the env var when starting the MCP process
- Lines 11–77 — `tools:` array — the 6 GitHub API tools (`get_pr_diff`, `post_pr_comment`, `post_inline_comment`, `apply_pr_label`, `get_pr_review_comments`, `list_open_prs`) that the agent calls by name during a review

**`mcp/google-chat-mcp/mcp_config.json`**
- Line 2 — `$schema` — Antigravity MCP schema, same as above
- Line 5 — `transport: sse` — unlike GitHub MCP, this connects to Google's remote MCP server over SSE instead of spawning a local subprocess
- Line 6 — `url: https://chatmcp.googleapis.com/mcp/v1` — the remote MCP endpoint Antigravity connects to
- Lines 7–12 — `auth: oauth2` — Antigravity handles the full OAuth2 login flow when you click Authenticate in the IDE
- Line 15 — `default_space: ${GOOGLE_CHAT_SPACE_ID}` — Antigravity injects this so the agent doesn't need to specify the space on every call
- Lines 19–31 — `send_message` tool definition — the only tool in this MCP; used by the agent every time it sends a notification

**`scheduled-tasks/stale-pr-digest.json`**
- Line 2 — `$schema` pointing to Antigravity's scheduled task schema — marks this as a scheduler config
- Line 6 — `cron: "0 9 * * 1-5"` — Antigravity reads this to know when to fire the task (weekdays 9 AM IST)
- Line 7 — `timezone: Asia/Kolkata` — Antigravity converts this to UTC when scheduling internally
- Line 10 — `agent: pr-review-agent` — Antigravity routes the task to this specific agent when it fires
- Line 11 — `prompt:` — the natural language instruction Antigravity sends to the agent as its input when the cron fires
- Line 12 — `script: src/stale_pr_checker.py` — the Python script Antigravity executes directly (alternative to the agent prompt)
- Lines 23–26 — `retry:` block — Antigravity retries the task up to 2 times with a 30-second delay if it fails

**`scheduled-tasks/weekly-review-report.json`**
- Line 6 — `cron: "0 8 * * 1"` — every Monday at 8 AM IST
- Line 10 — `agent: pr-review-agent` — same agent, different task
- Line 12 — `script: src/weekly_reporter.py` — the Python script Antigravity runs for this task
- Lines 28–30 — `retry:` — 2 attempts, 60-second delay (longer than the digest because this task aggregates more data)

**`plugin/plugin.json`**
- Line 2 — `$schema` pointing to Antigravity's plugin schema — registers this directory as a CLI plugin
- Line 3 — `name: pr-review` — the plugin name; this is what makes `antigravity pr-review` a valid CLI command
- Lines 14–26 — `commands:` block — defines the exact usage, examples, and flags for `antigravity pr-review <repo> <pr-number>`
- Lines 28–30 — `env_required:` — Antigravity validates that `GEMINI_API_KEY` and `GITHUB_TOKEN` are set before it lets the command run

**`src/reviewer.py` — where Gemini is called (Antigravity invokes this via skills)**
- Line 5 — `from google import genai` — imports the Gemini SDK
- Line 17 — `_client = genai.Client(api_key=GEMINI_API_KEY)` — initialises the Gemini client at startup
- Lines 141–150 — `_call_gemini()` function — the single place where the Gemini API is called; retries once on failure
- Line 143 — `model="gemini-2.0-flash-lite"` — the specific Gemini model Antigravity's agent uses for every review

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

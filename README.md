# PR Review Bot — Anti-Gravity EVOlution

An autonomous AI-powered code review agent built on **Google Antigravity 2.0**. Automatically reviews every GitHub Pull Request using Gemini or Groq/Llama — posting severity-scored inline comments, applying labels, and notifying your team on Google Chat.

---

## What It Does

When a PR is opened or updated against `main`, the agent:

1. **Fetches the diff** from GitHub via the GitHub MCP
2. **Analyzes the code** with Gemini 2.0 Flash or Groq Llama 3.3 — scoring every issue as 🔴 CRITICAL, 🟡 WARNING, or 🟢 INFO
3. **Posts inline comments** directly on the flagged lines in the diff
4. **Applies a GitHub label** — `✅ approved`, `⚠️ needs-changes`, or `🔴 blocked`
5. **Notifies the team** with a summary in your Google Chat space
6. **Detects re-reviews** — if new commits are pushed, the bot highlights only what changed

You can also trigger a review manually from the terminal:
```bash
antigravity pr-review org/my-repo 42
```

---

## Architecture

```
GitHub PR Event
      │
      ▼
Webhook Server (Flask) ──── or ──── GitHub Actions
      │                                   │
      └──────────────┬────────────────────┘
                     ▼
           pr-review-agent (agent.md)
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
  pr-diff-analyzer       review-commenter
  (SKILL 1)              (SKILL 2)
  • fetch diff           • post PR comment
  • call Gemini          • post inline comments
  • parse severity       • apply label
  • return review obj    • notify Google Chat
          │
    ┌─────┴─────┐
    ▼           ▼
GitHub MCP  Google Chat MCP
```

---

## Project Structure

```
auto-pr-review/
├── agent.md                          # Agent orchestration definition
├── skills/
│   ├── pr-diff-analyzer/SKILL.md    # Skill 1: fetch + analyze PR diff
│   └── review-commenter/SKILL.md    # Skill 2: post feedback + notify
├── mcp/
│   ├── github-mcp/mcp_config.json   # GitHub API integration
│   └── google-chat-mcp/mcp_config.json  # Google Chat integration
├── scheduled-tasks/
│   ├── stale-pr-digest.json         # Daily 9am: flag unreviewed PRs
│   └── weekly-review-report.json    # Monday 8am: weekly activity report
├── plugin/
│   ├── plugin.json                  # CLI plugin manifest
│   └── skills/pr-review-trigger/SKILL.md
├── src/
│   ├── reviewer.py                  # Core review engine
│   ├── webhook_server.py            # Flask webhook receiver
│   ├── stale_pr_checker.py          # Scheduled task 1 script
│   ├── weekly_reporter.py           # Scheduled task 2 script
│   ├── test_reviewer.py             # Local test tool
│   └── requirements.txt
└── .github/workflows/pr-review.yml  # GitHub Actions alternative
```

---

## Setup

### 1. Environment Variables

Create a `.env` file (never commit this):

```env
GEMINI_API_KEY=your_google_ai_studio_key
GITHUB_TOKEN=ghp_your_github_pat
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...
GOOGLE_CHAT_SPACE_ID=spaces/your_space_id
WATCHED_REPOS=org/repo-one,org/repo-two
```

### 2. Install Dependencies

```bash
pip install -r src/requirements.txt
```

### 3. Configure MCPs in Antigravity

Open Antigravity IDE → MCP panel → Add MCP:
- **GitHub MCP**: point to `mcp/github-mcp/mcp_config.json`
- **Google Chat MCP**: point to `mcp/google-chat-mcp/mcp_config.json` → click Authenticate → sign in with your Google Workspace account

### 4. Install the CLI Plugin

```bash
cp -r plugin ~/.gemini/antigravity-cli/pr-review
```

### 5. Set Up Scheduled Tasks in Antigravity

```
/schedule stale-pr-digest — load from scheduled-tasks/stale-pr-digest.json
/schedule weekly-review-report — load from scheduled-tasks/weekly-review-report.json
```

### 6. Start the Webhook Server

```bash
# Terminal 1 — start Flask
python src/webhook_server.py

# Terminal 2 — expose to internet
ngrok http 5000
```

Then add the ngrok URL to your GitHub repo: **Settings → Webhooks → Add webhook**
- Payload URL: `https://your-ngrok-url/webhook`
- Content type: `application/json`
- Secret: same as `GITHUB_WEBHOOK_SECRET`
- Events: Pull requests only

### Alternative: GitHub Actions (no server needed)

Add these secrets to your GitHub repo (**Settings → Secrets and variables → Actions**):
- `GEMINI_API_KEY` *(if using Gemini)*
- `GROQ_API_KEY` *(if using Groq)*
- `GOOGLE_CHAT_WEBHOOK_URL`
- `GITHUB_TOKEN` *(already available as a default secret)*

Add a repository variable (same settings page → **Variables** tab):
- `IS_GEMINI` = `true` (Gemini) or `false` (Groq)

The `.github/workflows/pr-review.yml` workflow will run automatically on every PR.

---

## Testing Locally

```bash
# Dry run — calls Gemini with a fake diff, prints to terminal, no GitHub writes
python src/test_reviewer.py

# Dry run on a real PR — fetches real diff, prints review, no writes
python src/test_reviewer.py --dry-run 1

# Live test — posts a real comment and label on the specified PR
python src/test_reviewer.py --live 1
```

---

## CLI Plugin Usage

```bash
# Review a PR
antigravity pr-review org/my-repo 42

# Review without sending a Google Chat notification
antigravity pr-review org/my-repo 42 --no-chat

# Preview the review without posting anything
antigravity pr-review org/my-repo 42 --dry-run
```

---

## Scheduled Tasks

| Task | Schedule | What it does |
|---|---|---|
| Stale PR Digest | Daily 9:00 AM (weekdays) | Lists PRs open >24h without a bot review, posts to Google Chat |
| Weekly Review Report | Every Monday 8:00 AM | Aggregates 7-day review stats: totals, verdicts, avg review time, per-author breakdown |

---

## Review Output Format

Every review follows this structure:

```markdown
## Summary
[2-3 sentence overview of what the PR does and overall impression]

## Issues Found

### 🔴 CRITICAL
`src/auth.js:14` — JWT secret read from hardcoded string — **Fix:** use `process.env.JWT_SECRET`

### 🟡 WARNING
`src/middleware.js:8` — No error handling on async call — **Fix:** wrap in try/catch

### 🟢 INFO
`src/utils.js:3` — Function name could be more descriptive

## Suggestions
[Broader feedback on architecture, testing, naming]

## Verdict
⚠️ Needs Changes — Two issues must be resolved before merging.
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent framework | Google Antigravity 2.0 |
| AI model | Gemini 2.0 Flash Lite (default) or Groq Llama 3.3 70B |
| AI SDK | google-genai / groq (Python) |
| Webhook server | Flask |
| GitHub integration | GitHub REST API + GitHub MCP |
| Notifications | Google Chat MCP (chatmcp.googleapis.com) |
| Scheduling | Antigravity Scheduled Tasks |
| CLI extension | Antigravity Plugin |
| CI/CD alternative | GitHub Actions |

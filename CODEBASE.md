# Codebase — PR Review Bot

What every file does. One place to look before opening any file.

---

## Entry Points

**`Makefile`**
- Defines `make install`, `make start`, and `make now` — the three commands to run the whole system.
- `start` runs the webhook server + both scheduled jobs. `now` runs both reports immediately then starts the server.

**`src/runner.py`**
- The engine behind `make start` and `make now`.
- `start` mode: launches the Flask server in a background thread and uses the `schedule` library to fire both report scripts at their configured times.
- `now` mode: runs both report scripts immediately, then starts the webhook server.

---

## Core Review Engine

**`src/reviewer.py`**
- Fetches the PR diff from GitHub, builds the Gemini prompt, calls the API, and parses the response.
- Extracts verdict, inline comment targets (`filename:line`), issue counts, and the summary line.
- Posts the review comment, inline comments, and label to GitHub, then sends the Google Chat notification.
- Handles re-review detection — prepends a header if the bot has already reviewed this PR.

**`src/webhook_server.py`**
- Flask server that listens for GitHub PR events on `POST /webhook`.
- Verifies every request with HMAC-SHA256 before touching the payload — rejects anything that doesn't match.
- Dispatches the review in a background thread so GitHub gets an instant `200 OK` response.

---

## Scheduled Reports

**`src/stale_pr_checker.py`**
- Runs weekdays at 9 AM via `make start` or Antigravity scheduler.
- Scans all repos in `WATCHED_REPOS` for PRs open more than 24 hours with no bot review comment.
- Posts a digest list to Google Chat, or an all-clear message if everything is reviewed.

**`src/weekly_reporter.py`**
- Runs every Monday at 8 AM via `make start` or Antigravity scheduler.
- Aggregates the last 7 days: total PRs reviewed, verdict breakdown, avg time to review, per-author counts.
- Posts the full formatted report to Google Chat.

---

## Testing

**`src/test_reviewer.py`**
- Three modes: fake diff (no GitHub calls), dry-run on a real PR (prints review, no writes), live run (full pipeline on a real PR).
- Use this to confirm credentials are working before going live with the webhook or GitHub Actions.

---

## GitHub Actions Alternative

**`.github/workflows/pr-review.yml`**
- Triggers on every PR opened or updated against `main` — no server or ngrok needed.
- Installs dependencies, then calls `handle_pr()` from `reviewer.py` with the PR details from the event context.
- Requires `GEMINI_API_KEY` and `GOOGLE_CHAT_WEBHOOK_URL` added as GitHub repo secrets.

---

## Antigravity Integration

**`agent.md`**
- Defines the Antigravity agent identity, the two-skill orchestration pipeline, and behavioral rules.
- *(AI prompt file — not for editing.)*

**`skills/pr-diff-analyzer/SKILL.md`**
- Skill 1: instructs the agent to fetch the diff and run the Gemini analysis.
- *(AI prompt file — not for editing.)*

**`skills/review-commenter/SKILL.md`**
- Skill 2: instructs the agent to post the review, inline comments, label, and Chat notification.
- *(AI prompt file — not for editing.)*

**`mcp/github-mcp/mcp_config.json`**
- Registers the GitHub MCP with Antigravity and declares all six GitHub API tools the agent can call.

**`mcp/google-chat-mcp/mcp_config.json`**
- Registers the Google Chat MCP and declares the `send_message` tool used for all notifications.

**`scheduled-tasks/stale-pr-digest.json`**
- Antigravity scheduler config: runs `stale_pr_checker.py` weekdays at 9 AM IST.

**`scheduled-tasks/weekly-review-report.json`**
- Antigravity scheduler config: runs `weekly_reporter.py` every Monday at 8 AM IST.

**`plugin/plugin.json`**
- Registers the `antigravity pr-review` CLI command and declares its flags and required env vars.

**`plugin/skills/pr-review-trigger/SKILL.md`**
- Defines how the CLI plugin parses arguments and runs the same review pipeline on demand.
- *(AI prompt file — not for editing.)*

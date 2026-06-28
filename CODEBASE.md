# Codebase Documentation — PR Review Bot

What each file does, logically. No code snippets.

---

## Agent & Skills

**`agent.md`**
- Defines the PR Review Agent's identity, role, and the two-skill orchestration pipeline it runs on every PR event.
- Specifies which MCPs the agent has access to (GitHub and Google Chat) and documents the exact decision flow from trigger to completion.
- Sets the behavioral rules the agent follows: always reference real line numbers, never post duplicate reviews, include a suggested fix for every CRITICAL or WARNING issue.

**`skills/pr-diff-analyzer/SKILL.md`**
- Defines when this skill activates (PR opened, PR updated, or manual CLI trigger) and what inputs it expects from the webhook payload.
- Documents the step-by-step fetch → prompt → call → parse pipeline, including the exact 8000-character diff truncation rule and the Gemini prompt structure.
- Specifies the shape of the structured review object this skill returns, including the `inline_targets` list that drives inline comment placement.

**`skills/review-commenter/SKILL.md`**
- Defines when this skill activates (when a completed review object is ready) and what inputs it expects from the previous skill.
- Documents all five publishing steps in order: re-review detection, main comment post, inline comment placement, label application, and Google Chat notification.
- Specifies which severity levels get inline comments (CRITICAL and WARNING only) and defines the exact label-to-verdict mapping with hex color codes.

---

## MCP Configurations

**`mcp/github-mcp/mcp_config.json`**
- Registers the GitHub MCP with Antigravity and declares all six tools the agent is allowed to call against the GitHub REST API.
- Each tool declaration names the tool, describes its purpose in plain English, and lists its required parameters — this is what the agent reads to know how to call GitHub.
- Uses `stdio` transport and delegates authentication to the `GITHUB_TOKEN` environment variable.

**`mcp/google-chat-mcp/mcp_config.json`**
- Registers the official Google remote MCP server (`chatmcp.googleapis.com`) and declares the `send_message` tool the agent uses for all notifications.
- Configures OAuth 2.0 authentication with the minimum required Chat API scopes (create messages, read spaces).
- Sets the default Chat space via `GOOGLE_CHAT_SPACE_ID` so the agent doesn't need to specify it on every call.

---

## Scheduled Tasks

**`scheduled-tasks/stale-pr-digest.json`**
- Configures the daily weekday 9 AM cron task that checks all watched repos for PRs open longer than 24 hours without a bot review.
- Defines the agent prompt the scheduled task sends, the script it executes, and the fallback "no stale PRs" message sent when everything is on track.
- Sets a 120-second timeout and 2-attempt retry policy for reliability.

**`scheduled-tasks/weekly-review-report.json`**
- Configures the Monday 8 AM cron task that aggregates all PR review activity from the previous 7 days into a team summary.
- Declares the five report sections the agent must produce: summary stats, verdict breakdown, top issue types, average review time, and per-author counts.
- Sets a 180-second timeout to accommodate the larger data aggregation workload.

---

## Plugin

**`plugin/plugin.json`**
- The manifest that registers this directory as an Antigravity CLI plugin and defines the `antigravity pr-review` command.
- Declares the command's usage signature, available flags (`--no-chat`, `--dry-run`), and which environment variables are required vs optional.
- References the plugin's own skill file and the shared MCP configs it reuses from the main project.

**`plugin/skills/pr-review-trigger/SKILL.md`**
- Defines how the plugin skill parses the CLI arguments (`repo`, `pr_number`, and flags) and validates them before running.
- Orchestrates the same pr-diff-analyzer → review-commenter pipeline as the webhook flow, but initiated manually from the terminal.
- Documents the dry-run behavior (print to terminal, no writes) and the success confirmation printed to the terminal on completion.

---

## Source Code

**`src/reviewer.py`**
- The core engine that implements all review logic: fetching diffs, building the AI prompt, calling the configured provider, parsing the response, and publishing results back to GitHub and Google Chat.
- Supports two AI providers: Gemini 2.0 Flash Lite (default) and Groq Llama 3.3 70B — selected at runtime via the `IS_GEMINI` environment variable with no code changes required.
- Contains the severity parser that reads the AI output and extracts inline comment targets (file path + line number + body) for CRITICAL and WARNING issues.
- Handles re-review detection by checking for the `[pr-review-bot]` marker in existing PR comments before posting, and prepends a re-review header when a prior review is found.
- Manages label lifecycle: reads current labels, strips any previous review labels, ensures the new label exists in the repo, then applies it.

**`src/webhook_server.py`**
- A minimal Flask server that exposes a single `POST /webhook` endpoint for receiving GitHub PR events.
- Verifies every incoming request using HMAC-SHA256 signature comparison before any payload processing occurs, rejecting unauthorized requests with a 401.
- Filters events to only process `opened` and `synchronize` actions targeting the `main` branch, then dispatches the review as a background daemon thread so the endpoint responds to GitHub immediately.

**`src/stale_pr_checker.py`**
- Iterates over all repos in `WATCHED_REPOS`, fetches their open PRs, and computes how long each has been open in hours.
- For any PR exceeding the stale threshold, checks whether the bot has already reviewed it by scanning existing comments for the `[pr-review-bot]` marker.
- Formats and sends either a digest of stale PRs or an all-clear message to the Google Chat webhook URL.

**`src/weekly_reporter.py`**
- Fetches both merged and open PRs from the past 7 days across all watched repos and checks each one for a bot review comment.
- Aggregates verdict counts, per-author PR counts, and calculates the average time between PR creation and first bot review.
- Formats a structured weekly summary and sends it to Google Chat, with a short-circuit message when no PRs were reviewed that week.

**`src/test_reviewer.py`**
- Provides three test modes: a fake-diff dry run (calls Gemini only, no GitHub interaction), a dry-run on a real PR (fetches live diff, prints review, no writes), and a full live test (posts real comment and label to an actual PR).
- Useful for verifying that the Gemini API key and GitHub token are valid before going live with the webhook or GitHub Actions setup.

---

## Infrastructure

**`.github/workflows/pr-review.yml`**
- GitHub Actions workflow that runs the full review pipeline in GitHub's cloud on every PR opened or updated against `main`, with no local server or ngrok required.
- Passes all necessary context (PR number, title, author, head SHA, repo name) as environment variables into the Python review script.
- AI provider is controlled by the `IS_GEMINI` repository variable (`true` = Gemini, `false` = Groq) — switchable without touching the workflow file.
- Requests `pull-requests: write`, `issues: write`, and `contents: read` permissions — the minimum needed for the bot to post comments, apply labels, and read the diff.

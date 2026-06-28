Core Review
- Triggers automatically when a PR is opened or updated against main — no manual action needed.
- Sends the diff to the configured AI model (Gemini 2.0 Flash or Groq Llama 3.3) and returns specific, code-aware feedback.
- Every issue is tagged 🔴 CRITICAL, 🟡 WARNING, or 🟢 INFO so engineers know what to fix first.
- Output is always structured: Summary → Issues Found → Suggestions → Verdict.

GitHub Integration
- Posts inline comments directly on the flagged lines of the diff, not just at the bottom of the PR.
- Applies a label automatically — `✅ approved`, `⚠️ needs-changes`, or `🔴 blocked` — after every review.
- Detects when new commits are pushed to an already-reviewed PR and opens with a "Re-review" header.
- Never posts duplicate reviews — checks for existing bot comments before writing.

Notifications
- Sends a formatted review summary to the team Google Chat space after every completed review.

Scheduled Automation
- Every weekday at 9 AM: lists all PRs open more than 24 hours without a review in Google Chat.
- Every Monday at 8 AM: posts a weekly report with total reviews, verdict breakdown, avg turnaround time, and per-author counts.

CLI
- `antigravity pr-review <repo> <pr-number>` triggers a full review from the terminal on any PR.
- `--dry-run` prints the review to the terminal without writing anything to GitHub or Chat.
- `--no-chat` posts the GitHub review and label but suppresses the Google Chat notification.

Infrastructure
- Runs as a GitHub Actions workflow (no server) or a local Flask server with ngrok — team's choice.
- Webhook requests are HMAC-SHA256 verified before any processing begins.
- Reviews run in a background thread so the webhook endpoint responds to GitHub instantly.
- Retries the AI API call once on failure before surfacing an error comment on the PR.
- Switches AI provider at runtime via a single repo variable (`IS_GEMINI=false` activates Groq/Llama, no code change needed).

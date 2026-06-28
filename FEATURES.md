Core Review
- Triggers automatically when a PR is opened or updated against main — no manual action needed.
- Sends the diff to Gemini 2.0 Flash Lite and returns specific, code-aware feedback.
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

Local Runner
- `make start` — starts the webhook server and both scheduled jobs in one command; reports fire at their configured times.
- `make now` — runs both reports immediately without waiting for the schedule, then starts the webhook server.
- `make install` — installs all dependencies.

Testing
- `python src/test_reviewer.py` — calls Gemini with a fake diff, prints the review, no GitHub writes.
- `python src/test_reviewer.py --dry-run <PR#>` — fetches a real diff, prints the review, no writes.
- `python src/test_reviewer.py --live <PR#>` — full live run: posts comment, label, and Chat notification.

Infrastructure
- Runs as a GitHub Actions workflow (no server) or a local Flask server — team's choice.
- Webhook requests are HMAC-SHA256 verified before any processing begins.
- Reviews run in a background thread so the webhook endpoint responds to GitHub instantly.
- Retries the Gemini API call once on failure before surfacing an error.
- All source files are fully commented — every function and every step explained inline.

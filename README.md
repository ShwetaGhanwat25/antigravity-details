# PR Review Bot

An AI-powered code review bot that automatically reviews every GitHub Pull Request using Gemini 2.0. Posts severity-scored inline comments, applies labels, sends Google Chat notifications, and runs scheduled digest reports — all without any manual action.

---

## What It Does

When a PR is opened or updated against `main`:
- Fetches the diff and sends it to Gemini for analysis
- Tags every issue as 🔴 CRITICAL, 🟡 WARNING, or 🟢 INFO
- Posts a structured review comment on the PR
- Adds inline comments directly on the flagged lines
- Applies a label — `✅ approved`, `⚠️ needs-changes`, or `🔴 blocked`
- Notifies the team in Google Chat
- Detects re-reviews and adds a header when new commits are pushed to an already-reviewed PR

On a schedule:
- **Weekdays 9 AM** — digest of all PRs open >24h without a review
- **Mondays 8 AM** — weekly report: total reviews, verdict breakdown, avg turnaround time, per-author counts

---

## Quick Start

```bash
# Install dependencies
make install

# Run everything — webhook server + scheduled reports at their configured times
make start

# Run both reports right now, then start the webhook server
make now
```

For testing without running the full server:
```bash
python src/test_reviewer.py                  # fake diff, no GitHub writes
python src/test_reviewer.py --dry-run <PR#>  # real diff, prints review, no writes
python src/test_reviewer.py --live <PR#>     # full live run on a real PR
```

---

## Project Structure

```
auto-pr-review/
├── Makefile                              # make start / make now / make install
├── src/
│   ├── runner.py                         # entry point for both run modes
│   ├── reviewer.py                       # core AI review engine
│   ├── webhook_server.py                 # Flask server for receiving GitHub events
│   ├── stale_pr_checker.py               # daily stale PR digest
│   ├── weekly_reporter.py                # Monday weekly report
│   ├── test_reviewer.py                  # local testing utility
│   └── requirements.txt
├── .github/workflows/pr-review.yml       # GitHub Actions alternative (no server needed)
├── agent.md                              # Antigravity agent definition
├── skills/
│   ├── pr-diff-analyzer/SKILL.md         # Skill 1: fetch + analyze PR diff
│   └── review-commenter/SKILL.md         # Skill 2: post feedback + notify
├── mcp/
│   ├── github-mcp/mcp_config.json        # GitHub API integration
│   └── google-chat-mcp/mcp_config.json   # Google Chat integration
├── scheduled-tasks/
│   ├── stale-pr-digest.json              # Antigravity schedule config for daily digest
│   └── weekly-review-report.json         # Antigravity schedule config for weekly report
└── plugin/
    ├── plugin.json                        # CLI plugin manifest
    └── skills/pr-review-trigger/SKILL.md  # CLI trigger skill
```

---

## Two Ways to Run

**Option A — GitHub Actions (recommended, no server needed)**
Push `.github/workflows/pr-review.yml` to the target repo and add secrets. The workflow runs automatically on every PR.
→ See `SETUP_GUIDE.md` for the full steps.

**Option B — Local Flask server**
Run `make start` and point a GitHub webhook at the exposed URL via ngrok.
→ See `SETUP_GUIDE.md` for the full steps.

---

## Review Output Format

```
## Summary
[2-3 sentence overview]

## Issues Found

### 🔴 CRITICAL
`src/auth.js:14` — JWT secret hardcoded — **Fix:** use process.env.JWT_SECRET

### 🟡 WARNING
`src/middleware.js:8` — no error handling on async call — **Fix:** wrap in try/catch

### 🟢 INFO
`src/utils.js:3` — function name could be more descriptive

## Suggestions
[Broader feedback]

## Verdict
⚠️ Needs Changes — two issues must be resolved before merging.
```

---

## Docs

| File | What it covers |
|---|---|
| `FEATURES.md` | Full feature list at a glance |
| `SETUP_GUIDE.md` | Step-by-step setup from scratch |
| `CODEBASE.md` | What every file does |

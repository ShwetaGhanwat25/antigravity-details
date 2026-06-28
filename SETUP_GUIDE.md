# Setup Guide — PR Review Bot

Complete this once. After setup, the bot runs automatically on every PR.

---

## Prerequisites

- Python 3.9+
- A GitHub Personal Access Token (PAT)
- A Gemini API key from Google AI Studio
- A Google Chat space for notifications

---

## Step 1 — Get Your Credentials

**Gemini API key**
1. Go to [aistudio.google.com](https://aistudio.google.com) → **Get API Key** → **Create API key**
2. Copy the key (starts with `AIza...`)

**GitHub Personal Access Token**
1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)** → name it `pr-review-bot`
3. Check scopes: `repo`, `pull_requests:write`
4. Generate and copy immediately

**Google Chat Webhook URL**
1. Open your Chat space → click the space name → **Apps & integrations** → **Webhooks**
2. **Add webhook** → name it `PR Review Bot` → **Save** → copy the URL

---

## Step 2 — Create Your .env File

In the `auto-pr-review/` folder, create a `.env` file:

```env
GEMINI_API_KEY=AIza...
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=any-secret-string-you-choose
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...
WATCHED_REPOS=YourOrg/your-repo
```

> `WATCHED_REPOS` is comma-separated for multiple repos: `org/repo-one,org/repo-two`
> `.env` is already in `.gitignore` — never commit it.

---

## Step 3 — Install Dependencies

```bash
make install
```

---

## Step 4 — Verify It Works

```bash
python src/test_reviewer.py
```

You should see a structured markdown review printed to the terminal. If you do, Gemini and the GitHub token are both working.

---

## Step 5 — Wire Up GitHub (Pick One)

### Option A: GitHub Actions (no server needed — recommended)

1. The workflow file is already at `.github/workflows/pr-review.yml` — push it to your target repo.
2. Add secrets: **Settings → Secrets and variables → Actions → New repository secret**

   | Secret | Value |
   |---|---|
   | `GEMINI_API_KEY` | Your Gemini key |
   | `GOOGLE_CHAT_WEBHOOK_URL` | Your Chat webhook URL |

   > `GITHUB_TOKEN` is injected automatically by GitHub — do not add it manually.

3. Open a test PR against `main` — the **PR Review Bot** workflow will trigger automatically.

---

### Option B: Local Flask Server + ngrok

Use this if you want to run the server locally or can't push to the target repo.

```bash
# Terminal 1 — start everything
make start

# Terminal 2 — expose to internet
ngrok http 5000
```

Then add the webhook in GitHub: **Settings → Webhooks → Add webhook**
- Payload URL: `https://your-ngrok-url/webhook`
- Content type: `application/json`
- Secret: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
- Events: **Pull requests** only

---

## Step 6 — Test End to End

1. Push a small change to a new branch and open a PR against `main`
2. Wait 20–30 seconds
3. Check the PR — you should see:
   - A structured review comment with severity-scored issues
   - Inline comments on flagged lines
   - A label (`✅ approved`, `⚠️ needs-changes`, or `🔴 blocked`)
4. Check your Google Chat space — a notification should have appeared

---

## Running the Scheduled Reports

```bash
make start    # reports fire at their configured times (weekdays 9 AM / Mondays 8 AM)
make now      # run both reports immediately right now, then start the server
```

To use Antigravity's scheduler instead of `make start`:
```
/schedule load scheduled-tasks/stale-pr-digest.json
/schedule load scheduled-tasks/weekly-review-report.json
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Gemini 429 error | Link a billing account in Google Cloud Console |
| GitHub 401 | Token expired or missing `repo` scope — regenerate PAT |
| No inline comments | The diff line must be part of the PR diff — check the commit SHA |
| Google Chat not receiving | Verify the webhook URL in `.env` matches the one from Chat settings |
| Webhook 401 | `GITHUB_WEBHOOK_SECRET` in `.env` must exactly match GitHub's webhook secret field |
| Scheduled reports not firing | Confirm the process started with `make start` is still running |

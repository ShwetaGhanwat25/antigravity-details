# Setup Guide — PR Review Bot

Step-by-step manual configuration. Complete these after the code is in place.

---

## Prerequisites

- Python 3.9+
- `pip install -r src/requirements.txt` done
- A GitHub account with a Personal Access Token
- A Google AI Studio account (free) for the Gemini API key
- Antigravity 2.0 installed (CLI or IDE)
- Access to a Google Chat space where you want notifications posted

---

## Step 1 — Collect Your Credentials

You need 4 values before anything else.

### 1a. AI Model API Key (pick one)

**Option A — Gemini (Google AI Studio)**
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API Key** → **Create API key in new project**
3. Copy the key — it starts with `AIza...`
4. In Google Cloud Console, link a billing account to the project (required for quota even on free tier)

**Option B — Groq (free, no credit card)**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in → **API Keys** → **Create API key**
3. Copy the key — it starts with `gsk_...`

### 1b. GitHub Personal Access Token
1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name it: `pr-review-bot`
4. Expiration: 90 days (or No expiration for a demo)
5. Scopes — check these:
   - `repo` (full repo access — needed to post comments and labels)
   - `pull_requests:write` (inline comments)
6. Click **Generate token** — copy it immediately, it won't show again

### 1c. Google Chat Webhook URL
1. Open Google Chat → open the space you want notifications in
2. Click the space name at the top → **Apps & integrations** → **Webhooks**
3. Click **Add webhook**
4. Name: `PR Review Bot`, Avatar URL: (optional)
5. Click **Save** → copy the webhook URL (starts with `https://chat.googleapis.com/v1/spaces/...`)

### 1d. Google Chat Space ID
From the webhook URL, the space ID is the value after `/spaces/` — e.g. if the URL contains `/spaces/AAABC123/`, the space ID is `spaces/AAABC123`.

---

## Step 2 — Create Your .env File

In the `auto-pr-review/` root, create a file named `.env`:

```env
GEMINI_API_KEY=AIza...
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=pr-review-secret-2026
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...
GOOGLE_CHAT_SPACE_ID=spaces/AAABC123
WATCHED_REPOS=YourOrg/your-repo
```

> **GITHUB_WEBHOOK_SECRET** — choose any string. You'll paste this exact same value into GitHub's webhook settings in Step 4. `pr-review-secret-2026` works fine.
>
> **WATCHED_REPOS** — comma-separated list of repos the scheduled tasks will scan, e.g. `org/frontend,org/backend`

⚠️ Never commit `.env` to Git. It's already in `.gitignore`.

---

## Step 3 — Verify Everything Works Locally

```powershell
# Set env vars for this session
$env:GEMINI_API_KEY        = "AIza..."
$env:GITHUB_TOKEN          = "ghp_..."
$env:GITHUB_WEBHOOK_SECRET = "pr-review-secret-2026"
$env:GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/..."

# Run the dry-run test — calls Gemini, prints review, no GitHub writes
python src/test_reviewer.py
```

You should see a structured markdown review printed to the terminal. If you see that, Gemini is working.

---

## Step 4 — Configure MCPs in Antigravity

### GitHub MCP

1. Open Antigravity IDE
2. Open the MCP panel (sidebar icon or `Ctrl+Shift+M`)
3. Click **+ Add MCP** → **From file**
4. Select `mcp/github-mcp/mcp_config.json`
5. Antigravity will register the 6 GitHub tools — no authentication needed (uses your `GITHUB_TOKEN` env var)

### Google Chat MCP

1. In the MCP panel, click **+ Add MCP** → **From file**
2. Select `mcp/google-chat-mcp/mcp_config.json`
3. The panel will show **Google Chat MCP — Authenticate**
4. Click **Authenticate** → a browser tab opens → sign in with your Google Workspace account
5. Approve the permissions (Chat messages: create, Chat spaces: read)
6. Copy the authorization code from the browser → paste it into Antigravity → click **Submit**
7. Status should change to ✅ Connected

---

## Step 5 — Install the CLI Plugin

```powershell
# Windows
Copy-Item -Recurse "plugin" "$env:USERPROFILE\.gemini\antigravity-cli\pr-review"
```

Verify it's registered:
```bash
antigravity --list-plugins
# Should show: pr-review — Manual PR review trigger
```

Test the plugin (dry-run, no writes):
```bash
antigravity pr-review YourOrg/your-repo 1 --dry-run
```

---

## Step 6 — Set Up Scheduled Tasks in Antigravity

Open Antigravity CLI and run:

```
/schedule load scheduled-tasks/stale-pr-digest.json
/schedule load scheduled-tasks/weekly-review-report.json
```

Or via the Antigravity IDE:
1. Open the **Scheduled Tasks** panel
2. Click **+ Import** → select `scheduled-tasks/stale-pr-digest.json`
3. Click **+ Import** → select `scheduled-tasks/weekly-review-report.json`
4. Both tasks should appear as **Active** with their cron schedules shown

To test a scheduled task immediately without waiting for the cron time:
```bash
python src/stale_pr_checker.py
python src/weekly_reporter.py
```

---

## Step 7 — Wire Up GitHub (Choose One Method)

### Option A: GitHub Actions (Recommended — no server needed)

1. Push the workflow file to your target repo's `main` branch:
   ```bash
   git add .github/workflows/pr-review.yml
   git commit -m "feat: add AI PR review bot"
   git push origin main
   ```

2. Add secrets to the repo (**Settings → Secrets and variables → Actions → New repository secret**):

   | Secret name | Value |
   |---|---|
   | `GEMINI_API_KEY` | Your Gemini key (if using Gemini) |
   | `GROQ_API_KEY` | Your Groq key (if using Groq) |
   | `GOOGLE_CHAT_WEBHOOK_URL` | Your Google Chat webhook URL |

   > `GITHUB_TOKEN` is auto-injected by GitHub Actions — do **not** add it manually.

3. Add a repository variable (**same settings page → Variables tab → New repository variable**):

   | Variable name | Value |
   |---|---|
   | `IS_GEMINI` | `true` to use Gemini, `false` to use Groq |

3. Go to the repo → **Actions** tab → confirm **PR Review Bot** workflow appears

4. Open a test PR against `main` — the workflow triggers automatically

---

### Option B: Flask + ngrok (Local server)

Use this if you can't push to the target repo or want to test locally.

**Terminal 1 — Start Flask:**
```powershell
$env:GEMINI_API_KEY        = "AIza..."
$env:GITHUB_TOKEN          = "ghp_..."
$env:GITHUB_WEBHOOK_SECRET = "pr-review-secret-2026"
$env:GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/..."
python src/webhook_server.py
```

**Terminal 2 — Expose to internet:**
```bash
ngrok http 5000
# Copy the https:// URL shown, e.g. https://abc123.ngrok-free.app
```

**GitHub webhook config:**
1. Go to your repo → **Settings → Webhooks → Add webhook**
2. Fill in:
   - **Payload URL**: `https://abc123.ngrok-free.app/webhook`
   - **Content type**: `application/json`
   - **Secret**: `pr-review-secret-2026` (must match `GITHUB_WEBHOOK_SECRET`)
   - **Events**: select **Let me select individual events** → check **Pull requests** only
3. Click **Add webhook**
4. GitHub sends a ping — you should see `POST /webhook 200` in Terminal 1

---

## Step 8 — Test End to End

1. Open a PR against `main` in your target repo (push any small code change to a new branch)
2. Wait 20-30 seconds
3. Refresh the PR page — you should see:
   - A structured review comment with severity-scored issues
   - Inline comments on flagged lines
   - A GitHub label (`✅ approved` or `⚠️ needs-changes`)
4. Open your Google Chat space — a notification should have appeared

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Gemini 429 / limit: 0 | Link a billing account in Google Cloud Console — required even for free tier |
| Groq API error | Check `GROQ_API_KEY` is set; get a free key at console.groq.com |
| GitHub 401 | Token expired or missing `repo` scope — regenerate PAT |
| GitHub 403 on label | Add `issues: write` to GitHub Actions workflow permissions |
| No inline comments | Inline comments require the `commit_id` to match — confirm the PR head SHA is correct |
| Google Chat 401 | Re-authenticate the Google Chat MCP in Antigravity |
| Webhook 401 | `GITHUB_WEBHOOK_SECRET` in `.env` must exactly match what's in GitHub webhook settings |
| Plugin not found | Check the plugin folder is at `~/.gemini/antigravity-cli/pr-review/plugin.json` |
| Scheduled tasks not running | Confirm Antigravity is running (tasks need the agent harness active) |

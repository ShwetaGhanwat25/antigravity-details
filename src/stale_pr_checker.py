# Overview: This is the daily stale PR digest script.
# It runs every weekday at 9 AM IST (via the Antigravity scheduler) and scans all
# watched repositories for open PRs that have been waiting more than 24 hours without
# receiving a bot review comment. It then posts a summary list to Google Chat.

import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load credentials from .env when running locally; in Antigravity they are injected automatically.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Read configuration from environment variables.
# WATCHED_REPOS is a comma-separated list e.g. "org/repo1,org/repo2".
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GOOGLE_CHAT_WEBHOOK_URL = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
WATCHED_REPOS = os.environ.get("WATCHED_REPOS", "").split(",")
STALE_THRESHOLD_HOURS = int(os.environ.get("STALE_THRESHOLD_HOURS", "24"))
BOT_MARKER = "[pr-review-bot]"


def _github_headers():
    # Return the Authorization header needed for every GitHub API request.
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_open_prs(repo):
    # Fetch up to 50 currently open PRs targeting main from the given repository.
    # We limit to 50 because a repo with more than 50 open PRs is already in trouble.
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "open", "base": "main", "per_page": 50}
    resp = requests.get(url, headers=_github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def has_bot_review(repo, pr_number):
    # Fetch all comments on this PR and check if any of them start with our BOT_MARKER.
    # Returns True if the bot has already reviewed this PR, False if it is still unreviewed.
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    return any(c["body"].startswith(BOT_MARKER) for c in resp.json())


def hours_open(pr):
    # Calculate how many hours ago this PR was created compared to now (UTC).
    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).total_seconds() / 3600


def send_to_google_chat(text):
    # POST a plain text message to the Google Chat incoming webhook.
    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": text})
    resp.raise_for_status()


def run():
    print(f"[stale_pr_checker] Checking {len(WATCHED_REPOS)} repos for stale PRs...")
    stale = []

    # Step 1: Loop over every watched repository and collect all open PRs.
    for repo in WATCHED_REPOS:
        repo = repo.strip()
        if not repo:
            continue
        try:
            prs = get_open_prs(repo)
        except Exception as e:
            # Log the error but continue checking the remaining repos.
            print(f"[stale_pr_checker] Warning: could not fetch PRs for {repo}: {e}")
            continue

        # Step 2: For each PR, check if it is old enough and still unreviewed.
        for pr in prs:
            age_hours = hours_open(pr)
            if age_hours >= STALE_THRESHOLD_HOURS:
                reviewed = has_bot_review(repo, pr["number"])
                if not reviewed:
                    # Step 3: Collect the stale PR's details for the digest message.
                    stale.append({
                        "repo": repo,
                        "number": pr["number"],
                        "title": pr["title"],
                        "author": pr["user"]["login"],
                        "url": pr["html_url"],
                        "age_hours": round(age_hours, 1),
                    })

    # Step 4: If nothing is stale, send an all-clear message and exit early.
    if not stale:
        send_to_google_chat(
            "✅ *Daily PR Digest* — No stale PRs today. "
            "All pull requests have been reviewed within 24 hours."
        )
        print("[stale_pr_checker] No stale PRs found.")
        return

    # Step 5: Build one line per stale PR and send the digest to Google Chat.
    lines = [f"⚠️ *Daily PR Digest* — {len(stale)} PR(s) awaiting review:\n"]
    for pr in stale:
        lines.append(
            f"• <{pr['url']}|#{pr['number']} {pr['title']}> "
            f"by *{pr['author']}* in `{pr['repo']}` — open for *{pr['age_hours']}h*"
        )

    send_to_google_chat("\n".join(lines))
    print(f"[stale_pr_checker] Digest sent — {len(stale)} stale PR(s) reported.")


if __name__ == "__main__":
    run()

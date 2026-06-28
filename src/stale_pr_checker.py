"""
Scheduled Task 1 — Stale PR Digest
Runs daily at 9:00 AM IST (weekdays).
Finds open PRs with no bot review after 24 hours and posts a digest to Google Chat.
"""

import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GOOGLE_CHAT_WEBHOOK_URL = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
WATCHED_REPOS = os.environ.get("WATCHED_REPOS", "").split(",")
STALE_THRESHOLD_HOURS = int(os.environ.get("STALE_THRESHOLD_HOURS", "24"))
BOT_MARKER = "[pr-review-bot]"


def _github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_open_prs(repo):
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "open", "base": "main", "per_page": 50}
    resp = requests.get(url, headers=_github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def has_bot_review(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    return any(c["body"].startswith(BOT_MARKER) for c in resp.json())


def hours_open(pr):
    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).total_seconds() / 3600


def send_to_google_chat(text):
    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": text})
    resp.raise_for_status()


def run():
    print(f"[stale_pr_checker] Checking {len(WATCHED_REPOS)} repos for stale PRs...")
    stale = []

    for repo in WATCHED_REPOS:
        repo = repo.strip()
        if not repo:
            continue
        try:
            prs = get_open_prs(repo)
        except Exception as e:
            print(f"[stale_pr_checker] Warning: could not fetch PRs for {repo}: {e}")
            continue

        for pr in prs:
            age_hours = hours_open(pr)
            if age_hours >= STALE_THRESHOLD_HOURS:
                reviewed = has_bot_review(repo, pr["number"])
                if not reviewed:
                    stale.append({
                        "repo": repo,
                        "number": pr["number"],
                        "title": pr["title"],
                        "author": pr["user"]["login"],
                        "url": pr["html_url"],
                        "age_hours": round(age_hours, 1),
                    })

    if not stale:
        send_to_google_chat(
            "✅ *Daily PR Digest* — No stale PRs today. "
            "All pull requests have been reviewed within 24 hours."
        )
        print("[stale_pr_checker] No stale PRs found.")
        return

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

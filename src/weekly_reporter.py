"""
Scheduled Task 2 — Weekly Review Report
Runs every Monday at 8:00 AM IST.
Aggregates PR review activity from the past 7 days and posts a report to Google Chat.
"""

import os
import re
import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GOOGLE_CHAT_WEBHOOK_URL = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
WATCHED_REPOS = os.environ.get("WATCHED_REPOS", "").split(",")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
BOT_MARKER = "[pr-review-bot]"


def _github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_closed_prs(repo, since):
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "closed", "base": "main", "per_page": 100, "sort": "updated", "direction": "desc"}
    resp = requests.get(url, headers=_github_headers(), params=params)
    resp.raise_for_status()
    cutoff = since
    return [
        pr for pr in resp.json()
        if pr.get("merged_at") and
        datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")) >= cutoff
    ]


def get_open_prs(repo):
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "open", "base": "main", "per_page": 100}
    resp = requests.get(url, headers=_github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def get_bot_comment(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    for c in resp.json():
        if c["body"].startswith(BOT_MARKER):
            return c
    return None


def extract_verdict(comment_body):
    if "✅ Approved" in comment_body:
        return "approved"
    if "🔴 Blocked" in comment_body:
        return "blocked"
    if "⚠️ Needs Changes" in comment_body:
        return "needs-changes"
    return "unknown"


def time_to_review_hours(pr, comment):
    opened = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
    reviewed = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
    return round((reviewed - opened).total_seconds() / 3600, 1)


def send_to_google_chat(text):
    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": text})
    resp.raise_for_status()


def run():
    since = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    print(f"[weekly_reporter] Generating report for the past {LOOKBACK_DAYS} days...")

    total_reviewed = 0
    verdict_counts = defaultdict(int)
    author_counts = defaultdict(int)
    review_times = []

    for repo in WATCHED_REPOS:
        repo = repo.strip()
        if not repo:
            continue

        all_prs = []
        try:
            all_prs += get_closed_prs(repo, since)
            all_prs += get_open_prs(repo)
        except Exception as e:
            print(f"[weekly_reporter] Warning: could not fetch PRs for {repo}: {e}")
            continue

        for pr in all_prs:
            comment = get_bot_comment(repo, pr["number"])
            if not comment:
                continue
            reviewed_at = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
            if reviewed_at < since:
                continue

            total_reviewed += 1
            verdict = extract_verdict(comment["body"])
            verdict_counts[verdict] += 1
            author_counts[pr["user"]["login"]] += 1
            review_times.append(time_to_review_hours(pr, comment))

    avg_time = round(sum(review_times) / len(review_times), 1) if review_times else 0

    date_range = f"{since.strftime('%b %d')} – {datetime.now(timezone.utc).strftime('%b %d, %Y')}"

    lines = [
        f"📊 *Weekly PR Review Report* ({date_range})\n",
        f"*Total PRs reviewed:* {total_reviewed}",
        f"*Average time to review:* {avg_time}h\n",
        "*Verdict breakdown:*",
        f"  ✅ Approved: {verdict_counts['approved']}",
        f"  ⚠️ Needs Changes: {verdict_counts['needs-changes']}",
        f"  🔴 Blocked: {verdict_counts['blocked']}",
    ]

    if author_counts:
        lines.append("\n*PRs by author:*")
        for author, count in sorted(author_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {author}: {count} PR(s)")

    if total_reviewed == 0:
        lines = [f"📊 *Weekly PR Review Report* ({date_range})\n",
                 "No PRs were reviewed this week."]

    send_to_google_chat("\n".join(lines))
    print(f"[weekly_reporter] Report sent — {total_reviewed} PRs reviewed this week.")


if __name__ == "__main__":
    run()

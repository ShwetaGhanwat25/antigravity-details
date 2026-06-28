# Overview: This is the weekly PR review report script.
# It runs every Monday at 8 AM IST (via the Antigravity scheduler) and looks back
# 7 days across all watched repositories. It counts how many PRs were reviewed,
# breaks them down by verdict, calculates average review turnaround time, and posts
# the full report to Google Chat.

import os
import re
import requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv

# Load credentials from .env when running locally; in Antigravity they are injected automatically.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Read configuration from environment variables.
# LOOKBACK_DAYS controls how far back the report looks — defaults to 7 days.
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GOOGLE_CHAT_WEBHOOK_URL = os.environ["GOOGLE_CHAT_WEBHOOK_URL"]
WATCHED_REPOS = os.environ.get("WATCHED_REPOS", "").split(",")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "7"))
BOT_MARKER = "[pr-review-bot]"


def _github_headers():
    # Return the Authorization header needed for every GitHub API request.
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_closed_prs(repo, since):
    # Fetch merged PRs from the past LOOKBACK_DAYS days, sorted newest first.
    # We filter to only PRs that have a merged_at timestamp on or after the cutoff.
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
    # Fetch all currently open PRs targeting main — these may also have been reviewed this week.
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "open", "base": "main", "per_page": 100}
    resp = requests.get(url, headers=_github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def get_bot_comment(repo, pr_number):
    # Scan all comments on this PR and return the first one that starts with our BOT_MARKER.
    # Returns None if the bot has not reviewed this PR yet.
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    for c in resp.json():
        if c["body"].startswith(BOT_MARKER):
            return c
    return None


def extract_verdict(comment_body):
    # Read the bot comment body and return the verdict as a simple string key.
    # Defaults to "unknown" if the comment doesn't contain a recognised verdict emoji.
    if "✅ Approved" in comment_body:
        return "approved"
    if "🔴 Blocked" in comment_body:
        return "blocked"
    if "⚠️ Needs Changes" in comment_body:
        return "needs-changes"
    return "unknown"


def time_to_review_hours(pr, comment):
    # Calculate how many hours elapsed between when the PR was opened and when the bot reviewed it.
    # This gives us the average review turnaround time for the weekly report.
    opened = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
    reviewed = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
    return round((reviewed - opened).total_seconds() / 3600, 1)


def send_to_google_chat(text):
    # POST a plain text message to the Google Chat incoming webhook.
    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": text})
    resp.raise_for_status()


def run():
    # Calculate the start of the reporting window (7 days ago from now, UTC).
    since = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    print(f"[weekly_reporter] Generating report for the past {LOOKBACK_DAYS} days...")

    # Initialise counters that will accumulate data across all repos.
    total_reviewed = 0
    verdict_counts = defaultdict(int)
    author_counts = defaultdict(int)
    review_times = []

    # Step 1: Loop over every watched repository and collect both merged and open PRs.
    for repo in WATCHED_REPOS:
        repo = repo.strip()
        if not repo:
            continue

        all_prs = []
        try:
            all_prs += get_closed_prs(repo, since)
            all_prs += get_open_prs(repo)
        except Exception as e:
            # Log the error but continue with the remaining repos.
            print(f"[weekly_reporter] Warning: could not fetch PRs for {repo}: {e}")
            continue

        # Step 2: For each PR, find the bot's review comment and skip PRs with no review.
        for pr in all_prs:
            comment = get_bot_comment(repo, pr["number"])
            if not comment:
                continue

            # Step 3: Skip reviews that were posted before our reporting window.
            reviewed_at = datetime.fromisoformat(comment["created_at"].replace("Z", "+00:00"))
            if reviewed_at < since:
                continue

            # Step 4: Accumulate stats — total count, verdict breakdown, author count, review time.
            total_reviewed += 1
            verdict = extract_verdict(comment["body"])
            verdict_counts[verdict] += 1
            author_counts[pr["user"]["login"]] += 1
            review_times.append(time_to_review_hours(pr, comment))

    # Step 5: Calculate the average review turnaround time across all PRs this week.
    avg_time = round(sum(review_times) / len(review_times), 1) if review_times else 0

    date_range = f"{since.strftime('%b %d')} – {datetime.now(timezone.utc).strftime('%b %d, %Y')}"

    # Step 6: Build the report message lines with all the aggregated statistics.
    lines = [
        f"📊 *Weekly PR Review Report* ({date_range})\n",
        f"*Total PRs reviewed:* {total_reviewed}",
        f"*Average time to review:* {avg_time}h\n",
        "*Verdict breakdown:*",
        f"  ✅ Approved: {verdict_counts['approved']}",
        f"  ⚠️ Needs Changes: {verdict_counts['needs-changes']}",
        f"  🔴 Blocked: {verdict_counts['blocked']}",
    ]

    # Step 7: Add a per-author breakdown sorted by number of PRs submitted (most active first).
    if author_counts:
        lines.append("\n*PRs by author:*")
        for author, count in sorted(author_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {author}: {count} PR(s)")

    # Step 8: Replace the report with a simple "no activity" message if nothing was reviewed.
    if total_reviewed == 0:
        lines = [f"📊 *Weekly PR Review Report* ({date_range})\n",
                 "No PRs were reviewed this week."]

    # Step 9: Send the final report to Google Chat.
    send_to_google_chat("\n".join(lines))
    print(f"[weekly_reporter] Report sent — {total_reviewed} PRs reviewed this week.")


if __name__ == "__main__":
    run()

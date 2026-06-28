import os
import re
import time
import requests
from google import genai
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GOOGLE_CHAT_WEBHOOK_URL = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")
BOT_MARKER = "[pr-review-bot]"

_client = genai.Client(api_key=GEMINI_API_KEY)


# ── GitHub helpers ──────────────────────────────────────────────────────────

def _github_headers(accept="application/vnd.github.v3+json"):
    return {"Authorization": f"token {GITHUB_TOKEN}", "Accept": accept}


def get_pr_diff(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_github_headers("application/vnd.github.v3.diff"))
    resp.raise_for_status()
    diff = resp.text
    if len(diff) > 4000:
        diff = diff[:4000] + f"\n\n[diff truncated — showing first 4000 chars]"
    return diff


def get_pr_metadata(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    data = resp.json()
    return {
        "title": data["title"],
        "author": data["user"]["login"],
        "url": data["html_url"],
        "head_sha": data["head"]["sha"],
        "base_sha": data["base"]["sha"],
    }


def get_existing_bot_comment(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())
    resp.raise_for_status()
    for comment in resp.json():
        if comment["body"].startswith(BOT_MARKER):
            return comment
    return None


def post_pr_comment(repo, pr_number, body):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=_github_headers(), json={"body": body})
    resp.raise_for_status()


def post_inline_comment(repo, pr_number, commit_sha, path, line, body):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
    payload = {
        "body": body,
        "commit_id": commit_sha,
        "path": path,
        "line": line,
        "side": "RIGHT",
    }
    resp = requests.post(url, headers=_github_headers(), json=payload)
    if not resp.ok:
        print(f"[reviewer] Warning: could not post inline comment on {path}:{line} — {resp.status_code}")


def apply_pr_label(repo, pr_number, verdict):
    label_map = {
        "approved": "✅ approved",
        "needs-changes": "⚠️ needs-changes",
        "blocked": "🔴 blocked",
    }
    review_labels = set(label_map.values())
    label = label_map.get(verdict, "⚠️ needs-changes")

    # Remove existing review labels
    current_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels"
    current = requests.get(current_url, headers=_github_headers()).json()
    for lbl in current:
        if lbl["name"] in review_labels:
            requests.delete(f"{current_url}/{lbl['name']}", headers=_github_headers())

    # Ensure label exists in repo
    labels_url = f"https://api.github.com/repos/{repo}/labels"
    color_map = {"✅ approved": "0e8a16", "⚠️ needs-changes": "e4a400", "🔴 blocked": "d93f0b"}
    requests.post(labels_url, headers=_github_headers(),
                  json={"name": label, "color": color_map[label]})

    # Apply label
    resp = requests.post(current_url, headers=_github_headers(), json={"labels": [label]})
    if resp.ok:
        print(f"[reviewer] Applied label '{label}' to PR #{pr_number}")


# ── Google Chat notification ────────────────────────────────────────────────

def notify_google_chat(pr_title, pr_number, pr_url, repo, author, verdict, summary_line,
                       critical_count, warning_count, info_count):
    if not GOOGLE_CHAT_WEBHOOK_URL:
        print("[reviewer] GOOGLE_CHAT_WEBHOOK_URL not set — skipping Chat notification")
        return

    verdict_display = {
        "approved": "✅ Approved",
        "needs-changes": "⚠️ Needs Changes",
        "blocked": "🔴 Blocked",
    }.get(verdict, verdict)

    text = (
        f"🤖 *PR Review Complete*\n\n"
        f"*PR:* <{pr_url}|#{pr_number} — {pr_title}>\n"
        f"*Author:* {author}\n"
        f"*Repository:* {repo}\n"
        f"*Verdict:* {verdict_display}\n\n"
        f"{summary_line}\n\n"
        f"_{critical_count} critical · {warning_count} warnings · {info_count} suggestions_"
    )
    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": text})
    if resp.ok:
        print(f"[reviewer] Google Chat notification sent")
    else:
        print(f"[reviewer] Warning: Google Chat notification failed — {resp.status_code}")


# ── Gemini analysis ─────────────────────────────────────────────────────────

def _call_gemini(prompt, retries=1):
    for attempt in range(retries + 1):
        try:
            result = _client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
            return result.text
        except Exception as e:
            if attempt < retries:
                print(f"[reviewer] Gemini error, retrying in 3s: {e}")
                time.sleep(3)
            else:
                raise


def build_review_prompt(pr_title, author, repo, diff):
    return f"""You are a senior software engineer performing a thorough code review.

PR Title: {pr_title}
Author: {author}
Repository: {repo}

DIFF:
{diff}

Review this pull request and produce structured feedback using the format below.
For every issue you identify, assign a severity level:
  🔴 CRITICAL — bug, security vulnerability, data loss risk, broken logic
  🟡 WARNING  — code smell, performance concern, missing error handling, unclear naming
  🟢 INFO     — style suggestion, minor improvement, optional refactor

Required output format (strict markdown):

## Summary
[2-3 sentences describing what this PR does and your overall impression]

## Issues Found

### 🔴 CRITICAL
[List each critical issue. Format: `filename:line` — description — **Fix:** suggested correction]
[Write "None" if no critical issues]

### 🟡 WARNING
[List each warning. Same format as above]
[Write "None" if no warnings]

### 🟢 INFO
[List each info item. Same format as above]

## Suggestions
[Broader suggestions not tied to a specific line]

## Verdict
[Exactly one of: ✅ Approved | ⚠️ Needs Changes | 🔴 Blocked]
[One sentence justifying the verdict]"""


# ── Result parsing ──────────────────────────────────────────────────────────

def parse_verdict(review_text):
    if "✅ Approved" in review_text:
        return "approved"
    if "🔴 Blocked" in review_text:
        return "blocked"
    return "needs-changes"


def parse_summary_line(review_text):
    match = re.search(r"## Summary\s*\n(.+)", review_text)
    if match:
        return match.group(1).strip()
    return ""


def parse_inline_targets(review_text):
    targets = []
    severity_map = {"CRITICAL": "🔴", "WARNING": "🟡"}
    pattern = re.compile(r"`([^:]+):(\d+)`\s*[—-]\s*(.+?)(?:\s*\*\*Fix:\*\*\s*(.+))?$", re.MULTILINE)

    current_severity = None
    for line in review_text.splitlines():
        if "### 🔴 CRITICAL" in line:
            current_severity = "CRITICAL"
        elif "### 🟡 WARNING" in line:
            current_severity = "WARNING"
        elif "### 🟢 INFO" in line:
            current_severity = "INFO"
        elif current_severity in ("CRITICAL", "WARNING"):
            m = pattern.search(line)
            if m:
                path, lineno, desc, fix = m.group(1), int(m.group(2)), m.group(3).strip(), m.group(4)
                body = f"**{severity_map[current_severity]} {current_severity}**: {desc}"
                if fix:
                    body += f"\n\n**Suggested fix:** {fix.strip()}"
                targets.append({"path": path, "line": lineno, "body": body})
    return targets


def count_issues(review_text):
    critical = len(re.findall(r"🔴 CRITICAL", review_text)) - 1  # subtract section header
    warning = len(re.findall(r"🟡 WARNING", review_text)) - 1
    info = len(re.findall(r"🟢 INFO", review_text)) - 1
    return max(critical, 0), max(warning, 0), max(info, 0)


# ── Main orchestration ──────────────────────────────────────────────────────

def handle_pr(payload, dry_run=False, skip_chat=False):
    repo = payload["repository"]["full_name"]
    pr_number = payload["pull_request"]["number"]
    pr_title = payload["pull_request"]["title"]
    author = payload["pull_request"]["user"]["login"]
    pr_url = payload["pull_request"].get("html_url", f"https://github.com/{repo}/pull/{pr_number}")
    commit_sha = payload["pull_request"]["head"]["sha"]

    print(f"[reviewer] Reviewing PR #{pr_number} '{pr_title}' by {author} in {repo}")

    # ── Skill 1: pr-diff-analyzer ──
    diff = get_pr_diff(repo, pr_number)
    prompt = build_review_prompt(pr_title, author, repo, diff)
    review_text = _call_gemini(prompt)

    verdict = parse_verdict(review_text)
    summary_line = parse_summary_line(review_text)
    inline_targets = parse_inline_targets(review_text)
    critical_count, warning_count, info_count = count_issues(review_text)

    print(f"[reviewer] Analysis complete — verdict: {verdict}, "
          f"{critical_count} critical, {warning_count} warnings, {info_count} info")

    if dry_run:
        print("\n" + "=" * 60)
        print(review_text)
        print("=" * 60)
        print(f"\n[dry-run] Would post {len(inline_targets)} inline comments, label: {verdict}")
        return

    # ── Skill 2: review-commenter ──

    # Re-review detection
    existing = get_existing_bot_comment(repo, pr_number)
    re_review_header = ""
    if existing:
        from datetime import datetime
        prev_date = existing["created_at"][:10]
        re_review_header = (
            f"> **Re-review** — new commits pushed since the last review on {prev_date}.\n"
            f"> Focusing on changes introduced since then.\n\n"
        )

    full_body = f"{BOT_MARKER}\n{re_review_header}{review_text}"
    post_pr_comment(repo, pr_number, full_body)
    print(f"[reviewer] Posted review comment on PR #{pr_number}")

    # Inline comments
    for target in inline_targets:
        post_inline_comment(repo, pr_number, commit_sha, target["path"], target["line"], target["body"])

    # Auto-label
    apply_pr_label(repo, pr_number, verdict)

    # Google Chat notification
    if not skip_chat:
        notify_google_chat(
            pr_title, pr_number, pr_url, repo, author,
            verdict, summary_line, critical_count, warning_count, info_count
        )

    print(f"[reviewer] Done — PR #{pr_number} reviewed and labelled")

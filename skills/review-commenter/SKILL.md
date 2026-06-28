---
name: review-commenter
description: >
  Posts a completed PR diff analysis as structured feedback on GitHub.
  Use this skill when a PR analysis result is ready to be published.
  Posts inline comments on flagged lines, applies a GitHub label based
  on the verdict, and sends a notification to the Google Chat space.
  Detects re-reviews and highlights only what changed since the last review.
---

# Review Commenter

## Purpose

This skill is the publishing engine of the PR Review Agent. It takes the structured review object produced by `pr-diff-analyzer` and delivers it to the right places: GitHub PR comments, GitHub labels, and Google Chat.

## When This Skill Activates

- Immediately after `pr-diff-analyzer` returns a completed review object
- Only if the review object is non-empty and contains a verdict

## Inputs Required

| Input | Source | Description |
|---|---|---|
| `review` | Output of pr-diff-analyzer | Structured review object (raw_text, verdict, inline_targets) |
| `repo` | GitHub webhook payload | Full repo name |
| `pr_number` | GitHub webhook payload | PR number |
| `pr_title` | GitHub webhook payload | PR title (used in Google Chat message) |
| `author` | GitHub webhook payload | PR author (used in Google Chat message) |
| `pr_url` | GitHub webhook payload | Direct link to the PR |

## Step-by-Step Instructions

### Step 1 — Re-review detection

Before posting anything, use the **GitHub MCP** `get_pr_review_comments` tool to check if the bot has already commented on this PR.

- Look for comments where the author is the bot account (identified by `[pr-review-bot]` prefix in the body)
- If a previous review exists:
  - Prepend the new review with a re-review header:
    ```
    > **Re-review** — new commits pushed since the last review on {previous_review_date}.
    > Focusing on changes introduced since then.
    ```
  - Continue with posting the full new review below the header

### Step 2 — Post the main review comment

Use the **GitHub MCP** `post_pr_comment` tool:
- Body: the `raw_text` from the review object, prefixed with `[pr-review-bot]` on the first line (invisible to readers but used for re-review detection)
- This posts as a single comment at the PR conversation level

### Step 3 — Post inline comments

Use the **GitHub MCP** `post_inline_comment` tool for each entry in `inline_targets`:
- Only post inline comments for `CRITICAL` and `WARNING` severity items
- `INFO` items are included only in the main comment, not as inline annotations
- For each inline target:
  - `path`: the file path from the diff
  - `line`: the line number
  - `body`: the issue description + fix suggestion, formatted as:
    ```
    **{severity_emoji} {SEVERITY}**: {description}

    **Suggested fix:** {fix}
    ```
- Skip any inline target where the file path or line number could not be parsed reliably

### Step 4 — Apply GitHub label

Use the **GitHub MCP** `apply_pr_label` tool based on the verdict:

| Verdict | Label applied | Label color |
|---|---|---|
| `approved` | `✅ approved` | `#0e8a16` (green) |
| `needs-changes` | `⚠️ needs-changes` | `#e4a400` (yellow) |
| `blocked` | `🔴 blocked` | `#d93f0b` (red) |

Remove any previously applied review label before adding the new one (prevents stacking labels on re-reviews).

### Step 5 — Send Google Chat notification

Use the **Google Chat MCP** `send_message` tool to post to the configured review notifications space:

Message format:
```
🤖 *PR Review Complete*

*PR:* <{pr_url}|#{pr_number} — {pr_title}>
*Author:* {author}
*Repository:* {repo}
*Verdict:* {verdict_emoji} {verdict_label}

{summary_line}

_{critical_count} critical · {warning_count} warnings · {info_count} suggestions_
```

Where `summary_line` is the first sentence of the Summary section from the review.

## Error Handling

| Error | Action |
|---|---|
| GitHub comment API fails | Retry once; log error but do not block — label and Chat still proceed |
| Inline comment fails on a specific line | Skip that line silently; log which lines were skipped |
| Label API fails | Log warning; do not retry — review comment has already been posted |
| Google Chat send fails | Log warning; the GitHub review is still complete — Chat is best-effort |

## Implementation

Implemented in `src/reviewer.py` — functions `post_pr_comment()`, `post_inline_comment()`, `apply_pr_label()`, and `notify_google_chat()`.

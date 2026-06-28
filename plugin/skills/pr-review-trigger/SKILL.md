---
name: pr-review-trigger
description: >
  Manually triggers an AI code review on a GitHub pull request from the
  Antigravity CLI. Use this skill when the user runs 'antigravity pr-review
  <repo> <pr-number>' or asks to review a specific PR by number. Runs the
  full pr-diff-analyzer and review-commenter pipeline on demand.
---

# PR Review Trigger

## Purpose

This skill exposes the full PR review pipeline as an on-demand CLI command. It is identical in behaviour to the webhook-triggered flow but is initiated manually by a developer rather than automatically by a GitHub event.

## When This Skill Activates

- User runs: `antigravity pr-review <repo> <pr-number>`
- User says: "review PR 42 in org/my-repo"
- User says: "re-run the review on this PR"

## Inputs

Parsed from the CLI command arguments:

| Argument | Required | Description |
|---|---|---|
| `repo` | Yes | Full repository name e.g. `org/my-repo` |
| `pr_number` | Yes | Pull request number |
| `--no-chat` | No | Suppress Google Chat notification |
| `--dry-run` | No | Print review to terminal only, skip all GitHub and Chat writes |

## Execution Steps

1. Validate that `repo` and `pr_number` are provided — exit with usage hint if not
2. Fetch PR metadata (title, author, URL) via GitHub MCP `get_pr_diff`
3. Run the **pr-diff-analyzer** skill with the fetched data
4. Run the **review-commenter** skill with the analysis result
   - If `--no-chat` flag is set, skip Step 5 of review-commenter
   - If `--dry-run` flag is set, print the review markdown to stdout and exit without any writes
5. Print confirmation to terminal:
   ```
   ✅ Review posted on PR #42 in org/my-repo
      Verdict: ⚠️ Needs Changes
      GitHub: https://github.com/org/my-repo/pull/42
   ```

## Dry Run Mode

When `--dry-run` is passed, no writes are made to GitHub or Google Chat. The full review is printed to the terminal. This is useful for testing the bot output before publishing.

## Implementation

Calls `src/reviewer.py` directly via subprocess or imports `handle_pr()` when invoked from the plugin runtime.

---
name: pr-diff-analyzer
description: >
  Fetches a GitHub Pull Request diff and analyzes it using the configured AI model
  (Gemini 2.0 Flash Lite or Groq Llama 3.3 70B). Use this skill when a pull request
  is opened or updated and needs code review analysis. Returns a structured review
  with severity-scored issues (CRITICAL / WARNING / INFO), a summary, suggestions, and a verdict.
---

# PR Diff Analyzer

## Purpose

This skill is the analysis engine of the PR Review Agent. It retrieves the raw code diff from GitHub and sends it to Gemini with a structured prompt that produces consistent, severity-scored review output every time.

## When This Skill Activates

- A pull request is opened against the `main` branch
- New commits are pushed to an existing open PR (`synchronize` event)
- A manual review is triggered via the `antigravity pr-review` CLI command

## Inputs Required

| Input | Source | Description |
|---|---|---|
| `repo` | GitHub webhook payload | Full repo name e.g. `org/repo-name` |
| `pr_number` | GitHub webhook payload | PR number e.g. `42` |
| `pr_title` | GitHub webhook payload | Title of the pull request |
| `author` | GitHub webhook payload | GitHub username of the PR author |

## Step-by-Step Instructions

### Step 1 — Fetch the PR diff

Use the **GitHub MCP** `get_pr_diff` tool:
- Endpoint: `GET /repos/{repo}/pulls/{pr_number}`
- Accept header: `application/vnd.github.v3.diff`
- Trim diff to **4000 characters** maximum to stay within model token limits
- If diff exceeds 4000 chars, trim from the bottom and append: `[diff truncated — showing first 4000 chars]`

### Step 2 — Build the AI prompt

Construct the prompt using this exact structure:

```
You are a senior software engineer performing a thorough code review.

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

### 🟡 WARNING
[List each warning. Same format as above]

### 🟢 INFO
[List each info item. Same format as above]

## Suggestions
[Broader suggestions not tied to a specific line — architecture, test coverage, naming conventions]

## Verdict
[One of: ✅ Approved | ⚠️ Needs Changes | 🔴 Blocked]
[One sentence justifying the verdict]
```

### Step 3 — Call the AI model

Provider is selected via the `IS_GEMINI` environment variable:

- **Gemini** (default, `IS_GEMINI=true`): model `gemini-2.0-flash-lite`, SDK `google-genai`, key `GEMINI_API_KEY`
- **Groq** (`IS_GEMINI=false`): model `llama-3.3-70b-versatile`, SDK `groq`, key `GROQ_API_KEY`

### Step 4 — Parse and return the result

Return a structured review object with:
```json
{
  "raw_text": "<full Gemini markdown output>",
  "verdict": "approved | needs-changes | blocked",
  "has_critical": true | false,
  "inline_targets": [
    { "path": "src/auth.js", "line": 12, "severity": "CRITICAL", "body": "..." }
  ]
}
```

To extract `inline_targets`: parse the Issues Found section for lines matching the pattern `filename:line — description`.

## Error Handling

| Error | Action |
|---|---|
| GitHub API 401 | Fail with: "GitHub authentication failed — check GITHUB_TOKEN" |
| GitHub API 404 | Fail with: "PR not found — verify repo name and PR number" |
| Diff is empty | Skip review, post comment: "No changes detected in this PR" |
| AI API error | Retry once after 3 seconds; if still failing, post: "AI review temporarily unavailable" |

## Implementation

Implemented in `src/reviewer.py` — functions `get_pr_diff()` and `handle_pr()`.

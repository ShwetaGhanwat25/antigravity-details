# Overview: This is the local development and testing utility for the reviewer.
# It lets you test the full review pipeline from your terminal without needing a
# real webhook or a GitHub Actions run. It has three modes:
#   - Default (no flags): fake diff, no GitHub writes — just tests the Gemini call.
#   - --dry-run <PR#>:    real PR diff from GitHub, prints review to terminal only.
#   - --live <PR#>:       real PR, full run — posts comment, label, and Chat notification.

import os
import sys
from reviewer import handle_pr, get_pr_diff, build_review_prompt, _call_gemini

# The repository to use for live and dry-run tests — change this to the repo you want to test against.
REPO = "ShwetaGhanwat25/antigravity-demo"

# A fake webhook payload used in default dry-run mode so no real GitHub API calls are needed.
FAKE_PAYLOAD = {
    "repository": {"full_name": REPO},
    "pull_request": {
        "number": 1,
        "title": "feat: add user authentication middleware",
        "user": {"login": "test-dev"},
        "base": {"ref": "main"},
        "head": {"sha": "abc1234"},
        "html_url": f"https://github.com/{REPO}/pull/1",
    },
    "action": "opened",
}

# A small hardcoded diff used in default mode so we can test Gemini's output without hitting GitHub.
FAKE_DIFF = """\
diff --git a/src/middleware/auth.js b/src/middleware/auth.js
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/src/middleware/auth.js
@@ -0,0 +1,20 @@
+const jwt = require('jsonwebtoken');
+
+function authMiddleware(req, res, next) {
+  const token = req.headers['authorization'];
+  if (!token) {
+    return res.status(401).json({ error: 'No token provided' });
+  }
+  try {
+    const decoded = jwt.verify(token, process.env.JWT_SECRET);
+    req.user = decoded;
+    next();
+  } catch (err) {
+    return res.status(401).json({ error: 'Invalid token' });
+  }
+}
+
+module.exports = authMiddleware;
"""


def test_dry_run():
    # Step 1: Build the review prompt using the fake diff and fake PR metadata.
    # Step 2: Call Gemini directly and print the raw review text — no GitHub writes at all.
    print("=== DRY RUN TEST (Gemini only — no GitHub writes) ===\n")
    prompt = build_review_prompt(
        FAKE_PAYLOAD["pull_request"]["title"],
        FAKE_PAYLOAD["pull_request"]["user"]["login"],
        REPO,
        FAKE_DIFF,
    )
    result = _call_gemini(prompt)
    print(result)
    print("\n=== DRY RUN COMPLETE ===")


def test_live(pr_number: int):
    # Step 1: Build a real payload for the given PR number using REPO above.
    # Step 2: Call handle_pr() which runs the full pipeline — posts to GitHub and Chat.
    print(f"=== LIVE TEST — PR #{pr_number} in {REPO} ===\n")
    payload = {
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": pr_number,
            "title": f"Live test PR #{pr_number}",
            "user": {"login": "test-dev"},
            "base": {"ref": "main"},
            "head": {"sha": "live"},
            "html_url": f"https://github.com/{REPO}/pull/{pr_number}",
        },
        "action": "opened",
    }
    handle_pr(payload)
    print("=== LIVE TEST COMPLETE — check the PR for comments and label ===")


def test_dry_run_live(pr_number: int):
    # Step 1: Build a real payload for the given PR number so the diff is fetched from GitHub.
    # Step 2: Call handle_pr() with dry_run=True — prints the review but writes nothing to GitHub.
    print(f"=== DRY RUN on real PR #{pr_number} — no GitHub writes ===\n")
    payload = {
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": pr_number,
            "title": f"PR #{pr_number}",
            "user": {"login": "test-dev"},
            "base": {"ref": "main"},
            "head": {"sha": "live"},
            "html_url": f"https://github.com/{REPO}/pull/{pr_number}",
        },
        "action": "opened",
    }
    handle_pr(payload, dry_run=True)
    print("=== DRY RUN COMPLETE ===")


if __name__ == "__main__":
    # Route to the correct test function based on the command-line flags provided.
    if "--live" in sys.argv:
        idx = sys.argv.index("--live")
        test_live(int(sys.argv[idx + 1]))
    elif "--dry-run" in sys.argv:
        idx = sys.argv.index("--dry-run")
        test_dry_run_live(int(sys.argv[idx + 1]))
    else:
        test_dry_run()

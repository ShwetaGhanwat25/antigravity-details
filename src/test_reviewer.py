"""
Standalone test for reviewer.py — no webhook or ngrok needed.

Usage:
  python test_reviewer.py                    # dry-run with fake diff, no GitHub writes
  python test_reviewer.py --live <PR#>       # real PR diff, posts real comment + label
  python test_reviewer.py --dry-run <PR#>    # real PR diff, prints to terminal only
"""

import os
import sys
from reviewer import handle_pr, get_pr_diff, build_review_prompt, _call_gemini

REPO = "ShwetaGhanwat25/antigravity-demo"

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
    if "--live" in sys.argv:
        idx = sys.argv.index("--live")
        test_live(int(sys.argv[idx + 1]))
    elif "--dry-run" in sys.argv:
        idx = sys.argv.index("--dry-run")
        test_dry_run_live(int(sys.argv[idx + 1]))
    else:
        test_dry_run()

# Overview: This is the alternative trigger mode for the PR review bot.
# Instead of relying on GitHub Actions, you run this Flask server locally (or on a VM)
# and point GitHub's webhook settings at it. GitHub sends a POST request here whenever
# a PR is opened or updated, and this server verifies the request then hands it off
# to reviewer.py in a background thread so GitHub gets an instant response.

import hmac
import hashlib
import os
import threading

from dotenv import load_dotenv
from flask import Flask, request
from reviewer import handle_pr

# Load credentials from .env — GITHUB_WEBHOOK_SECRET must match the secret set in GitHub's webhook settings.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]


def verify_signature(body: bytes, sig_header: str) -> bool:
    # Recompute the HMAC-SHA256 signature of the raw request body using our shared secret.
    # Comparing with hmac.compare_digest prevents timing attacks.
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig_header, expected)


@app.route("/webhook", methods=["POST"])
def webhook():
    # Step 1: Read the signature header GitHub sends with every webhook request.
    sig = request.headers.get("X-Hub-Signature-256", "")
    body = request.data

    # Step 2: Reject the request immediately if the signature is missing or invalid.
    # This prevents anyone without the secret from triggering a review.
    if not sig or not verify_signature(body, sig):
        return "Unauthorized", 401

    # Step 3: Read the event type and payload from the verified request.
    event = request.headers.get("X-GitHub-Event")
    payload = request.json

    # Step 4: Only process pull_request events for PRs opened or updated against main.
    # All other events (push, issue comments, etc.) are silently ignored.
    if (
        event == "pull_request"
        and payload["action"] in ("opened", "synchronize")
        and payload["pull_request"]["base"]["ref"] == "main"
    ):
        # Step 5: Run the review in a background thread so this endpoint returns instantly.
        # GitHub expects a response within 10 seconds — the review itself takes longer.
        threading.Thread(target=handle_pr, args=(payload,), daemon=True).start()

    # Step 6: Return 200 OK immediately to acknowledge receipt of the webhook.
    return "OK", 200


if __name__ == "__main__":
    # Start the Flask dev server on the configured port (default 5000).
    # Use ngrok or a reverse proxy to expose this to the public internet for GitHub.
    port = int(os.environ.get("PORT", 5000))
    print(f"[webhook_server] Listening on port {port}")
    app.run(port=port)

import hmac
import hashlib
import os
import threading

from dotenv import load_dotenv
from flask import Flask, request
from reviewer import handle_pr

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]


def verify_signature(body: bytes, sig_header: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig_header, expected)


@app.route("/webhook", methods=["POST"])
def webhook():
    sig = request.headers.get("X-Hub-Signature-256", "")
    body = request.data

    if not sig or not verify_signature(body, sig):
        return "Unauthorized", 401

    event = request.headers.get("X-GitHub-Event")
    payload = request.json

    if (
        event == "pull_request"
        and payload["action"] in ("opened", "synchronize")
        and payload["pull_request"]["base"]["ref"] == "main"
    ):
        threading.Thread(target=handle_pr, args=(payload,), daemon=True).start()

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[webhook_server] Listening on port {port}")
    app.run(port=port)

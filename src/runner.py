# Overview: This is the single entry point for running the entire PR review system locally.
# It has two modes controlled by a command-line argument:
#   start → Runs the webhook server continuously and fires the two reports on their
#            real schedules (stale digest weekdays 9 AM, weekly report Mondays 8 AM).
#   now   → Runs both reports immediately right now, then starts the webhook server.
#            Use this to test or to catch up without waiting for the scheduled time.

import sys
import threading
import time
import schedule

# Import the three runnable components of the system.
import stale_pr_checker
import weekly_reporter
import webhook_server


def run_webhook_server_in_background():
    # Start the Flask webhook server in a daemon thread so it does not block the scheduler.
    # Daemon threads are killed automatically when the main process exits.
    t = threading.Thread(target=lambda: webhook_server.app.run(
        port=int(__import__('os').environ.get("PORT", 5000))
    ), daemon=True)
    t.start()
    print("[runner] Webhook server started in background on port 5000")


def start_mode():
    # Step 1: Start the webhook server in the background so PR review works immediately.
    run_webhook_server_in_background()

    # Step 2: Schedule the stale PR digest to run on every weekday at 09:00 AM.
    # The schedule library checks these in the loop below — no cron daemon needed.
    schedule.every().monday.at("09:00").do(stale_pr_checker.run)
    schedule.every().tuesday.at("09:00").do(stale_pr_checker.run)
    schedule.every().wednesday.at("09:00").do(stale_pr_checker.run)
    schedule.every().thursday.at("09:00").do(stale_pr_checker.run)
    schedule.every().friday.at("09:00").do(stale_pr_checker.run)

    # Step 3: Schedule the weekly report to run every Monday at 08:00 AM.
    schedule.every().monday.at("08:00").do(weekly_reporter.run)

    print("[runner] Schedules registered:")
    print("         - Stale PR digest  → weekdays at 09:00 AM")
    print("         - Weekly report    → every Monday at 08:00 AM")
    print("[runner] System is live. Press Ctrl+C to stop.\n")

    # Step 4: Run the schedule loop forever, checking every 60 seconds for pending jobs.
    while True:
        schedule.run_pending()
        time.sleep(60)


def now_mode():
    # Step 1: Run the stale PR digest immediately without waiting for 9 AM.
    print("[runner] Running stale PR digest now...\n")
    stale_pr_checker.run()

    # Step 2: Run the weekly report immediately without waiting for Monday.
    print("\n[runner] Running weekly report now...\n")
    weekly_reporter.run()

    # Step 3: Start the webhook server so PR reviews keep working after the reports finish.
    print("\n[runner] Both reports done. Starting webhook server...\n")
    run_webhook_server_in_background()

    print("[runner] Webhook server is live. Press Ctrl+C to stop.\n")

    # Step 4: Keep the main thread alive so the background webhook server keeps running.
    while True:
        time.sleep(60)


if __name__ == "__main__":
    # Read the mode from the first command-line argument — default to "start" if not provided.
    mode = sys.argv[1] if len(sys.argv) > 1 else "start"

    if mode == "start":
        print("[runner] Mode: SCHEDULED — reports will fire at their configured times.\n")
        start_mode()
    elif mode == "now":
        print("[runner] Mode: NOW — running both reports immediately.\n")
        now_mode()
    else:
        print(f"[runner] Unknown mode '{mode}'. Use: python runner.py start   or   python runner.py now")
        sys.exit(1)

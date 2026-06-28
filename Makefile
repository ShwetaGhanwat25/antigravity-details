# Overview: These are the project's runnable commands — the Python equivalent of npm scripts.
# Run them from the auto-pr-review/ directory with: make <command>
#
#   make install   → install all dependencies
#   make start     → run everything with scheduled triggers (for daily use / production)
#   make now       → run both reports immediately, then start the webhook server (for testing)

.PHONY: install start now

install:
	pip install -r src/requirements.txt

# Starts the full system: webhook server for PR reviews + scheduled stale digest + scheduled weekly report.
# Reports fire at their real configured times (stale digest weekdays 9 AM, weekly report Mondays 8 AM).
start:
	cd src && python runner.py start

# Runs both reports right now without waiting for the schedule, then starts the webhook server.
# Use this to test the reports or to manually trigger them outside their normal schedule.
now:
	cd src && python runner.py now

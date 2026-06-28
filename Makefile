# Overview: These are the project's runnable commands — the Python equivalent of npm scripts.
# Run them from the auto-pr-review/ directory with: make <command>
#
#   make install             → install all dependencies
#
#   PR Reports only (no AI PR review):
#   make reports             → run both reports immediately and exit
#   make reports-scheduled   → run both reports on their real schedules (9 AM / Monday 8 AM)
#
#   Full system (AI PR review + reports):
#   make start               → webhook server + reports on their real schedules
#   make now                 → both reports immediately, then starts the webhook server

.PHONY: install reports reports-scheduled start now

install:
	pip install -r src/requirements.txt

# Runs stale PR digest + weekly report immediately, then exits. No webhook server.
reports:
	cd src && python runner.py reports

# Runs stale PR digest + weekly report on their real schedules. No webhook server.
# Stale digest fires weekdays at 9 AM, weekly report fires every Monday at 8 AM.
reports-scheduled:
	cd src && python runner.py reports-scheduled

# Starts the full system: webhook server for AI PR reviews + both reports on schedule.
start:
	cd src && python runner.py start

# Runs both reports immediately, then starts the webhook server for AI PR reviews.
now:
	cd src && python runner.py now

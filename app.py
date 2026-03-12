import atexit
import os

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, redirect, render_template_string, url_for

from db import get_logs, init_db
from scheduler import process_inbox


load_dotenv()


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

scheduler = BackgroundScheduler()


def _scheduler_enabled() -> bool:
    """
    Read the scheduler flag from the environment.
    """
    return os.getenv("SCHEDULER_ENABLED", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _start_scheduler() -> None:
    """
    Start the background scheduler once and register the inbox job.

    Flask debug mode can import the app more than once, so this function
    checks whether the scheduler is already running before starting it.
    """
    if not _scheduler_enabled() or scheduler.running:
        return

    interval_minutes = max(1, int(os.getenv("CHECK_INTERVAL_MINUTES", "5")))

    scheduler.add_job(
        func=process_inbox,
        trigger="interval",
        minutes=interval_minutes,
        id="process_inbox_job",
        replace_existing=True,
    )
    scheduler.start()


def _initialize_app() -> None:
    """
    Create the database table and start background jobs.
    """
    init_db()
    _start_scheduler()


@app.route("/")
def dashboard():
    """
    Show recent email processing logs in a simple HTML table.
    """
    logs = get_logs(limit=100)

    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>AI Email Agent</title>
            <style>
                body {
                    font-family: "Segoe UI", Arial, sans-serif;
                    background: #f4f7fb;
                    color: #1f2937;
                    margin: 0;
                    padding: 32px;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 24px;
                    gap: 16px;
                    flex-wrap: wrap;
                }
                h1 {
                    margin: 0;
                    font-size: 28px;
                }
                p {
                    margin: 6px 0 0;
                    color: #4b5563;
                }
                .button {
                    display: inline-block;
                    padding: 10px 16px;
                    background: #2563eb;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                }
                .button:hover {
                    background: #1d4ed8;
                }
                .card {
                    background: white;
                    border-radius: 14px;
                    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
                    overflow: hidden;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 12px 14px;
                    text-align: left;
                    border-bottom: 1px solid #e5e7eb;
                    vertical-align: top;
                    font-size: 14px;
                }
                th {
                    background: #eff6ff;
                    font-size: 13px;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                    color: #1e3a8a;
                }
                tr:hover td {
                    background: #f9fafb;
                }
                .empty {
                    padding: 24px;
                    color: #6b7280;
                }
                .body-cell {
                    max-width: 280px;
                    white-space: pre-wrap;
                    word-break: break-word;
                }
                .status {
                    font-weight: 600;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>AI Email Agent Dashboard</h1>
                        <p>Recent processed emails and draft creation logs.</p>
                    </div>
                    <a class="button" href="{{ url_for('run_now') }}">Run Inbox Check Now</a>
                </div>

                <div class="card">
                    {% if logs %}
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Sender</th>
                                <th>Subject</th>
                                <th>Status</th>
                                <th>Draft ID</th>
                                <th>Created At</th>
                                <th>Original Body</th>
                                <th>AI Reply</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td>{{ log.id }}</td>
                                <td>{{ log.sender }}</td>
                                <td>{{ log.subject }}</td>
                                <td class="status">{{ log.status }}</td>
                                <td>{{ log.draft_id }}</td>
                                <td>{{ log.created_at }}</td>
                                <td class="body-cell">{{ log.original_body }}</td>
                                <td class="body-cell">{{ log.ai_reply }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="empty">No logs yet. Run the inbox check to start processing emails.</div>
                    {% endif %}
                </div>
            </div>
        </body>
        </html>
        """,
        logs=logs,
    )


@app.route("/run-now")
def run_now():
    """
    Trigger inbox processing immediately, then return to the dashboard.
    """
    process_inbox()
    return redirect(url_for("dashboard"))


# Initialize once when the Flask app is imported.
_initialize_app()


@atexit.register
def shutdown_scheduler() -> None:
    """
    Stop the background scheduler cleanly when the app exits.
    """
    if scheduler.running:
        scheduler.shutdown()


if __name__ == "__main__":
    app.run(debug=True)

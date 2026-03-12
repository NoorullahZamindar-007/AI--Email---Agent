import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


load_dotenv()

# Store the database in the project root by default.
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DATABASE_FILE", str(BASE_DIR / "email_agent.db"))


def get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite connection.

    sqlite3.Row lets us access columns by name, which is easier to read.
    """
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """
    Create the processed_email_logs table if it does not already exist.
    """
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id TEXT NOT NULL UNIQUE,
                thread_id TEXT,
                sender TEXT,
                subject TEXT,
                original_body TEXT,
                ai_reply TEXT,
                draft_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_log(
    gmail_message_id: str,
    thread_id: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    original_body: Optional[str] = None,
    ai_reply: Optional[str] = None,
    draft_id: Optional[str] = None,
    status: str = "processed",
) -> int:
    """
    Save one processed email log row and return the inserted row id.

    The timestamp is stored in UTC as an ISO string so it is easy to sort
    and display later in the dashboard.
    """
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO processed_email_logs (
                    gmail_message_id,
                    thread_id,
                    sender,
                    subject,
                    original_body,
                    ai_reply,
                    draft_id,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gmail_message_id,
                    thread_id,
                    sender,
                    subject,
                    original_body,
                    ai_reply,
                    draft_id,
                    status,
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            f"Message already logged with gmail_message_id={gmail_message_id}"
        ) from exc


def already_processed(gmail_message_id: str) -> bool:
    """
    Return True if this Gmail message ID already exists in the log table.

    This helps prevent the app from creating duplicate drafts for the same
    email when the scheduler runs multiple times.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT 1
            FROM processed_email_logs
            WHERE gmail_message_id = ?
            LIMIT 1
            """,
            (gmail_message_id,),
        ).fetchone()
        return row is not None


def get_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Return recent email logs ordered from newest to oldest.

    The result is converted to plain dictionaries so it is easy to use in
    Flask templates or API responses later.
    """
    safe_limit = max(1, int(limit))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                gmail_message_id,
                thread_id,
                sender,
                subject,
                original_body,
                ai_reply,
                draft_id,
                status,
                created_at
            FROM processed_email_logs
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at: {DB_PATH}")

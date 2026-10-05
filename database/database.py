import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime


if getattr(sys, "frozen", False):
    # The PyInstaller extraction directory is temporary. Keep meeting history
    # in the user's profile so it survives application updates and restarts.
    _data_directory = Path(os.getenv("LOCALAPPDATA", Path.home())) / "AI Meeting Companion"
    _data_directory.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH = _data_directory / "meeting_assistant.db"
else:
    DATABASE_PATH = Path(__file__).parent / "meeting_assistant.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(meeting_id, username),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcript_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


def create_meeting(title="AI Meeting"):
    connection = get_connection()
    cursor = connection.cursor()

    # India local time
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO meetings (title, created_at)
        VALUES (?, ?)
        """,
        (title, created_at)
    )

    meeting_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return meeting_id


def add_user(meeting_id, username):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (meeting_id, username)
        VALUES (?, ?)
    """, (meeting_id, username))

    cursor.execute("""
        SELECT id
        FROM users
        WHERE meeting_id = ? AND username = ?
    """, (meeting_id, username))

    user_id = cursor.fetchone()["id"]

    connection.commit()
    connection.close()

    return user_id


def save_message(meeting_id, user_id, message):
    connection = get_connection()
    cursor = connection.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO transcript_messages
        (meeting_id, user_id, message, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (meeting_id, user_id, message, created_at)
    )

    connection.commit()
    connection.close()


def get_transcript(meeting_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            users.username,
            transcript_messages.message,
            transcript_messages.created_at
        FROM transcript_messages
        JOIN users
            ON transcript_messages.user_id = users.id
        WHERE transcript_messages.meeting_id = ?
        ORDER BY transcript_messages.id
    """, (meeting_id,))

    messages = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return messages


def save_summary(meeting_id, summary):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE meetings
        SET summary = ?
        WHERE id = ?
    """, (summary, meeting_id))

    connection.commit()
    connection.close()

"""SQLite storage for registry entries and mood entries (swap for Supabase/Postgres later)."""
import os, sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "herevidence.db"))

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS registry_entries(
            id INTEGER PRIMARY KEY, user_hash TEXT, drug TEXT, trimester INTEGER,
            outcome TEXT, entry_date TEXT, is_simulated INTEGER NOT NULL DEFAULT 1, consent INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS mood_entries(
            id INTEGER PRIMARY KEY, user_hash TEXT, entry_date TEXT, phq9 INTEGER, gad7 INTEGER,
            pill_event TEXT, is_simulated INTEGER NOT NULL DEFAULT 0);
        """)

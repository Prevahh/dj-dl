"""Tests for lyrics_path column in Database."""
import tempfile
from pathlib import Path
from dj_dl.db import Database


def test_insert_track_with_lyrics_path():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        tid = db.insert_track(
            artist="Test", title="Song", file_path="/tmp/test.m4a",
            source="yt-dlp", quality="256k", lyrics_path="/tmp/test.lrc"
        )
        track = db.get_track(tid)
        assert track["lyrics_path"] == "/tmp/test.lrc"
        db.close()


def test_update_track_lyrics_path():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        tid = db.insert_track(
            artist="Test", title="Song", file_path="/tmp/test.m4a",
            source="yt-dlp", quality="256k"
        )
        db.update_track(tid, lyrics_path="/tmp/test.lrc")
        track = db.get_track(tid)
        assert track["lyrics_path"] == "/tmp/test.lrc"
        db.close()


def test_migrate_existing_db_adds_lyrics_path():
    """Existing DBs without lyrics_path should be migrated transparently."""
    import sqlite3
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "old.db"
        # Create old-style DB without lyrics_path
        conn = sqlite3.connect(str(db_path))
        conn.execute("""CREATE TABLE tracks (
            id INTEGER PRIMARY KEY, isrc TEXT, artist TEXT NOT NULL,
            title TEXT NOT NULL, album TEXT, file_path TEXT NOT NULL,
            source TEXT NOT NULL, quality TEXT, downloaded_at TEXT NOT NULL
        )""")
        conn.execute("INSERT INTO tracks VALUES (1,'','A','T','','f.m4a','yt-dlp','256k','2026-01-01')")
        conn.commit()
        conn.close()

        # Opening via Database should add the column without error
        db = Database(db_path)
        cols = [r[1] for r in db.conn.execute("PRAGMA table_info(tracks)").fetchall()]
        assert "lyrics_path" in cols
        db.close()

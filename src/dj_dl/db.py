"""SQLite database for tracking downloaded tracks."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class Database:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, isrc TEXT, artist TEXT NOT NULL,
                title TEXT NOT NULL, album TEXT, file_path TEXT NOT NULL, flac_path TEXT,
                stems_path TEXT, source TEXT NOT NULL, quality TEXT, bpm REAL, key TEXT,
                lyrics_path TEXT, spotify_uri TEXT, downloaded_at TEXT NOT NULL
            )
        """)
        # Migrate existing databases that may be missing newer columns
        existing_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(tracks)").fetchall()}
        migrations = [
            ("lyrics_path", "ALTER TABLE tracks ADD COLUMN lyrics_path TEXT"),
            ("spotify_uri", "ALTER TABLE tracks ADD COLUMN spotify_uri TEXT"),
            ("flac_path", "ALTER TABLE tracks ADD COLUMN flac_path TEXT"),
            ("stems_path", "ALTER TABLE tracks ADD COLUMN stems_path TEXT"),
            ("bpm", "ALTER TABLE tracks ADD COLUMN bpm REAL"),
            ("key", "ALTER TABLE tracks ADD COLUMN key TEXT"),
        ]
        for col, sql in migrations:
            if col not in existing_cols:
                self.conn.execute(sql)
        self.conn.commit()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks(isrc)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tracks_spotify_uri ON tracks(spotify_uri)")
        self.conn.commit()

    def insert_track(self, *, artist: str, title: str, file_path: str, source: str, quality: str, album: str = "", isrc: str = "", spotify_uri: str = "", lyrics_path: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO tracks (artist, title, album, file_path, source, quality, isrc, spotify_uri, lyrics_path, downloaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (artist, title, album, file_path, source, quality, isrc or None, spotify_uri or None, lyrics_path or None, datetime.now(timezone.utc).isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def get_track(self, track_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
        return dict(row) if row else None

    def get_track_by_isrc(self, isrc: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM tracks WHERE isrc = ?", (isrc,)).fetchone()
        return dict(row) if row else None

    def is_downloaded(self, *, isrc: str = "", spotify_uri: str = "") -> bool:
        if spotify_uri:
            if self.conn.execute("SELECT 1 FROM tracks WHERE spotify_uri = ?", (spotify_uri,)).fetchone():
                return True
        if isrc:
            if self.conn.execute("SELECT 1 FROM tracks WHERE isrc = ?", (isrc,)).fetchone():
                return True
        return False

    def update_track(self, track_id: int, **fields):
        allowed = {"bpm", "key", "flac_path", "stems_path", "lyrics_path", "file_path", "artist", "title", "album", "isrc"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates: return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self.conn.execute(f"UPDATE tracks SET {set_clause} WHERE id = ?", list(updates.values()) + [track_id])
        self.conn.commit()

    def get_all_tracks(self) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM tracks ORDER BY downloaded_at DESC").fetchall()]

    def close(self):
        self.conn.close()

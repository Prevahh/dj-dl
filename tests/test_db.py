import tempfile
from pathlib import Path
from dj_dl.db import Database

def test_create_tables():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        row = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'").fetchone()
        assert row is not None
        db.close()

def test_insert_and_get_track():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        db.insert_track(artist="Kanye West", title="BULLY", album="BULLY", file_path="/tmp/Kanye West - BULLY.m4a", source="yt-dlp", quality="256k", isrc="USUM72400001", spotify_uri="spotify:track:abc123")
        track = db.get_track_by_isrc("USUM72400001")
        assert track is not None
        assert track["artist"] == "Kanye West"
        assert track["source"] == "yt-dlp"
        db.close()

def test_is_downloaded_by_spotify_uri():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        assert db.is_downloaded(spotify_uri="spotify:track:abc123") is False
        db.insert_track(artist="Test", title="Track", file_path="/tmp/test.m4a", source="spotdl", quality="320k", spotify_uri="spotify:track:abc123")
        assert db.is_downloaded(spotify_uri="spotify:track:abc123") is True
        db.close()

def test_is_downloaded_by_isrc():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        assert db.is_downloaded(isrc="US1234567890") is False
        db.insert_track(artist="Test", title="Track", file_path="/tmp/test.m4a", source="spotdl", quality="320k", isrc="US1234567890")
        assert db.is_downloaded(isrc="US1234567890") is True
        db.close()

def test_update_track():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        db.insert_track(artist="Test", title="Track", file_path="/tmp/test.m4a", source="yt-dlp", quality="256k")
        tracks = db.get_all_tracks()
        track_id = tracks[0]["id"]
        db.update_track(track_id, bpm=128.0, key="Cm")
        updated = db.get_track(track_id)
        assert updated["bpm"] == 128.0
        assert updated["key"] == "Cm"
        db.close()

def test_get_all_tracks():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        db.insert_track(artist="A", title="1", file_path="/a.m4a", source="x", quality="320k")
        db.insert_track(artist="B", title="2", file_path="/b.m4a", source="y", quality="256k")
        tracks = db.get_all_tracks()
        assert len(tracks) == 2
        db.close()

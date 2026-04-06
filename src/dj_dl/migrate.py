"""Migrate from existing yt-dlp archive and scan library."""
import logging
from pathlib import Path
from mutagen import File as MutagenFile
from .db import Database

logger = logging.getLogger(__name__)

def migrate(db: Database, music_dir: Path):
    archive_file = music_dir / ".yt-dlp-archive"
    if archive_file.exists():
        with open(archive_file) as f:
            archive_ids = {line.strip() for line in f if line.strip()}
        logger.info("Found %d entries in yt-dlp archive", len(archive_ids))
    extensions = (".m4a", ".mp3", ".flac", ".ogg", ".opus")
    audio_files = [f for f in music_dir.rglob("*") if f.suffix.lower() in extensions and not f.name.startswith(".")]
    logger.info("Found %d audio files", len(audio_files))
    imported = 0
    for path in audio_files:
        existing = db.conn.execute("SELECT 1 FROM tracks WHERE file_path = ?", (str(path),)).fetchone()
        if existing:
            continue
        artist, title = _parse_metadata(path)
        db.insert_track(artist=artist, title=title, file_path=str(path), source="migrated", quality="unknown")
        imported += 1
    logger.info("Migrated %d tracks into database", imported)

def _parse_metadata(path: Path) -> tuple[str, str]:
    try:
        audio = MutagenFile(str(path), easy=True)
        if audio and audio.tags:
            artist = audio.tags.get("artist", [""])[0]
            title = audio.tags.get("title", [""])[0]
            if artist and title:
                return artist, title
    except Exception:
        pass
    stem = path.stem
    if stem.startswith("NA - "):
        stem = stem[5:]
    if " - " in stem:
        parts = stem.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "Unknown", stem

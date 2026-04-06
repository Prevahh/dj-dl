"""Synced lyrics download, embedding, and terminal display.

Primary source: LRCLIB (lrclib.net) — free, no auth needed.
Fallback: Syrics (Spotify synced lyrics).
"""
import logging
import re
import time
from pathlib import Path

import httpx
from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, SYLT, Encoding

logger = logging.getLogger(__name__)

LRCLIB_API = "https://lrclib.net/api"


# ── Fetch ──────────────────────────────────────────────────────────────────

def _fetch_lrclib(artist: str, title: str, album: str = "", duration: int = 0) -> dict | None:
    """Query LRCLIB for synced and plain lyrics. Returns raw API response or None."""
    params: dict = {"artist_name": artist, "track_name": title}
    if album:
        params["album_name"] = album
    if duration:
        params["duration"] = duration
    try:
        resp = httpx.get(
            f"{LRCLIB_API}/get",
            params=params,
            headers={"User-Agent": "dj-dl/0.1 (https://github.com/Prevahh/dj-dl)"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            # Try search endpoint as fallback
            resp2 = httpx.get(
                f"{LRCLIB_API}/search",
                params={"artist_name": artist, "track_name": title},
                headers={"User-Agent": "dj-dl/0.1 (https://github.com/Prevahh/dj-dl)"},
                timeout=10,
            )
            if resp2.status_code == 200:
                results = resp2.json()
                if results:
                    return results[0]
    except Exception as e:
        logger.debug("LRCLIB request failed: %s", e)
    return None


# ── Parse LRC ─────────────────────────────────────────────────────────────

def parse_lrc(lrc_text: str) -> list[tuple[float, str]]:
    """Parse LRC format into list of (timestamp_seconds, lyric_line) tuples."""
    pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
    lines = []
    for raw in lrc_text.splitlines():
        m = pattern.match(raw.strip())
        if m:
            minutes, seconds, text = float(m.group(1)), float(m.group(2)), m.group(3).strip()
            lines.append((minutes * 60 + seconds, text))
    return sorted(lines, key=lambda x: x[0])


# ── Embed ──────────────────────────────────────────────────────────────────

def embed_lyrics(path: Path, plain: str = "", synced: str = "") -> bool:
    """Embed lyrics into audio file tags. Returns True on success."""
    ext = path.suffix.lower()
    try:
        if ext == ".m4a":
            audio = MP4(str(path))
            if plain:
                audio["\xa9lyr"] = [plain]
            audio.save()
            return True
        elif ext == ".mp3":
            try:
                tags = ID3(str(path))
            except Exception:
                audio = MP3(str(path))
                audio.add_tags()
                audio.save()
                tags = ID3(str(path))
            if plain:
                tags["USLT::eng"] = USLT(encoding=Encoding.UTF8, lang="eng", desc="", text=plain)
            if synced:
                parsed = parse_lrc(synced)
                sylt_data = [(line, int(ts * 1000)) for ts, line in parsed if line]
                if sylt_data:
                    tags["SYLT::eng"] = SYLT(
                        encoding=Encoding.UTF8, lang="eng", format=2, type=1,
                        desc="", text=sylt_data,
                    )
            tags.save()
            return True
        elif ext == ".flac":
            from mutagen.flac import FLAC
            audio = FLAC(str(path))
            if plain:
                audio["lyrics"] = [plain]
            audio.save()
            return True
    except Exception as e:
        logger.error("Failed to embed lyrics in %s: %s", path, e)
    return False


def save_lrc_sidecar(audio_path: Path, lrc_text: str) -> Path:
    """Save .lrc file alongside the audio file."""
    lrc_path = audio_path.with_suffix(".lrc")
    lrc_path.write_text(lrc_text, encoding="utf-8")
    return lrc_path


# ── Public API ─────────────────────────────────────────────────────────────

def download_lyrics(
    path: Path,
    *,
    artist: str,
    title: str,
    album: str = "",
    duration: int = 0,
    embed: bool = True,
    sidecar_lrc: bool = True,
) -> Path | None:
    """Download and optionally embed synced lyrics for a track.

    Returns path to the saved .lrc sidecar file, or None if not found.
    """
    data = _fetch_lrclib(artist, title, album, duration)
    if not data:
        logger.info("No lyrics found on LRCLIB for: %s - %s", artist, title)
        return None

    synced = data.get("syncedLyrics") or ""
    plain = data.get("plainLyrics") or ""

    if not synced and not plain:
        logger.info("LRCLIB returned empty lyrics for: %s - %s", artist, title)
        return None

    lrc_path = None
    if sidecar_lrc and synced:
        lrc_path = save_lrc_sidecar(path, synced)
        logger.info("Saved .lrc sidecar: %s", lrc_path)

    if embed:
        success = embed_lyrics(path, plain=plain, synced=synced)
        if success:
            logger.info("Embedded lyrics in: %s", path.name)

    return lrc_path


# ── Terminal display ────────────────────────────────────────────────────────

def display_lyrics(lrc_path: Path):
    """Display synced lyrics in the terminal with real-time highlighting.

    Reads timestamps from an .lrc file and prints lines as they come due.
    Press Ctrl+C to exit.
    """
    if not lrc_path.exists():
        print(f"LRC file not found: {lrc_path}")
        return

    lines = parse_lrc(lrc_path.read_text(encoding="utf-8"))
    if not lines:
        print("No timed lines found in LRC file.")
        return

    start_time = time.monotonic()
    idx = 0
    print("\n🎵  Lyrics Display — Ctrl+C to exit\n")
    try:
        while idx < len(lines):
            elapsed = time.monotonic() - start_time
            ts, text = lines[idx]
            if elapsed >= ts:
                print(f"\033[1m{text}\033[0m" if text else "")
                idx += 1
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped.")

"""MusicBrainz-based metadata enrichment and cover art tagging."""
import logging
import re
from pathlib import Path

import httpx
from mutagen import File as MutagenFile

from .postprocess import fetch_cover_art, embed_cover_art, tag_file

logger = logging.getLogger(__name__)

MB_API = "https://musicbrainz.org/ws/2"
MB_HEADERS = {"User-Agent": "dj-dl/0.2 (https://github.com/Prevahh/dj-dl)"}


def _mb_search_recording(artist: str, title: str) -> dict | None:
    """Search MusicBrainz for a recording and return the best match."""
    try:
        resp = httpx.get(
            f"{MB_API}/recording/",
            params={
                "query": f'artist:"{artist}" AND recording:"{title}"',
                "fmt": "json",
                "limit": 5,
                "inc": "artist-credits releases",
            },
            headers=MB_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        recordings = resp.json().get("recordings", [])
        if not recordings:
            return None
        return recordings[0]
    except Exception as e:
        logger.debug("MB search failed for %s - %s: %s", artist, title, e)
        return None


def _mb_get_release(mbid: str) -> dict | None:
    """Fetch full release info including genres/tags."""
    try:
        resp = httpx.get(
            f"{MB_API}/release/{mbid}",
            params={"fmt": "json", "inc": "genres tags"},
            headers=MB_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug("MB release fetch failed for %s: %s", mbid, e)
        return None


def _fix_na_prefix(path: Path, db=None) -> Path:
    """Rename files whose artist is literally 'NA' if we can infer better metadata."""
    stem = path.stem
    if not stem.startswith("NA-"):
        return path
    # Try to parse title from the rest
    rest = stem[3:].strip(" -")
    new_path = path.parent / f"Unknown - {rest}{path.suffix}"
    if not new_path.exists():
        path.rename(new_path)
        logger.info("Renamed NA- file: %s → %s", path.name, new_path.name)
        return new_path
    return path


def enrich_track(path: Path, *, artist: str = "", title: str = "",
                 album: str = "", embed_art: bool = True, db=None) -> dict:
    """
    Enrich a track with MusicBrainz metadata.

    Returns a dict with enriched fields: artist, title, album, year, genre, isrc.
    """
    result = {"artist": artist, "title": title, "album": album, "year": "", "genre": "", "isrc": ""}

    # Fix NA- prefixed files first
    path = _fix_na_prefix(path, db=db)

    # Try to read existing tags if artist/title not provided
    if not (artist and title):
        try:
            audio = MutagenFile(str(path), easy=True)
            if audio and audio.tags:
                artist = artist or (audio.tags.get("artist") or [""])[0]
                title = title or (audio.tags.get("title") or [""])[0]
                album = album or (audio.tags.get("album") or [""])[0]
        except Exception:
            pass
    # Fallback: parse from filename
    if not (artist and title) and " - " in path.stem:
        parts = path.stem.split(" - ", 1)
        artist = artist or parts[0].strip()
        title = title or parts[1].strip()

    if not (artist and title):
        logger.warning("Cannot enrich %s — no artist/title available", path.name)
        return result

    logger.info("Enriching: %s - %s", artist, title)
    recording = _mb_search_recording(artist, title)
    if not recording:
        logger.info("No MusicBrainz match for %s - %s", artist, title)
        # Still write what we have
        tag_file(path, artist=artist, title=title, album=album)
        return result

    # Extract enriched metadata
    result["artist"] = artist
    result["title"] = recording.get("title", title)
    result["isrc"] = (recording.get("isrcs") or [""])[0]

    releases = recording.get("releases", [])
    if releases:
        rel = releases[0]
        result["album"] = rel.get("title", album)
        result["year"] = (rel.get("date") or "")[:4]
        release_mbid = rel.get("id", "")
        if release_mbid:
            rel_data = _mb_get_release(release_mbid)
            if rel_data:
                genres = rel_data.get("genres", [])
                if genres:
                    result["genre"] = genres[0].get("name", "")
                elif rel_data.get("tags"):
                    result["genre"] = rel_data["tags"][0].get("name", "")

    # Write enriched tags
    tag_file(
        path,
        artist=result["artist"],
        title=result["title"],
        album=result["album"],
        year=result["year"],
        genre=result["genre"],
    )

    # Embed cover art
    if embed_art:
        art = fetch_cover_art(result["artist"], result["title"])
        if art:
            try:
                embed_cover_art(path, art)
                logger.info("Cover art embedded for %s - %s", result["artist"], result["title"])
            except Exception as e:
                logger.warning("Cover art embed failed: %s", e)

    logger.info("Enriched: %s - %s (ISRC: %s)", result["artist"], result["title"], result["isrc"])
    return result

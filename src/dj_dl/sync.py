"""Spotify playlist sync."""
import logging
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .db import Database
from .download import DownloadEngine
from .postprocess import postprocess

logger = logging.getLogger(__name__)

def get_spotify_client(cfg: dict) -> spotipy.Spotify:
    auth = SpotifyOAuth(
        client_id=cfg["spotify"]["client_id"],
        client_secret=cfg["spotify"]["client_secret"],
        redirect_uri="http://127.0.0.1:8080",
        scope="playlist-read-private playlist-read-collaborative",
        cache_path=str(Path.home() / ".cache/spotify-export-token"),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth)

def fetch_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=["track"])
    while results:
        for item in results["items"]:
            track = item.get("track")
            if not track or track.get("type") != "track":
                continue
            artists = "; ".join(a["name"] for a in track["artists"])
            isrc = track.get("external_ids", {}).get("isrc", "")
            tracks.append({
                "artist": artists, "title": track["name"],
                "album": track.get("album", {}).get("name", ""),
                "isrc": isrc, "spotify_uri": track["uri"],
            })
        results = sp.next(results) if results.get("next") else None
    return tracks

def sync_playlist(cfg: dict, db: Database, engine: DownloadEngine,
                  playlist_id: str | None = None, tag: bool = False, analyze: bool = False):
    playlist_id = playlist_id or cfg["spotify"]["playlist_id"]
    if not playlist_id:
        logger.error("No playlist ID configured")
        return
    sp = get_spotify_client(cfg)
    info = sp.playlist(playlist_id)
    logger.info("Syncing playlist: %s", info["name"])
    tracks = fetch_playlist_tracks(sp, playlist_id)
    logger.info("Found %d tracks", len(tracks))
    output_dir = Path(cfg["general"]["output_dir"])
    fmt = cfg["general"]["format"]
    naming = cfg["general"]["naming"]
    downloaded = 0
    skipped = 0
    for track in tracks:
        if db.is_downloaded(spotify_uri=track["spotify_uri"], isrc=track.get("isrc", "")):
            skipped += 1
            continue
        query = f"{track['artist']} - {track['title']}"
        logger.info("Downloading: %s", query)
        result = engine.download(query, output_dir, fmt)
        if result and result.file_path:
            final_path = postprocess(
                Path(result.file_path),
                artist=result.artist or track["artist"],
                title=result.title or track["title"],
                album=result.album or track.get("album", ""),
                target_fmt=fmt, naming=naming,
            )
            db.insert_track(
                artist=result.artist or track["artist"],
                title=result.title or track["title"],
                album=result.album or track.get("album", ""),
                file_path=str(final_path), source=result.source,
                quality=result.quality, isrc=track.get("isrc", ""),
                spotify_uri=track["spotify_uri"],
            )
            downloaded += 1
        else:
            logger.warning("Failed to download: %s", query)
    logger.info("Sync complete: %d downloaded, %d skipped", downloaded, skipped)

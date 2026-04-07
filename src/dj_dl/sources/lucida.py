"""lucida.to web ripper source wrapper.

lucida.to is a multi-site web ripper supporting Spotify, Apple Music, Deezer,
Tidal, Qobuz, SoundCloud, and YouTube — returning 320k MP3 or FLAC depending
on availability.

No CLI tool exists; this wrapper calls the lucida.to unofficial API via HTTP.
API endpoint: POST https://lucida.to/api/download
"""
import re
import time
import urllib.request
import urllib.parse
import json
from pathlib import Path

from .base import Source, TrackResult

_API_BASE = "https://lucida.to"
_TIMEOUT = 120  # seconds for download attempts


class LucidaSource(Source):
    name = "lucida"

    URL_PATTERNS = [
        r"https?://open\.spotify\.com/(track|album|playlist)/",
        r"https?://music\.apple\.com/",
        r"https?://www\.deezer\.com/(track|album)/",
        r"https?://tidal\.com/browse/(track|album)/",
        r"https?://listen\.tidal\.com/",
        r"https?://www\.qobuz\.com/",
        r"https?://(www\.)?soundcloud\.com/",
        r"https?://(www\.|music\.)?youtube\.com/",
        r"https?://youtu\.be/",
    ]

    def available(self) -> bool:
        # Always "available" — HTTP only, no local install needed
        # but we do a lightweight connectivity check against the domain
        try:
            req = urllib.request.Request(
                f"{_API_BASE}/",
                headers={"User-Agent": "dj-dl/0.1"},
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=8):
                return True
        except Exception:
            return False

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _api_request(self, url: str) -> dict | None:
        """Submit URL to lucida API and get download link."""
        payload = json.dumps({"url": url}).encode()
        req = urllib.request.Request(
            f"{_API_BASE}/api/download",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "dj-dl/0.1",
                "Origin": _API_BASE,
                "Referer": f"{_API_BASE}/",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                body = resp.read()
                return json.loads(body)
        except Exception:
            return None

    def _download_file(self, download_url: str, dest_path: Path) -> bool:
        """Stream a file from download_url to dest_path."""
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "dj-dl/0.1"},
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(resp.read())
            return True
        except Exception:
            return False

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.accepts_url(query):
            return None

        data = self._api_request(query)
        if not data:
            return None

        # lucida API typically returns:
        # { "url": "<direct download link>", "filename": "Artist - Title.flac",
        #   "quality": "flac" | "320", ... }
        download_url = data.get("url") or data.get("download_url")
        filename = data.get("filename") or data.get("name")
        if not download_url:
            return None

        if not filename:
            # Derive from URL
            filename = download_url.split("/")[-1].split("?")[0] or "track.mp3"

        dest_path = dest_dir / filename
        if not self._download_file(download_url, dest_path):
            return None

        stem = dest_path.stem
        artist, title = self._parse_filename(stem)
        quality_str = data.get("quality", "")
        quality = "lossless" if dest_path.suffix.lower() == ".flac" else "lossy"
        if "flac" in quality_str.lower():
            quality = "lossless"

        return TrackResult(
            artist=artist, title=title,
            file_path=str(dest_path), quality=quality, source=self.name,
        )

    def _parse_filename(self, stem: str) -> tuple[str, str]:
        if " - " in stem:
            parts = stem.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return "Unknown", stem

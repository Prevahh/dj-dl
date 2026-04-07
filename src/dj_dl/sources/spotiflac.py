"""SpotiFLAC source wrapper.

SpotiFLAC is a FLAC downloader targeting Qobuz, Tidal, and Amazon Music.
It resolves Spotify links to ISRC, then pulls the best lossless match from
these streaming platforms.

Install: pip install spotiflac  (or https://github.com/nicoboss/spotiflac)
Usage:   spotiflac -o /dest <spotify_url|search_query>
Config:  ~/.config/spotiflac/config.json  (platform credentials)
"""
import re
import shutil
import subprocess
from pathlib import Path

from .base import Source, TrackResult


class SpotiFLACSource(Source):
    name = "spotiflac"

    # SpotiFLAC handles Spotify URLs (resolves to ISRC, then fetches lossless)
    # as well as Qobuz / Tidal / Amazon direct URLs
    URL_PATTERNS = [
        r"https?://open\.spotify\.com/(track|album)/",
        r"https?://www\.qobuz\.com/",
        r"https?://tidal\.com/",
        r"https?://listen\.tidal\.com/",
        r"https?://music\.amazon\.com/",
    ]

    def available(self) -> bool:
        return shutil.which("spotiflac") is not None

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _build_command(self, query: str, dest_dir: str) -> list[str]:
        return [
            "spotiflac",
            "-o", dest_dir,
            query,
        ]

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available():
            return None
        # SpotiFLAC can also be used for plain search queries; accept both URL
        # and plain-text modes. URL check is advisory — if accepts_url is False
        # but no URL source handled it, we try a keyword search.
        audio_exts = {".flac", ".m4a", ".mp3"}
        before = set(f for f in dest_dir.rglob("*") if f.suffix.lower() in audio_exts)
        cmd = self._build_command(query, str(dest_dir))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                return None
            after = set(f for f in dest_dir.rglob("*") if f.suffix.lower() in audio_exts)
            new_files = after - before
            if not new_files:
                return None
            # Always prefer FLAC — that's the whole point of this source
            for ext in (".flac", ".m4a", ".mp3"):
                matches = [f for f in new_files if f.suffix.lower() == ext]
                if matches:
                    file_path = matches[0]
                    break
            else:
                file_path = next(iter(new_files))
            artist, title = self._parse_filename(file_path.stem)
            quality = "lossless" if file_path.suffix.lower() == ".flac" else "lossy"
            return TrackResult(
                artist=artist, title=title,
                file_path=str(file_path), quality=quality, source=self.name,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _parse_filename(self, stem: str) -> tuple[str, str]:
        if " - " in stem:
            parts = stem.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return "Unknown", stem

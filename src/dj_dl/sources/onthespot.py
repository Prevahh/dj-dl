"""OnTheSpot source wrapper.

OnTheSpot is a GUI app, but can be driven via its CLI mode:
  onthespot_cli --url <spotify/deezer/tidal/qobuz/apple/bandcamp url>
"""
import re
import shutil
import subprocess
from pathlib import Path
from .base import Source, TrackResult


class OnTheSpotSource(Source):
    name = "onthespot"

    URL_PATTERNS = [
        r"https?://open\.spotify\.com/",
        r"https?://www\.deezer\.com/",
        r"https?://tidal\.com/",
        r"https?://www\.qobuz\.com/",
        r"https?://music\.apple\.com/",
        r"https?://(.*\.)?bandcamp\.com/",
    ]

    def available(self) -> bool:
        return shutil.which("onthespot_cli") is not None or shutil.which("onthespot") is not None

    def _bin(self) -> str:
        return shutil.which("onthespot_cli") or shutil.which("onthespot") or "onthespot_cli"

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _build_command(self, url: str, dest_dir: str) -> list[str]:
        return [self._bin(), "--url", url, "--output", dest_dir]

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available():
            return None
        if not self.accepts_url(query):
            return None  # OnTheSpot only handles URLs, not text search
        before = set(dest_dir.glob("*.*"))
        cmd = self._build_command(query, str(dest_dir))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return None
            new_files = set(dest_dir.glob("*.*")) - before
            audio_exts = {".m4a", ".mp3", ".flac", ".ogg", ".opus"}
            new_audio = [f for f in new_files if f.suffix.lower() in audio_exts]
            if not new_audio:
                return None
            file_path = new_audio[0]
            artist, title = self._parse_filename(file_path.stem)
            quality = "flac" if file_path.suffix.lower() == ".flac" else "320k"
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

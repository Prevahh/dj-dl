"""OrpheusDL source wrapper.

OrpheusDL is a modular music downloader supporting Deezer, Qobuz, Tidal, and more
via the Firehawk52 plugin ecosystem.

Install: pip install orpheusdl  (or clone https://github.com/OrfiTeam/OrpheusDL)
Usage:   orpheus <url>  --output-path /dest
Config:  ~/.config/orpheusdl/settings.json  (per-module credentials)
"""
import re
import shutil
import subprocess
from pathlib import Path

from .base import Source, TrackResult


class OrpheusDLSource(Source):
    name = "orpheusdl"

    # Platforms supported by common OrpheusDL modules
    URL_PATTERNS = [
        r"https?://www\.deezer\.com/",
        r"https?://deezer\.page\.link/",
        r"https?://www\.qobuz\.com/",
        r"https?://tidal\.com/",
        r"https?://listen\.tidal\.com/",
    ]

    def available(self) -> bool:
        return shutil.which("orpheus") is not None

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _build_command(self, url: str, dest_dir: str) -> list[str]:
        return [
            "orpheus",
            "--output-path", dest_dir,
            url,
        ]

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available() or not self.accepts_url(query):
            return None

        audio_exts = {".flac", ".m4a", ".mp3", ".ogg", ".opus"}
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
            # Prefer FLAC, then M4A, then MP3
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

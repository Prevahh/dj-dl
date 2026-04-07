"""Soulseek source wrapper via slsk-batchdl.

slsk-batchdl: https://github.com/fiso64/slsk-batchdl
Install: Download binary from releases, place in PATH as sldl.
Usage: sldl "Artist - Title" --path /dest --pref-format flac
"""
import re
import shutil
import subprocess
from pathlib import Path
from .base import Source, TrackResult


class SlskSource(Source):
    name = "soulseek"

    def available(self) -> bool:
        return shutil.which("sldl") is not None

    def accepts_url(self, url: str) -> bool:
        # sldl can handle Spotify/Bandcamp URLs for batch mode, but primarily
        # used for search queries. We handle URLs only if they look like Spotify.
        return bool(re.match(r"https?://open\.spotify\.com/(track|album)/", url))

    def _build_command(self, query: str, dest_dir: str) -> list[str]:
        cmd = [
            "sldl", query,
            "--path", dest_dir,
            "--pref-format", "flac",
            "--format", "mp3,m4a,flac",
            "--length-tol", "3",
            "--album-art-embed",
            "--write-playlist",  # skip playlist files
        ]
        # Remove --write-playlist (it's not a real flag); keep the rest lean
        return [
            "sldl", query,
            "--path", dest_dir,
            "--pref-format", "flac",
            "--format", "mp3,m4a,flac",
            "--length-tol", "3",
        ]

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available():
            return None
        audio_exts = {".flac", ".m4a", ".mp3"}
        before = set(f for f in dest_dir.rglob("*") if f.suffix.lower() in audio_exts)
        cmd = self._build_command(query, str(dest_dir))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            after = set(f for f in dest_dir.rglob("*") if f.suffix.lower() in audio_exts)
            new_files = after - before
            if not new_files:
                return None
            # Prefer FLAC
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

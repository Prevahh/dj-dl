"""DeemixFix source wrapper.

deemix is a Deezer downloader. "DeemixFix" refers to the maintained fork/fix
that works with current Deezer APIs.

Install: pip install deemix
Usage:   deemix --path /dest <url>
ARL:     Set via ~/.config/deemix/.arl  or DEEZER_ARL env variable
         (ARL is your Deezer authentication cookie — 192-char hex string)
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

from .base import Source, TrackResult

_ARL_FILE = Path.home() / ".config" / "deemix" / ".arl"


class DeemixFixSource(Source):
    name = "deemixfix"

    URL_PATTERNS = [
        r"https?://www\.deezer\.com/",
        r"https?://deezer\.page\.link/",
    ]

    def available(self) -> bool:
        if not shutil.which("deemix"):
            return False
        # Require ARL — either env var or file
        if os.environ.get("DEEZER_ARL"):
            return True
        if _ARL_FILE.exists() and _ARL_FILE.read_text().strip():
            return True
        return False

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _get_arl(self) -> str:
        arl = os.environ.get("DEEZER_ARL", "")
        if not arl and _ARL_FILE.exists():
            arl = _ARL_FILE.read_text().strip()
        return arl

    def _build_command(self, url: str, dest_dir: str) -> list[str]:
        cmd = ["deemix", "--path", dest_dir]
        arl = self._get_arl()
        if arl:
            cmd += ["--arl", arl]
        cmd.append(url)
        return cmd

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available() or not self.accepts_url(query):
            return None

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

"""yt-dlp source wrapper."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from .base import Source, TrackResult

class YtDlpSource(Source):
    name = "yt-dlp"
    URL_PATTERNS = [
        r"https?://(www\.)?youtube\.com/",
        r"https?://music\.youtube\.com/",
        r"https?://youtu\.be/",
        r"https?://(www\.)?soundcloud\.com/",
        r"https?://(.*\.)?bandcamp\.com/",
    ]

    def __init__(self, cookies_browser: str = "firefox"):
        self.cookies_browser = cookies_browser

    def available(self) -> bool:
        return shutil.which("yt-dlp") is not None

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _build_search_url(self, artist: str, title: str) -> str:
        return f"ytsearch1:{artist} - {title}"

    def _build_command(self, url: str, dest_dir: str, fmt: str) -> list[str]:
        cmd = [
            "yt-dlp", "--no-update", "--extract-audio",
            "--audio-format", fmt, "--audio-quality", "0",
            "--output", f"{dest_dir}/%(artist)s - %(title)s.%(ext)s",
            "--add-metadata", "--embed-thumbnail", "--no-warnings", "--print-json",
        ]
        if self.cookies_browser:
            cmd.extend(["--cookies-from-browser", self.cookies_browser])
        if url.startswith("ytsearch"):
            cmd.extend(["--playlist-items", "1"])
        cmd.append(url)
        return cmd

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available():
            return None
        url = query if self.accepts_url(query) else self._build_search_url(*self._parse_query(query))
        cmd = self._build_command(url, str(dest_dir), fmt)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return None
            info = None
            for line in result.stdout.strip().splitlines():
                try:
                    info = json.loads(line)
                except json.JSONDecodeError:
                    continue
            if not info:
                return None
            artist = info.get("artist") or info.get("uploader") or "NA"
            title = info.get("title", "Unknown")
            file_path = self._find_downloaded_file(dest_dir, artist, title, fmt)
            return TrackResult(artist=artist, title=title, album=info.get("album", ""),
                             file_path=str(file_path) if file_path else "", quality=f"{info.get('abr', '?')}k", source=self.name)
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _parse_query(self, query: str) -> tuple[str, str]:
        if " - " in query:
            parts = query.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return "", query.strip()

    def _find_downloaded_file(self, dest_dir: Path, artist: str, title: str, fmt: str) -> Path | None:
        candidates = sorted(dest_dir.glob(f"*.{fmt}"), key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0] if candidates else None

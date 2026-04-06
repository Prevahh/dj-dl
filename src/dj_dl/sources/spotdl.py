"""spotdl source wrapper."""
import re
import shutil
import subprocess
from pathlib import Path
from .base import Source, TrackResult

class SpotdlSource(Source):
    name = "spotdl"
    URL_PATTERNS = [r"https?://open\.spotify\.com/(track|album|playlist)/"]

    def available(self) -> bool:
        return shutil.which("spotdl") is not None

    def accepts_url(self, url: str) -> bool:
        return any(re.match(p, url) for p in self.URL_PATTERNS)

    def _build_command(self, query: str, dest_dir: str, fmt: str) -> list[str]:
        return ["spotdl", "download", query, "--output", dest_dir, "--format", fmt, "--bitrate", "320k", "--threads", "4"]

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        if not self.available():
            return None
        before = set(dest_dir.glob(f"*.{fmt}"))
        cmd = self._build_command(query, str(dest_dir), fmt)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return None
            new_files = set(dest_dir.glob(f"*.{fmt}")) - before
            if not new_files:
                return None
            file_path = new_files.pop()
            artist, title = self._parse_filename(file_path.stem)
            return TrackResult(artist=artist, title=title, file_path=str(file_path), quality="320k", source=self.name)
        except (subprocess.TimeoutExpired, OSError):
            return None

    def _parse_filename(self, stem: str) -> tuple[str, str]:
        if " - " in stem:
            parts = stem.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return "Unknown", stem

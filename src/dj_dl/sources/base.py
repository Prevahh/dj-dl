"""Base class for download sources."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass
class TrackResult:
    artist: str
    title: str
    album: str = ""
    isrc: str = ""
    file_path: str = ""
    quality: str = ""
    source: str = ""

class Source(ABC):
    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Check if the external tool is installed and configured."""

    @abstractmethod
    def accepts_url(self, url: str) -> bool:
        """Check if this source handles the given URL."""

    @abstractmethod
    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        """Download a track. Returns TrackResult on success, None on failure."""

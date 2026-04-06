"""Download orchestrator with fallback chain."""
import logging
from pathlib import Path
from .sources.base import Source, TrackResult

logger = logging.getLogger(__name__)

class DownloadEngine:
    def __init__(self, sources: list[Source]):
        self.sources = sources

    def download(self, query: str, dest_dir: Path, fmt: str = "m4a") -> TrackResult | None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        url_sources = [s for s in self.sources if s.available() and s.accepts_url(query)]
        other_sources = [s for s in self.sources if s.available() and s not in url_sources]
        ordered = url_sources + other_sources
        for source in ordered:
            logger.info("Trying %s for: %s", source.name, query)
            try:
                result = source.download(query, dest_dir, fmt)
                if result and result.file_path:
                    logger.info("Success via %s: %s", source.name, result.file_path)
                    return result
                logger.info("No result from %s", source.name)
            except Exception as e:
                logger.warning("Error from %s: %s", source.name, e)
                continue
        logger.error("All sources failed for: %s", query)
        return None

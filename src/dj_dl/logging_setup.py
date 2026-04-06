"""Logging configuration with file rotation."""
import logging
from datetime import datetime
from pathlib import Path
from .config import DATA_DIR

def setup_logging(verbose: bool = False):
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"dj-dl-{datetime.now():%Y-%m-%d}.log"
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, handlers=[
        logging.FileHandler(log_file), logging.StreamHandler(),
    ])
    cutoff = datetime.now().timestamp() - (30 * 86400)
    for old_log in log_dir.glob("dj-dl-*.log"):
        if old_log.stat().st_mtime < cutoff:
            old_log.unlink()

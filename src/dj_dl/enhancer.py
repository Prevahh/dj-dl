"""FLAC enhancement: search lossless sources for a track and save to DJ/FLAC/."""
import logging
import shutil
from pathlib import Path

from mutagen import File as MutagenFile

logger = logging.getLogger(__name__)

FLAC_DIR_NAME = "FLAC"


def _read_tags(path: Path) -> tuple[str, str, str]:
    """Read artist, title, album from file tags."""
    try:
        audio = MutagenFile(str(path), easy=True)
        if audio and audio.tags:
            artist = (audio.tags.get("artist") or [""])[0]
            title = (audio.tags.get("title") or [""])[0]
            album = (audio.tags.get("album") or [""])[0]
            return artist, title, album
    except Exception:
        pass
    # Fallback to filename
    stem = path.stem
    if " - " in stem:
        parts = stem.split(" - ", 1)
        return parts[0].strip(), parts[1].strip(), ""
    return "Unknown", stem, ""


def _try_streamrip(query: str, dest_dir: Path) -> Path | None:
    """Try streamrip (rip) to download lossless FLAC."""
    if not shutil.which("rip"):
        logger.debug("streamrip (rip) not in PATH — skipping lossless search")
        return None
    import subprocess
    before = set(dest_dir.rglob("*.flac"))
    try:
        result = subprocess.run(
            ["rip", "search", "--source", "qobuz", "--type", "track", query,
             "--folder", str(dest_dir)],
            capture_output=True, text=True, timeout=120,
        )
        after = set(dest_dir.rglob("*.flac"))
        new_files = after - before
        if new_files:
            return next(iter(new_files))
    except Exception as e:
        logger.debug("streamrip enhance failed: %s", e)
    return None


def _try_soulseek(query: str, dest_dir: Path) -> Path | None:
    """Try sldl (slsk-batchdl) to find FLAC on Soulseek."""
    if not shutil.which("sldl"):
        logger.debug("sldl not in PATH — skipping Soulseek lossless search")
        return None
    import subprocess
    before = set(dest_dir.rglob("*.flac"))
    try:
        result = subprocess.run(
            ["sldl", query, "--path", str(dest_dir),
             "--pref-format", "flac", "--format", "flac", "--max-stale-time", "10"],
            capture_output=True, text=True, timeout=60,
        )
        after = set(dest_dir.rglob("*.flac"))
        new_files = after - before
        if new_files:
            return next(iter(new_files))
    except Exception as e:
        logger.debug("sldl enhance failed: %s", e)
    return None


def enhance_track(path: Path, music_dir: Path) -> Path | None:
    """
    Search lossless sources for the given track and save a FLAC copy to
    <music_dir>/FLAC/<Artist> - <Title>.flac

    Returns the FLAC path on success, None otherwise.
    """
    artist, title, album = _read_tags(path)
    if not (artist and title):
        logger.warning("Cannot enhance %s — no artist/title metadata", path.name)
        return None

    # Already have FLAC? Check
    flac_dir = music_dir / FLAC_DIR_NAME
    safe_name = f"{artist} - {title}".replace("/", "_").replace(":", "-")
    expected_flac = flac_dir / f"{safe_name}.flac"
    if expected_flac.exists():
        logger.info("FLAC already exists: %s", expected_flac.name)
        return expected_flac

    flac_dir.mkdir(parents=True, exist_ok=True)
    query = f"{artist} - {title}"
    logger.info("Searching lossless sources for: %s", query)

    # Try streamrip first (best quality)
    flac_path = _try_streamrip(query, flac_dir)
    if flac_path:
        logger.info("Got lossless via streamrip: %s", flac_path.name)
        return flac_path

    # Try Soulseek
    flac_path = _try_soulseek(query, flac_dir)
    if flac_path:
        logger.info("Got lossless via Soulseek: %s", flac_path.name)
        return flac_path

    logger.info("No lossless found for: %s", query)
    return None

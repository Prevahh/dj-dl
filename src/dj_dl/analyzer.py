"""Track analysis: BPM and musical key detection.

Primary: essentia (high quality, GPU-capable)
Fallback: aubio (lightweight, widely available)
Last resort: ffmpeg + rudimentary beat detection (not recommended for production)
"""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _try_essentia(path: Path) -> tuple[float | None, str | None]:
    """Run essentia's streaming extractor for BPM + key."""
    try:
        import essentia.standard as es  # type: ignore
        loader = es.MonoLoader(filename=str(path))
        audio = loader()

        # BPM
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, *_ = rhythm_extractor(audio)

        # Key
        key_extractor = es.KeyExtractor()
        key, scale, strength = key_extractor(audio)
        key_str = f"{key} {scale}"

        return round(float(bpm), 2), key_str
    except ImportError:
        logger.debug("essentia not installed, skipping")
        return None, None
    except Exception as e:
        logger.warning("essentia analysis failed for %s: %s", path.name, e)
        return None, None


def _try_aubio(path: Path) -> tuple[float | None, str | None]:
    """Run aubio for BPM detection (key not supported)."""
    if not shutil.which("aubiotrack"):
        return None, None
    try:
        result = subprocess.run(
            ["aubiotempo", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if not lines:
            return None, None
        # aubiotempo prints beat timestamps; compute mean BPM from intervals
        beats = [float(l) for l in lines if l.replace(".", "").isdigit()]
        if len(beats) < 2:
            return None, None
        intervals = [beats[i+1] - beats[i] for i in range(len(beats)-1)]
        mean_interval = sum(intervals) / len(intervals)
        bpm = 60.0 / mean_interval if mean_interval > 0 else None
        return (round(bpm, 2) if bpm else None), None
    except Exception as e:
        logger.debug("aubio analysis failed: %s", e)
        return None, None


def _try_keyfinder(path: Path) -> tuple[float | None, str | None]:
    """Run keyfinder-cli for key detection."""
    if not shutil.which("keyfinder-cli"):
        return None, None
    try:
        result = subprocess.run(
            ["keyfinder-cli", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        key = result.stdout.strip()
        return None, key if key else None
    except Exception as e:
        logger.debug("keyfinder-cli failed: %s", e)
        return None, None


def analyze_track(path: Path) -> tuple[float | None, str | None]:
    """
    Analyze a track for BPM and musical key.

    Returns: (bpm, key_string) — either may be None if detection fails.
    Tries: essentia → aubio (bpm) + keyfinder-cli (key) → None
    """
    bpm, key = _try_essentia(path)
    if bpm is not None and key is not None:
        return bpm, key

    # Fallbacks
    if bpm is None:
        bpm, _ = _try_aubio(path)
    if key is None:
        _, key = _try_keyfinder(path)

    return bpm, key

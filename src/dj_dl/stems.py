"""Stem separation via Demucs (htdemucs model on CUDA GPU).

Demucs: https://github.com/facebookresearch/demucs
Install: pip install demucs  (add torch with CUDA support first)
Output structure: <stems_dir>/<model>/<track_stem>/vocals.wav, drums.wav, bass.wav, other.wav
"""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "htdemucs"
STEMS_DIR_NAME = "stems"


def separate_stems(
    path: Path,
    music_dir: Path,
    model: str = DEFAULT_MODEL,
    device: str = "cuda",
) -> Path | None:
    """
    Run Demucs stem separation on a track.

    Outputs: <music_dir>/stems/<model>/<track_stem>/{vocals,drums,bass,other}.wav
    Returns the stem output directory on success, None on failure.
    """
    if not shutil.which("demucs"):
        # Try python -m demucs
        try:
            result = subprocess.run(
                ["python", "-m", "demucs", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                logger.warning("demucs not available — install with: pip install demucs")
                return None
            _demucs_cmd = ["python", "-m", "demucs"]
        except (OSError, subprocess.TimeoutExpired):
            logger.warning("demucs not available — install with: pip install demucs")
            return None
    else:
        _demucs_cmd = ["demucs"]

    stems_out = music_dir / STEMS_DIR_NAME
    stems_out.mkdir(parents=True, exist_ok=True)

    # Check if stems already exist
    track_stem = path.stem
    expected_dir = stems_out / model / track_stem
    if expected_dir.exists() and list(expected_dir.glob("*.wav")):
        logger.info("Stems already exist: %s", expected_dir)
        return expected_dir

    cmd = [
        *_demucs_cmd,
        "--name", model,
        "--device", device,
        "--out", str(stems_out),
        str(path),
    ]

    logger.info("Running Demucs stem separation: %s (device=%s)", path.name, device)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        if result.returncode != 0:
            # Try CPU fallback if CUDA failed
            if device == "cuda":
                logger.warning("CUDA stem separation failed, retrying on CPU")
                return separate_stems(path, music_dir, model=model, device="cpu")
            logger.error("Demucs failed for %s: %s", path.name, result.stderr[-500:])
            return None
        if expected_dir.exists():
            wav_files = list(expected_dir.glob("*.wav"))
            logger.info("Stems separated: %d files in %s", len(wav_files), expected_dir)
            return expected_dir
        # Demucs may place output differently; search
        for found_dir in stems_out.rglob(track_stem):
            if found_dir.is_dir() and list(found_dir.glob("*.wav")):
                return found_dir
        logger.warning("Stem output directory not found after demucs run")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Demucs timed out for %s", path.name)
        return None
    except OSError as e:
        logger.error("Failed to run demucs: %s", e)
        return None

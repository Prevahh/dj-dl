"""TOML config loader with defaults and path expansion."""
import tomllib
from copy import deepcopy
from os.path import expanduser
from pathlib import Path

CONFIG_DIR = Path(expanduser("~/.config/dj-dl"))
CONFIG_PATH = CONFIG_DIR / "config.toml"
DATA_DIR = Path(expanduser("~/.local/share/dj-dl"))

DEFAULT_CONFIG = {
    "general": {
        "output_dir": expanduser("~/Music/DJ"),
        "format": "m4a",
        "quality": "320",
        "archive": True,
        "naming": "{artist} - {title}",
    },
    "sources": {
        "priority": [
            "onthespot", "spotdl", "streamrip", "orpheusdl",
            "deemixfix", "spotiflac", "slsk-batchdl", "yt-dlp",
            "lucida", "doubledouble",
        ],
    },
    "spotify": {"client_id": "", "client_secret": "", "playlist_id": ""},
    "lyrics": {
        "sources": ["lrclib", "syrics"],
        "embed": True,
        "sidecar_lrc": True,
    },
    "deezer": {"arl": ""},
    "enhance": {
        "flac_dir": expanduser("~/Music/DJ/FLAC"),
        "sources": ["streamrip", "orpheusdl", "deemixfix", "spotiflac", "slsk-batchdl"],
    },
    "stems": {"model": "htdemucs", "output_dir": expanduser("~/Music/DJ/stems"), "device": "cuda"},
    "analysis": {"bpm": True, "key": True},
}

def _deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result

def _expand_paths(cfg: dict) -> dict:
    for section in cfg.values():
        if not isinstance(section, dict):
            continue
        for key, val in section.items():
            if isinstance(val, str) and "~" in val:
                section[key] = expanduser(val)
    return cfg

def load_config(path: Path | None = None) -> dict:
    path = path or CONFIG_PATH
    cfg = deepcopy(DEFAULT_CONFIG)
    if path.exists():
        with open(path, "rb") as f:
            user_cfg = tomllib.load(f)
        cfg = _deep_merge(cfg, user_cfg)
    return _expand_paths(cfg)

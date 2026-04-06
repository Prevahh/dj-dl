import os
import tempfile
from pathlib import Path
from dj_dl.config import load_config, DEFAULT_CONFIG

def test_load_config_defaults():
    cfg = load_config(Path("/nonexistent/config.toml"))
    assert cfg["general"]["format"] == "m4a"
    assert cfg["general"]["quality"] == "320"
    assert cfg["general"]["archive"] is True
    assert "yt-dlp" in cfg["sources"]["priority"]

def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[general]\nformat = "mp3"\noutput_dir = "/tmp/dj"\n')
        f.flush()
        cfg = load_config(Path(f.name))
    os.unlink(f.name)
    assert cfg["general"]["format"] == "mp3"
    assert cfg["general"]["output_dir"] == "/tmp/dj"
    assert cfg["general"]["quality"] == "320"

def test_expand_paths():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[general]\noutput_dir = "~/Music/DJ"\n')
        f.flush()
        cfg = load_config(Path(f.name))
    os.unlink(f.name)
    assert "~" not in cfg["general"]["output_dir"]
    assert cfg["general"]["output_dir"].startswith("/")

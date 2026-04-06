import shutil
from dj_dl.sources.spotdl import SpotdlSource

def test_spotdl_available():
    src = SpotdlSource()
    assert src.available() == (shutil.which("spotdl") is not None)

def test_spotdl_accepts_url():
    src = SpotdlSource()
    assert src.accepts_url("https://open.spotify.com/track/abc123") is True
    assert src.accepts_url("https://open.spotify.com/album/abc123") is True
    assert src.accepts_url("https://www.youtube.com/watch?v=abc") is False
    assert src.accepts_url("Kanye West - BULLY") is False

def test_spotdl_build_command():
    src = SpotdlSource()
    cmd = src._build_command("Kanye West - BULLY", "/tmp/out", "m4a")
    assert "spotdl" in cmd[0]
    assert "--output" in cmd
    assert "--format" in cmd

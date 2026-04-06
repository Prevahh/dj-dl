import shutil
from dj_dl.sources.ytdlp import YtDlpSource

def test_ytdlp_available():
    src = YtDlpSource()
    assert src.available() == (shutil.which("yt-dlp") is not None)

def test_ytdlp_build_search_url():
    src = YtDlpSource()
    url = src._build_search_url("Kanye West", "BULLY")
    assert "ytsearch1:" in url
    assert "Kanye West" in url
    assert "BULLY" in url

def test_ytdlp_accepts_youtube_url():
    src = YtDlpSource()
    assert src.accepts_url("https://www.youtube.com/watch?v=abc123") is True
    assert src.accepts_url("https://music.youtube.com/watch?v=abc123") is True
    assert src.accepts_url("https://soundcloud.com/artist/track") is True
    assert src.accepts_url("https://open.spotify.com/track/abc") is False

def test_ytdlp_build_command():
    src = YtDlpSource(cookies_browser="firefox")
    cmd = src._build_command("ytsearch1:test", "/tmp/out", "m4a")
    assert "yt-dlp" in cmd[0]
    assert "--cookies-from-browser" in cmd
    assert "firefox" in cmd
    assert "--extract-audio" in cmd
    assert "--audio-format" in cmd

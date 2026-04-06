"""Tests for lyrics module."""
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from dj_dl.lyrics import parse_lrc, embed_lyrics, save_lrc_sidecar, download_lyrics


SAMPLE_LRC = """\
[00:10.50]Hello world
[00:15.20]Second line
[00:20.00]Third line
"""


def test_parse_lrc():
    lines = parse_lrc(SAMPLE_LRC)
    assert len(lines) == 3
    assert abs(lines[0][0] - 10.5) < 0.01
    assert lines[0][1] == "Hello world"
    assert abs(lines[1][0] - 15.2) < 0.01


def test_parse_lrc_empty():
    assert parse_lrc("") == []
    assert parse_lrc("[ti:Title]\n[ar:Artist]\n") == []


def _make_test_audio_m4a(path: Path):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:a", "aac", "-b:a", "128k", str(path)],
        capture_output=True, check=True
    )


def test_embed_lyrics_m4a():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.m4a"
        _make_test_audio_m4a(f)
        result = embed_lyrics(f, plain="Hello world\nSecond line", synced=SAMPLE_LRC)
        assert result is True
        from mutagen.mp4 import MP4
        tags = MP4(str(f))
        assert "\xa9lyr" in tags
        assert "Hello world" in tags["\xa9lyr"][0]


def test_save_lrc_sidecar():
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "Artist - Track.m4a"
        audio.touch()
        lrc_path = save_lrc_sidecar(audio, SAMPLE_LRC)
        assert lrc_path == audio.with_suffix(".lrc")
        assert lrc_path.exists()
        assert "Hello world" in lrc_path.read_text()


def test_download_lyrics_success():
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "Artist - Track.m4a"
        _make_test_audio_m4a(audio)
        mock_response = {
            "syncedLyrics": SAMPLE_LRC,
            "plainLyrics": "Hello world\nSecond line\nThird line",
        }
        with patch("dj_dl.lyrics._fetch_lrclib", return_value=mock_response):
            lrc = download_lyrics(audio, artist="Artist", title="Track",
                                  embed=True, sidecar_lrc=True)
        assert lrc is not None
        assert lrc.suffix == ".lrc"
        assert lrc.exists()


def test_download_lyrics_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "Unknown - Track.m4a"
        audio.touch()
        with patch("dj_dl.lyrics._fetch_lrclib", return_value=None):
            result = download_lyrics(audio, artist="Unknown", title="Track")
        assert result is None

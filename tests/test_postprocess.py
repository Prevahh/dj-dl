import tempfile
import subprocess
from pathlib import Path
from dj_dl.postprocess import format_filename, convert_audio, tag_file

def test_format_filename():
    assert format_filename("Kanye West", "BULLY", "{artist} - {title}") == "Kanye West - BULLY"

def test_format_filename_sanitizes():
    result = format_filename("AC/DC", "Track/1", "{artist} - {title}")
    assert "/" not in result

def _make_test_audio(path: Path):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                    "-c:a", "aac", "-b:a", "128k", str(path)], capture_output=True, check=True)

def test_tag_file():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.m4a"
        _make_test_audio(f)
        tag_file(f, artist="Test Artist", title="Test Title", album="Test Album")
        from mutagen.mp4 import MP4
        tags = MP4(str(f))
        assert tags["\xa9ART"] == ["Test Artist"]
        assert tags["\xa9nam"] == ["Test Title"]
        assert tags["\xa9alb"] == ["Test Album"]

def test_convert_audio_m4a_to_mp3():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "test.m4a"
        _make_test_audio(src)
        dest = convert_audio(src, "mp3")
        assert dest.suffix == ".mp3"
        assert dest.exists()

def test_convert_audio_same_format():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "test.m4a"
        _make_test_audio(src)
        dest = convert_audio(src, "m4a")
        assert dest == src

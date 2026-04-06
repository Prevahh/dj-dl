"""Post-download processing: convert, tag, rename."""
import logging
import re
import subprocess
from pathlib import Path
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)

def format_filename(artist: str, title: str, pattern: str) -> str:
    name = pattern.format(artist=artist, title=title)
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    return name.strip()

def convert_audio(src: Path, target_fmt: str) -> Path:
    current_fmt = src.suffix.lstrip(".")
    if current_fmt == target_fmt:
        return src
    dest = src.with_suffix(f".{target_fmt}")
    try:
        subprocess.run(["ffmpeg", "-y", "-i", str(src), "-q:a", "0", str(dest)],
                      capture_output=True, check=True, timeout=120)
        src.unlink()
        return dest
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error("Conversion failed for %s: %s", src, e)
        return src

def tag_file(path: Path, *, artist: str = "", title: str = "", album: str = "", year: str = "", genre: str = ""):
    ext = path.suffix.lower()
    if ext == ".m4a":
        _tag_m4a(path, artist=artist, title=title, album=album, year=year, genre=genre)
    elif ext == ".mp3":
        _tag_mp3(path, artist=artist, title=title, album=album, year=year, genre=genre)

def _tag_m4a(path: Path, **tags):
    audio = MP4(str(path))
    tag_map = {"artist": "\xa9ART", "title": "\xa9nam", "album": "\xa9alb", "year": "\xa9day", "genre": "\xa9gen"}
    for key, atom in tag_map.items():
        val = tags.get(key, "")
        if val:
            audio[atom] = [val]
    audio.save()

def _tag_mp3(path: Path, **tags):
    try:
        audio = EasyID3(str(path))
    except Exception:
        audio = MP3(str(path))
        audio.add_tags()
        audio.save()
        audio = EasyID3(str(path))
    tag_map = {"artist": "artist", "title": "title", "album": "album", "year": "date", "genre": "genre"}
    for key, id3_key in tag_map.items():
        val = tags.get(key, "")
        if val:
            audio[id3_key] = val
    audio.save()

def rename_file(path: Path, artist: str, title: str, pattern: str) -> Path:
    new_name = format_filename(artist, title, pattern)
    new_path = path.parent / f"{new_name}{path.suffix}"
    if new_path == path:
        return path
    if new_path.exists():
        return path
    path.rename(new_path)
    return new_path

def postprocess(path: Path, *, artist: str, title: str, album: str = "",
                target_fmt: str = "m4a", naming: str = "{artist} - {title}") -> Path:
    path = convert_audio(path, target_fmt)
    tag_file(path, artist=artist, title=title, album=album)
    path = rename_file(path, artist, title, naming)
    return path

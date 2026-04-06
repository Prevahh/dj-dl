"""CLI entry point for dj-dl."""
import logging
import re
from pathlib import Path
import click
from . import __version__
from .config import load_config, DATA_DIR
from .db import Database
from .download import DownloadEngine
from .logging_setup import setup_logging
from .postprocess import postprocess
from .sources.ytdlp import YtDlpSource
from .sources.spotdl import SpotdlSource

logger = logging.getLogger(__name__)

def _build_engine(cfg: dict) -> DownloadEngine:
    source_map = {
        "yt-dlp": lambda: YtDlpSource(),
        "spotdl": lambda: SpotdlSource(),
    }
    sources = []
    for name in cfg["sources"]["priority"]:
        factory = source_map.get(name)
        if factory:
            sources.append(factory())
    return DownloadEngine(sources)

def _parse_playlist_id(arg: str) -> str:
    m = re.match(r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)", arg)
    if m:
        return m.group(1)
    return arg

@click.group()
@click.version_option(__version__, prog_name="dj-dl")
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging")
@click.pass_context
def main(ctx, verbose):
    """dj-dl — All-in-one DJ track downloader."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = load_config()
    ctx.obj["db"] = Database(DATA_DIR / "library.db")

@main.command()
@click.argument("query")
@click.pass_context
def get(ctx, query):
    """Download a single track by search query or URL."""
    cfg = ctx.obj["cfg"]
    db = ctx.obj["db"]
    engine = _build_engine(cfg)
    output_dir = Path(cfg["general"]["output_dir"])
    fmt = cfg["general"]["format"]
    naming = cfg["general"]["naming"]
    click.echo(f"Searching: {query}")
    result = engine.download(query, output_dir, fmt)
    if result and result.file_path:
        final_path = postprocess(Path(result.file_path), artist=result.artist, title=result.title,
                                album=result.album, target_fmt=fmt, naming=naming)
        db.insert_track(artist=result.artist, title=result.title, album=result.album,
                       file_path=str(final_path), source=result.source, quality=result.quality)
        click.echo(f"Downloaded: {final_path.name} (via {result.source})")
    else:
        click.echo("Failed — no source could download this track.", err=True)
        raise SystemExit(1)

@main.command()
@click.argument("playlist", required=False)
@click.option("--tag", is_flag=True, help="Auto-tag after download")
@click.option("--analyze", is_flag=True, help="Auto-analyze after download")
@click.pass_context
def sync(ctx, playlist, tag, analyze):
    """Sync a Spotify playlist to local library."""
    from .sync import sync_playlist
    cfg = ctx.obj["cfg"]
    db = ctx.obj["db"]
    engine = _build_engine(cfg)
    playlist_id = _parse_playlist_id(playlist) if playlist else None
    sync_playlist(cfg, db, engine, playlist_id=playlist_id, tag=tag, analyze=analyze)

@main.command()
@click.argument("file", type=click.Path(exists=True), required=False)
@click.option("--all", "all_tracks", is_flag=True, help="Process entire library")
@click.option("--display", is_flag=True, help="Display synced lyrics in terminal")
@click.pass_context
def lyrics(ctx, file, all_tracks, display):
    """Download and embed synced lyrics for tracks."""
    from pathlib import Path
    from .lyrics import download_lyrics, display_lyrics
    from mutagen import File as MutagenFile

    cfg = ctx.obj["cfg"]
    db = ctx.obj["db"]
    lyrics_cfg = cfg.get("lyrics", {})
    embed = lyrics_cfg.get("embed", True)
    sidecar = lyrics_cfg.get("sidecar_lrc", True)

    def _process(track_path: Path):
        audio = MutagenFile(str(track_path), easy=True)
        artist, title, album = "", "", ""
        if audio and audio.tags:
            artist = (audio.tags.get("artist") or [""])[0]
            title = (audio.tags.get("title") or [""])[0]
            album = (audio.tags.get("album") or [""])[0]
        if not (artist and title) and " - " in track_path.stem:
            parts = track_path.stem.split(" - ", 1)
            artist, title = parts[0].strip(), parts[1].strip()
        lrc_path = download_lyrics(
            track_path, artist=artist, title=title, album=album,
            embed=embed, sidecar_lrc=sidecar,
        )
        if lrc_path:
            click.echo(f"  ✓ {track_path.name}")
            # Update DB if track is known
            row = db.conn.execute(
                "SELECT id FROM tracks WHERE file_path = ?", (str(track_path),)
            ).fetchone()
            if row:
                db.update_track(row[0], lyrics_path=str(lrc_path))
        else:
            click.echo(f"  ✗ {track_path.name} (not found)")

    if display:
        if not file:
            click.echo("--display requires a FILE argument.", err=True)
            raise SystemExit(1)
        lrc = Path(file).with_suffix(".lrc")
        if not lrc.exists():
            click.echo(f"No .lrc sidecar found at {lrc}. Run without --display first.", err=True)
            raise SystemExit(1)
        from .lyrics import display_lyrics
        display_lyrics(lrc)
        return

    if all_tracks:
        music_dir = Path(cfg["general"]["output_dir"])
        exts = (".m4a", ".mp3", ".flac")
        files = [f for f in music_dir.rglob("*") if f.suffix.lower() in exts]
        click.echo(f"Processing {len(files)} tracks in {music_dir}...")
        for f in files:
            _process(f)
    elif file:
        _process(Path(file))
    else:
        click.echo("Provide a FILE or use --all.", err=True)
        raise SystemExit(1)


@main.command()
@click.pass_context
def migrate(ctx):
    """Import existing yt-dlp archive and scan library into database."""
    from .migrate import migrate as run_migrate
    cfg = ctx.obj["cfg"]
    db = ctx.obj["db"]
    music_dir = Path(cfg["general"]["output_dir"])
    click.echo(f"Scanning {music_dir}...")
    run_migrate(db, music_dir)
    click.echo("Migration complete.")

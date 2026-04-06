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

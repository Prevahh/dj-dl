"""Integration tests — require external tools and network.

Run with: pytest tests/test_integration.py -v -m integration
Skip in CI with: pytest -m "not integration"
"""
import tempfile
from pathlib import Path

import pytest

from dj_dl.config import load_config
from dj_dl.db import Database
from dj_dl.download import DownloadEngine
from dj_dl.sources.ytdlp import YtDlpSource
from dj_dl.sources.spotdl import SpotdlSource
from dj_dl.postprocess import postprocess

pytestmark = pytest.mark.integration


@pytest.fixture
def engine():
    return DownloadEngine(sources=[SpotdlSource(), YtDlpSource()])


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


@pytest.mark.skipif(
    not YtDlpSource().available(),
    reason="yt-dlp not installed",
)
def test_download_via_ytdlp(engine, db, tmp_path):
    """Download a short public domain track via yt-dlp."""
    result = engine.download(
        "Kevin MacLeod - Monkeys Spinning Monkeys",
        tmp_path, "m4a",
    )
    assert result is not None
    assert Path(result.file_path).exists()
    assert result.source in ("yt-dlp", "spotdl")

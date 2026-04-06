import tempfile
from pathlib import Path
from dj_dl.download import DownloadEngine
from dj_dl.sources.base import Source, TrackResult

class FakeSourceOk(Source):
    name = "fake-ok"
    def available(self): return True
    def accepts_url(self, url): return False
    def download(self, query, dest_dir, fmt="m4a"):
        fake_file = dest_dir / "Artist - Track.m4a"
        fake_file.write_text("fake audio")
        return TrackResult(artist="Artist", title="Track", file_path=str(fake_file), quality="320k", source=self.name)

class FakeSourceFail(Source):
    name = "fake-fail"
    def available(self): return True
    def accepts_url(self, url): return False
    def download(self, query, dest_dir, fmt="m4a"): return None

class FakeSourceUnavailable(Source):
    name = "fake-unavailable"
    def available(self): return False
    def accepts_url(self, url): return False
    def download(self, query, dest_dir, fmt="m4a"): return None

def test_first_source_succeeds():
    engine = DownloadEngine(sources=[FakeSourceOk(), FakeSourceFail()])
    with tempfile.TemporaryDirectory() as tmp:
        result = engine.download("Artist - Track", Path(tmp))
    assert result is not None
    assert result.source == "fake-ok"

def test_fallback_to_second_source():
    engine = DownloadEngine(sources=[FakeSourceFail(), FakeSourceOk()])
    with tempfile.TemporaryDirectory() as tmp:
        result = engine.download("Artist - Track", Path(tmp))
    assert result is not None
    assert result.source == "fake-ok"

def test_all_sources_fail():
    engine = DownloadEngine(sources=[FakeSourceFail(), FakeSourceFail()])
    with tempfile.TemporaryDirectory() as tmp:
        result = engine.download("Artist - Track", Path(tmp))
    assert result is None

def test_skips_unavailable_sources():
    engine = DownloadEngine(sources=[FakeSourceUnavailable(), FakeSourceOk()])
    with tempfile.TemporaryDirectory() as tmp:
        result = engine.download("Artist - Track", Path(tmp))
    assert result is not None
    assert result.source == "fake-ok"

def test_url_routing():
    url_source = FakeSourceOk()
    url_source.name = "url-handler"
    url_source.accepts_url = lambda url: "youtube.com" in url
    fallback = FakeSourceFail()
    fallback.accepts_url = lambda url: False
    engine = DownloadEngine(sources=[fallback, url_source])
    with tempfile.TemporaryDirectory() as tmp:
        result = engine.download("https://youtube.com/watch?v=abc", Path(tmp))
    assert result is not None
    assert result.source == "url-handler"

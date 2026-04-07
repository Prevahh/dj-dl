"""Download source wrappers."""
from .ytdlp import YtDlpSource
from .spotdl import SpotdlSource
from .onthespot import OnTheSpotSource
from .streamrip import StreamripSource
from .slsk import SlskSource
from .orpheusdl import OrpheusDLSource
from .deemixfix import DeemixFixSource
from .spotiflac import SpotiFLACSource
from .lucida import LucidaSource
from .doubledouble import DoubleDoubleSource

__all__ = [
    "YtDlpSource",
    "SpotdlSource",
    "OnTheSpotSource",
    "StreamripSource",
    "SlskSource",
    "OrpheusDLSource",
    "DeemixFixSource",
    "SpotiFLACSource",
    "LucidaSource",
    "DoubleDoubleSource",
]

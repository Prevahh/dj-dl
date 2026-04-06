# dj-dl

All-in-one DJ track downloader with multi-source fallback chain, metadata tagging, stem separation, and track analysis.

## Install

```bash
pip install -e .
```

## Quick Start

```bash
# Copy and edit config
cp config.example.toml ~/.config/dj-dl/config.toml

# Download a track
dj-dl get "Artist - Track"

# Sync a Spotify playlist
dj-dl sync <spotify-playlist-url>
```

## Sources

Tries sources in priority order until one succeeds:

1. OnTheSpot (Spotify/Deezer/Tidal/Qobuz/Apple Music/Bandcamp)
2. spotdl (Spotify → YouTube match)
3. streamrip (Deezer/Tidal/Qobuz/SoundCloud)
4. OrpheusDL (Deezer/Qobuz)
5. DeemixFix (Deezer)
6. SpotiFLAC (Qobuz/Tidal/Amazon)
7. slsk-batchdl (Soulseek P2P)
8. yt-dlp (YouTube/SoundCloud/Bandcamp/everything)
9. lucida (web ripper)
10. DoubleDouble (web ripper)

## License

MIT

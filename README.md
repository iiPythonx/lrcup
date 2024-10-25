# LRCUP

Python CLI and library for interacting with the [LRCLIB.net API](https://lrclib.net/).  
Also includes tools for embedding lyrics, along with general LRC tools.

## Installation

Install via PyPI:
```sh
pip install lrcup
```

## CLI Usage

```sh
# Upload a synced/unsynced LRC file:
lrcup upload example.lrc

# Upload lyrics from an already embedded track:
lrcup upload file.flac

# Embed lyrics into a file:
lrcup embed lyrics.lrc track.flac

# Search for lyrics and download them:
lrcup search never gonna give you up

# Search and download lyrics for a given folder:
lrcup autosearch /mnt/music/

# Search and embed lyrics for a given folder:
lrcup autosearch --embed /mnt/music/

# Search and embed lyrics for a given folder, also save lrc files:
lrcup autosearch --embed --download /mnt/music/
```

## Module Usage

The class method names are based off of the LRCLIB API endpoints.  
Please refer to them for more information.

```py
from lrcup import LRCLib

lrclib = LRCLib()

# Fetch synced lyrics via search
results = lrclib.search(
    track = "Never Gonna Give You Up",
    artist = "Rick Astley"
)
print(results[0]["syncedLyrics"])

# Fetch synced lyrics directly
track = lrclib.get(
    track = "Never Gonna Give You Up",
    artist = "Rick Astley",
    album = "Whenever You Need Somebody",
    duration = 215
)
if track is not None:
    print(track["syncedLyrics"])

# Publish synced lyrics
lrclib.publish(
    token = lrclib.request_challenge(),
    track = "Never Gonna Give You Up",
    artist = "Rick Astley",
    album = "Whenever You Need Somebody",
    duration = 215,
    plain_lyrics = "*Rickrolling*",
    synced_lyrics = "[00:00.00] *Rickrolling*"
)
```

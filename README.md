# LRCUP

Python CLI and library for interacting with the [LRCLIB.net API](https://lrclib.net/).

## Installation

Install via PyPI:
```sh
pip install lrcup
```

## CLI Usage

```py
# If you have an unsynced/synced LRC file:
lrcup upload example.lrc

# If you have a track with embedded lyrics:
lrcup upload file.flac
```

## Module Usage

The class method names are based off of the LRCLIB API endpoints.  
Please refer to them for more information.

```py
from lrcup import LRCLib

lrclib = LRCLib()

# Example of getting synced lyrics via search
results = lrclib.search(
    track = "Never gonna give you up",
    artist = "Rick Astley"
)
print(results[0]["syncedLyrics"])
```

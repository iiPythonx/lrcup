# Copyright (c) 2024 iiPython

# Modules
import re
import math
from pathlib import Path
from typing import Literal

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.id3._frames import USLT, SYLT

# Initialization
CLASS_MAPPING = {
    ".mp3": MP3, ".flac": FLAC
}
TAG_MAPPING = {
    "TITLE": "TIT2",
    "ALBUM": "TALB",
    "ARTIST": "TPE1",
    "ALBUMARTIST": "TPE2"
}
SYNCED_EXPR = re.compile(r"\[(\d{2}:\d{2}.\d{2})\](.*)")

# Exceptions
class UnsupportedSuffix(ValueError):
    pass

# Audio handler
class AudioFile():
    def __init__(self, path: Path) -> None:
        self.path = path
        if path.suffix not in CLASS_MAPPING:
            raise UnsupportedSuffix(f"Unsupported file extension: '{path.suffix}'!")

        self.file = CLASS_MAPPING[path.suffix](path)
        self.length = self.file.info.length

    def get_tag(self, tag: str) -> str | None:
        if isinstance(self.file, MP3):
            tag = TAG_MAPPING.get(tag, tag)

        if tag in self.file:
            return self.file[tag][0] if isinstance(self.file[tag], list) else self.file[tag]

    def set_tag(self, tag: str, value: str) -> None:
        if isinstance(self.file, MP3):
            tag = TAG_MAPPING.get(tag, tag)

        self.file[tag] = value
        self.file.save()

    def get_lyrics(self, language: str | None = None) -> str | None:
        if isinstance(self.file, FLAC):
            return self.get_tag("LYRICS")

        lyrics = None
        if language is not None:
            lyrics = self.get_tag(f"USLT::{language}") or self.get_tag(f"SYLT::{language}")

        else:

            # Cycle until we find ANY lyrics since we didn't specify
            # a language to look for
            lyrics = [
                value for tag, value in self.file.items()
                if tag[:4] in ["USLT", "SYLT"]
            ]
            lyrics = lyrics[0] if lyrics else None
    
        if isinstance(lyrics, SYLT):
            lyrics = "\n".join([

                # This is absolute garbage and I'll replace it eventually
                f"[{str(math.floor(time / 60000)).zfill(2)}:{str(time / 1000).split('.')[0].zfill(2)}.{str(time / 1000).split('.')[1].zfill(2)}] {text}"
                for (text, time) in lyrics.text  # type: ignore
            ])

        return lyrics

    def set_lyrics(self, state: Literal["synced"] | Literal["unsynced"], lyrics: str | list, language: str = "XXX") -> None:
        if isinstance(self.file, FLAC):
            if isinstance(lyrics, list):
                raise ValueError

            return self.set_tag("LYRICS", lyrics)

        if state == "synced" and isinstance(lyrics, str):
            new_lyrics = []
            for line in lyrics.split("\n"):
                if not line.strip():
                    continue

                time, text = re.findall(SYNCED_EXPR, line)[0]
                new_lyrics.append((text.strip(), int((60000 * int(time[:2])) + (1000 * float(time[3:])))))

            lyrics = new_lyrics

        arguments = {"lang": language, "text": lyrics}
        if state == "synced":
            arguments |= {"format": 2, "type": 1}

        object = {"unsynced": USLT, "synced": SYLT}[state](**arguments)
        self.set_tag(f"{type(object).__name__}::{language}", object)

# Handle lyrics formatting
def format_lyrics(lyrics: str) -> str:
    return "\n".join([
        f"[{time}] {line}" for (time, line) in re.findall(SYNCED_EXPR, lyrics)
    ])

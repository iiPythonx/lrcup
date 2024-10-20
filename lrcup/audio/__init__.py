# Copyright (c) 2024 iiPython

# Modules
import re
import math
from pathlib import Path
from typing import Literal

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3._frames import USLT, SYLT

# Initialization
CLASS_MAPPING = {
    ".mp3": MP3,
    ".flac": FLAC,
    ".m4a": MP4
}

# Tag Mapping based on FileType
TAG_MAPPING = {
    "mp3": {
        "TITLE": "TIT2",
        "ALBUM": "TALB",
        "ARTIST": "TPE1",
        "ALBUMARTIST": "TPE2"
    },
    "m4a": {
        "TITLE": "\xa9nam",
        "ALBUM": "\xa9alb",
        "ARTIST": "\xa9ART",
        "ALBUMARTIST": "aART"
    },
}

# Regular expressions
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

    def __repr__(self) -> str:
        return f"<AudioFile '{self.path}' length={round(self.length)} fields={len(self.file)} />"

    @staticmethod
    def parse_lyrics(lyrics: str) -> list[tuple[str, int]]:
        new_lyrics = []
        for line in lyrics.split("\n"):
            if not line.strip():
                continue

            time, text = re.findall(SYNCED_EXPR, line)[0]
            new_lyrics.append((text.strip(), int((60000 * int(time[:2])) + (1000 * float(time[3:])))))

        return new_lyrics

    @staticmethod
    def dump_lyrics(lyrics: list[tuple[str, int]]) -> str:
        converted = []
        for text, time in lyrics:
            minutes = math.floor(time / 60000)
            seconds = math.floor((time / 1000) - (minutes * 60))
            millisc = time - (minutes * 60000) - (seconds * 1000)
            converted.append(f"[{str(minutes).zfill(2)}:{str(seconds).zfill(2)}.{str(millisc).rstrip('0').ljust(2, '0')}] {text}")

        return "\n".join(converted)

    def get_tag(self, tag: str, as_string: bool = True) -> str | None:
        if isinstance(self.file, MP3):
            tag = TAG_MAPPING["mp3"].get(tag, tag)

        if isinstance(self.file, MP4):
            tag = TAG_MAPPING["m4a"].get(tag, tag)

        if tag in self.file:
            field = self.file[tag]
            return field[0] if isinstance(field, list) else (str(field) if as_string else field)

    def set_tag(self, tag: str, value: str) -> None:
        if isinstance(self.file, MP3):
            tag = TAG_MAPPING["mp3"].get(tag, tag)

        if isinstance(self.file, MP4):
            tag = TAG_MAPPING["m4a"].get(tag, tag)

        self.file[tag] = value
        self.file.save()

    def get_lyrics(self, language: str | None = None) -> str | None:
        if isinstance(self.file, FLAC):
            return self.get_tag("LYRICS")

        if isinstance(self.file, MP4):
            return self.get_tag("\xa9lyr")

        lyrics = None
        if language is not None:
            lyrics = self.get_tag(f"USLT::{language}", False) or self.get_tag(f"SYLT::{language}", False)

        else:

            # Cycle until we find ANY lyrics since we didn't specify
            # a language to look for
            lyrics = [
                value for tag, value in self.file.items()
                if tag[:4] in ["USLT", "SYLT"]
            ]
            lyrics = lyrics[0] if lyrics else None
    
        if isinstance(lyrics, SYLT):
            lyrics = self.dump_lyrics(lyrics.text)  # type: ignore

        return str(lyrics) if lyrics else None

    def set_lyrics(self, state: Literal["synced"] | Literal["unsynced"], lyrics: str | list, language: str = "XXX") -> None:
        if isinstance(self.file, FLAC):
            if isinstance(lyrics, list):
                raise ValueError

            return self.set_tag("LYRICS", lyrics)

        if isinstance(self.file, MP4):
            return self.set_tag("\xa9lyr", lyrics)

        if state == "synced" and isinstance(lyrics, str):
            lyrics = self.parse_lyrics(lyrics)

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

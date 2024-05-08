# Copyright (c) 2024 iiPython

# Modules
import sys
from pathlib import Path

import click
import mutagen

from . import __version__
from .controller import LRCLib

# Initialization
GREEN_FMT = "\033[32m{}\033[0m"

def t(text: str) -> str:
    return f"{text}{' ' * (13 - len(text))}: "

lrclib = LRCLib()

# Input helpers
def update_previous(value: str, prompt: str) -> None:
    print(f"\033[1F\033[2K{prompt}{value}")

def custom_input(prompt: str, value_format: str = None) -> str:
    value = input(prompt)
    if value_format is not None:
        update_previous(value_format.format(value), prompt)

    return value

# Handle CLI
@click.group()
def lrcup() -> None:
    """Basic API wrapper for LRCLIB with a CLI included.

    To get started with the module, visit: https://github.com/iiPythonx/lrcup"""
    pass

@lrcup.command(help = "Upload lyrics to LRCLIB from local file")
@click.argument("filename")
def upload(filename: str) -> None:
    def process_lyrics(lyrics: str) -> (str, str):
        if all([line.startswith("[") for line in lyrics.split("\n") if line.strip()]):
            print(t("LRC Status"), "\033[32msynced\033[0m", sep = "")
            return None, lyrics

        print(t("LRC Status"), "\033[31munsynced\033[0m", sep = "")
        return lyrics, None

    filename = Path(filename).resolve()
    if not filename.is_file():
        return click.secho("Specified filename does not exist.", fg = "red")

    # Load lyrics format
    if filename.suffix in [".txt", ".lrc"]:
        with filename.open() as fh:
            plain_lyrics, synced_lyrics = process_lyrics(fh.read())

    elif filename.suffix in [".mp3", ".flac", ".ogg", ".`m4a"]:
        lyrics = mutagen.File(filename)["lyrics"]
        if not lyrics:
            return print(t("LRC Status"), "\033[31mmissing\033[0m", sep = "")

        plain_lyrics, synced_lyrics = process_lyrics(lyrics)

    else:
        return click.secho(f"Unsupported file extension for file '{filename.name}'.", fg = "red")

    # Ask every question known to man
    track = custom_input(t("Track title"), GREEN_FMT)
    artist = custom_input(t("Artist"), GREEN_FMT)
    album = custom_input(t("Album") + f"({track}) ", GREEN_FMT) or track
    update_previous(GREEN_FMT.format(album), t("Album"))

    # Take care of duration
    duration = custom_input(t("Duration") + "(M:S or S) ", GREEN_FMT)
    if ":" in duration:
        duration = duration.split(":")
        duration = (int(duration[0]) * 60) + int(duration[1])

    else:
        duration = int(duration)

    update_previous(GREEN_FMT.format(f"{duration} second(s)"), t("Duration"))

    # Confirmation
    if "-y" not in sys.argv:
        if input("\nConfirm upload (y/N)? ") not in ["y", "yes"]:
            return

    # Upload to LRCLIB
    success = lrclib.publish(
        lrclib.request_challenge(),
        track,
        artist,
        album,
        duration,
        plain_lyrics,
        synced_lyrics
    )
    if not success:
        return click.secho("\nFailed to upload to LRCLIB.", fg = "red")

    click.secho("\nUploaded to LRCLIB successfully.", fg = "green")

@lrcup.command(help = "Embed an LRC file into an audio file")
@click.argument("lrc")
@click.argument("destination")
def embed(lrc: str, destination: str) -> None:
    file = mutagen.File(destination)
    file["LYRICS"] = Path(lrc).read_text()
    file.save()

@lrcup.command(help = "Search for specific lyrics by query")
@click.argument("query", nargs = -1, required = True)
def search(query: str) -> None:
    results = []
    for i in lrclib.search(" ".join(query)):
        if not (i["plainLyrics"] or i["syncedLyrics"]):
            continue  # Ignore instrumentals

        results.append(i)

    for i, r in enumerate(results):
        click.echo(f"{i + 1}) {r['artistName'].replace(';', ', ')} - {r['trackName']}")

    if not results:
        return click.secho("No search results found.", fg = "red")

    click.echo()
    try:
        download_id = int(input("ID to Download > "))
        if download_id < 1 or download_id > len(results):
            raise ValueError

        result = results[download_id - 1]
        filename = f"{result['trackName']}.lrc"
        with Path(filename).open("w+") as fh:
            fh.write(result["syncedLyrics"] or result["plainLyrics"])
            click.echo(f"Lyrics written to '{filename}'.")

    except ValueError:
        click.secho("Invalid lyric result ID.", fg = "red")

    except KeyboardInterrupt:
        pass

@lrcup.command(help = "Display version information")
def version() -> None:
    click.echo(f"LRCUP v{__version__} (https://github.com/iiPythonx/lrcup)")

if __name__ == "__main__":
    lrcup()

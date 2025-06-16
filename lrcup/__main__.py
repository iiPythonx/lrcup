# Copyright (c) 2024-2025 iiPython

# Modules
import sys
from pathlib import Path

import click

from . import __version__
from .audio import AudioFile, UnsupportedSuffix, CLASS_MAPPING, format_lyrics
from .controller import LRCLib

# Initialization
GREEN_FMT = "\033[32m{}\033[0m"

def t(text: str) -> str:
    return f"{text}{' ' * (13 - len(text))}: "

lrclib = LRCLib()

# Input helpers
def update_previous(value: str, prompt: str) -> None:
    print(f"\033[1F\033[2K{prompt}{value}")

def custom_input(prompt: str, value_format: str | None = None) -> str:
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

def process_lyrics(lyrics: str) -> tuple[str, str | None]:
    if all([line.startswith("[") for line in lyrics.split("\n") if line.strip()]):
        return "\n".join(
            [
                line.split("]")[1].lstrip()
                for line in lyrics.split("\n")
                if line.strip()
            ]
        ), format_lyrics(lyrics)

    return lyrics, None

@lrcup.command(help = "Upload lyrics to LRCLIB from local file")
@click.argument("file", type = click.Path(exists = True, dir_okay = False, path_type = Path))
def upload(file: Path) -> None:
    metadata = None

    # Load lyrics format
    if file.suffix in [".txt", ".lrc"]:
        plain_lyrics, synced_lyrics = process_lyrics(file.read_text(encoding = "utf-8"))
        if synced_lyrics:
            print(t("LRC Status"), "\033[32msynced\033[0m", sep = "")

        else:
            print(t("LRC Status"), "\033[31munsynced\033[0m", sep = "")

    else:
        try:
            metadata = AudioFile(file)
            lyrics = metadata.get_lyrics()
            if not lyrics:
                return print(t("LRC Status"), "\033[31mmissing\033[0m", sep = "")

            plain_lyrics, synced_lyrics = process_lyrics(lyrics)

        except UnsupportedSuffix as e:
            return click.secho(e, fg = "red")

    # Ask every question known to man
    payload = {}
    for field, readable in [("TITLE", "Track title"), ("ARTIST", "Artist"), ("ALBUM", ("Album", "({TITLE}) "))]:
        addition = ""
        if isinstance(readable, tuple):
            readable, addition = readable

        payload[field] = metadata and metadata.get_tag(field)
        if not payload[field]:  # Catch empty fields as well
            payload[field] = custom_input(t(readable) + addition.format(**payload), GREEN_FMT)
            if field == "ALBUM":
                payload[field] = payload[field] or payload["TITLE"]
                update_previous(GREEN_FMT.format(payload[field]), t(readable))

        else:
            print(t(readable), GREEN_FMT.format(payload[field]), sep = "")

    # Take care of duration
    if metadata is None:
        duration = custom_input(t("Duration") + "(M:S or S) ", GREEN_FMT)
        if ":" in duration:
            duration = duration.split(":")
            duration = (int(duration[0]) * 60) + int(duration[1])

        else:
            duration = int(duration)

        update_previous(GREEN_FMT.format(f"{duration} second(s)"), t("Duration"))

    else:
        duration = metadata.length

    # Confirmation
    if "-y" not in sys.argv:
        if input("\nConfirm upload (y/N)? ") not in ["y", "yes"]:
            return

    # Upload to LRCLIB
    success = lrclib.publish(
        lrclib.request_challenge(),
        payload["TITLE"],
        payload["ARTIST"],
        payload["ALBUM"],
        duration,
        plain_lyrics or "",
        synced_lyrics or ""
    )
    if not success:
        return click.secho("\nFailed to upload to LRCLIB.", fg = "red")

    click.secho("\nUploaded to LRCLIB successfully.", fg = "green")

@lrcup.command(help = "Embed an LRC file into an audio file")
@click.argument("lrc", type = click.Path(exists = True, dir_okay = False, path_type = Path))
@click.argument("destination", type = click.Path(exists = True, dir_okay = False, path_type = Path))
def embed(lrc: Path, destination: Path) -> None:
    lyrics = lrc.read_text(encoding = "utf-8")
    AudioFile(destination).set_lyrics("synced" if "[" in lyrics else "unsynced", lyrics)

@lrcup.command(help = "Search for specific lyrics by query")
@click.argument("query", nargs = -1, required = True)
def search(query: str) -> None:
    results = []
    for item in lrclib.search(" ".join(query)):
        if not (item.plainLyrics or item.syncedLyrics):
            continue  # Ignore instrumentals

        results.append(item)

    for index, result in enumerate(results):
        click.echo(f"{index + 1}) {result.artistName.replace(';', ', ')} - {result.trackName}")

    if not results:
        return click.secho("No search results found.", fg = "red")

    click.echo()
    try:
        download_id = int(input("ID to Download > "))
        if download_id < 1 or download_id > len(results):
            raise ValueError

        result = results[download_id - 1]

        output_file = Path(f"{result.trackName}.{'lrc' if result.syncedLyrics else 'txt'}")
        output_file.write_text(result.syncedLyrics or result.plainLyrics)
        click.echo(f"Lyrics written to '{output_file.name}'.")

    except ValueError:
        click.secho("Invalid lyric result ID.", fg = "red")

    except KeyboardInterrupt:
        pass

@lrcup.command(help = "Display version information")
def version() -> None:
    click.echo(f"LRCUP v{__version__} (https://github.com/iiPythonx/lrcup)")

@lrcup.command(help = "Automatically search and download lyrics for a folder")
@click.argument("target", type = click.Path(exists = True, file_okay = False, path_type = Path))
@click.option("--force", is_flag = True, show_default = True, default = False, help = "Force searching for lyrics even when they already exist")
@click.option("--embed", is_flag = True, show_default = True, default = False, help = "Embed the lyrics into the original file, can be chained with --download")
@click.option("--download", is_flag = True, show_default = True, default = False, help = "Download a LRC/TXT file with lyrics in it, can be chained with --embed")
def autosearch(target: Path, force: bool, embed: bool, download: bool) -> None:
    if not (embed or download):
        return click.secho("[-] You must pass --embed or --download, otherwise there's nothing to do.", fg = "red")

    for file in target.rglob("*"):
        if not (file.is_file() and file.suffix in CLASS_MAPPING):
            continue

        try:
            data = AudioFile(file)

            # Handle field validation
            fields = (
                data.get_tag("TITLE"),
                data.get_tag("ALBUMARTIST") or data.get_tag("ARTIST"),
                data.get_tag("ALBUM"),
            )
            if not all(fields):
                print(f"[/] Skipping '{file}' due to missing tags.")
                continue

            artist, album, title = fields

            # Handle force flag
            if (data.get_lyrics() or file.with_suffix(".txt").is_file() or file.with_suffix(".lrc").is_file()) and not force:
                # print(f"[/] Skipping '{file}' because it already has lyrics present.")
                continue

            # Fetch actual lyrics
            result = lrclib.get(*fields, round(data.length))  # pyright: ignore
            if result is None:
                click.secho(f"[-] No lyrics found for '{file}'.", fg = "red")
                continue

            extension = "lrc" if result.syncedLyrics else "txt"
            if not (result.syncedLyrics or result.plainLyrics or "").strip():
                click.secho(f"[-] No lyrics found for '{file}'.", fg = "red")
                continue

            # Handle saving lyrics
            print(f"[+] Saving lyrics for '{file}'")
            if embed:
                data.set_lyrics("synced" if extension == "lrc" else "unsynced", result.syncedLyrics or result.plainLyrics)  # pyright: ignore | Line 215 fixes this.
                click.secho("    .. Saved lyrics to file metadata!", fg = "green")
            
            if download:
                destination = file.with_suffix(f".{extension}")
                destination.write_text(result.syncedLyrics or result.plainLyrics, encoding = "utf-8")  # pyright: ignore | Line 215 fixes this.

                click.secho(f"    .. Saved lyrics to '{destination.name}'!", fg = "green")

        except Exception:
            click.secho(f"[-] Failed to read tags from file '{file}'.", fg = "red")

@lrcup.command(
    help = "Apply a time offset to a specified LRC file or audio file.",
    context_settings = {"ignore_unknown_options": True}
)
@click.argument("target", type = click.Path(exists = True, dir_okay = False, path_type = Path))
@click.argument("offset")
def offset(target: Path, offset: str) -> None:

    # Check offset
    offset_direction = offset[0]
    if offset_direction not in ["+", "-"]:
        return click.secho("Invalid offset specified, must start with + or -.", fg = "red")

    offset, offset_parts = offset[1:], {}
    for timeframe in ["minutes", "seconds"]:
        try:
            split_items = offset.split(timeframe[0])
            if len(split_items) == 1:
                offset_parts[timeframe] = 0
                continue

            offset_parts[timeframe], offset = float(split_items[0]), split_items[1]

        except ValueError:
            return click.secho(f"Invalid offset specified, failed to convert {timeframe} to a float.", fg = "red")

    # Load file content
    try:
        file = AudioFile(target)
        lyrics = file.get_lyrics()
        if lyrics is None:
            return click.secho("Specified audio file does not have lyrics.", fg = "red")

        if "[" not in lyrics:
            return click.secho("Specified file has unsynced lyrics, not synced lyrics.", fg = "red")

    except UnsupportedSuffix:
        file, lyrics = target, target.read_text(encoding = "utf-8")

    lyrics = [
        [time, lyric]
        for lyric, time in AudioFile.parse_lyrics(lyrics)
    ]

    # Perform offset
    offset_int = (offset_parts["minutes"] * 60000) + (offset_parts["seconds"] * 1000) * (1 if offset_direction == "+" else -1)
    if lyrics[0][0] + offset_int < 0:
        return click.secho("Specified offset makes lyrics go out of range.", fg = "red")

    lyrics = [(lyric, int(time + offset_int)) for time, lyric in lyrics]

    # Reconstruct lyrics
    if isinstance(file, AudioFile):
        file.set_lyrics("synced", file.dump_lyrics(lyrics))

    else:
        file.write_text(AudioFile.dump_lyrics(lyrics))

    click.secho("Applied offset successfully.", fg = "green")

if __name__ == "__main__":
    lrcup()

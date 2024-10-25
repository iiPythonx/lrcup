# Copyright (c) 2024 iiPython

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

@lrcup.command(help = "Automatically search and download lyrics for a folder")
@click.argument("target", type = click.Path(exists = True, file_okay = False, path_type = Path))
@click.option("--force", is_flag = True, show_default = True, default = False, help = "Force searching for lyrics")
@click.option("--embed", is_flag = True, show_default = True, default = False, help = "Do not save the downloaded lyrics to a separate file, embed them into the music file")
@click.option("--download", is_flag = True, show_default = True, default = True, help = "Force download lrc file even with embed on")
def autosearch(target: Path, force: bool, embed: bool, download: bool) -> None:
    for file in target.rglob("*"):
        if not (file.is_file() and file.suffix in CLASS_MAPPING):
            continue

        lrcfile = file.with_suffix(".lrc")
        try:
            data = AudioFile(file)
            artist, album, title = (
                data.get_tag("ALBUMARTIST") or data.get_tag("ARTIST"),
                data.get_tag("ALBUM"),
                data.get_tag("TITLE"),
            )

            # Check if we already have lyrics from somwhere
            has_embedded = data.get_lyrics()
            has_lrcfile = lrcfile.is_file()

            # I would use all() here but Ruff won't stop complaining
            if not (artist and album and title):
                click.secho(f"[/] Skipping {file} due to missing tags.", fg = "yellow")
                continue

            synced, lyrics = False, None
            if not force:
                if download and has_embedded and not has_lrcfile:
                    click.secho(f"[/] Extracting {title} on {album} by {artist} from '{file.name}' to '{lrcfile.name}'")
                    lyrics = data.get_lyrics()

                elif embed and not has_embedded and has_lrcfile:
                    click.secho(f"[/] Embedding lyrics to '{file.name}' {title} on {album} by {artist} from '{lrcfile.name}'")
                    lyrics = lrcfile.read_text(encoding = "utf-8")

                if lyrics:
                    plain_lyrics, synced_lyrics = process_lyrics(lyrics)
                    synced, lyrics = synced_lyrics is not None, synced_lyrics or plain_lyrics

                # Skip file if we have what we want
                if (not embed or has_embedded) and (not download or has_lrcfile):
                    click.secho(f"[/] Skipping {title} on {album} by {artist}, lyrics already exist.", fg = "yellow")
                    continue

            # Perform lyrics search
            if not lyrics:
                if embed and download:
                    click.echo(f"[/] Fetching .lrc '{lrcfile.name}' and embedding lyrics to '{file.name}' for {title} on {album} by {artist}")

                elif embed:
                    click.echo(f"[/] Embedding lyrics to '{file.name}' for {title} on {album} by {artist}")

                else:
                    click.echo(f"[/] Fetching .lrc '{lrcfile.name}' for {title} on {album} by {artist}")

                results = lrclib.get(title, artist, album, round(data.length))
                if not results:
                    click.secho(
                        f"[-] No results found for {title} on {album} by {artist}",
                        fg = "red"
                    )
                    continue

                lyrics = (results.get("syncedLyrics") or results.get("plainLyrics")) or ""
                if not lyrics.strip():
                    click.secho(
                        f"[-] No results found for {title} on {album} by {artist}",
                        fg = "red"
                    )
                    continue

            if embed and (not has_embedded or force):
                data.set_lyrics("synced" if synced else "unsynced", lyrics)

            if download and (not has_lrcfile or force):
                lrcfile.write_text(lyrics, encoding = "utf-8")

            success_msg = f"[+] Fetched lyrics for {title} on {album} by {artist}. "
            if embed and download:
                success_msg += f"Embedded lyrics to '{file.name}' and wrote .lrc file '{lrcfile.name}'"

            elif embed:
                success_msg += f"Embedded lryics to '{file.name}'"

            else:
                success_msg += f"Wrote lyrics to .lrc file '{lrcfile.name}'"

            click.secho(success_msg, fg = "green")

        except Exception:
            click.secho(f"[-] Failed to read tags from file '{file}'", fg = "red")

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

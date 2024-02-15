# Copyright (c) 2024 iiPython

# Modules
import sys
from pathlib import Path

from .controller import LRCLib

# Initialization
GREEN_FMT = "\033[32m{}\033[0m"

def t(text: str) -> str:
    return f"{text}{' ' * (13 - len(text))}: "

# Handle entrypoint
def main() -> None:
    lrclib = LRCLib()

    # Handle argument parsing
    argv = sys.argv[1:]
    if not argv:
        exit("usage: lrcup upload/search")

    elif argv[0] in ["up", "upload"]:
        if not argv[1]:
            exit("usage: lrcup upload <lrc file>")

        # Load LRC file
        lrc_file = Path(argv[1])
        if not lrc_file.is_file():
            exit("lrcup: specified lrc file does not exist")

        plain_lyrics, synced_lyrics = "", ""
        with lrc_file.open() as fh:
            lrc_raw = fh.read()
            if all([line.startswith("[") for line in fh.readlines() if line.strip()]):
                synced_lyrics = lrc_raw
                print("LRC status   : \033[32msynced\033[0m")

            else:
                plain_lyrics = lrc_raw
                print("LRC status   : \033[31munsynced\033[0m")

        def update_previous(value: str, prompt: str) -> None:
            print(f"\033[1F\033[2K{prompt}{value}")

        def custom_input(prompt: str, value_format: str = None) -> str:
            value = input(prompt)
            if value_format is not None:
                update_previous(value_format.format(value), prompt)

            return value

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
                exit()

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
            exit("\nFailed to upload to LRCLIB.")

        exit("\nUploaded to LRCLIB successfully.")

    elif argv[0] in ["s", "search"]:
        results = []
        for i in lrclib.search(" ".join(argv[1:])):
            if not (i["plainLyrics"] or i["syncedLyrics"]):
                continue  # Ignore instrumentals

            results.append(i)

        for i, r in enumerate(results):
            print(f"{i + 1}) {r['artistName'].replace(';', ', ')} - {r['trackName']}")

        if not results:
            exit("lrcup: no search results")

        print()
        try:
            download_id = int(input("ID to Download > "))
            if download_id < 1 or download_id > len(results):
                raise ValueError

            result = results[download_id - 1]
            filename = f"{result['trackName']}.lrc"
            with Path(filename).open("w+") as fh:
                fh.write(result["syncedLyrics"] or result["plainLyrics"])
                print(f"Lyrics written to '{filename}'.")

        except ValueError:
            exit("Invalid lyric result ID.")

        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()

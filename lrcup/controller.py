# Copyright (c) 2024 iiPython

# Modules
import hashlib
from typing import Any, List, Dict

import requests

from . import __version__

# API Controller
class LRCLib():
    def __init__(self, api_url: str = "https://lrclib.net/api/") -> None:
        self.api_url = api_url
        if not self.api_url.endswith("/"):
            self.api_url += "/"

    def request(self, method: str, endpoint: str, headers: dict = {}, **kwargs) -> requests.Response:
        headers = {
            "User-Agent": f"LRCUP v{__version__} (https://github.com/iiPythonx/lrcup)",
            **headers
        }
        return getattr(requests, method)(
            self.api_url + endpoint,
            headers = headers,
            **kwargs
        )

    def request_with_404(self, *args, **kwargs) -> dict | list | None:
        resp = self.request(*args, **kwargs).json()
        return None if resp.get("statusCode", 200) == 404 else resp

    def search(
        self,
        query: str = None,
        track: str = None,
        artist: str = None,
        album: str = None
    ) -> List[Dict[str, Any]]:
        return self.request("get", "search", params = {
            "q": query,
            "track_name": track,
            "artist_name": artist,
            "album_name": album
        }).json()
    
    def get(
        self,
        track: str,
        artist: str,
        album: str,
        duration: int
    ) -> dict | None:
        return self.request_with_404("get", "get", params = {
            "track_name": track,
            "artist_name": artist,
            "album_name": album,
            "duration": duration
        })

    def get_cached(
        self,
        track: str,
        artist: str,
        album: str,
        duration: int
    ) -> dict | None:
        return self.request_with_404("get", "get-cached", params = {
            "track_name": track,
            "artist_name": artist,
            "album_name": album,
            "duration": duration
        })

    def get_by_id(self, id_: int) -> dict | None:
        return self.request_with_404("get", f"get/{id_}")

    def publish(
        self,
        token: str,
        track: str,
        artist: str,
        album: str,
        duration: int,
        plain_lyrics: str = "",
        synced_lyrics: str = ""
    ) -> bool:
        return self.request(
            "post",
            "publish",
            headers = {"X-Publish-Token": token},
            json = {
                "trackName": track,
                "artistName": artist,
                "albumName": album,
                "duration": duration,
                "plainLyrics": plain_lyrics,
                "syncedLyrics": synced_lyrics
            }
        ).status_code == 201

    def request_challenge(self) -> str:
        data = self.request("post", "request-challenge").json()

        def verify_nonce(result, target) -> bool:
            result_len = len(result)
            if result_len != len(target):
                return False

            for i in range(result_len - 1):
                if result[i] > target[i]:
                    return False

                elif result[i] < target[i]:
                    break

            return True

        def solve_challenge(prefix: str, target: str) -> int:
            nonce, target = 0, bytes.fromhex(target)
            while True:
                if verify_nonce(
                    hashlib.sha256(f"{prefix}{nonce}".encode()).digest(),
                    target
                ):
                    break

                else:
                    nonce += 1

            return nonce

        nonce = solve_challenge(data["prefix"], data["target"])
        return f"{data['prefix']}:{nonce}"

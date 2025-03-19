# Copyright (c) 2024 iiPython

# Modules
import typing

import requests
from pydantic import BaseModel

from . import __version__
from .challenge import solve

# Models
class Track(BaseModel):
    id:             int
    trackName:      str
    artistName:     str
    albumName:      str
    duration:       int | float
    instrumental:   bool
    plainLyrics:    str | None
    syncedLyrics:   str | None

# API Controller
class LRCLib:
    def __init__(self, api_url: str = "https://lrclib.net/api/") -> None:
        self.session = requests.Session()
        self.api_url = f"{api_url.rstrip('/')}/"

    def _request(self, method: str, endpoint: str, headers: dict = {}, **kwargs) -> requests.Response:
        headers = {
            "User-Agent": f"LRCUP v{__version__} (https://github.com/iiPythonx/lrcup)",
            **headers
        }
        return getattr(self.session, method)(
            self.api_url + endpoint,
            headers = headers,
            **kwargs
        )

    def get(
        self,
        track: str,
        artist: str,
        album: str,
        duration: int
    ) -> Track | None:
        response = self._request("get", "get", params = {
            "track_name": track,
            "artist_name": artist,
            "album_name": album,
            "duration": duration
        }).json()
        if response.get("statusCode", 200) == 404:
            return None

        return Track(**response)

    def get_by_id(self, record_id: int) -> Track | None:
        response = self._request("get", f"get/{record_id}").json()
        if response.get("statusCode", 200) == 404:
            return None

        return Track(**response)

    def search(
        self,
        query: typing.Optional[str] = None,
        track: typing.Optional[str] = None,
        artist: typing.Optional[str] = None,
        album: typing.Optional[str] = None
    ) -> list[Track]:
        if not (query or track):
            raise ValueError("Either query or track must be specified! Please see https://lrclib.net/docs.")

        return [
            Track(**record)
            for record in self._request("get", "search", params = {
                "q": query,
                "track_name": track,
                "artist_name": artist,
                "album_name": album
            }).json()
        ]

    def publish(
        self,
        token: str,
        track: str,
        artist: str,
        album: str,
        duration: int,
        plain_lyrics: typing.Optional[str] = "",
        synced_lyrics: typing.Optional[str] = ""
    ) -> bool:
        return self._request(
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
        data = self._request("post", "request-challenge").json()
        return f"{data['prefix']}:{solve(data['prefix'], data['target'])}"

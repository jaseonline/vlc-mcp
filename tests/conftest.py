import json
import os

import pytest

# main.py exits at import time without ROOT_VIDEO_FOLDER, so set it before anything imports the module
os.environ.setdefault("ROOT_VIDEO_FOLDER", os.path.dirname(__file__))

from vlc_mcp import main


class FakeResponse:
    """Stands in for requests.Response with just the attributes main.py reads."""

    def __init__(self, payload=None, content: bytes | None = None, headers: dict | None = None):
        if content is None:
            content = json.dumps(payload if payload is not None else {}).encode("utf-8")
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.headers = headers or {}


class FakeVLC:
    """Records every request and answers from a path -> response map, so no real VLC is needed."""

    def __init__(self):
        self.calls: list[tuple[str, dict | None]] = []
        self.responses: dict[str, FakeResponse] = {}
        self.error: Exception | None = None

    async def get(self, path, params=None):
        self.calls.append((path, params))
        if self.error is not None:
            raise self.error
        return self.responses.get(path, FakeResponse({}))

    def commands(self) -> list[dict]:
        """The query dicts of every status.xml command sent, in order."""
        return [params for path, params in self.calls if path == "/requests/status.xml"]


@pytest.fixture
def vlc(monkeypatch):
    fake = FakeVLC()
    monkeypatch.setattr(main, "vlc_get", fake.get)
    return fake


@pytest.fixture
def media_root(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT_VIDEO_FOLDER", str(tmp_path))
    return tmp_path

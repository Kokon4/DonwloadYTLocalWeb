"""Ayudantes compartidos por los tests: hablan con la app solo a través de la API HTTP."""

import time
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from tests.fakes import SONG, FakeVideoSource, PausePoint


def wait_for(
    client: TestClient, download_id: int, done: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    """Consulta la Descarga (como hace la web) hasta que cumpla la condición."""
    deadline = time.monotonic() + 5
    while True:
        body: dict[str, Any] = client.get(f"/api/downloads/{download_id}").json()
        if done(body):
            return body
        assert time.monotonic() < deadline, f"la Descarga no llegó al estado esperado: {body}"
        time.sleep(0.01)


def in_state(state: str) -> Callable[[dict[str, Any]], bool]:
    return lambda d: d["state"] == state


def create_download(client: TestClient, option_id: str = "mp3-192") -> dict[str, Any]:
    response = client.post(
        "/api/downloads", json={"video_id": "dQw4w9WgXcQ", "quality_option_id": option_id}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def paused_at(point: PausePoint) -> FakeVideoSource:
    return FakeVideoSource({"dQw4w9WgXcQ": SONG}, pause_at=point)


def cancel(client: TestClient, download: dict[str, Any]) -> Response:
    response: Response = client.post(f"/api/downloads/{download['id']}/cancel")
    return response


def retry(client: TestClient, download: dict[str, Any]) -> Response:
    response: Response = client.post(f"/api/downloads/{download['id']}/retry")
    return response

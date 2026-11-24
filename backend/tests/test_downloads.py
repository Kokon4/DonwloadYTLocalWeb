import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi.testclient import TestClient

from tests.conftest import MakeClient
from tests.fakes import (
    SONG,
    FakeVideoSource,
    PausePoint,
    fake_mp3_bytes,
    fake_mp4_bytes,
    videoclip,
)


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


def test_mp3_download_is_created_becomes_ready_and_delivers_the_file(
    make_client: MakeClient,
) -> None:
    client = make_client()

    download = create_download(client)

    assert download["video_id"] == "dQw4w9WgXcQ"
    assert download["title"] == "Artista - Canción (Official Video)"
    assert download["quality_option"] == {"id": "mp3-192", "label": "MP3 · Alta (192 kbps)"}
    assert download["error_message"] is None

    ready = wait_for(client, download["id"], in_state("ready"))
    assert ready["file_available"] is True

    file = client.get(f"/api/downloads/{download['id']}/file")
    assert file.status_code == 200
    assert file.content == fake_mp3_bytes("dQw4w9WgXcQ", 192)
    # El nombre va codificado (RFC 5987) porque lleva caracteres no ASCII; el navegador lo decodifica.
    disposition = file.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert unquote(disposition.split("filename*=utf-8''")[1]) == "Artista - Canción (Official Video).mp3"


def test_new_download_is_pending_until_it_starts(make_client: MakeClient) -> None:
    source = paused_at("start")
    client = make_client(source)

    download = create_download(client)

    assert download["state"] == "pending"
    assert client.get(f"/api/downloads/{download['id']}").json()["state"] == "pending"
    source.release()
    wait_for(client, download["id"], in_state("ready"))


def test_progress_is_visible_while_downloading(make_client: MakeClient) -> None:
    source = paused_at("downloading")
    client = make_client(source)

    download = create_download(client)
    downloading = wait_for(client, download["id"], in_state("downloading"))

    assert downloading["progress"] == 40.0
    assert downloading["file_available"] is False
    source.release()
    wait_for(client, download["id"], in_state("ready"))


def test_download_goes_through_converting_before_ready(make_client: MakeClient) -> None:
    source = paused_at("converting")
    client = make_client(source)

    download = create_download(client)
    converting = wait_for(client, download["id"], in_state("converting"))

    assert converting["progress"] is None
    assert converting["file_available"] is False
    source.release()
    ready = wait_for(client, download["id"], in_state("ready"))
    assert ready["progress"] is None


def test_download_never_goes_back_to_an_earlier_state(make_client: MakeClient) -> None:
    source = FakeVideoSource(
        {"dQw4w9WgXcQ": SONG}, pause_at="converting", late_events=[("downloading", 90.0)]
    )
    client = make_client(source)

    download = create_download(client)
    wait_for(client, download["id"], in_state("converting"))

    assert client.get(f"/api/downloads/{download['id']}").json()["state"] == "converting"
    source.release()
    wait_for(client, download["id"], in_state("ready"))


def test_file_is_deleted_from_the_server_once_collected(
    make_client: MakeClient, tmp_path: Path
) -> None:
    client = make_client()
    download = create_download(client)
    wait_for(client, download["id"], in_state("ready"))

    assert client.get(f"/api/downloads/{download['id']}/file").status_code == 200

    assert list(tmp_path.rglob("*.mp3")) == []
    assert client.get(f"/api/downloads/{download['id']}").json()["file_available"] is False
    second = client.get(f"/api/downloads/{download['id']}/file")
    assert (second.status_code, second.json()) == (410, {"code": "file_already_collected"})


def test_file_cannot_be_collected_before_the_download_is_ready(make_client: MakeClient) -> None:
    source = paused_at("downloading")
    client = make_client(source)
    download = create_download(client)

    response = client.get(f"/api/downloads/{download['id']}/file")

    assert (response.status_code, response.json()) == (409, {"code": "download_not_ready"})
    source.release()


def test_downloads_are_listed_newest_first(make_client: MakeClient) -> None:
    client = make_client()
    first = create_download(client, "mp3-192")
    second = create_download(client, "mp3-128")

    listed = client.get("/api/downloads").json()

    assert [d["id"] for d in listed] == [second["id"], first["id"]]


def test_mp3_light_option_produces_a_128_kbps_file(make_client: MakeClient) -> None:
    client = make_client()
    download = create_download(client, "mp3-128")
    wait_for(client, download["id"], in_state("ready"))

    file = client.get(f"/api/downloads/{download['id']}/file")

    assert file.content == fake_mp3_bytes("dQw4w9WgXcQ", 128)


def test_unknown_quality_option_is_rejected(make_client: MakeClient) -> None:
    response = make_client().post(
        "/api/downloads", json={"video_id": "dQw4w9WgXcQ", "quality_option_id": "mp3-999"}
    )

    assert (response.status_code, response.json()) == (422, {"code": "unknown_quality_option"})


def test_unknown_download_is_not_found(make_client: MakeClient) -> None:
    client = make_client()

    for path in ("/api/downloads/999", "/api/downloads/999/file"):
        response = client.get(path)
        assert (response.status_code, response.json()) == (404, {"code": "download_not_found"})


def test_failure_while_fetching_leaves_the_download_failed(make_client: MakeClient) -> None:
    source = FakeVideoSource({"dQw4w9WgXcQ": SONG}, fetch_error=RuntimeError("ffmpeg falló"))
    client = make_client(source)

    failed = wait_for(client, create_download(client)["id"], in_state("failed"))

    assert failed["error_message"]
    assert failed["file_available"] is False


def test_mp4_download_delivers_an_mp4_file_at_the_chosen_resolution(make_client: MakeClient) -> None:
    client = make_client(FakeVideoSource({"dQw4w9WgXcQ": videoclip(1080, 720)}))

    download = create_download(client, "mp4-720")
    assert download["quality_option"] == {"id": "mp4-720", "label": "MP4 · 720p"}
    wait_for(client, download["id"], in_state("ready"))

    file = client.get(f"/api/downloads/{download['id']}/file")

    assert file.content == fake_mp4_bytes("dQw4w9WgXcQ", 720)
    assert unquote(file.headers["content-disposition"]).endswith(".mp4")


def test_mp4_option_the_video_does_not_have_is_rejected(make_client: MakeClient) -> None:
    # SONG no tiene ninguna altura en H.264: no hay Opciones MP4.
    response = make_client().post(
        "/api/downloads", json={"video_id": "dQw4w9WgXcQ", "quality_option_id": "mp4-1080"}
    )

    assert (response.status_code, response.json()) == (422, {"code": "unknown_quality_option"})

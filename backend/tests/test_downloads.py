import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.video_source import VideoSourceError, VideoUnavailableError
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
    assert download["failure_code"] is None

    ready = wait_for(client, download["id"], in_state("ready"))
    assert ready["file_available"] is True

    file = client.get(f"/api/downloads/{download['id']}/file")
    assert file.status_code == 200
    assert file.content == fake_mp3_bytes("dQw4w9WgXcQ", 192)
    # El nombre va codificado (RFC 5987) porque lleva caracteres no ASCII; el navegador lo decodifica.
    disposition = file.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert unquote(disposition.split("filename*=utf-8''")[1]) == "Artista - Canción (Official Video).mp3"


def test_download_is_downloading_as_soon_as_it_gets_its_turn(make_client: MakeClient) -> None:
    # Pendiente significa "esperando turno": en cuanto arranca pasa a Descargando,
    # aunque todavía no se conozca el porcentaje.
    source = paused_at("start")
    client = make_client(source)

    download = create_download(client)
    started = wait_for(client, download["id"], in_state("downloading"))

    assert started["progress"] is None
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

    assert failed["failure_code"] == "unexpected_error"
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



@contextmanager
def five_downloads_three_running(
    make_client: MakeClient, fetch_error: Exception | None = None
) -> Iterator[tuple[TestClient, FakeVideoSource, list[dict[str, Any]]]]:
    """Crea 5 Descargas con la Fuente falsa parada en Descargando y espera a que 3 avancen.

    Al salir libera siempre todas las obtenciones, aunque el test falle, para no dejar
    hilos esperando.
    """
    source = FakeVideoSource({"dQw4w9WgXcQ": SONG}, pause_at="downloading", fetch_error=fetch_error)
    client = make_client(source)
    try:
        downloads = [create_download(client) for _ in range(5)]
        for running in downloads[:3]:
            wait_for(client, running["id"], in_state("downloading"))
        yield client, source, downloads
    finally:
        source.release(5)


def states(client: TestClient, downloads: list[dict[str, Any]]) -> list[str]:
    """Estado actual de cada Descarga, en el mismo orden."""
    return [client.get(f"/api/downloads/{d['id']}").json()["state"] for d in downloads]


def test_at_most_three_downloads_run_at_the_same_time(make_client: MakeClient) -> None:
    with five_downloads_three_running(make_client) as (client, _, downloads):
        time.sleep(0.1)  # margen por si una cuarta arrancara indebidamente

        assert states(client, downloads) == ["downloading"] * 3 + ["pending"] * 2


def test_oldest_pending_download_starts_when_a_running_one_finishes(
    make_client: MakeClient,
) -> None:
    with five_downloads_three_running(make_client) as (client, source, downloads):
        source.release()  # termina una de las tres en curso
        wait_for(client, downloads[3]["id"], in_state("downloading"))

        current = states(client, downloads)
        assert current[:3].count("ready") == 1
        assert current[:3].count("downloading") == 2
        assert current[3:] == ["downloading", "pending"]


def test_failed_download_also_frees_its_slot(make_client: MakeClient) -> None:
    error = RuntimeError("ffmpeg falló")
    with five_downloads_three_running(make_client, fetch_error=error) as (client, source, downloads):
        source.release()  # una de las tres en curso falla
        wait_for(client, downloads[3]["id"], in_state("downloading"))

        current = states(client, downloads)
        assert current[:3].count("failed") == 1
        assert current[3:] == ["downloading", "pending"]


def cancel(client: TestClient, download: dict[str, Any]) -> Response:
    response: Response = client.post(f"/api/downloads/{download['id']}/cancel")
    return response


def test_cancelling_a_pending_download_means_it_never_starts(
    make_client: MakeClient, tmp_path: Path
) -> None:
    with five_downloads_three_running(make_client) as (client, source, downloads):
        cancelled = cancel(client, downloads[3])
        assert (cancelled.status_code, cancelled.json()["state"]) == (200, "cancelled")

        source.release()  # termina una de las tres en curso: le toca a la 5.ª, no a la 4.ª
        wait_for(client, downloads[4]["id"], in_state("downloading"))
        assert states(client, downloads)[3] == "cancelled"

        # Cuando todas las demás terminan y se recogen, no queda ningún archivo: la
        # cancelada no llegó a descargar nada.
        source.release(4)
        for other in downloads[:3] + downloads[4:]:
            wait_for(client, other["id"], in_state("ready"))
            client.get(f"/api/downloads/{other['id']}/file")
        assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


@pytest.mark.parametrize("point", ["start", "downloading"])
def test_cancelling_a_running_download_stops_it_and_deletes_partial_files(
    make_client: MakeClient, tmp_path: Path, point: PausePoint
) -> None:
    source = paused_at(point)
    client = make_client(source)
    download = create_download(client)
    wait_for(client, download["id"], lambda d: d["state"] != "pending")

    response = cancel(client, download)

    assert (response.status_code, response.json()["state"]) == (200, "cancelled")
    wait_for(client, download["id"], lambda d: not any(tmp_path.rglob("*")))
    assert client.get(f"/api/downloads/{download['id']}").json()["state"] == "cancelled"
    file = client.get(f"/api/downloads/{download['id']}/file")
    assert (file.status_code, file.json()) == (409, {"code": "download_not_ready"})


def test_cancelling_while_converting_waits_for_the_step_and_then_discards_the_result(
    make_client: MakeClient, tmp_path: Path
) -> None:
    source = paused_at("converting")
    client = make_client(source)
    download = create_download(client)
    wait_for(client, download["id"], in_state("converting"))

    response = cancel(client, download)

    # Para el usuario está Cancelada al momento, aunque ffmpeg termine su paso.
    assert (response.status_code, response.json()["state"]) == (200, "cancelled")
    source.release()  # termina la conversión
    wait_for(client, download["id"], lambda d: not any(tmp_path.rglob("*")))
    assert client.get(f"/api/downloads/{download['id']}").json()["state"] == "cancelled"
    file = client.get(f"/api/downloads/{download['id']}/file")
    assert (file.status_code, file.json()) == (409, {"code": "download_not_ready"})


def test_cancelling_a_running_download_frees_its_slot(make_client: MakeClient) -> None:
    with five_downloads_three_running(make_client) as (client, _, downloads):
        cancel(client, downloads[0])

        wait_for(client, downloads[3]["id"], in_state("downloading"))
        assert states(client, downloads)[4] == "pending"


def test_finished_downloads_cannot_be_cancelled(make_client: MakeClient) -> None:
    client = make_client()
    ready = create_download(client)
    wait_for(client, ready["id"], in_state("ready"))
    failing = make_client(
        FakeVideoSource({"dQw4w9WgXcQ": SONG}, fetch_error=RuntimeError("ffmpeg falló"))
    )
    failed = create_download(failing)
    wait_for(failing, failed["id"], in_state("failed"))

    for owner, download in ((client, ready), (failing, failed)):
        response = cancel(owner, download)
        assert (response.status_code, response.json()) == (409, {"code": "download_not_cancellable"})

    cancelled = create_download(client)
    cancel(client, cancelled)
    again = cancel(client, cancelled)
    assert (again.status_code, again.json()) == (409, {"code": "download_not_cancellable"})


def test_cancelling_an_unknown_download_is_not_found(make_client: MakeClient) -> None:
    response = make_client().post("/api/downloads/999/cancel")

    assert (response.status_code, response.json()) == (404, {"code": "download_not_found"})


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (VideoUnavailableError("Private video"), "video_unavailable"),
        (VideoSourceError("unable to extract"), "source_failed"),
        (RuntimeError("ffmpeg: No space left on device"), "unexpected_error"),
    ],
)
@pytest.mark.parametrize("fail_at", ["downloading", "converting"])
def test_failed_download_tells_why_it_failed(
    make_client: MakeClient,
    error: Exception,
    code: str,
    fail_at: Literal["downloading", "converting"],
) -> None:
    source = FakeVideoSource({"dQw4w9WgXcQ": SONG}, fetch_error=error, fail_at=fail_at)
    client = make_client(source)

    failed = wait_for(client, create_download(client)["id"], in_state("failed"))

    assert failed["failure_code"] == code
    assert failed["file_available"] is False


def retry(client: TestClient, download: dict[str, Any]) -> Response:
    response: Response = client.post(f"/api/downloads/{download['id']}/retry")
    return response


def test_retrying_a_failed_download_creates_a_new_one_that_can_succeed(
    make_client: MakeClient,
) -> None:
    source = FakeVideoSource(
        {"dQw4w9WgXcQ": SONG}, fetch_error=VideoSourceError("corte de red"), fetch_error_times=1
    )
    client = make_client(source)
    original = wait_for(client, create_download(client, "mp3-128")["id"], in_state("failed"))

    response = retry(client, original)

    assert response.status_code == 201
    new = response.json()
    assert new["id"] != original["id"]
    assert (new["video_id"], new["title"], new["quality_option"]) == (
        original["video_id"],
        original["title"],
        original["quality_option"],
    )
    assert new["failure_code"] is None
    wait_for(client, new["id"], in_state("ready"))
    assert client.get(f"/api/downloads/{original['id']}").json() == original


def test_retrying_a_cancelled_download_creates_a_new_one(make_client: MakeClient) -> None:
    source = paused_at("downloading")
    client = make_client(source)
    original = create_download(client)
    cancel(client, original)

    response = retry(client, original)

    assert response.status_code == 201
    source.release()
    wait_for(client, response.json()["id"], in_state("ready"))
    assert client.get(f"/api/downloads/{original['id']}").json()["state"] == "cancelled"


def test_only_failed_or_cancelled_downloads_can_be_retried(make_client: MakeClient) -> None:
    with five_downloads_three_running(make_client) as (client, source, downloads):
        running, pending = downloads[0], downloads[4]
        for download in (running, pending):
            response = retry(client, download)
            assert (response.status_code, response.json()) == (409, {"code": "download_not_retryable"})

        source.release(5)
        wait_for(client, running["id"], in_state("ready"))
        response = retry(client, running)
        assert (response.status_code, response.json()) == (409, {"code": "download_not_retryable"})


def test_retrying_an_unknown_download_is_not_found(make_client: MakeClient) -> None:
    response = make_client().post("/api/downloads/999/retry")

    assert (response.status_code, response.json()) == (404, {"code": "download_not_found"})

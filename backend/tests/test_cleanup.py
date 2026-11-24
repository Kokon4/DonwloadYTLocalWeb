"""Limpieza de temporales y caducidad (ver ADR 0001 y el ticket #9).

Una Descarga desaparece de la lista 1 hora después de que ya no le quede nada pendiente:
al terminar (Fallida, Cancelada) o cuando su archivo deja de estar disponible (recogido o
caducado). Un archivo Listo que nadie recoge caduca a la hora.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import MakeClient
from tests.fakes import SONG, FakeClock, FakeVideoSource
from tests.helpers import cancel, create_download, in_state, paused_at, wait_for


def files_in(directory: Path) -> list[Path]:
    return [p for p in directory.rglob("*") if p.is_file()]


def listed_ids(client: TestClient) -> list[int]:
    return [d["id"] for d in client.get("/api/downloads").json()]


def test_uncollected_file_expires_after_one_hour(
    make_client: MakeClient, clock: FakeClock, tmp_path: Path
) -> None:
    client = make_client()
    download = wait_for(client, create_download(client)["id"], in_state("ready"))

    clock.advance(minutes=59)
    assert client.get(f"/api/downloads/{download['id']}").json()["file_available"] is True

    clock.advance(minutes=1)
    expired = client.get(f"/api/downloads/{download['id']}").json()
    assert (expired["state"], expired["file_available"]) == ("ready", False)
    file = client.get(f"/api/downloads/{download['id']}/file")
    assert (file.status_code, file.json()) == (410, {"code": "file_already_collected"})
    assert files_in(tmp_path) == []


def test_expired_download_leaves_the_list_one_hour_after_its_file_expired(
    make_client: MakeClient, clock: FakeClock
) -> None:
    client = make_client()
    download = wait_for(client, create_download(client)["id"], in_state("ready"))

    clock.advance(minutes=60)  # caduca el archivo
    clock.advance(minutes=59)
    assert listed_ids(client) == [download["id"]]

    clock.advance(minutes=1)
    assert listed_ids(client) == []
    response = client.get(f"/api/downloads/{download['id']}")
    assert (response.status_code, response.json()) == (404, {"code": "download_not_found"})


def test_collected_download_leaves_the_list_one_hour_after_collection(
    make_client: MakeClient, clock: FakeClock
) -> None:
    client = make_client()
    download = wait_for(client, create_download(client)["id"], in_state("ready"))
    clock.advance(minutes=30)
    client.get(f"/api/downloads/{download['id']}/file")

    clock.advance(minutes=59)
    assert listed_ids(client) == [download["id"]]

    clock.advance(minutes=1)
    assert listed_ids(client) == []


def test_failed_download_leaves_the_list_one_hour_after_failing(
    make_client: MakeClient, clock: FakeClock
) -> None:
    client = make_client(
        FakeVideoSource({"dQw4w9WgXcQ": SONG}, fetch_error=RuntimeError("ffmpeg falló"))
    )
    download = wait_for(client, create_download(client)["id"], in_state("failed"))

    clock.advance(minutes=59)
    assert listed_ids(client) == [download["id"]]
    clock.advance(minutes=1)
    assert listed_ids(client) == []


def test_cancelled_download_leaves_the_list_one_hour_after_cancelling(
    make_client: MakeClient, clock: FakeClock
) -> None:
    source = paused_at("downloading")
    client = make_client(source)
    download = create_download(client)
    cancel(client, download)

    clock.advance(minutes=59)
    assert listed_ids(client) == [download["id"]]
    clock.advance(minutes=1)
    assert listed_ids(client) == []


def test_downloads_in_progress_never_leave_the_list(
    make_client: MakeClient, clock: FakeClock
) -> None:
    source = paused_at("downloading")
    client = make_client(source)
    download = create_download(client)
    wait_for(client, download["id"], in_state("downloading"))

    clock.advance(hours=5)

    assert listed_ids(client) == [download["id"]]
    source.release()


def test_leftover_temp_files_are_deleted_when_the_app_starts(
    make_client: MakeClient, tmp_path: Path
) -> None:
    leftover = tmp_path / "7" / "Canción a medias.mp3.part"
    leftover.parent.mkdir()
    leftover.write_bytes(b"restos de una ejecucion anterior")

    make_client()

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("minutes", [0, 59])
def test_ready_file_is_still_available_before_one_hour(
    make_client: MakeClient, clock: FakeClock, minutes: int
) -> None:
    client = make_client()
    download = wait_for(client, create_download(client)["id"], in_state("ready"))

    clock.advance(minutes=minutes)

    assert client.get(f"/api/downloads/{download['id']}/file").status_code == 200


def test_app_starts_even_if_the_temp_folder_does_not_exist_yet(
    tmp_path: Path, clock: FakeClock
) -> None:
    missing = tmp_path / "todavia-no-existe"

    client = TestClient(
        create_app(video_source=FakeVideoSource({"dQw4w9WgXcQ": SONG}), temp_dir=missing, clock=clock.now)
    )
    download = wait_for(client, create_download(client)["id"], in_state("ready"))

    assert client.get(f"/api/downloads/{download['id']}/file").status_code == 200

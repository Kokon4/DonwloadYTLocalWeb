"""En modo uso, FastAPI sirve también la web compilada (ver ADR 0002)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import SONG, FakeClock, FakeVideoSource


@pytest.fixture
def built_frontend(tmp_path: Path) -> Path:
    """Una web "compilada" mínima, como la que genera ``npm run build``."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>DownloadYT Local</title>")
    (dist / "assets" / "index-abc123.js").write_text("console.log('hola')")
    return dist


def make_app_client(tmp_path: Path, frontend_dir: Path | None) -> TestClient:
    return TestClient(
        create_app(
            video_source=FakeVideoSource({"dQw4w9WgXcQ": SONG}),
            temp_dir=tmp_path / "temp",
            clock=FakeClock().now,
            frontend_dir=frontend_dir,
        )
    )


def test_the_web_and_its_assets_are_served_from_the_same_server(
    tmp_path: Path, built_frontend: Path
) -> None:
    client = make_app_client(tmp_path, built_frontend)

    page = client.get("/")
    script = client.get("/assets/index-abc123.js")

    assert page.status_code == 200
    assert "DownloadYT Local" in page.text
    assert page.headers["content-type"].startswith("text/html")
    assert (script.status_code, script.text) == (200, "console.log('hola')")


def test_the_api_keeps_working_when_the_web_is_served(tmp_path: Path, built_frontend: Path) -> None:
    client = make_app_client(tmp_path, built_frontend)

    response = client.post("/api/analysis", json={"url": "https://youtu.be/dQw4w9WgXcQ"})

    assert response.status_code == 200
    assert response.json()["video_id"] == "dQw4w9WgXcQ"


def test_without_a_built_web_only_the_api_is_served(tmp_path: Path) -> None:
    # Modo desarrollo: la web la sirve Vite.
    client = make_app_client(tmp_path, None)

    assert client.get("/").status_code == 404
    assert client.get("/api/downloads").status_code == 200

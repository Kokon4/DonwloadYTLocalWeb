from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import SONG, FakeVideoSource

MakeClient = Callable[..., TestClient]


@pytest.fixture
def make_client(tmp_path: Path) -> MakeClient:
    """Crea la app con una Fuente de vídeo falsa y una carpeta temporal propia del test."""

    def make(source: FakeVideoSource | None = None) -> TestClient:
        return TestClient(
            create_app(
                video_source=source or FakeVideoSource({"dQw4w9WgXcQ": SONG}),
                temp_dir=tmp_path,
            )
        )

    return make

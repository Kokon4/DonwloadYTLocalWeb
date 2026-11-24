from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import SONG, FakeClock, FakeVideoSource

MakeClient = Callable[..., TestClient]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_client(tmp_path: Path, clock: FakeClock) -> MakeClient:
    """Crea la app con una Fuente de vídeo falsa, un reloj falso y una carpeta temporal
    propia del test."""

    def make(source: FakeVideoSource | None = None) -> TestClient:
        return TestClient(
            create_app(
                video_source=source or FakeVideoSource({"dQw4w9WgXcQ": SONG}),
                temp_dir=tmp_path,
                clock=clock.now,
            )
        )

    return make

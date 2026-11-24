import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.video_source import LiveVideoError, VideoInfo, VideoSourceError, VideoUnavailableError
from tests.fakes import SONG, FakeVideoSource


def analyze(link: str, source: FakeVideoSource | None = None) -> tuple[int, object]:
    client = TestClient(create_app(video_source=source or FakeVideoSource({"dQw4w9WgXcQ": SONG})))
    response = client.post("/api/analysis", json={"url": link})
    return response.status_code, response.json()


@pytest.mark.parametrize(
    "link",
    [
        "esto no es un enlace",
        "https://vimeo.com/76979871",
        "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "https://www.youtube.com/watch",
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/",
        "https://www.youtube.com/watch?v=corto",
    ],
)
def test_link_that_is_not_a_youtube_video_is_rejected(link: str) -> None:
    assert analyze(link) == (422, {"code": "unsupported_link"})


@pytest.mark.parametrize(
    "link",
    [
        "https://www.youtube.com/playlist?list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG",
        "https://music.youtube.com/playlist?list=OLAK5uy_kgUBQf9C3o7aWlmtUNjzpMvV4bZ0cXgvs",
    ],
)
def test_playlist_link_without_a_video_is_rejected(link: str) -> None:
    assert analyze(link) == (422, {"code": "playlist_not_supported"})


def test_live_video_is_rejected() -> None:
    source = FakeVideoSource({"jfKfPfyJRdk": LiveVideoError()})

    assert analyze("https://www.youtube.com/watch?v=jfKfPfyJRdk", source) == (
        422,
        {"code": "live_not_supported"},
    )


def test_unavailable_video_is_rejected() -> None:
    source = FakeVideoSource({"xxxxxxxxxxx": VideoUnavailableError()})

    assert analyze("https://youtu.be/xxxxxxxxxxx", source) == (
        422,
        {"code": "video_unavailable"},
    )


def test_long_video_is_accepted_without_duration_limit() -> None:
    four_hour_mix = VideoInfo(
        title="Mix de 4 horas", thumbnail_url="https://i.ytimg.com/x.jpg", duration_seconds=4 * 3600
    )
    source = FakeVideoSource({"LongMix0001": four_hour_mix})

    status, body = analyze("https://www.youtube.com/watch?v=LongMix0001", source)

    assert status == 200
    assert isinstance(body, dict) and body["duration_seconds"] == 14400


def test_unexpected_video_source_failure_is_reported_as_source_failure() -> None:
    # P. ej. sin conexión, o yt-dlp roto tras un cambio de YouTube: el Vídeo puede estar bien.
    source = FakeVideoSource({"dQw4w9WgXcQ": VideoSourceError("yt-dlp: unable to extract")})

    assert analyze("https://youtu.be/dQw4w9WgXcQ", source) == (502, {"code": "source_failed"})

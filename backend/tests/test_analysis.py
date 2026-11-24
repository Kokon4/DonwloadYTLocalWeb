import pytest

from app.video_source import VideoInfo
from tests.conftest import MakeClient
from tests.fakes import SONG, FakeVideoSource, videoclip


def test_analysis_of_watch_link_returns_video_data_and_mp3_options(make_client: MakeClient) -> None:
    source = FakeVideoSource({"dQw4w9WgXcQ": SONG})
    client = make_client(source)

    response = client.post(
        "/api/analysis", json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "video_id": "dQw4w9WgXcQ",
        "title": "Artista - Canción (Official Video)",
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration_seconds": 213,
        "quality_options": [
            {"id": "mp3-192", "kind": "mp3", "label": "MP3 · Alta (192 kbps)", "default": True},
            {"id": "mp3-128", "kind": "mp3", "label": "MP3 · Ligera (128 kbps)", "default": False},
        ],
    }



@pytest.mark.parametrize(
    "link",
    [
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=AbCdEf123",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ&feature=share",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG&index=3",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_every_accepted_link_form_analyzes_the_same_video(link: str, make_client: MakeClient) -> None:
    source = FakeVideoSource({"dQw4w9WgXcQ": SONG})
    client = make_client(source)

    response = client.post("/api/analysis", json={"url": link})

    assert response.status_code == 200
    assert response.json()["video_id"] == "dQw4w9WgXcQ"



def option_ids(make_client: MakeClient, video: VideoInfo) -> list[str]:
    client = make_client(FakeVideoSource({"dQw4w9WgXcQ": video}))
    body = client.post("/api/analysis", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()
    return [o["id"] for o in body["quality_options"]]


def test_analysis_offers_mp4_options_for_available_compatible_resolutions(
    make_client: MakeClient,
) -> None:
    client = make_client(FakeVideoSource({"dQw4w9WgXcQ": videoclip(1080, 720, 480)}))

    body = client.post("/api/analysis", json={"url": "https://youtu.be/dQw4w9WgXcQ"}).json()

    assert body["quality_options"] == [
        {"id": "mp3-192", "kind": "mp3", "label": "MP3 · Alta (192 kbps)", "default": True},
        {"id": "mp3-128", "kind": "mp3", "label": "MP3 · Ligera (128 kbps)", "default": False},
        {"id": "mp4-1080", "kind": "mp4", "label": "MP4 · 1080p", "default": False},
        {"id": "mp4-720", "kind": "mp4", "label": "MP4 · 720p", "default": False},
        {"id": "mp4-480", "kind": "mp4", "label": "MP4 · 480p", "default": False},
    ]


def test_only_standard_resolutions_are_offered_as_mp4(make_client: MakeClient) -> None:
    # 144p y 240p no se ofrecen; las alturas llegan desordenadas y se ordenan de mayor a menor.
    assert option_ids(make_client, videoclip(144, 360, 240, 720)) == [
        "mp3-192",
        "mp3-128",
        "mp4-720",
        "mp4-360",
    ]


def test_video_without_compatible_mp4_offers_only_mp3(make_client: MakeClient) -> None:
    assert option_ids(make_client, videoclip()) == ["mp3-192", "mp3-128"]

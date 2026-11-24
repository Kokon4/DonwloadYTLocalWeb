import pytest
from tests.conftest import MakeClient
from tests.fakes import SONG, FakeVideoSource


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

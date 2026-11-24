"""Piezas falsas compartidas por los tests."""

from app.video_source import VideoInfo


class FakeVideoSource:
    """Fuente de vídeo falsa: para cada Vídeo devuelve sus datos o lanza el error indicado."""

    def __init__(self, videos: dict[str, VideoInfo | Exception]) -> None:
        self.videos = videos

    def get_video_info(self, video_id: str) -> VideoInfo:
        result = self.videos[video_id]
        if isinstance(result, Exception):
            raise result
        return result


SONG = VideoInfo(
    title="Artista - Canción (Official Video)",
    thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    duration_seconds=213,
)

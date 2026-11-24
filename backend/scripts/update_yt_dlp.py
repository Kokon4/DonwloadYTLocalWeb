"""Cambia la versión fijada de yt-dlp en requirements.txt a la última publicada en PyPI.

YouTube cambia a menudo y una versión fija de yt-dlp acaba dejando de funcionar (ver
ADR 0003). Se ejecuta con: docker compose run --rm update-yt-dlp
Solo usa la biblioteca estándar de Python.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
PIN = re.compile(r"^yt-dlp==(?P<version>\S+)$", re.MULTILINE)


def latest_version() -> str:
    with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=30) as response:
        version: str = json.load(response)["info"]["version"]
    return version


def main() -> int:
    text = REQUIREMENTS.read_text()
    match = PIN.search(text)
    if match is None:
        print("No se encontró la línea 'yt-dlp==...' en requirements.txt", file=sys.stderr)
        return 1
    current, latest = match["version"], latest_version()
    if current == latest:
        print(f"yt-dlp ya está en la última versión ({current}).")
        return 0
    REQUIREMENTS.write_text(PIN.sub(f"yt-dlp=={latest}", text))
    print(f"yt-dlp actualizado: {current} -> {latest}. Reconstruye la imagen para aplicarlo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

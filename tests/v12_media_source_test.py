#!/usr/bin/env python3
"""Deterministic media-source parsing and privacy checks for V12."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from route_bundle_sources import has

ROOT = Path(__file__).resolve().parents[1]


def extract_function(source: str, name: str, next_name: str) -> str:
    start = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if not start:
        raise AssertionError(f"Could not locate {name}")
    following = re.search(rf"function\s+{re.escape(next_name)}\s*\(", source[start.end():])
    if not following:
        raise AssertionError(f"Could not locate boundary after {name}")
    return source[start.start(): start.end() + following.start()].rstrip()


def main() -> int:
    app = (ROOT / "app.js").read_text(encoding="utf-8")
    public_html = (ROOT / "public.html").read_text(encoding="utf-8")
    public = (ROOT / "public-page.js").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    youtube_fn = extract_function(app, "youtubeId", "khmerDateFor")
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://evil.example/embed/dQw4w9WgXcQ",
    ]
    script = youtube_fn + "\nconsole.log(JSON.stringify(" + json.dumps(urls) + ".map(youtubeId)));"
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    parsed = json.loads(proc.stdout)
    assert parsed[:6] == ["dQw4w9WgXcQ"] * 6, parsed
    assert parsed[6] == "", parsed

    for control in ("musicSource", "musicEnabled", "musicStartAfterOpen", "musicLoop", "musicVolume", "musicFadeIn", "showMusicControl", "youtubeDisplayMode"):
        assert f'id="{control}"' in index, control
    assert "youtube-nocookie.com/embed/" in public and "youtube-nocookie.com/embed/" in app
    assert has('public.html','public-page.js')
    assert 'id="youtubeFeaturedPlayer"' in public
    assert "musicSource==='uploaded'" in public and "source==='uploaded'" in app
    assert "soundcloud.com" in public and "w.soundcloud.com/player/" in public
    assert "External media privacy" in index
    print("V12_MEDIA_SOURCE_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

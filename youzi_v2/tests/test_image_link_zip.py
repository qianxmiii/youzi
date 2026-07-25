"""图片链接批量打包测试。"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import xlwt

from youzi_v2.services.image_link_zip import (
    build_image_zip_from_urls,
    extract_image_urls,
)


def _make_xls(urls: list[str]) -> bytes:
    wb = xlwt.Workbook()
    sh = wb.add_sheet("s")
    sh.write(0, 15, "标签图片链接")
    for i, url in enumerate(urls, start=1):
        sh.write(i, 15, url)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_urls_from_xls_column_p() -> None:
    data = _make_xls(
        [
            "http://example.com/a.png",
            "https://example.com/b.jpg",
            "",
            "not-a-url",
            "http://example.com/a.png",
        ]
    )
    urls = extract_image_urls(data, filename="t.xls", column="P")
    assert urls == [
        "http://example.com/a.png",
        "https://example.com/b.jpg",
    ]


def test_build_zip_with_progress() -> None:
    urls = [
        "http://example.com/one.png",
        "http://example.com/two.png",
    ]
    progress_events: list[dict] = []

    def fake_get(url: str, timeout=None, stream: bool = True):
        class Resp:
            status_code = 200
            headers = {"Content-Type": "image/png"}

            def raise_for_status(self) -> None:
                return None

            def iter_content(self, chunk_size: int = 1024):
                yield b"\x89PNG" + url.encode()

        return Resp()

    with patch("youzi_v2.services.image_link_zip.requests.get", side_effect=fake_get):
        zip_bytes, stats = build_image_zip_from_urls(
            urls,
            on_progress=progress_events.append,
        )

    assert stats["downloaded"] == 2
    assert stats["failed"] == 0
    assert len(progress_events) == 2
    assert progress_events[-1]["done"] == 2
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert sorted(zf.namelist()) == ["one.png", "two.png"]

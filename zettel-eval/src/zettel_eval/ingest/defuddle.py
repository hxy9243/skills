from __future__ import annotations

from html.parser import HTMLParser
import shutil
import subprocess


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._current_href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._current_href = dict(attrs).get("href")
            self._link_text = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            if self._current_href is not None:
                self._link_text.append(text)
            else:
                self._chunks.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        anchor = " ".join(self._link_text).strip() or self._current_href
        self._chunks.append(f"[{anchor}]({self._current_href})")
        self._current_href = None
        self._link_text = []

    def text(self) -> str:
        return "\n".join(self._chunks)


def html_to_markdown_fallback(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.text().strip() + "\n"


def extract_markdown(url: str, html: str) -> str:
    if shutil.which("defuddle"):
        try:
            process = subprocess.run(  # noqa: S603
                ["defuddle", "parse", url, "--md"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            process = None
        if process and process.returncode == 0 and process.stdout.strip():
            return process.stdout
    return html_to_markdown_fallback(html)

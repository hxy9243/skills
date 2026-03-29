from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from zettel_eval.ingest.links import is_internal_url, normalize_url, resolve_href


USER_AGENT = "zettel-eval/0.1 (+https://example.invalid)"


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


@dataclass(slots=True)
class CrawledPage:
    url: str
    html: str
    discovered_links: list[str]


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8", errors="replace")


def crawl_site(seed_url: str, max_pages: int = 150) -> list[CrawledPage]:
    normalized_seed = normalize_url(seed_url)
    queue: deque[str] = deque([normalized_seed])
    seen: set[str] = set()
    pages: list[CrawledPage] = []

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch_html(url)
        except Exception:
            continue
        parser = LinkExtractor()
        parser.feed(html)
        resolved_links = [resolve_href(url, href) for href in parser.links]
        pages.append(CrawledPage(url=url, html=html, discovered_links=resolved_links))
        for candidate in resolved_links:
            if candidate in seen:
                continue
            if is_internal_url(normalized_seed, candidate):
                queue.append(candidate)

    return pages

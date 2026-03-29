from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    normalized = parsed._replace(fragment="", query="", path=path)
    return urlunparse(normalized)


def resolve_href(base_url: str, href: str) -> str:
    return normalize_url(urljoin(base_url, href))


def is_internal_url(seed_url: str, candidate_url: str) -> bool:
    seed = urlparse(seed_url)
    candidate = urlparse(candidate_url)
    return seed.netloc == candidate.netloc

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from internet_testing.analyzer import extract_same_origin_links


@dataclass(frozen=True)
class ExploredPage:
    url: str
    html: str
    depth: int


def explore_html_site(
    start_url: str,
    fetch_html,
    max_pages: int = 5,
    max_depth: int = 1,
) -> tuple[ExploredPage, ...]:
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    seen: set[str] = set()
    explored: list[ExploredPage] = []

    while queue and len(explored) < max_pages:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        html = fetch_html(url)
        explored.append(ExploredPage(url=url, html=html, depth=depth))

        if depth >= max_depth:
            continue

        for link in extract_same_origin_links(html, base_url=url):
            if link not in seen:
                queue.append((link, depth + 1))

    return tuple(explored)

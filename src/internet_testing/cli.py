from __future__ import annotations

import argparse
from pathlib import Path

from internet_testing.generator import generate_playwright_tests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="internet-testing",
        description="Explore website DOMs and generate deterministic Python Playwright tests.",
    )
    parser.add_argument("url", nargs="*", help="Website URL to explore with Playwright.")
    parser.add_argument(
        "--html",
        action="append",
        default=[],
        metavar="URL=PATH",
        help="Use a saved HTML file for a URL. Repeat for multiple pages.",
    )
    parser.add_argument(
        "--output",
        default="generated_playwright_tests.py",
        help="Path for the generated Python Playwright test file.",
    )
    parser.add_argument("--timeout-ms", type=int, default=45_000)
    args = parser.parse_args(argv)

    pages: list[tuple[str, str]] = []
    for mapping in args.html:
        pages.append(_read_html_mapping(mapping))

    if args.url:
        pages.extend(_crawl_urls(args.url, timeout_ms=args.timeout_ms))

    if not pages:
        parser.error("provide at least one URL or --html URL=PATH")

    output = Path(args.output)
    output.write_text(generate_playwright_tests(pages))
    print(f"wrote {output}")
    return 0


def _read_html_mapping(mapping: str) -> tuple[str, str]:
    if "=" not in mapping:
        raise SystemExit(f"invalid --html value {mapping!r}; expected URL=PATH")
    url, path = mapping.split("=", 1)
    return url, Path(path).read_text()


def _crawl_urls(urls: list[str], timeout_ms: int) -> list[tuple[str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required for live crawling. Run `uv sync`.") from exc

    pages: list[tuple[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            for url in urls:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1500)
                pages.append((url, page.content()))
        finally:
            browser.close()
    return pages


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from internet_testing.generator import generate_playwright_tests, generate_tests_with_llm


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
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument(
        "--llm-command",
        help="Command that reads explored DOM JSON from stdin and writes Python Playwright tests to stdout.",
    )
    args = parser.parse_args(argv)

    pages: list[tuple[str, str]] = []
    for mapping in args.html:
        pages.append(_read_html_mapping(mapping))

    if args.url:
        pages.extend(
            _crawl_urls(
                args.url,
                timeout_ms=args.timeout_ms,
                max_pages=args.max_pages,
                max_depth=args.max_depth,
            )
        )

    if not pages:
        parser.error("provide at least one URL or --html URL=PATH")

    output = Path(args.output)
    if args.llm_command:
        code = generate_tests_with_llm(pages, command=shlex.split(args.llm_command))
    else:
        code = generate_playwright_tests(pages)
    output.write_text(code)
    print(f"wrote {output}")
    return 0


def _read_html_mapping(mapping: str) -> tuple[str, str]:
    if "=" not in mapping:
        raise SystemExit(f"invalid --html value {mapping!r}; expected URL=PATH")
    url, path = mapping.split("=", 1)
    return url, Path(path).read_text()


def _crawl_urls(urls: list[str], timeout_ms: int, max_pages: int, max_depth: int) -> list[tuple[str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required for live crawling. Run `uv sync`.") from exc

    from internet_testing.explorer import explore_html_site

    pages: list[tuple[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            def fetch(url: str) -> str:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1500)
                return page.content()

            for url in urls:
                for explored in explore_html_site(
                    url,
                    fetch_html=fetch,
                    max_pages=max_pages,
                    max_depth=max_depth,
                ):
                    pages.append((explored.url, explored.html))
        finally:
            browser.close()
    return pages


if __name__ == "__main__":
    raise SystemExit(main())

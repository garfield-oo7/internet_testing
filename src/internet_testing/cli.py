from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from internet_testing.agent_tools import AgentToolCaps, AgentToolSession
from internet_testing.generator import generate_playwright_tests, generate_tests_with_llm
from internet_testing.openai_generator import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_REASONING_EFFORT,
    OpenAIGenerationConfig,
    generate_tests_with_openai_agent,
    generate_tests_with_openai,
)


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
    parser.add_argument("--agent-max-tool-calls", type=int, default=40)
    parser.add_argument("--agent-max-urls", type=int, default=8)
    parser.add_argument("--agent-max-seconds", type=float, default=120.0)
    parser.add_argument(
        "--llm-command",
        help="Command that reads explored DOM JSON from stdin and writes Python Playwright tests to stdout.",
    )
    parser.add_argument(
        "--openai",
        action="store_true",
        help="Use the OpenAI Responses API to generate Playwright tests from explored DOM evidence.",
    )
    parser.add_argument(
        "--openai-model",
        default=DEFAULT_OPENAI_MODEL,
        help=f"OpenAI model for test generation. Defaults to {DEFAULT_OPENAI_MODEL}.",
    )
    parser.add_argument(
        "--openai-reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=["none", "low", "medium", "high", "xhigh"],
        help=f"OpenAI reasoning effort for test generation. Defaults to {DEFAULT_REASONING_EFFORT}.",
    )
    args = parser.parse_args(argv)
    if args.openai and args.llm_command:
        parser.error("use either --openai or --llm-command, not both")

    config = OpenAIGenerationConfig(
        model=args.openai_model,
        reasoning_effort=args.openai_reasoning_effort,
    )
    caps = AgentToolCaps(
        max_tool_calls=args.agent_max_tool_calls,
        max_distinct_urls=args.agent_max_urls,
        max_wall_seconds=args.agent_max_seconds,
    )

    if args.openai and args.url and not args.html:
        code = _generate_openai_agent_from_url(
            args.url[0],
            timeout_ms=args.timeout_ms,
            config=config,
            caps=caps,
            screenshot_dir=Path(args.output).parent / "screenshots",
        )
        output = Path(args.output)
        output.write_text(code)
        print(f"wrote {output}")
        return 0

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
    if args.openai:
        code = generate_tests_with_openai(
            pages,
            config=config,
        )
    elif args.llm_command:
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


def _generate_openai_agent_from_url(
    url: str,
    timeout_ms: int,
    config: OpenAIGenerationConfig,
    caps: AgentToolCaps,
    screenshot_dir: Path,
) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required for live OpenAI generation. Run `uv sync`.") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            session = AgentToolSession(
                page=page,
                start_url=url,
                screenshot_dir=screenshot_dir,
                timeout_ms=timeout_ms,
                caps=caps,
            )
            return generate_tests_with_openai_agent(url, session=session, config=config)
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())

# Internet Testing

A deterministic DOM explorer and Python Playwright test generator.

The application can crawl live website URLs with Playwright, extract stable DOM
contracts, and write Python Playwright tests that run without any model call at
test execution time.

## Environment

Use the active `internet_testing` Python environment with `uv`:

```bash
uv sync --active
```

For live crawling or running generated Playwright tests, install a browser once:

```bash
uv run --active playwright install chromium
```

## Generate Tests

From live URLs:

```bash
uv run --active internet-testing \
  https://www.swiggy.com/ \
  https://www.zomato.com/ncr \
  --output generated_playwright_tests.py
```

From saved HTML fixtures, which is useful for repeatable verification:

```bash
uv run --active internet-testing \
  --html https://www.swiggy.com/=tests/fixtures/swiggy_complex.html \
  --html https://www.zomato.com/ncr=tests/fixtures/zomato_complex.html \
  --output examples/test_generated_indian_sites.py
```

## What It Generates

Generated tests import Playwright directly:

```python
from playwright.sync_api import Page, expect
```

The generator prefers stable selectors in this order:

1. `data-testid`, `data-test`, `data-qa`, `data-cy`
2. accessible names such as `aria-label`
3. named form inputs
4. roles and links

It intentionally ignores generated CSS class names such as `sc-*` or hashed
utility classes because they are unstable across deployments.

## Verify

```bash
uv run --active python -m unittest discover -s tests
```

## Current Indian-Site Evidence

This repository includes deterministic fixtures for Swiggy and Zomato under
`tests/fixtures/`, plus a generated Playwright artifact at
`examples/test_generated_indian_sites.py`.

Live crawling was also exercised against Swiggy and generated a URL-level smoke
artifact at `examples/test_generated_live_swiggy.py`; this environment did not
receive enough stable Swiggy DOM content for richer live assertions. Zomato live
crawling from this environment failed at HTTPS transport before DOM capture:
`net::ERR_HTTP2_PROTOCOL_ERROR` in Playwright and an HTTP/2 stream error with
`curl`. The Zomato generator path is therefore verified with the committed
complex DOM fixture rather than a live capture from this machine.

# Internet Testing

A bounded DOM explorer and Python Playwright test generator.

The application crawls live website URLs with Playwright, explores same-origin
links in a deterministic breadth-first order, extracts stable DOM contracts, and
writes Python Playwright tests. Test generation can use an external model
command, but the generated tests are validated and run without any model call at
test execution time.

For a detailed architecture write-up, see
[docs/architecture.md](docs/architecture.md).

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
  https://www.flipkart.com/ \
  https://www.amazon.in/ \
  --max-pages 4 \
  --max-depth 1 \
  --output generated_playwright_tests.py
```

To use an external model during generation, pass a command that reads the
explored DOM JSON from stdin and writes a complete Python Playwright test file
to stdout:

```bash
uv run --active internet-testing \
  https://www.flipkart.com/ \
  --max-pages 4 \
  --max-depth 1 \
  --llm-command "python scripts/write_tests_with_model.py" \
  --output generated_playwright_tests.py
```

The CLI validates the model output before writing it.

## Web Console

Run the local web UI:

```bash
uv run --active internet-testing-web --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`, paste a website URL, set crawl limits, and
optionally provide an LLM command for the generation phase. The UI streams the
generation and pytest logs from the same run. The pytest execution command is
separate from the LLM command, so generated tests still run without LLM usage.

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
uv run --active pytest \
  examples/test_generated_live_flipkart_deep.py \
  examples/test_generated_live_amazon_in_deep.py \
  --browser chromium
```

## Current Indian-Site Evidence

This repository includes deterministic fixtures for Swiggy and Zomato under
`tests/fixtures/`, plus a generated Playwright artifact at
`examples/test_generated_indian_sites.py`.

Live deep crawling was exercised against two complex Indian commerce sites:

1. Flipkart: `examples/test_generated_live_flipkart_deep.py`
2. Amazon India: `examples/test_generated_live_amazon_in_deep.py`

Those generated Playwright tests were run with Chromium through
`pytest-playwright` and passed in this environment.

Zomato live crawling from this environment failed at HTTPS transport before DOM
capture: `net::ERR_HTTP2_PROTOCOL_ERROR` in Playwright and an HTTP/2 stream
error with `curl`. Zomato is therefore covered with the committed complex DOM
fixture rather than a live capture from this machine.

# Internet Testing

A bounded DOM explorer and Python Playwright test generator.

## Purpose

Internet Testing helps evaluate real websites by exploring their DOMs and
generating Python Playwright tests from the discovered page structure. It is
designed for complicated production websites with generated markup, dynamic
links, and large DOMs.

The important boundary is that an LLM may help define or write the test cases
during generation, but the generated tests are plain Playwright tests. Test
execution uses `pytest-playwright` and does not call an LLM.

At a high level, the application:

1. Opens a website with Playwright.
2. Crawls same-origin links in a bounded breadth-first order.
3. Extracts stable DOM evidence such as accessible names, roles, and test IDs.
4. Generates a Python Playwright test file.
5. Runs that generated test file and shows the logs.

For a detailed architecture write-up, see
[docs/architecture.md](docs/architecture.md).

## Setup

Use the active `internet_testing` Python environment with `uv`:

```bash
uv sync --active
```

For live crawling or running generated Playwright tests, install a browser once:

```bash
uv run --active playwright install chromium
```

## Run the Web Application

Start the local web console:

```bash
uv run --active internet-testing-web --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

In the web UI:

1. Paste a full website URL, for example `https://www.flipkart.com/`.
2. Set `Max pages` and `Max depth` to control how much of the site is explored.
3. Optionally enter an LLM command for the generation phase.
4. Click `Run website test`.
5. Watch the generation and pytest logs in the same page.

The LLM command is only used to generate the test file. The pytest command that
runs the generated test file is separate and does not receive the LLM command.

## Run From the CLI

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

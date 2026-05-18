# Internet Testing

A bounded DOM explorer and Python Playwright test generator.

## Purpose

Internet Testing explores a website with Playwright and turns the observed DOM
evidence into Python Playwright tests. It can use OpenAI or another LLM only
while generating the test file; the generated tests run later with
`pytest-playwright` and do not call any LLM.

For a detailed architecture write-up, see
[docs/architecture.md](docs/architecture.md).

## Run the Application

1. Install dependencies into the active Python environment:

```bash
uv sync --active
```

2. Install Chromium for Playwright:

```bash
uv run --active playwright install chromium
```

3. Start the local web console:

```bash
uv run --active internet-testing-web --host 127.0.0.1 --port 8765
```

4. Open the app:

```text
http://127.0.0.1:8765
```

In the web UI, enter a full URL, choose deterministic generation or OpenAI
generation, set the crawl or agent limits, and click `Run website test`.

Alternative pip setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
```

The `requirements.txt` file is exported from `uv.lock` and includes the local
package in editable mode, so the `internet-testing` and `internet-testing-web`
commands are installed in the virtual environment.

OpenAI and LLM commands are only used to generate the test file. The pytest
command that runs the generated test file is separate and does not receive the
OpenAI configuration or LLM command.

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

To use OpenAI during generation, set `OPENAI_API_KEY` in the environment or a
local `.env` file:

```bash
OPENAI_API_KEY=sk-...
```

Then run:

```bash
uv run --active internet-testing \
  https://example.com/ \
  --openai \
  --openai-model gpt-5.5 \
  --agent-max-tool-calls 40 \
  --agent-max-urls 8 \
  --agent-max-seconds 120 \
  --output generated_playwright_tests.py
```

For live URLs with `--openai`, the model drives a persistent Playwright page via
bounded tools such as `navigate`, `get_dom`, `get_accessible_tree`, `query`,
`verify_selector`, `link_status`, `screenshot`, and `note`. Tool calls are
printed as `TOOL {...}` trace lines. The default OpenAI model is `gpt-5.5`,
based on the OpenAI API docs guidance that recommends it for complex reasoning
and coding. The generated Playwright file is validated and then can be run with
pytest without calling OpenAI.

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
uv run --active pytest tests
```

## Current Indian-Site Evidence

Recent OpenAI-agent real-site findings are documented in
[docs/real_site_agent_findings.md](docs/real_site_agent_findings.md). The live
runs include India.gov.in, Meesho, RBI, and Wikipedia. Some sites return
automation blocks such as `Access Denied`; those are documented as site-access
findings rather than treated as normal functional coverage.

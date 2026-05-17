# OpenAI LLM Test Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAI-backed Playwright test generation that uses an LLM only during test authoring and never during pytest execution.

**Architecture:** Keep deterministic crawling and pytest execution unchanged. Add a focused OpenAI generator module that sends bounded DOM evidence to the Responses API, validates the returned Python Playwright test file, and reuses the existing execution pipeline.

**Tech Stack:** Python 3.11+, Playwright, pytest-playwright, OpenAI Python SDK, OpenAI Responses API, model default `gpt-5.5`.

---

### Task 1: Tests for OpenAI Generation Boundary

**Files:**
- Modify: `tests/test_deep_exploration_and_llm.py`
- Modify: `tests/test_webapp.py`

- [ ] Add a unit test that patches an OpenAI client object and verifies generation sends DOM evidence, uses the configured model, returns plain Playwright code, and validates the result.
- [ ] Add a unit test that verifies missing `OPENAI_API_KEY` produces a clear error before making an API call.
- [ ] Add a CLI test that passes `--openai` and `--openai-model gpt-5.5` and writes the generated file.
- [ ] Add a webapp command-building test that proves OpenAI flags are present only in the generation command and absent from the pytest command.
- [ ] Run the targeted tests and confirm they fail for missing implementation.

### Task 2: OpenAI Generator Implementation

**Files:**
- Create: `src/internet_testing/openai_generator.py`
- Modify: `src/internet_testing/generator.py`
- Modify: `src/internet_testing/cli.py`
- Modify: `src/internet_testing/webapp.py`

- [ ] Create `OpenAIGenerationConfig` with model default `gpt-5.5`, optional API key, and reasoning effort default `medium`.
- [ ] Load `OPENAI_API_KEY` from the environment and, if absent, from a local `.env` file without logging secret values.
- [ ] Build a concise prompt that instructs the model to inspect DOM evidence and write deterministic Python Playwright pytest tests.
- [ ] Call the OpenAI Responses API through the OpenAI Python SDK.
- [ ] Extract output text robustly from the SDK response.
- [ ] Validate generated code with the existing validator.
- [ ] Add CLI flags `--openai`, `--openai-model`, and `--openai-reasoning-effort`.
- [ ] Add web UI fields that route OpenAI options to generation only.

### Task 3: Dependencies and Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `docs/architecture.md`

- [ ] Add `openai` to runtime dependencies.
- [ ] Regenerate `requirements.txt` from `uv.lock`.
- [ ] Document `OPENAI_API_KEY`, default model `gpt-5.5`, model override, and the fact that pytest execution never calls OpenAI.
- [ ] Cite that OpenAI docs recommend `gpt-5.5` for complex reasoning and coding and that latest models are available through the Responses API.

### Task 4: Verification

**Files:**
- All modified files

- [ ] Run `uv run --active python -m unittest discover -s tests`.
- [ ] Run a dry-run or mocked OpenAI generation path without exposing any API key.
- [ ] Check `git diff` to ensure `.env` and `.runs/` are untouched.
- [ ] Complete a requirement-by-requirement audit before reporting completion.

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

from internet_testing.generator import build_generation_payload, validate_generated_playwright


DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "medium"
VALID_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh"}


@dataclass(frozen=True)
class OpenAIGenerationConfig:
    api_key: str | None = None
    model: str = DEFAULT_OPENAI_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT


def generate_tests_with_openai(
    pages: list[tuple[str, str]],
    config: OpenAIGenerationConfig | None = None,
    client: Any | None = None,
) -> str:
    config = config or OpenAIGenerationConfig()
    effort = _validate_reasoning_effort(config.reasoning_effort)
    api_key = config.api_key or _load_openai_api_key()

    if client is None:
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI test generation.")
        client = _create_openai_client(api_key)

    response = client.responses.create(
        model=config.model,
        reasoning={"effort": effort},
        input=[
            {
                "role": "system",
                "content": _system_prompt(),
            },
            {
                "role": "user",
                "content": json.dumps(build_generation_payload(pages), sort_keys=True),
            },
        ],
    )
    code = _extract_output_text(response)
    validate_generated_playwright(code)
    return code


def _create_openai_client(api_key: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the openai package before using --openai.") from exc
    return OpenAI(api_key=api_key)


def _load_openai_api_key() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]

    env_path = Path(".env")
    if not env_path.exists():
        return None

    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name.strip() == "OPENAI_API_KEY":
            return value.strip().strip('"').strip("'") or None
    return None


def _validate_reasoning_effort(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_REASONING_EFFORTS:
        allowed = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ValueError(f"OpenAI reasoning effort must be one of: {allowed}.")
    return normalized


def _system_prompt() -> str:
    return (
        "You are a senior QA automation engineer. Inspect the provided website DOM "
        "evidence and write deterministic Python pytest tests using Playwright. "
        "Return only a complete Python file. The file must import exactly "
        "`from playwright.sync_api import Page, expect`. Do not import OpenAI, "
        "Anthropic, LangChain, browser automation SDKs other than Playwright, or "
        "any model/runtime service. The generated tests will run later without an "
        "LLM. Prefer stable selectors, accessible roles, and visible user-facing "
        "contracts. Avoid login, checkout, account, cart, personalized, tracking, "
        "or destructive flows. Keep assertions meaningful and bounded."
    )


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return _strip_markdown_fence(output_text)

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    if chunks:
        return _strip_markdown_fence("\n".join(chunks))

    raise ValueError("OpenAI response did not contain generated test code.")


def _strip_markdown_fence(value: str) -> str:
    stripped = value.strip()
    if not stripped.startswith("```"):
        return value
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip() + "\n"

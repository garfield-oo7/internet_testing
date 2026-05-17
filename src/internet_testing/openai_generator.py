from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import time
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
    max_tool_turns: int = 12


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

    response = _create_response(
        client,
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
    code = _validated_or_repaired_code(
        client=client,
        response=response,
        code=_extract_output_text(response),
        config=config,
        effort=effort,
    )
    return code


def generate_tests_with_openai_agent(
    start_url: str,
    session: Any,
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

    response = _create_response(
        client,
        model=config.model,
        reasoning={"effort": effort},
        tools=_tool_definitions(),
        input=[
            {"role": "system", "content": _agent_explore_prompt()},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "start_url": start_url,
                        "instructions": (
                            "Explore this website with tools. Take notes. Signal DONE_EXPLORING "
                            "when you have enough evidence to author deterministic Playwright tests."
                        ),
                    },
                    sort_keys=True,
                ),
            },
        ],
    )

    chain_author_to_response = True
    for _ in range(config.max_tool_turns):
        calls = _extract_tool_calls(response)
        if not calls:
            break
        outputs = []
        budget_exhausted = False
        for index, call in enumerate(calls):
            try:
                result = _dispatch_tool_call(session, call["name"], call["arguments"])
            except RuntimeError as exc:
                if not _is_agent_budget_error(exc):
                    raise
                if hasattr(session, "notes"):
                    session.notes.setdefault("exploration_stop_reason", []).append(str(exc))
                result = {"error": str(exc), "stop_exploration": True}
                budget_exhausted = True
            except ValueError as exc:
                if str(exc).startswith("Unsupported OpenAI tool call:"):
                    raise
                result = {"error": str(exc)}
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": call["call_id"],
                    "output": json.dumps(result, sort_keys=True),
                }
            )
            if budget_exhausted:
                for skipped_call in calls[index + 1:]:
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": skipped_call["call_id"],
                            "output": json.dumps(
                                {
                                    "error": "Skipped because agent tool budget was exhausted.",
                                    "stop_exploration": True,
                                },
                                sort_keys=True,
                            ),
                        }
                    )
                break
        response = _create_response(
            client,
            model=config.model,
            reasoning={"effort": effort},
            tools=_tool_definitions(),
            previous_response_id=getattr(response, "id", None),
            input=outputs,
        )
        if budget_exhausted:
            chain_author_to_response = False
            break
    else:
        raise RuntimeError(f"OpenAI exploration exceeded max tool turns: {config.max_tool_turns}")

    author_request = {
        "model": config.model,
        "reasoning": {"effort": effort},
        "input": [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instructions": _agent_author_prompt(),
                        "notes": getattr(session, "notes", {}),
                        "tool_trace": getattr(session, "trace", []),
                    },
                    sort_keys=True,
                ),
            }
        ],
    }
    if chain_author_to_response:
        author_request["previous_response_id"] = getattr(response, "id", None)

    author_response = _create_response(client, **author_request)
    code = _validated_or_repaired_code(
        client=client,
        response=author_response,
        code=_extract_output_text(author_response),
        config=config,
        effort=effort,
        baseline_dir=getattr(session, "screenshot_dir", None),
    )
    return code


def _validated_or_repaired_code(
    *,
    client: Any,
    response: Any,
    code: str,
    config: OpenAIGenerationConfig,
    effort: str,
    baseline_dir: Path | None = None,
) -> str:
    try:
        validate_generated_playwright(code, baseline_dir=baseline_dir)
        return code
    except ValueError as exc:
        repair_response = _create_response(
            client,
            model=config.model,
            reasoning={"effort": effort},
            previous_response_id=getattr(response, "id", None),
            input=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "instructions": (
                                "Repair the generated Python Playwright pytest file so it passes "
                                "the local validator. Return only complete Python code. Keep all "
                                "test inputs as literal strings and keep the single allowed import."
                            ),
                            "validation_error": str(exc),
                            "rejected_code": code,
                        },
                        sort_keys=True,
                    ),
                }
            ],
        )
    repaired_code = _extract_output_text(repair_response)
    validate_generated_playwright(repaired_code, baseline_dir=baseline_dir)
    return repaired_code


def _create_response(client: Any, **kwargs: Any) -> Any:
    for attempt in range(3):
        try:
            return client.responses.create(**kwargs)
        except Exception as exc:
            if not _is_rate_limit_error(exc) or attempt == 2:
                raise
            time.sleep(_retry_delay_seconds(str(exc)))
    raise RuntimeError("unreachable")


def _is_rate_limit_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    return "ratelimit" in name or "rate limit" in message or "rate_limit" in message


def _retry_delay_seconds(message: str) -> float:
    match = re.search(r"try again in ([0-9.]+)s", message, flags=re.IGNORECASE)
    if not match:
        return 2.0
    return min(max(float(match.group(1)), 0.5), 10.0)


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


def _agent_explore_prompt() -> str:
    return (
        "You are a senior QA automation agent with browser tools. Explore the site thoroughly "
        "in one bounded pass. Use note(key, value) to organize observations before authoring. "
        "Use verify_selector(selector) before you plan to use any selector in final test code. "
        "For each interactive element or input field, note candidate deterministic test variants. "
        "Do not generate Python yet. Avoid login, checkout, payment, account, destructive, "
        "personalized, or tracking flows. When done, respond with DONE_EXPLORING."
    )


def _agent_author_prompt() -> str:
    return (
        "Using only the accumulated notes and tool trace, emit the final Python Playwright pytest "
        "file. Return only Python code. Import only `from playwright.sync_api import Page, expect`. "
        "Do not import model SDKs, os, requests, httpx, or read files/env at runtime. For every "
        "input field covered, emit 2-4 test functions or a pytest parametrize block with "
        "deterministic literal values baked directly into the tests, covering happy path, "
        "boundary, and invalid cases where applicable. Use Playwright Python Locator.first "
        "and Locator.last as properties, for example `.first`, not `.first()`."
    )


def _tool_definitions() -> list[dict[str, object]]:
    return [
        _tool("navigate", "Navigate the persistent page to a same-origin URL.", {"url": "string"}),
        _tool("list_links", "Return same-origin links from the current page.", {}),
        _tool("link_status", "Return HTTP status for a same-origin URL without page navigation.", {"url": "string"}),
        _tool("get_dom", "Return bounded current-page HTML.", {"limit": "integer"}),
        _tool("get_accessible_tree", "Return bounded accessible and interactive page nodes.", {}),
        _tool("query", "Return count and sample text for a CSS selector.", {"selector": "string"}),
        _tool("verify_selector", "Verify count and visibility for a CSS selector.", {"selector": "string"}),
        _tool("screenshot", "Save a named full-page screenshot baseline.", {"name": "string"}),
        _tool("note", "Store structured scratchpad notes for final authoring.", {"key": "string", "value": "string"}),
    ]


def _tool(name: str, description: str, properties: dict[str, str]) -> dict[str, object]:
    schema_properties = {
        key: {"type": value}
        for key, value in properties.items()
    }
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": schema_properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


def _extract_tool_calls(response: Any) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "function_call":
            continue
        raw_arguments = getattr(item, "arguments", "{}") or "{}"
        calls.append(
            {
                "name": getattr(item, "name"),
                "arguments": json.loads(raw_arguments),
                "call_id": getattr(item, "call_id"),
            }
        )
    return calls


def _dispatch_tool_call(session: Any, name: str, arguments: dict[str, object]) -> dict[str, object]:
    allowed = {
        "navigate",
        "list_links",
        "link_status",
        "get_dom",
        "get_accessible_tree",
        "query",
        "verify_selector",
        "screenshot",
        "note",
    }
    if name not in allowed:
        raise ValueError(f"Unsupported OpenAI tool call: {name}")
    method = getattr(session, name)
    return method(**arguments)


def _is_agent_budget_error(exc: RuntimeError) -> bool:
    message = str(exc)
    return (
        "Agent tool call limit reached" in message
        or "Agent tool URL limit reached" in message
        or "Agent tool wall-clock limit reached" in message
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

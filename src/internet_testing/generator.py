from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

from internet_testing.analyzer import DiscoveredElement, analyze_html, extract_same_origin_links, iter_top_elements, site_slug


def generate_playwright_tests(pages: list[tuple[str, str]]) -> str:
    models = [analyze_html(html, base_url=url) for url, html in pages]
    lines = [
        "from playwright.sync_api import Page, expect",
        "",
        "",
    ]

    for model in models:
        function_name = f"test_{site_slug(model.url)}_critical_dom_contracts"
        lines.extend(
            [
                f"def {function_name}(page: Page):",
                f"    page.goto({json.dumps(model.url)}, wait_until=\"domcontentloaded\")",
                f"    expect(page).to_have_url({json.dumps(model.url)})",
            ]
        )

        for element in iter_top_elements(model):
            lines.append(f"    {_assertion_for(element)}")

        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_tests_with_llm(pages: list[tuple[str, str]], command: list[str]) -> str:
    payload = build_generation_payload(pages)
    completed = subprocess.run(
        command,
        input=json.dumps(payload, sort_keys=True),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)

    code = completed.stdout
    validate_generated_playwright(code)
    return code


def build_generation_payload(pages: list[tuple[str, str]]) -> dict[str, object]:
    return {
        "instructions": (
            "Write Python Playwright pytest tests from the provided explored DOM evidence. "
            "The generated file must import only playwright.sync_api Page and expect, "
            "must not call any model provider or external service, and must be deterministic."
        ),
        "pages": [_page_payload(url, html) for url, html in pages],
    }


def validate_generated_playwright(code: str, baseline_dir: Path | None = None) -> None:
    tree = ast.parse(code, filename="<generated_playwright_tests>")
    _validate_imports(tree)
    _validate_no_environment_access(tree)
    _validate_literal_input_values(tree)
    _validate_screenshot_baselines(tree, baseline_dir=baseline_dir)

    lowered = code.lower()
    blocked_terms = ("openai", "anthropic", "langchain", "llama", "chatgpt", "litellm")
    for term in blocked_terms:
        if term in lowered:
            raise ValueError(f"generated Playwright test depends on blocked model term: {term}")
    compile(tree, "<generated_playwright_tests>", "exec")
    if "from playwright.sync_api import Page, expect" not in code:
        raise ValueError("generated tests must import Page and expect from playwright.sync_api")


def _validate_imports(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            raise ValueError(f"generated Playwright test may not import runtime dependency: {names}")
        if isinstance(node, ast.ImportFrom):
            imported = {alias.name for alias in node.names}
            if node.module != "playwright.sync_api" or imported != {"Page", "expect"}:
                module = node.module or ""
                raise ValueError(f"generated Playwright test has unsupported import: {module}")


def _validate_no_environment_access(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in {"environ", "getenv"}:
                raise ValueError("generated Playwright test may not read environment variables")


def _validate_literal_input_values(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"fill", "type"}:
            continue
        values = list(node.args) + [keyword.value for keyword in node.keywords]
        if not values:
            raise ValueError(f"generated Playwright test {node.func.attr}() requires literal string values")
        for value in values:
            if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                raise ValueError(
                    f"generated Playwright test {node.func.attr}() arguments must be string literals"
                )


def _validate_screenshot_baselines(tree: ast.AST, baseline_dir: Path | None) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "to_have_screenshot":
            continue
        if not node.args or not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            raise ValueError("generated Playwright test screenshot assertion must use a literal baseline name")
        if baseline_dir is None:
            raise ValueError("generated Playwright test screenshot baseline directory is required")
        baseline_name = node.args[0].value
        if not (baseline_dir / baseline_name).exists():
            raise ValueError(f"generated Playwright test missing screenshot baseline: {baseline_name}")


def _page_payload(url: str, html: str) -> dict[str, object]:
    model = analyze_html(html, base_url=url)
    return {
        "url": url,
        "links": list(extract_same_origin_links(html, base_url=url)[:30]),
        "html_excerpt": _html_excerpt(html),
        "elements": [
            {
                "selector": element.selector,
                "role": element.role,
                "name": element.name,
                "text": element.text,
            }
            for element in iter_top_elements(model, limit=20)
        ],
    }


def _html_excerpt(html: str, limit: int = 15_000) -> str:
    compact = " ".join(html.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "...[truncated]"


def _assertion_for(element: DiscoveredElement) -> str:
    if element.role and element.name and element.role in {"button", "link", "textbox", "combobox"}:
        return f"expect(page.get_by_role({_q(element.role)}, name={_q(element.name)}).first).to_be_visible()"

    return f"expect(page.locator({_single_q(element.selector)}).first).to_be_visible()"


def _q(value: str) -> str:
    return json.dumps(value)


def _single_q(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

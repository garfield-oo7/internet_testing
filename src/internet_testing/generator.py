from __future__ import annotations

import json

from internet_testing.analyzer import DiscoveredElement, analyze_html, iter_top_elements, site_slug


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
                f"    page.goto({json.dumps(model.url)})",
                f"    expect(page).to_have_url({json.dumps(model.url)})",
            ]
        )

        for element in iter_top_elements(model):
            lines.append(f"    {_assertion_for(element)}")

        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _assertion_for(element: DiscoveredElement) -> str:
    if element.role and element.name and element.role in {"button", "link", "textbox", "combobox"}:
        return f"expect(page.get_by_role({_q(element.role)}, name={_q(element.name)})).to_be_visible()"

    return f"expect(page.locator({_single_q(element.selector)}).first).to_be_visible()"


def _q(value: str) -> str:
    return json.dumps(value)


def _single_q(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
import re
from typing import Iterable


@dataclass(frozen=True)
class DiscoveredElement:
    selector: str
    role: str | None = None
    name: str | None = None
    text: str | None = None


@dataclass(frozen=True)
class PageModel:
    url: str
    elements: tuple[DiscoveredElement, ...]


def analyze_html(html: str, base_url: str) -> PageModel:
    parser = _DomCandidateParser()
    parser.feed(html)
    parser.close()

    elements: list[DiscoveredElement] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for candidate in parser.candidates:
        element = _candidate_to_element(candidate)
        if element is None:
            continue
        if element.selector.startswith("[data-"):
            key = (element.selector, None, None)
        else:
            key = (element.selector, element.role, element.name)
        if key in seen:
            continue
        seen.add(key)
        elements.append(element)

    elements.sort(key=lambda item: (_selector_rank(item.selector), item.role or "", item.name or "", item.selector))
    return PageModel(url=base_url, elements=tuple(elements[:40]))


@dataclass
class _Candidate:
    tag: str
    attrs: dict[str, str]
    text_parts: list[str]

    @property
    def text(self) -> str:
        return _normalize_space(" ".join(self.text_parts))


class _DomCandidateParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[_Candidate] = []
        self._stack: list[_Candidate | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = {name.lower(): value or "" for name, value in attrs}
        candidate = _Candidate(tag=tag.lower(), attrs=normalized, text_parts=[])
        if _is_interesting(candidate):
            self.candidates.append(candidate)
            self._stack.append(candidate)
        else:
            self._stack.append(None)

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        for candidate in self._stack:
            if candidate is not None:
                candidate.text_parts.append(data)


def _is_interesting(candidate: _Candidate) -> bool:
    attrs = candidate.attrs
    if candidate.tag in {"a", "button", "input", "textarea", "select"}:
        return True
    return any(attr in attrs for attr in ("data-testid", "data-test", "aria-label", "role"))


def _candidate_to_element(candidate: _Candidate) -> DiscoveredElement | None:
    selector = _stable_selector(candidate)
    if selector is None:
        return None
    role = _role(candidate)
    name = _accessible_name(candidate)
    text = candidate.text or None
    return DiscoveredElement(selector=selector, role=role, name=name, text=text)


def _stable_selector(candidate: _Candidate) -> str | None:
    attrs = candidate.attrs
    for attr in ("data-testid", "data-test", "data-qa", "data-cy"):
        if attrs.get(attr):
            return f'[{attr}="{_css_string(attrs[attr])}"]'

    if attrs.get("aria-label"):
        return f'{candidate.tag}[aria-label="{_css_string(attrs["aria-label"])}"]'

    if candidate.tag == "input" and attrs.get("name"):
        return f'input[name="{_css_string(attrs["name"])}"]'

    if attrs.get("role") and _accessible_name(candidate):
        return f'{candidate.tag}[role="{_css_string(attrs["role"])}"]'

    if candidate.tag == "a" and attrs.get("href"):
        return f'a[href="{_css_string(attrs["href"])}"]'

    if candidate.tag == "button" and candidate.text:
        return "button"

    return None


def _role(candidate: _Candidate) -> str | None:
    explicit = candidate.attrs.get("role")
    if explicit:
        return explicit
    if candidate.tag == "button":
        return "button"
    if candidate.tag == "a" and candidate.attrs.get("href"):
        return "link"
    if candidate.tag == "select":
        return "combobox"
    if candidate.tag == "textarea":
        return "textbox"
    if candidate.tag == "input":
        input_type = candidate.attrs.get("type", "text").lower()
        if input_type in {"search", "email", "tel", "text", "url", "password"}:
            return "textbox"
    return None


def _accessible_name(candidate: _Candidate) -> str | None:
    attrs = candidate.attrs
    for attr in ("aria-label", "alt", "title", "placeholder"):
        if attrs.get(attr):
            return _normalize_space(attrs[attr])
    if candidate.text:
        return candidate.text
    return None


def _selector_rank(selector: str) -> int:
    if selector.startswith("[data-"):
        return 0
    if "aria-label" in selector:
        return 1
    if "[name=" in selector:
        return 2
    if "[role=" in selector:
        return 3
    if selector.startswith("a[href="):
        return 4
    return 5


def _css_string(value: str) -> str:
    return escape(value, quote=True).replace("\\", "\\\\")


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def site_slug(url: str) -> str:
    slug = re.sub(r"^https?://", "", url.lower())
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    return slug or "page"


def iter_top_elements(model: PageModel, limit: int = 12) -> Iterable[DiscoveredElement]:
    return model.elements[:limit]

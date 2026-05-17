from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from internet_testing.analyzer import extract_same_origin_links


@dataclass
class AgentToolSession:
    page: Any
    start_url: str
    screenshot_dir: Path = Path(".runs/screenshots")
    timeout_ms: int = 10_000
    notes: dict[str, list[str]] = field(default_factory=dict)
    trace: list[dict[str, str]] = field(default_factory=list)
    visited_urls: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._origin = _origin(self.start_url)
        self.visited_urls.add(self.start_url)

    def navigate(self, url: str) -> dict[str, object]:
        self._require_same_origin(url)
        self.page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        current_url = getattr(self.page, "url", url)
        self.visited_urls.add(current_url)
        return self._record("navigate", {"url": current_url})

    def list_links(self) -> dict[str, object]:
        base_url = getattr(self.page, "url", self.start_url)
        links = list(extract_same_origin_links(self.page.content(), base_url=base_url))
        return self._record("list_links", {"url": base_url, "links": links})

    def get_dom(self, limit: int = 20_000) -> dict[str, object]:
        html = self.page.content()
        truncated = len(html) > limit
        if truncated:
            html = html[:limit] + "...[truncated]"
        return self._record("get_dom", {"html": html, "truncated": truncated})

    def get_accessible_tree(self) -> dict[str, object]:
        nodes = self.page.evaluate(_ACCESSIBLE_TREE_SCRIPT)
        return self._record("get_accessible_tree", {"nodes": nodes})

    def query(self, selector: str, sample_limit: int = 5) -> dict[str, object]:
        locator = self.page.locator(selector)
        count = locator.count()
        samples: list[str] = []
        for index in range(min(count, sample_limit)):
            text = _safe_inner_text(locator.nth(index), timeout_ms=self.timeout_ms)
            if text:
                samples.append(text)
        return self._record("query", {"selector": selector, "count": count, "samples": samples})

    def verify_selector(self, selector: str) -> dict[str, object]:
        locator = self.page.locator(selector)
        count = locator.count()
        visible = False
        if count:
            try:
                visible = bool(locator.first.is_visible(timeout=self.timeout_ms))
            except Exception:
                visible = False
        return self._record("verify_selector", {"selector": selector, "count": count, "visible": visible})

    def screenshot(self, name: str) -> dict[str, object]:
        safe_name = _safe_screenshot_name(name)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / safe_name
        self.page.screenshot(path=str(path), full_page=True)
        return self._record("screenshot", {"name": safe_name, "path": str(path)})

    def note(self, key: str, value: str) -> dict[str, object]:
        normalized_key = _safe_note_key(key)
        self.notes.setdefault(normalized_key, []).append(value.strip())
        return self._record("note", {"key": normalized_key, "notes": self.notes})

    def _require_same_origin(self, url: str) -> None:
        if _origin(url) != self._origin:
            raise ValueError(f"Agent tools may only navigate same origin as {self.start_url}")

    def _record(self, tool: str, result: dict[str, object]) -> dict[str, object]:
        event = {"tool": tool}
        if "url" in result:
            event["url"] = str(result["url"])
        if "selector" in result:
            event["selector"] = str(result["selector"])
        if "key" in result:
            event["key"] = str(result["key"])
        if "name" in result:
            event["name"] = str(result["name"])
        self.trace.append(event)
        return result


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _safe_inner_text(element: Any, timeout_ms: int) -> str:
    try:
        return " ".join(element.inner_text(timeout=timeout_ms).split())
    except Exception:
        return ""


def _safe_screenshot_name(name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name.strip()).strip("._") or "screenshot"
    if not stem.lower().endswith(".png"):
        stem += ".png"
    return stem


def _safe_note_key(key: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", key.strip()).strip("._") or "note"


_ACCESSIBLE_TREE_SCRIPT = """
() => {
  const nodes = [];
  const interesting = Array.from(document.querySelectorAll(
    'a,button,input,textarea,select,h1,h2,h3,[role],[aria-label],[data-testid],[data-test],[data-qa],[data-cy]'
  ));
  for (const element of interesting.slice(0, 120)) {
    const text = (element.innerText || element.value || '').replace(/\\s+/g, ' ').trim();
    const name = (
      element.getAttribute('aria-label') ||
      element.getAttribute('alt') ||
      element.getAttribute('title') ||
      element.getAttribute('placeholder') ||
      text
    );
    nodes.push({
      tag: element.tagName.toLowerCase(),
      role: element.getAttribute('role') || '',
      name,
      text,
      testid: element.getAttribute('data-testid') || element.getAttribute('data-test') || ''
    });
  }
  return nodes;
}
"""

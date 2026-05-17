import tempfile
import unittest
from pathlib import Path

from internet_testing.agent_tools import AgentToolCaps, AgentToolSession


class FakeElement:
    def __init__(self, text: str, visible: bool = True):
        self._text = text
        self._visible = visible

    def inner_text(self, timeout: int = 1000) -> str:
        return self._text

    def is_visible(self, timeout: int = 1000) -> bool:
        return self._visible


class FakeLocator:
    def __init__(self, elements: list[FakeElement]):
        self._elements = elements

    def count(self) -> int:
        return len(self._elements)

    def nth(self, index: int) -> FakeElement:
        return self._elements[index]

    @property
    def first(self) -> FakeElement:
        return self._elements[0]


class FakePage:
    def __init__(self):
        self.url = "https://example.com/"
        self.navigated: list[str] = []
        self.html = """
            <html>
              <body>
                <h1>Example Domain</h1>
                <a href="/docs">Docs</a>
                <a href="https://other.test/">External</a>
                <button aria-label="Search">Search</button>
              </body>
            </html>
        """
        self.locators = {
            "h1": FakeLocator([FakeElement("Example Domain")]),
            "button": FakeLocator([FakeElement("Search")]),
            ".missing": FakeLocator([]),
        }
        self.screenshots: list[Path] = []

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int | None = None):
        self.url = url
        self.navigated.append(url)

    def content(self) -> str:
        return self.html

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator([]))

    def evaluate(self, script: str):
        return [
            {"tag": "h1", "role": "heading", "name": "Example Domain", "text": "Example Domain"},
            {"tag": "button", "role": "button", "name": "Search", "text": "Search"},
        ]

    def screenshot(self, path: str, full_page: bool = True):
        screenshot_path = Path(path)
        screenshot_path.write_bytes(b"fake-png")
        self.screenshots.append(screenshot_path)


class AgentToolSessionTests(unittest.TestCase):
    def test_navigation_is_restricted_to_same_origin_and_traced(self):
        page = FakePage()
        session = AgentToolSession(page=page, start_url="https://example.com/")

        result = session.navigate("https://example.com/docs")

        self.assertEqual(result["url"], "https://example.com/docs")
        self.assertEqual(page.navigated, ["https://example.com/docs"])
        self.assertEqual(session.trace[-1]["tool"], "navigate")
        with self.assertRaisesRegex(ValueError, "same origin"):
            session.navigate("https://other.test/")

    def test_dom_and_link_tools_return_bounded_same_origin_evidence(self):
        page = FakePage()
        session = AgentToolSession(page=page, start_url="https://example.com/")

        dom = session.get_dom(limit=25)
        links = session.list_links()
        tree = session.get_accessible_tree()

        self.assertTrue(dom["truncated"])
        self.assertLessEqual(len(dom["html"]), 40)
        self.assertEqual(links["links"], ["https://example.com/docs"])
        self.assertEqual(tree["nodes"][0]["role"], "heading")

    def test_query_verify_screenshot_and_note_tools_return_structured_results(self):
        page = FakePage()
        with tempfile.TemporaryDirectory() as tmpdir:
            session = AgentToolSession(
                page=page,
                start_url="https://example.com/",
                screenshot_dir=Path(tmpdir),
            )

            query = session.query("h1")
            verified = session.verify_selector("button")
            missing = session.verify_selector(".missing")
            screenshot = session.screenshot("home")
            note = session.note("static_content", "Homepage has a single Example Domain heading.")

            self.assertEqual(query["count"], 1)
            self.assertEqual(query["samples"], ["Example Domain"])
            self.assertTrue(verified["visible"])
            self.assertFalse(missing["visible"])
            self.assertTrue(Path(screenshot["path"]).exists())
            self.assertEqual(note["notes"]["static_content"], ["Homepage has a single Example Domain heading."])
            self.assertEqual(session.trace[-1]["tool"], "note")

    def test_tool_call_cap_stops_unbounded_agent_exploration(self):
        session = AgentToolSession(
            page=FakePage(),
            start_url="https://example.com/",
            caps=AgentToolCaps(max_tool_calls=1),
        )

        session.get_dom()

        with self.assertRaisesRegex(RuntimeError, "tool call limit"):
            session.list_links()

    def test_distinct_url_cap_stops_extra_navigation_before_browser_call(self):
        page = FakePage()
        session = AgentToolSession(
            page=page,
            start_url="https://example.com/",
            caps=AgentToolCaps(max_distinct_urls=1),
        )

        with self.assertRaisesRegex(RuntimeError, "URL limit"):
            session.navigate("https://example.com/docs")

        self.assertEqual(page.navigated, [])

    def test_wall_clock_cap_stops_late_tool_calls(self):
        times = iter([100.0, 100.5, 101.2])
        session = AgentToolSession(
            page=FakePage(),
            start_url="https://example.com/",
            caps=AgentToolCaps(max_wall_seconds=1.0),
            time_provider=lambda: next(times),
        )

        session.get_dom()

        with self.assertRaisesRegex(RuntimeError, "wall-clock"):
            session.list_links()

    def test_link_status_checks_route_without_navigating_page(self):
        page = FakePage()
        checked: list[str] = []

        def fake_status_fetcher(url: str, timeout_ms: int) -> int:
            checked.append(url)
            return 204

        session = AgentToolSession(
            page=page,
            start_url="https://example.com/",
            status_fetcher=fake_status_fetcher,
        )

        result = session.link_status("https://example.com/docs")

        self.assertEqual(result["status"], 204)
        self.assertEqual(checked, ["https://example.com/docs"])
        self.assertEqual(page.navigated, [])
        self.assertEqual(session.trace[-1]["tool"], "link_status")
        with self.assertRaisesRegex(ValueError, "same origin"):
            session.link_status("https://other.test/")


if __name__ == "__main__":
    unittest.main()

import re
import tempfile
import unittest
from pathlib import Path

from internet_testing.cli import main
from internet_testing.analyzer import analyze_html
from internet_testing.generator import generate_playwright_tests


FIXTURES = Path(__file__).parent / "fixtures"


class DomToPlaywrightTests(unittest.TestCase):
    def test_analyzer_prefers_stable_selectors_over_generated_classes(self):
        html = (FIXTURES / "swiggy_complex.html").read_text()

        model = analyze_html(html, base_url="https://www.swiggy.com/")

        selectors = [element.selector for element in model.elements]
        self.assertIn('[data-testid="restaurant-card"]', selectors)
        self.assertIn('input[name="q"]', selectors)
        self.assertIn('button[aria-label="Add Chicken Biryani from Meghana Foods"]', selectors)
        self.assertNotIn('[data-test="button"]', selectors)
        self.assertNotIn('button[aria-label="Login/ Register"]', selectors)
        self.assertNotIn(".sc-kpOJdX", selectors)
        self.assertNotIn("._1x93s", selectors)

    def test_generator_is_deterministic_for_complicated_indian_site_doms(self):
        swiggy = (FIXTURES / "swiggy_complex.html").read_text()
        zomato = (FIXTURES / "zomato_complex.html").read_text()

        first = generate_playwright_tests(
            [
                ("https://www.swiggy.com/", swiggy),
                ("https://www.zomato.com/ncr", zomato),
            ]
        )
        second = generate_playwright_tests(
            [
                ("https://www.swiggy.com/", swiggy),
                ("https://www.zomato.com/ncr", zomato),
            ]
        )

        self.assertEqual(first, second)
        self.assertIn("from playwright.sync_api import Page, expect", first)
        self.assertIn('page.goto("https://www.swiggy.com/", wait_until="domcontentloaded")', first)
        self.assertIn('page.goto("https://www.zomato.com/ncr", wait_until="domcontentloaded")', first)
        self.assertRegex(first, re.escape('expect(page.locator(\'[data-testid="restaurant-card"]\').first).to_be_visible()'))
        self.assertRegex(first, re.escape('expect(page.get_by_role("button", name="Book a table").first).to_be_visible()'))
        self.assertNotIn("openai", first.lower())
        self.assertNotIn("llm", first.lower())

    def test_cli_writes_parseable_playwright_tests_from_indian_site_fixtures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test_generated_indian_sites.py"

            exit_code = main(
                [
                    "--html",
                    f"https://www.swiggy.com/={FIXTURES / 'swiggy_complex.html'}",
                    "--html",
                    f"https://www.zomato.com/ncr={FIXTURES / 'zomato_complex.html'}",
                    "--output",
                    str(output),
                ]
            )

            generated = output.read_text()
            self.assertEqual(exit_code, 0)
            compile(generated, str(output), "exec")
            self.assertIn("def test_www_swiggy_com_critical_dom_contracts", generated)
            self.assertIn("def test_www_zomato_com_ncr_critical_dom_contracts", generated)
            self.assertIn("from playwright.sync_api import Page, expect", generated)


if __name__ == "__main__":
    unittest.main()

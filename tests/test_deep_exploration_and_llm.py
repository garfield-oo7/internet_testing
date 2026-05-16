import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from internet_testing.explorer import explore_html_site
from internet_testing.generator import generate_tests_with_llm, validate_generated_playwright


class DeepExplorationAndLlmTests(unittest.TestCase):
    def test_explorer_visits_same_origin_links_in_stable_breadth_first_order(self):
        pages = {
            "https://www.flipkart.com/": """
                <a href="/0pm/~cs-ad/pr?sid=0pm&ctx=tracking-payload&nnc=AD">Sponsored</a>
                <a href="/mobiles">Mobiles</a>
                <a href="https://seller.flipkart.com/">Seller</a>
                <a href="/fashion">Fashion</a>
                <button aria-label="Search for Products, Brands and More">Search</button>
            """,
            "https://www.flipkart.com/fashion": """
                <a href="/fashion/women">Women</a>
                <button aria-label="Filter by price">Price</button>
            """,
            "https://www.flipkart.com/mobiles": """
                <a href="/mobiles/samsung">Samsung phones</a>
                <button aria-label="Add Galaxy phone to cart">Add</button>
            """,
        }

        explored = explore_html_site(
            "https://www.flipkart.com/",
            fetch_html=pages.__getitem__,
            max_pages=3,
            max_depth=1,
        )

        self.assertEqual(
            [page.url for page in explored],
            [
                "https://www.flipkart.com/",
                "https://www.flipkart.com/fashion",
                "https://www.flipkart.com/mobiles",
            ],
        )

    def test_explorer_skips_generic_tracking_links(self):
        pages = {
            "https://www.flipkart.com/": """
                <a href="/0pm/~cs-ad/pr?sid=0pm&ctx=tracking-payload&nnc=AD">Sponsored</a>
                <a href="/account/?rd=0&link=home_account">Account</a>
                <a href="/4g-mobile-phones-store?otracker=undefined_footer">4G mobiles</a>
            """,
            "https://www.flipkart.com/4g-mobile-phones-store?otracker=undefined_footer": """
                <button aria-label="Search for Products, Brands and More">Search</button>
            """,
        }

        explored = explore_html_site(
            "https://www.flipkart.com/",
            fetch_html=pages.__getitem__,
            max_pages=2,
            max_depth=1,
        )

        self.assertEqual(
            [page.url for page in explored],
            [
                "https://www.flipkart.com/",
                "https://www.flipkart.com/4g-mobile-phones-store?otracker=undefined_footer",
            ],
        )

    def test_llm_generation_receives_explored_pages_and_validates_plain_playwright(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "writer.py"
            script.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys

                    payload = json.load(sys.stdin)
                    urls = [page["url"] for page in payload["pages"]]
                    print("from playwright.sync_api import Page, expect")
                    print()
                    print("def test_llm_written_contracts(page: Page):")
                    for url in urls:
                        print(f"    page.goto({url!r})")
                        print(f"    expect(page).to_have_url({url!r})")
                    """
                )
            )

            code = generate_tests_with_llm(
                [
                    ("https://www.flipkart.com/", "<button aria-label='Search'>Search</button>"),
                    ("https://www.flipkart.com/mobiles", "<button aria-label='Add'>Add</button>"),
                ],
                command=[sys.executable, str(script)],
            )

            self.assertIn("https://www.flipkart.com/mobiles", code)
            validate_generated_playwright(code)

    def test_validator_rejects_generated_tests_that_depend_on_model_libraries(self):
        generated = "import openai\n\ndef test_bad(page):\n    pass\n"

        with self.assertRaises(ValueError):
            validate_generated_playwright(generated)


if __name__ == "__main__":
    unittest.main()

import sys
import tempfile
import textwrap
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from internet_testing.cli import main
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

    def test_validator_rejects_runtime_network_and_environment_access(self):
        generated = textwrap.dedent(
            """
            from playwright.sync_api import Page, expect
            import requests
            import os

            def test_bad(page: Page):
                token = os.environ["OPENAI_API_KEY"]
                page.goto("https://www.flipkart.com/")
                expect(page).to_have_url("https://www.flipkart.com/")
            """
        )

        with self.assertRaisesRegex(ValueError, "import"):
            validate_generated_playwright(generated)

    def test_validator_requires_fill_and_type_values_to_be_string_literals(self):
        generated = textwrap.dedent(
            """
            from playwright.sync_api import Page, expect

            def test_bad(page: Page):
                query = "phone"
                page.goto("https://www.flipkart.com/")
                page.get_by_role("textbox", name="Search").fill(query)
            """
        )

        with self.assertRaisesRegex(ValueError, "fill"):
            validate_generated_playwright(generated)

    def test_validator_rejects_javascript_style_first_and_last_locator_calls(self):
        generated = textwrap.dedent(
            """
            from playwright.sync_api import Page, expect

            def test_bad(page: Page):
                page.goto("https://www.flipkart.com/")
                expect(page.locator("h1").first()).to_be_visible()
            """
        )

        with self.assertRaisesRegex(ValueError, "first"):
            validate_generated_playwright(generated)

    def test_validator_allows_screenshot_assertion_only_with_existing_baseline(self):
        generated = textwrap.dedent(
            """
            from playwright.sync_api import Page, expect

            def test_visual(page: Page):
                page.goto("https://example.com/")
                expect(page).to_have_screenshot("home.png")
            """
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_dir = Path(tmpdir)
            with self.assertRaisesRegex(ValueError, "screenshot baseline"):
                validate_generated_playwright(generated, baseline_dir=baseline_dir)

            (baseline_dir / "home.png").write_bytes(b"fake-png")
            validate_generated_playwright(generated, baseline_dir=baseline_dir)

    def test_cli_llm_command_writes_validated_playwright_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = Path(tmpdir) / "writer.py"
            output = Path(tmpdir) / "test_generated.py"
            writer.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys

                    payload = json.load(sys.stdin)
                    assert payload["pages"][0]["url"] == "https://www.flipkart.com/"
                    print("from playwright.sync_api import Page, expect")
                    print()
                    print("def test_cli_llm_contract(page: Page):")
                    print("    page.goto('https://www.flipkart.com/')")
                    print("    expect(page).to_have_url('https://www.flipkart.com/')")
                    """
                )
            )

            exit_code = main(
                [
                    "--html",
                    f"https://www.flipkart.com/={Path(__file__).parent / 'fixtures' / 'swiggy_complex.html'}",
                    "--llm-command",
                    f"{sys.executable} {writer}",
                    "--output",
                    str(output),
                ]
            )

            generated = output.read_text()
            self.assertEqual(exit_code, 0)
            self.assertIn("def test_cli_llm_contract", generated)
            validate_generated_playwright(generated)

    def test_openai_generation_sends_dom_evidence_and_validates_plain_playwright(self):
        from internet_testing.openai_generator import OpenAIGenerationConfig, generate_tests_with_openai

        class FakeResponses:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return type(
                    "FakeResponse",
                    (),
                    {
                        "output_text": (
                            "from playwright.sync_api import Page, expect\n\n"
                            "def test_model_written_contract(page: Page):\n"
                            "    page.goto('https://www.flipkart.com/')\n"
                            "    expect(page).to_have_url('https://www.flipkart.com/')\n"
                        )
                    },
                )()

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponses()

        client = FakeClient()
        code = generate_tests_with_openai(
            [("https://www.flipkart.com/", "<button aria-label='Search'>Search</button>")],
            config=OpenAIGenerationConfig(api_key="test-key", model="gpt-5.5"),
            client=client,
        )

        self.assertIn("def test_model_written_contract", code)
        self.assertEqual(client.responses.calls[0]["model"], "gpt-5.5")
        serialized_input = str(client.responses.calls[0]["input"])
        self.assertIn("https://www.flipkart.com/", serialized_input)
        self.assertIn("Search", serialized_input)
        validate_generated_playwright(code)

    def test_openai_agent_generation_uses_tools_before_authoring_tests(self):
        from internet_testing.openai_generator import OpenAIGenerationConfig, generate_tests_with_openai_agent

        class FakeCall:
            type = "function_call"

            def __init__(self, name: str, arguments: str, call_id: str):
                self.name = name
                self.arguments = arguments
                self.call_id = call_id

        class FakeResponse:
            def __init__(self, response_id: str, output=None, output_text=""):
                self.id = response_id
                self.output = output or []
                self.output_text = output_text

        class FakeResponses:
            def __init__(self):
                self.calls = []
                self.responses = [
                    FakeResponse("r1", output=[FakeCall("get_dom", '{"limit": 100}', "call_1")]),
                    FakeResponse("r2", output_text="DONE_EXPLORING"),
                    FakeResponse(
                        "r3",
                        output_text=(
                            "from playwright.sync_api import Page, expect\n\n"
                            "def test_agent_written_contract(page: Page):\n"
                            "    page.goto('https://example.com/')\n"
                            "    expect(page).to_have_url('https://example.com/')\n"
                        ),
                    ),
                ]

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return self.responses.pop(0)

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponses()

        class FakeSession:
            notes = {"static_content": ["Example Domain heading exists."]}
            trace = []

            def get_dom(self, limit=20_000):
                self.trace.append({"tool": "get_dom"})
                return {"html": "<h1>Example Domain</h1>", "truncated": False}

        client = FakeClient()
        code = generate_tests_with_openai_agent(
            start_url="https://example.com/",
            session=FakeSession(),
            config=OpenAIGenerationConfig(api_key="test-key", model="gpt-5.5"),
            client=client,
        )

        self.assertIn("def test_agent_written_contract", code)
        self.assertIn("tools", client.responses.calls[0])
        self.assertEqual(client.responses.calls[1]["previous_response_id"], "r1")
        self.assertEqual(client.responses.calls[2]["previous_response_id"], "r2")
        function_output = client.responses.calls[1]["input"][0]
        self.assertEqual(function_output["type"], "function_call_output")
        self.assertIn("Example Domain", function_output["output"])
        validate_generated_playwright(code)

    def test_openai_agent_generation_validates_screenshot_against_session_baseline(self):
        from internet_testing.openai_generator import OpenAIGenerationConfig, generate_tests_with_openai_agent

        class FakeResponse:
            def __init__(self, response_id: str, output_text: str):
                self.id = response_id
                self.output = []
                self.output_text = output_text

        class FakeResponses:
            def __init__(self):
                self.responses = [
                    FakeResponse("r1", "DONE_EXPLORING"),
                    FakeResponse(
                        "r2",
                        "from playwright.sync_api import Page, expect\n\n"
                        "def test_visual_contract(page: Page):\n"
                        "    page.goto('https://example.com/')\n"
                        "    expect(page).to_have_screenshot('home.png')\n",
                    ),
                ]

            def create(self, **kwargs):
                return self.responses.pop(0)

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponses()

        class FakeSession:
            notes = {}
            trace = []

            def __init__(self, screenshot_dir: Path):
                self.screenshot_dir = screenshot_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot_dir = Path(tmpdir)
            (screenshot_dir / "home.png").write_bytes(b"fake-png")

            code = generate_tests_with_openai_agent(
                start_url="https://example.com/",
                session=FakeSession(screenshot_dir),
                config=OpenAIGenerationConfig(api_key="test-key"),
                client=FakeClient(),
            )

        self.assertIn("to_have_screenshot", code)

    def test_openai_generation_requires_api_key_before_client_creation(self):
        from internet_testing.openai_generator import OpenAIGenerationConfig, generate_tests_with_openai

        with patch("internet_testing.openai_generator._load_openai_api_key", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                generate_tests_with_openai(
                    [("https://www.flipkart.com/", "<button aria-label='Search'>Search</button>")],
                    config=OpenAIGenerationConfig(api_key=None),
                )

    def test_cli_openai_generation_writes_validated_playwright_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test_generated.py"

            with patch("internet_testing.cli.generate_tests_with_openai") as generate:
                generate.return_value = (
                    "from playwright.sync_api import Page, expect\n\n"
                    "def test_cli_model_contract(page: Page):\n"
                    "    page.goto('https://www.flipkart.com/')\n"
                    "    expect(page).to_have_url('https://www.flipkart.com/')\n"
                )

                exit_code = main(
                    [
                        "--html",
                        f"https://www.flipkart.com/={Path(__file__).parent / 'fixtures' / 'swiggy_complex.html'}",
                        "--openai",
                        "--openai-model",
                        "gpt-5.5",
                        "--output",
                        str(output),
                    ]
                )

            generated = output.read_text()
            self.assertEqual(exit_code, 0)
            self.assertIn("def test_cli_model_contract", generated)
            self.assertEqual(generate.call_args.kwargs["config"].model, "gpt-5.5")
            validate_generated_playwright(generated)

    def test_cli_live_openai_uses_agent_browser_path_instead_of_precrawl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "test_generated.py"

            with patch("internet_testing.cli._generate_openai_agent_from_url") as generate:
                with patch("internet_testing.cli._crawl_urls") as crawl:
                    generate.return_value = (
                        "from playwright.sync_api import Page, expect\n\n"
                        "def test_cli_agent_contract(page: Page):\n"
                        "    page.goto('https://example.com/')\n"
                        "    expect(page).to_have_url('https://example.com/')\n"
                    )

                    exit_code = main(
                        [
                            "https://example.com/",
                            "--openai",
                            "--openai-model",
                            "gpt-5.5",
                            "--agent-max-tool-calls",
                            "7",
                            "--agent-max-urls",
                            "3",
                            "--agent-max-seconds",
                            "12",
                            "--openai-max-tool-turns",
                            "22",
                            "--output",
                            str(output),
                        ]
                    )

            generated = output.read_text()
            self.assertEqual(exit_code, 0)
            self.assertIn("def test_cli_agent_contract", generated)
            crawl.assert_not_called()
            self.assertEqual(generate.call_args.args[0], "https://example.com/")
            self.assertEqual(generate.call_args.kwargs["caps"].max_tool_calls, 7)
            self.assertEqual(generate.call_args.kwargs["caps"].max_distinct_urls, 3)
            self.assertEqual(generate.call_args.kwargs["caps"].max_wall_seconds, 12)
            self.assertEqual(generate.call_args.kwargs["config"].max_tool_turns, 22)

    def test_cli_tool_trace_output_is_structured_for_web_logs(self):
        from internet_testing.cli import _print_tool_trace

        output = StringIO()
        with patch("sys.stdout", output):
            _print_tool_trace({"tool": "verify_selector", "selector": "h1"})

        self.assertEqual(output.getvalue(), 'TOOL {"selector": "h1", "tool": "verify_selector"}\n')

    def test_openai_agent_prompts_require_selector_verification_and_literal_variants(self):
        from internet_testing.openai_generator import _agent_author_prompt, _agent_explore_prompt

        explore = _agent_explore_prompt()
        author = _agent_author_prompt()

        self.assertIn("verify_selector", explore)
        self.assertIn("note(key, value)", explore)
        self.assertIn("2-4", author)
        self.assertIn("literal", author)
        self.assertIn("happy path", author)
        self.assertIn("boundary", author)
        self.assertIn("invalid", author)
        self.assertIn(".first", author)
        self.assertIn(".first()", author)


if __name__ == "__main__":
    unittest.main()

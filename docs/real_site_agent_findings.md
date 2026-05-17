# Real-Site Agent Test Findings

Date: 2026-05-18

These runs used the live OpenAI-backed agent browser flow with the API key loaded from `.env`. Generated test files were written under `.runs/real_sites/`, which is intentionally ignored by git.

## Summary

| Site | Type | Generated file | Pytest result | Finding |
| --- | --- | --- | --- | --- |
| `https://www.india.gov.in/` | Indian public site | `.runs/real_sites/test_india_gov_agent.py` | 4 passed, 0 failed | Site served an Akamai `Access Denied` page to automation, so the tests verify the blocked-page contract rather than the normal site. |
| `https://www.rbi.org.in/` | Indian public site | `.runs/real_sites/test_rbi_agent.py` | 1 passed, 3 failed | Agent found real search controls, but generated click tests failed because a `ui-widget-overlay` intercepted the search button. |
| `https://en.wikipedia.org/wiki/Main_Page` | Popular public site | `.runs/real_sites/test_wikipedia_agent.py` | 13 passed, 7 failed | Search and checkbox tests mostly worked; failures came from state-dependent submit/radio selectors that were absent on rerun. |

## Commands Run

```bash
uv run --active internet-testing https://www.india.gov.in/ --openai --openai-model gpt-5.5 --openai-max-tool-turns 50 --agent-max-tool-calls 80 --agent-max-urls 5 --agent-max-seconds 240 --timeout-ms 45000 --output .runs/real_sites/test_india_gov_agent.py
uv run --active pytest .runs/real_sites/test_india_gov_agent.py --browser chromium --tb=short

uv run --active internet-testing https://www.rbi.org.in/ --openai --openai-model gpt-5.5 --openai-max-tool-turns 20 --agent-max-tool-calls 30 --agent-max-urls 3 --agent-max-seconds 120 --timeout-ms 45000 --output .runs/real_sites/test_rbi_agent.py
uv run --active pytest .runs/real_sites/test_rbi_agent.py --browser chromium --tb=short

uv run --active internet-testing https://en.wikipedia.org/wiki/Main_Page --openai --openai-model gpt-5.5 --openai-max-tool-turns 20 --agent-max-tool-calls 35 --agent-max-urls 3 --agent-max-seconds 120 --timeout-ms 45000 --output .runs/real_sites/test_wikipedia_agent.py
uv run --active pytest .runs/real_sites/test_wikipedia_agent.py --browser chromium --tb=short
```

## Test Cases Generated

### India.gov.in

- `test_home_page_renders_access_denied_template`
- `test_services_page_renders_access_denied_template`
- `test_robots_txt_renders_access_denied_template`
- `test_blocked_page_has_no_links_forms_or_interactive_controls`

Result: all 4 passed. These are valid tests for what automation received, but they are not useful coverage of the intended citizen-services UI.

### RBI

- `test_home_search_field_is_visible_editable_and_blank_by_default`
- `test_home_search_field_happy_path_submits_common_query`
- `test_home_search_field_boundary_single_character_query`
- `test_home_search_field_invalid_whitespace_query_is_not_accepted_as_normal_search`

Result: the default-state test passed. The 3 submit tests failed because Playwright could resolve the button, but `.ui-widget-overlay` intercepted pointer events for the click. This is a useful signal: generated tests should avoid click flows unless the agent has already performed the click successfully during exploration, or should prefer direct URL/search-result contracts when overlays are detected.

### Wikipedia

- `test_search_happy_path_exact_article`
- `test_search_boundary_single_character_query`
- `test_search_boundary_empty_query_is_allowed_in_field`
- `test_search_invalid_special_character_query_is_preserved_in_field`
- `test_main_menu_checkbox_can_be_checked`
- `test_main_menu_checkbox_can_be_unchecked`
- `test_page_tools_checkbox_can_be_checked`
- `test_page_tools_checkbox_can_be_unchecked`
- `test_user_links_checkbox_can_be_checked`
- `test_user_links_checkbox_can_be_unchecked`
- `test_appearance_checkbox_can_be_checked`
- `test_appearance_checkbox_can_be_unchecked`
- `test_language_checkbox_can_be_checked`
- `test_language_checkbox_can_be_unchecked`
- `test_font_size_radio_can_be_selected`
- `test_font_size_radio_has_expected_boundary_value`
- `test_limited_width_radio_can_be_selected`
- `test_limited_width_radio_has_expected_boundary_value`
- `test_night_mode_radio_can_be_selected`
- `test_night_mode_radio_has_expected_literal_value`

Result: 13 passed and 7 failed. Failures were concentrated in one search submit helper and the appearance radio helpers, where selectors observed during exploration were not attached during the independent pytest rerun.

## Tooling Improvements Made During This Pass

- Agent budget exhaustion now proceeds to authoring from partial notes instead of aborting.
- Recoverable tool rejections, such as unsafe login/cart URLs, are returned to the model as tool output instead of crashing the run.
- When tool budgets stop exploration, the generator now satisfies pending Responses API function calls before authoring.
- If budget exhaustion leaves a pending tool-call chain, authoring starts from explicit notes and trace instead of chaining to a response with unsatisfied calls.
- Generated code that fails local validation gets one repair pass before the run fails.
- Transient OpenAI rate-limit errors now retry with a bounded delay.

## Recommended Next Improvements

- Add a post-generation execution repair loop: run the generated pytest file, summarize failures, and ask the model for a corrected file using the failure log.
- Require the agent to execute any planned click/input flow during exploration before it can author that flow as a test.
- Add an overlay detector tool or automatic note when Playwright reports intercepted pointer events.
- Penalize selectors that only exist after opening a menu/panel unless the generated test also opens that state first.
- Classify anti-bot/access-denied pages so the report can mark them as blocked-site findings instead of treating them like normal coverage.

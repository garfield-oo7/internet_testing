from playwright.sync_api import Page, expect


def test_www_amazon_in_critical_dom_contracts(page: Page):
    page.goto("https://www.amazon.in/", wait_until="domcontentloaded")
    expect(page).to_have_url("https://www.amazon.in/")

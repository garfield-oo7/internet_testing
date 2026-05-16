from playwright.sync_api import Page, expect


def test_www_swiggy_com_critical_dom_contracts(page: Page):
    page.goto("https://www.swiggy.com/")
    expect(page).to_have_url("https://www.swiggy.com/")

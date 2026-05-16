from playwright.sync_api import Page, expect


def test_www_amazon_in_critical_dom_contracts(page: Page):
    page.goto("https://www.amazon.in/")
    expect(page).to_have_url("https://www.amazon.in/")
    expect(page.locator('span[aria-label="Go"]').first).to_be_visible()
    expect(page.locator('div[aria-label="More on Amazon"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Back to top").first).to_be_visible()
    expect(page.get_by_role("button", name="Choose a country/region for shopping. The current selection is India.").first).to_be_visible()
    expect(page.get_by_role("button", name="Expand to Change Language or Country").first).to_be_visible()
    expect(page.get_by_role("button", name="Fresh Details").first).to_be_visible()
    expect(page.get_by_role("button", name="Open All Categories Menu").first).to_be_visible()
    expect(page.get_by_role("button", name="Prime Details").first).to_be_visible()
    expect(page.get_by_role("button", name="Show/hide shortcuts, shift, option, z").first).to_be_visible()
    expect(page.locator('span[aria-label="India"]').first).to_be_visible()
    expect(page.get_by_role("link", name="0 items in cart").first).to_be_visible()
    expect(page.get_by_role("link", name="ASUS | Up to 35% off").first).to_be_visible()


def test_www_amazon_in_amazon_custom_b_ie_utf8_node_32615889031_ref_nav_cs_custom_critical_dom_contracts(page: Page):
    page.goto("https://www.amazon.in/Amazon-Custom/b/?ie=UTF8&node=32615889031&ref_=nav_cs_custom")
    expect(page).to_have_url("https://www.amazon.in/Amazon-Custom/b/?ie=UTF8&node=32615889031&ref_=nav_cs_custom")
    expect(page.locator('span[aria-label="Go"]').first).to_be_visible()
    expect(page.locator('div[aria-label="More on Amazon"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Back to top").first).to_be_visible()
    expect(page.get_by_role("button", name="Choose a country/region for shopping. The current selection is India.").first).to_be_visible()
    expect(page.get_by_role("button", name="Expand to Change Language or Country").first).to_be_visible()
    expect(page.get_by_role("button", name="Fresh Details").first).to_be_visible()
    expect(page.get_by_role("button", name="Open All Categories Menu").first).to_be_visible()
    expect(page.get_by_role("button", name="Prime Details").first).to_be_visible()
    expect(page.get_by_role("button", name="Show/hide shortcuts, shift, option, z").first).to_be_visible()
    expect(page.locator('span[aria-label="India"]').first).to_be_visible()
    expect(page.get_by_role("link", name="0 items in cart").first).to_be_visible()
    expect(page.get_by_role("link", name="Amazon India Home").first).to_be_visible()


def test_www_amazon_in_audible_books_and_originals_b_ie_utf8_node_17941593031_ref_nav_cs_audible_critical_dom_contracts(page: Page):
    page.goto("https://www.amazon.in/Audible-Books-and-Originals/b/?ie=UTF8&node=17941593031&ref_=nav_cs_audible")
    expect(page).to_have_url("https://www.amazon.in/Audible-Books-and-Originals/b/?ie=UTF8&node=17941593031&ref_=nav_cs_audible")
    expect(page.locator('span[aria-label="Go"]').first).to_be_visible()
    expect(page.locator('div[aria-label="More on Amazon"]').first).to_be_visible()
    expect(page.locator('adbl-bookwall[aria-label=" by Ram Dinesh Sharan, White Script,  by Chris Bailey,  by Peeyush Singh,  by R.K. Yadav,  by Prajakta Koli,  by Akshat Gupta,  by OSHO,  by Mantradmugdh Productions,  by Sun Tzu,  by Ankur Warikoo,  by George Orwell, Joe White - adaptation,  by Dale Carnegie"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Back to top").first).to_be_visible()
    expect(page.get_by_role("button", name="Categories, You are currently on a drop-down. To open this drop-down, Press Enter.").first).to_be_visible()
    expect(page.get_by_role("button", name="Choose a country/region for shopping. The current selection is India.").first).to_be_visible()
    expect(page.get_by_role("button", name="Expand to Change Language or Country").first).to_be_visible()
    expect(page.get_by_role("button", name="Fresh Details").first).to_be_visible()
    expect(page.get_by_role("button", name="More to Explore, You are currently on a drop-down. To open this drop-down, Press Enter.").first).to_be_visible()
    expect(page.get_by_role("button", name="New & Trending, You are currently on a drop-down. To open this drop-down, Press Enter.").first).to_be_visible()
    expect(page.get_by_role("button", name="Open All Categories Menu").first).to_be_visible()
    expect(page.get_by_role("button", name="Prime Details").first).to_be_visible()


def test_www_amazon_in_baby_b_ie_utf8_node_1571274031_ref_nav_cs_baby_critical_dom_contracts(page: Page):
    page.goto("https://www.amazon.in/Baby/b/?ie=UTF8&node=1571274031&ref_=nav_cs_baby")
    expect(page).to_have_url("https://www.amazon.in/Baby/b/?ie=UTF8&node=1571274031&ref_=nav_cs_baby")
    expect(page.locator('[data-testid="load-more-footer"]').first).to_be_visible()
    expect(page.locator('[data-testid="load-more-header"]').first).to_be_visible()
    expect(page.locator('[data-testid="load-more-spinner"]').first).to_be_visible()
    expect(page.locator('[data-testid="B07Q2F3DC9"]').first).to_be_visible()
    expect(page.locator('[data-testid="B07Q2BRTV7"]').first).to_be_visible()
    expect(page.locator('[data-testid="B07XZFHW2Q"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-departments-all"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-reviewRating-all"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-departments-1571275031"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-departments-2454170031"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-departments-1355017031"]').first).to_be_visible()
    expect(page.locator('[data-testid="filter-departments-4772061031"]').first).to_be_visible()

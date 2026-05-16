from playwright.sync_api import Page, expect


def test_www_swiggy_com_critical_dom_contracts(page: Page):
    page.goto("https://www.swiggy.com/")
    expect(page).to_have_url("https://www.swiggy.com/")
    expect(page.locator('[data-testid="restaurant-card"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Add All American Cheese Burger from Truffles").first).to_be_visible()
    expect(page.get_by_role("button", name="Add Chicken Biryani from Meghana Foods").first).to_be_visible()
    expect(page.get_by_role("link", name="Cart with 0 items").first).to_be_visible()
    expect(page.get_by_role("link", name="Meghana Foods restaurant").first).to_be_visible()
    expect(page.get_by_role("link", name="Truffles restaurant").first).to_be_visible()
    expect(page.get_by_role("textbox", name="Search for restaurant and food").first).to_be_visible()
    expect(page.get_by_role("link", name="Offers").first).to_be_visible()
    expect(page.get_by_role("button", name="Search").first).to_be_visible()


def test_www_zomato_com_ncr_critical_dom_contracts(page: Page):
    page.goto("https://www.zomato.com/ncr")
    expect(page).to_have_url("https://www.zomato.com/ncr")
    expect(page.locator('[data-testid="restaurant-card"]').first).to_be_visible()
    expect(page.get_by_role("combobox", name="Search for restaurant, cuisine or a dish").first).to_be_visible()
    expect(page.get_by_role("link", name="Open Bukhara").first).to_be_visible()
    expect(page.get_by_role("link", name="Open Indian Accent").first).to_be_visible()
    expect(page.get_by_role("link", name="Zomato home").first).to_be_visible()
    expect(page.get_by_role("link", name="Add restaurant").first).to_be_visible()
    expect(page.get_by_role("link", name="Who we are").first).to_be_visible()
    expect(page.get_by_role("button", name="Book a table").first).to_be_visible()
    expect(page.get_by_role("button", name="Reserve now").first).to_be_visible()

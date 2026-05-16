from playwright.sync_api import Page, expect


def test_www_swiggy_com_critical_dom_contracts(page: Page):
    page.goto("https://www.swiggy.com/")
    expect(page).to_have_url("https://www.swiggy.com/")
    expect(page.locator('[data-testid="restaurant-card"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Add All American Cheese Burger from Truffles")).to_be_visible()
    expect(page.get_by_role("button", name="Add Chicken Biryani from Meghana Foods")).to_be_visible()
    expect(page.get_by_role("link", name="Cart with 0 items")).to_be_visible()
    expect(page.get_by_role("link", name="Meghana Foods restaurant")).to_be_visible()
    expect(page.get_by_role("link", name="Truffles restaurant")).to_be_visible()
    expect(page.get_by_role("textbox", name="Search for restaurant and food")).to_be_visible()
    expect(page.get_by_role("link", name="Offers")).to_be_visible()
    expect(page.get_by_role("button", name="Search")).to_be_visible()


def test_www_zomato_com_ncr_critical_dom_contracts(page: Page):
    page.goto("https://www.zomato.com/ncr")
    expect(page).to_have_url("https://www.zomato.com/ncr")
    expect(page.locator('[data-testid="restaurant-card"]').first).to_be_visible()
    expect(page.get_by_role("combobox", name="Search for restaurant, cuisine or a dish")).to_be_visible()
    expect(page.get_by_role("link", name="Open Bukhara")).to_be_visible()
    expect(page.get_by_role("link", name="Open Indian Accent")).to_be_visible()
    expect(page.get_by_role("link", name="Zomato home")).to_be_visible()
    expect(page.get_by_role("link", name="Add restaurant")).to_be_visible()
    expect(page.get_by_role("link", name="Who we are")).to_be_visible()
    expect(page.get_by_role("button", name="Book a table")).to_be_visible()
    expect(page.get_by_role("button", name="Reserve now")).to_be_visible()

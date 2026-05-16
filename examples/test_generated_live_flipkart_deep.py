from playwright.sync_api import Page, expect


def test_www_flipkart_com_critical_dom_contracts(page: Page):
    page.goto("https://www.flipkart.com/")
    expect(page).to_have_url("https://www.flipkart.com/")
    expect(page.locator('span[aria-label="Advertise"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Search for Products, Brands and More").first).to_be_visible()
    expect(page.get_by_role("link", name="About Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Become a Seller").first).to_be_visible()
    expect(page.get_by_role("link", name="Cancellation & Returns").first).to_be_visible()
    expect(page.get_by_role("link", name="Careers").first).to_be_visible()
    expect(page.get_by_role("link", name="Cleartrip").first).to_be_visible()
    expect(page.get_by_role("link", name="Contact Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Corporate Information").first).to_be_visible()
    expect(page.get_by_role("link", name="EPR Compliance").first).to_be_visible()
    expect(page.get_by_role("link", name="FAQ").first).to_be_visible()
    expect(page.get_by_role("link", name="FSSAI Food Safety Connect App").first).to_be_visible()


def test_www_flipkart_com_4g_mobile_phones_store_otracker_undefined_footer_critical_dom_contracts(page: Page):
    page.goto("https://www.flipkart.com/4g-mobile-phones-store?otracker=undefined_footer")
    expect(page).to_have_url("https://www.flipkart.com/4g-mobile-phones-store?otracker=undefined_footer")
    expect(page.locator('span[aria-label="Advertise"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Search for Products, Brands and More").first).to_be_visible()
    expect(page.get_by_role("link", name="About Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Become a Seller").first).to_be_visible()
    expect(page.get_by_role("link", name="Cancellation & Returns").first).to_be_visible()
    expect(page.get_by_role("link", name="Careers").first).to_be_visible()
    expect(page.get_by_role("link", name="Cleartrip").first).to_be_visible()
    expect(page.get_by_role("link", name="Contact Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Corporate Information").first).to_be_visible()
    expect(page.get_by_role("link", name="EPR Compliance").first).to_be_visible()
    expect(page.get_by_role("link", name="FAQ").first).to_be_visible()
    expect(page.get_by_role("link", name="FSSAI Food Safety Connect App").first).to_be_visible()


def test_www_flipkart_com_aa_2025_new_at_store_critical_dom_contracts(page: Page):
    page.goto("https://www.flipkart.com/aa-2025-new-at-store")
    expect(page).to_have_url("https://www.flipkart.com/aa-2025-new-at-store")
    expect(page.locator('span[aria-label="Advertise"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Next Slide").first).to_be_visible()
    expect(page.get_by_role("button", name="Search for Products, Brands and More").first).to_be_visible()
    expect(page.get_by_role("link", name="About Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Become a Seller").first).to_be_visible()
    expect(page.get_by_role("link", name="Cancellation & Returns").first).to_be_visible()
    expect(page.get_by_role("link", name="Careers").first).to_be_visible()
    expect(page.get_by_role("link", name="Cleartrip").first).to_be_visible()
    expect(page.get_by_role("link", name="Contact Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Corporate Information").first).to_be_visible()
    expect(page.get_by_role("link", name="EPR Compliance").first).to_be_visible()
    expect(page.get_by_role("link", name="FAQ").first).to_be_visible()


def test_www_flipkart_com_ai_laptops_store_otracker_undefined_footer_critical_dom_contracts(page: Page):
    page.goto("https://www.flipkart.com/ai-laptops-store?otracker=undefined_footer")
    expect(page).to_have_url("https://www.flipkart.com/ai-laptops-store?otracker=undefined_footer")
    expect(page.locator('span[aria-label="Advertise"]').first).to_be_visible()
    expect(page.get_by_role("button", name="Search for Products, Brands and More").first).to_be_visible()
    expect(page.get_by_role("link", name="About Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Become a Seller").first).to_be_visible()
    expect(page.get_by_role("link", name="Cancellation & Returns").first).to_be_visible()
    expect(page.get_by_role("link", name="Careers").first).to_be_visible()
    expect(page.get_by_role("link", name="Cleartrip").first).to_be_visible()
    expect(page.get_by_role("link", name="Contact Us").first).to_be_visible()
    expect(page.get_by_role("link", name="Corporate Information").first).to_be_visible()
    expect(page.get_by_role("link", name="EPR Compliance").first).to_be_visible()
    expect(page.get_by_role("link", name="FAQ").first).to_be_visible()
    expect(page.get_by_role("link", name="FSSAI Food Safety Connect App").first).to_be_visible()

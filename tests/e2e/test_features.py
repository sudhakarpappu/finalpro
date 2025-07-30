from playwright.sync_api import Page

def test_features_page(page: Page):
    # Change to your staging URL in sandbox, or run a local server in CI
    page.goto("http://127.0.0.1:5000/features")
    assert page.locator("h1", has_text="Features Page").is_visible()
    assert page.locator("li", has_text="User Authentication").is_visible()

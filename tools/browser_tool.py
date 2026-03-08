from playwright.sync_api import sync_playwright
from backend.tools.registry import register_tool


@register_tool(
    name="browse_website",
    description="Browse website pages"
)
def browse_website(payload):

    url = payload.get("url")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url)

        title = page.title()

        browser.close()

        return {"title": title}

from playwright.sync_api import sync_playwright


class ShoppingAgent:

    def search_product(self, query):

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://www.amazon.com")

            page.fill("#twotabsearchtextbox", query)
            page.press("#twotabsearchtextbox", "Enter")

            page.wait_for_timeout(3000)

            products = []

            results = page.query_selector_all(
                "[data-component-type='s-search-result'] h2"
            )

            for r in results[:5]:
                products.append(r.inner_text())

            browser.close()

            return products
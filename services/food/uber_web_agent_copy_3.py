from dotenv import load_dotenv
import os
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from backend.utils.logger import logger  # assuming you have this

# Load env
secrets_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "secrets", ".env")
)
load_dotenv(secrets_path)

UBER_EATS_URL = "https://www.ubereats.com/ca"


class UberWebAgent:
    def __init__(self, email: str):
        self.email = email
        self.playwright = None
        self.context = None
        self.page = None
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)

    async def _screenshot(self, name: str):
        path = self.screenshot_dir / f"{name}_{int(asyncio.get_event_loop().time())}.png"
        await self.page.screenshot(path=path)
        logger.info(f"Screenshot saved: {path}")

    async def start(self, headless=True):
        logger.info(f"Launching browser (headless={headless})")
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir="./uber_user_data",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            locale="en-CA",
            timezone_id="America/Toronto",
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await self.page.set_extra_http_headers({"Accept-Language": "en-CA,en;q=0.9"})

    async def login(self):
        logger.info("Starting login flow")
        await self.page.goto(UBER_EATS_URL, wait_until="domcontentloaded", timeout=90000)

        # Try to find and click Sign In button (common on landing page)
        try:
            sign_in_btn = self.page.get_by_role("button", name=re.compile(r"sign in|log in", re.I)).first
            if await sign_in_btn.is_visible(timeout=8000):
                await sign_in_btn.click()
                await asyncio.sleep(2.5)
            else:
                sign_in_link = self.page.get_by_role("link", name=re.compile(r"sign in|log in", re.I)).first
                if await sign_in_link.is_visible(timeout=5000):
                    await sign_in_link.click()
                    await asyncio.sleep(2.5)
        except PlaywrightTimeoutError:
            logger.info("No sign-in button found on landing — assuming already logged or form visible")

        # Email / phone input (try multiple strategies)
        input_locators = [
            self.page.get_by_label(re.compile(r"email|phone|mobile", re.I)),
            self.page.get_by_placeholder(re.compile(r"email|phone|number", re.I)),
            self.page.locator('input[type="email"], input[type="tel"], input[name*="email"], input[autocomplete="email"]'),
        ]

        entry = None
        for loc in input_locators:
            if await loc.count() > 0 and await loc.is_visible(timeout=10000):
                entry = loc.first
                break

        if not entry:
            # Possible iframe (still happens sometimes)
            try:
                frame = self.page.frame_locator('iframe[src*="auth"], iframe[title*="sign"], iframe')
                entry = frame.locator('input[type="email"], input[type="tel"]').first
            except:
                await self._screenshot("login_input_not_found")
                raise RuntimeError("Could not locate email/phone input field")

        await entry.wait_for(state="visible", timeout=30000)
        await entry.fill(self.email)
        await asyncio.sleep(1.2)

        # Click Next / Continue instead of Enter
        next_btn = (
            self.page.get_by_role("button").filter(has_text=re.compile(r"next|continue|submit|get.*code|sign.*in", re.I)).first
            or self.page.get_by_role("button", name=re.compile(r"next|continue", re.I))
        )

        if await next_btn.is_visible(timeout=10000):
            await next_btn.click()
        else:
            await self.page.keyboard.press("Enter")  # fallback

        await asyncio.sleep(8)  # time for OTP screen / redirect
        logger.info("Login submission sent. OTP may be required — check manually if stuck.")
        await self._screenshot("post_login_attempt")

    async def set_delivery_location(self, address: str):
        logger.info(f"Setting delivery address: {address}")

        await self.page.goto(UBER_EATS_URL, wait_until="networkidle", timeout=60000)

        # Common address input locators
        address_input = (
            self.page.get_by_placeholder(re.compile(r"address|location|postal|deliver|where.*to", re.I))
            or self.page.get_by_label(re.compile(r"address|delivery|location", re.I))
            or self.page.get_by_role("combobox").first
        ).first

        await address_input.wait_for(state="visible", timeout=25000)
        await address_input.click()
        await address_input.fill(address)
        await asyncio.sleep(3.5)

        # Select first suggestion or confirm button
        try:
            suggestion = self.page.get_by_role("option").first
            if await suggestion.is_visible(timeout=12000):
                await suggestion.click()
            else:
                confirm_btn = self.page.get_by_role("button").filter(
                    has_text=re.compile(r"confirm|deliver here|save|set.*location|done", re.I)
                ).first
                if await confirm_btn.is_visible(timeout=8000):
                    await confirm_btn.click()
                else:
                    await self.page.keyboard.press("Enter")
        except:
            logger.warning("No suggestion/confirm found — assuming address set")
        
        await asyncio.sleep(5)
        await self._screenshot("address_set")

    async def search_restaurant(self, restaurant: str):
        logger.info(f"Searching restaurant: {restaurant}")

        search_input = (
            self.page.get_by_placeholder(re.compile(r"search.*food|restaurant|dish|store", re.I))
            or self.page.get_by_role("searchbox").first
            or self.page.get_by_role("textbox").first
        ).first

        await search_input.wait_for(state="visible", timeout=20000)
        await search_input.fill(restaurant)
        await asyncio.sleep(1.8)
        await search_input.press("Enter")
        await self.page.wait_for_load_state("networkidle", timeout=45000)

        # Find restaurant link/card
        await asyncio.sleep(4)

        restaurant_link = None
        candidates = await self.page.get_by_role("link").all()
        for link in candidates:
            try:
                text = (await link.inner_text(timeout=3000)).lower()
                if restaurant.lower() in text or restaurant.lower().replace("'", "") in text:
                    restaurant_link = link
                    break
            except:
                continue

        if not restaurant_link:
            # Fallback: look for article / list item
            restaurant_link = self.page.get_by_role("article").filter(
                has_text=re.compile(re.escape(restaurant), re.I)
            ).first

        if restaurant_link and await restaurant_link.is_visible():
            await restaurant_link.click()
            await self.page.wait_for_load_state("networkidle", timeout=30000)
        else:
            await self._screenshot("restaurant_not_found")
            raise RuntimeError(f"Could not find restaurant: {restaurant}")

        await asyncio.sleep(5)
        await self._screenshot("restaurant_page")

    async def open_meals_section(self):
        try:
            logger.info("Trying to open Meals / Popular Items section")
            tab = (
                self.page.get_by_role("tab").filter(has_text=re.compile(r"meals|popular|all.*items", re.I))
                or self.page.get_by_text(re.compile(r"meals|popular.*items", re.I)).first
            )
            if await tab.is_visible(timeout=12000):
                await tab.click()
                await asyncio.sleep(3.5)
        except Exception as e:
            logger.warning(f"Meals section not found or not needed: {e}")

    async def add_item_to_cart(self, item: dict):
        name = item["name"]
        logger.info(f"Adding item: {name}")

        normalized = name.lower().replace("combo", "").replace("meal", "").strip()
        keywords = normalized.split()

        # Scroll to load more items
        for _ in range(8):
            await self.page.mouse.wheel(0, 1800)
            await asyncio.sleep(1.1)

        # Look for menu item buttons / cards
        menu_items = await self.page.locator("button, a, [role='button'], article, div[data-testid*='menu-item']").all()

        selected = None
        for el in menu_items:
            try:
                text = (await el.inner_text(timeout=2500)).lower()
                price_present = bool(re.search(r'\$\d', text))
                if (normalized in text or all(k in text for k in keywords)) and price_present:
                    selected = el
                    break
            except:
                continue

        if not selected:
            await self._screenshot("item_not_found_" + normalized.replace(" ", "_"))
            raise RuntimeError(f"Menu item not found: {name}")

        await selected.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        await selected.click()
        await asyncio.sleep(3.5)

        # Handle customization modal if appears — just add (skip options for demo)
        try:
            add_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"add.*cart|add.*bag|add.*items?", re.I)
            ).first
            if await add_btn.is_visible(timeout=15000):
                await add_btn.click()
            else:
                await self.page.keyboard.press("Escape")  # close modal if stuck
        except:
            pass

        logger.info(f"Added: {name}")
        await asyncio.sleep(2.5)

    async def proceed_to_checkout(self):
        logger.info("Proceeding to checkout")
        cart_btn = (
            self.page.get_by_role("button").filter(has_text=re.compile(r"cart|bag|checkout|view.*order", re.I))
            or self.page.get_by_role("link", name=re.compile(r"cart|bag", re.I))
        ).first

        await cart_btn.click(timeout=20000)
        await asyncio.sleep(6)
        await self._screenshot("checkout_page")
        logger.info("Checkout opened — review manually (payment not automated)")

    async def close(self):
        logger.info("Closing session")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()


# ────────────────────────────────────────────────
# Demo
# ────────────────────────────────────────────────
async def demo_order(order: dict):
    email = os.getenv("UBER_EMAIL")
    if not email:
        raise ValueError("UBER_EMAIL not set in .env")

    agent = UberWebAgent(email)

    try:
        await agent.start(headless=True)  # Set to True for headless on VPS/iPhone setup
        await agent.login()
        await agent.set_delivery_location("3359 Morningstar Drive, Mississauga, ON L4T 1X6")
        await agent.search_restaurant(order["restaurant"])
        await agent.open_meals_section()

        for item in order["items"]:
            await agent.add_item_to_cart(item)

        await agent.proceed_to_checkout()
        logger.info("Demo completed — browser stays open for manual OTP/review")

        # Keep open for 5 min so you can handle OTP/payment
        await asyncio.sleep(300)

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        await agent._screenshot("error_final")
        raise
    finally:
        await agent.close()


if __name__ == "__main__":
    sample_order = {
        "restaurant": "McDonald's",
        "items": [{"name": "Big Mac Meal"}],
    }
    asyncio.run(demo_order(sample_order))
from dotenv import load_dotenv
import os
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from backend.utils.logger import logger

secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "secrets", ".env"))
load_dotenv(secrets_path)

UBER_EATS_URL = "https://www.ubereats.com/ca"

class UberWebAgent:
    def __init__(self, email: str):
        self.email = email
        self.phone = os.getenv("UBER_PHONE")
        self.playwright = None
        self.context = None
        self.page = None
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)

    async def start(self, headless: bool = True):
        logger.info(f"UberWebAgent: Starting browser (headless={headless})")
        self.playwright = await async_playwright().start()
        user_data_dir = "./uber_user_data"
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ],
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def login(self):
        logger.info("UberWebAgent: Login process started")
        try:
            for attempt in range(3):
                try:
                    await self.page.goto("https://auth.uber.com/login", wait_until="networkidle", timeout=120000)
                    break
                except Exception as e:
                    logger.warning(f"Login page load attempt {attempt+1} failed: {e}")
                    if attempt == 2:
                        raise

            await self._dismiss_modals()

            if await self.page.get_by_role("button", name=re.compile(r"deliver to|account|profile|à livrer", re.I)).is_visible(timeout=10000):
                logger.info("Already logged in")
                return

            entry = self.page.get_by_placeholder(re.compile(r"phone|email|number", re.I)).first
            if await entry.is_visible(timeout=20000):
                await entry.fill(self.email)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(4)

            otp = self.page.get_by_role("textbox", name=re.compile(r"code|pin|otp|verify", re.I)).first
            if await otp.is_visible(timeout=25000):
                code = input("Enter Uber verification code: ").strip()
                await otp.fill(code)
                await self.page.keyboard.press("Enter")
                await self.page.wait_for_load_state("networkidle", timeout=45000)

            # Phone verification prompt
            if await self.page.get_by_text(re.compile(r"phone number|email|verify|what's your|continuing", re.I)).is_visible(timeout=12000):
                logger.info("Phone/email prompt detected")
                input_field = self.page.get_by_placeholder(re.compile(r"phone|email|number", re.I)).first
                value = self.phone or self.email
                await input_field.fill(value)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(6)

            await self._dismiss_modals()
            logger.info("Login handling complete.")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self._save_screenshot("login_error")
            raise

    async def set_delivery_location(self, address: str):
        logger.info(f"Setting delivery location: {address}")
        try:
            await self.page.goto(UBER_EATS_URL, wait_until="networkidle", timeout=90000)
            await self._dismiss_modals()

            deliver_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"deliver to|à livrer|livraison|address|where", re.I)
            ).first

            address_input = None
            if await deliver_btn.is_visible(timeout=12000):
                await deliver_btn.click()
                await self.page.wait_for_timeout(4000)
                address_input = (
                    self.page.get_by_role("combobox").first
                    .or_(self.page.get_by_placeholder(re.compile(r"address|where to|deliver|location|add address|search", re.I)))
                    .or_(self.page.get_by_role("textbox").first)
                    .first
                )
            else:
                address_input = (
                    self.page.get_by_role("combobox").first
                    .or_(self.page.get_by_placeholder(re.compile(r"address|where to|deliver|location|add address|search", re.I)))
                    .or_(self.page.get_by_role("textbox").first)
                    .first
                )

            if not address_input:
                raise RuntimeError("No address input found")

            await address_input.wait_for(state="visible", timeout=45000)
            await address_input.click()
            await address_input.fill("")
            await address_input.fill(address)
            await self.page.wait_for_timeout(7000)


# Do this:
suggestions = await self.page.get_by_role("option").all()
# Filter only visible and containing your address text
target = None
for s in suggestions:
    text = await s.inner_text()
    if "Morningstar" in text or "Mississauga" in text:
        target = s
        break

if target:
    await target.click()
else:
    logger.warning("No matching address suggestion found, pressing Enter instead")
    await address_input.press("Enter")
            if await suggestion.is_visible(timeout=15000):
                await suggestion.click()
            else:
                await address_input.press("Enter")

            await self.page.wait_for_load_state("networkidle", timeout=40000)
            logger.info("Location set successfully.")
        except Exception as e:
            logger.error(f"Location error: {e}")
            await self._save_screenshot("location_error")
            raise

    async def search_restaurant(self, restaurant_name: str):
        logger.info(f"Searching for {restaurant_name}")
        try:
            search_input = self.page.get_by_placeholder(re.compile(r"search|find|restaurant|store", re.I)).first
            await search_input.fill(restaurant_name)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(6)

            card = self.page.get_by_role("link").filter(has_text=re.compile(restaurant_name, re.I)).first
            await card.click()
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            logger.info(f"Entered {restaurant_name} page")
        except Exception as e:
            logger.error(f"Search failed: {e}")
            await self._save_screenshot("search_error")

    async def add_item_to_cart(self, item_name: str):
        logger.info(f"Adding {item_name} to cart...")
        try:
            item = self.page.get_by_text(re.compile(item_name, re.I), exact=False).first
            await item.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)
            await item.click(force=True)
            await self.page.wait_for_timeout(4000)

            # Required options – click all visible radios/checkboxes
            required_texts = self.page.get_by_text(re.compile(r"required|must choose|select", re.I))
            if await required_texts.count() > 0:
                logger.info("Required options found – selecting defaults")
                for sel in ['input[type="radio"]:visible', 'input[type="checkbox"]:visible']:
                    elements = await self.page.locator(sel).all()
                    for el in elements:
                        try:
                            await el.scroll_into_view_if_needed()
                            await self.page.wait_for_timeout(500)
                            await el.click(force=True)
                            await self.page.wait_for_timeout(800)
                        except:
                            continue

            # Flexible add button
            add_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"add.*(cart|bag)|add item|continue|confirm.*order|add \d", re.I)
            ).last

            await add_btn.scroll_into_view_if_needed()
            await add_btn.wait_for(state="visible", timeout=15000)

            if not await add_btn.is_enabled(timeout=8000):
                logger.warning("Add button is disabled – attempting force click")
                await add_btn.dispatch_event("click")
            else:
                await add_btn.click()
            logger.info(f"Added {item_name}")
            await self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.error(f"Add to cart failed: {e}")
            await self._save_screenshot("add_item_error")
            with open(self.screenshot_dir / "add_item_error.html", "w", encoding="utf-8") as f:
                f.write(await self.page.content())
            raise

    async def proceed_to_checkout(self):
        logger.info("Proceeding to checkout...")
        try:
            checkout_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"checkout|go to checkout|view cart|review", re.I)
            ).first
            if await checkout_btn.is_visible(timeout=10000):
                await checkout_btn.click()
            else:
                await self.page.goto(f"{UBER_EATS_URL}/checkout", wait_until="networkidle")

            await self.page.wait_for_timeout(6000)
            await self._dismiss_modals()

            place_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"place order|confirm order|pay now|complete|submit order", re.I)
            ).first

            if await place_btn.is_visible(timeout=15000):
                logger.info("Place Order screen reached")
                await self._save_screenshot("checkout_ready")
            else:
                logger.warning("Place Order not found – checking if cart is empty")
                if await self.page.get_by_text(re.compile(r"empty|no items", re.I)).is_visible(timeout=5000):
                    logger.warning("Cart is empty – add to cart failed earlier")
                await self._save_screenshot("checkout_missing_place")
        except Exception as e:
            logger.error(f"Checkout failed: {e}")
            await self._save_screenshot("checkout_error")

    async def _dismiss_modals(self):
        try:
            texts = ["accept", "agree", "continue", "allow", "ok", "got it", "close", "dismiss", "not now", "skip", "no thanks"]
            for t in texts:
                btn = self.page.get_by_role("button").filter(has_text=re.compile(t, re.I)).first
                if await btn.is_visible(timeout=4000):
                    await btn.click()
                    await asyncio.sleep(1)
        except:
            pass

    async def _save_screenshot(self, name: str):
        path = self.screenshot_dir / f"{name}.png"
        await self.page.screenshot(path=str(path))
        logger.info(f"Screenshot saved: {path}")

    async def close(self):
        logger.info("Closing browser")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()

async def demo():
    email = os.getenv("UBER_EMAIL")
    if not email:
        logger.error("UBER_EMAIL not set")
        return

    agent = UberWebAgent(email)
    try:
        await agent.start(headless=True)
        await agent.login()
        await agent.set_delivery_location("3359 Morningstar Drive, Mississauga, ON L4T 1X6")
        await agent.search_restaurant("McDonald's")
        await agent.add_item_to_cart("McChicken")
        await agent.proceed_to_checkout()
        logger.info("Demo sequence completed")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(demo())
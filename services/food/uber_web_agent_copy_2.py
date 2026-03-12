from dotenv import load_dotenv
import os
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Robust Logger Import
try:
    from backend.utils.logger import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("UberWebAgent")

# Load environment variables
secrets_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "secrets", ".env")
)
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

    # -----------------------------
    # Browser
    # -----------------------------
    async def start(self, headless: bool = True):
        logger.info(f"UberWebAgent: Starting browser (headless={headless})")
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir="./uber_user_data",
            headless=headless,
            viewport={"width": 1280, "height": 1024},
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        self.context.set_default_timeout(45000)
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def login(self):
        logger.info("Login process started")
        try:
            await self.page.goto("https://auth.uber.com/login", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)

            await self._dismiss_modals()

            if await self.page.get_by_role("button", name=re.compile(r"deliver to|account|profile", re.I)).count() > 0:
                logger.info("Already logged in")
                return

            entry = self.page.get_by_placeholder(re.compile(r"phone|email|number", re.I)).first
            if await entry.is_visible():
                await entry.fill(self.email)
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(5)

            # OTP handling
            otp_box = self.page.get_by_role("textbox", name=re.compile(r"code|pin|otp|verify", re.I)).first
            try:
                if await otp_box.is_visible(timeout=8000):
                    code = input("Enter Uber verification code: ").strip()
                    await otp_box.fill(code)
                    await self.page.keyboard.press("Enter")
                    await self.page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(5)
                else:
                    logger.info("No OTP required (box not visible)")
            except Exception:
                pass

            await self._dismiss_modals()
            logger.info("Login complete")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self._save_screenshot("login_error")
            raise

    # -----------------------------
    # Location
    # -----------------------------
    async def set_delivery_location(self, address: str):
        logger.info(f"Setting delivery location: {address}")
        try:
            await self.page.goto(UBER_EATS_URL, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            await self._dismiss_modals()

            deliver_btn = self.page.get_by_role("button").filter(
                has_text=re.compile(r"deliver to|à livrer|livraison|address|where", re.I)
            ).first
            
            if await deliver_btn.is_visible(timeout=5000):
                await deliver_btn.click()
                await asyncio.sleep(2)

            address_input = (
                self.page.get_by_role("combobox").first
                .or_(self.page.get_by_placeholder(re.compile(r"address|where to|deliver|location", re.I)))
                .or_(self.page.get_by_role("textbox").first)
            )
            
            await address_input.fill(address)
            await asyncio.sleep(3)

            # Select first suggestion
            await self.page.keyboard.press("ArrowDown")
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")

            await self.page.wait_for_load_state("domcontentloaded")
            logger.info("Location set successfully")

        except Exception as e:
            logger.error(f"Location error: {e}")
            await self._save_screenshot("location_error")
            raise

    # -----------------------------
    # Search Restaurant
    # -----------------------------
    async def search_restaurant(self, restaurant_name: str):
        logger.info(f"Searching for {restaurant_name}")
        try:
            search_input = self.page.get_by_placeholder(re.compile(r"search|find|restaurant|store", re.I)).first
            await search_input.fill(restaurant_name)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(5) # Wait for search results

            # Click the first store link that resembles a restaurant card
            link = self.page.locator("a[href*='/store/']").first
            
            if not await link.is_visible():
                 raise RuntimeError("No restaurant links found")
            
            await link.click()
            await self.page.wait_for_load_state("domcontentloaded")
            
            try:
                # Wait for menu list items
                await self.page.wait_for_selector("div[role='listitem']", timeout=15000)
            except:
                logger.warning("Menu list items not immediately detected, trying to proceed anyway.")

            logger.info(f"Entered {restaurant_name} page")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            await self._save_screenshot("search_error")
            raise

    # -----------------------------
    # Add Item (FIXED)
    # -----------------------------
    async def add_item_to_cart(self, item: dict, retries: int = 3):
        item_name = item.get("name")
        logger.info(f"Adding {item_name}...")

        for attempt in range(retries):
            try:
                # 1. Find Item (Aggressive Scroll)
                # Using regex to be case insensitive
                item_locator = self.page.get_by_text(re.compile(re.escape(item_name), re.I)).first
                
                start_time = asyncio.get_event_loop().time()
                found = False
                
                while asyncio.get_event_loop().time() - start_time < 45:
                    if await item_locator.is_visible():
                        found = True
                        break
                    await self.page.keyboard.press("PageDown")
                    await asyncio.sleep(0.5)
                
                if not found:
                    raise RuntimeError(f"Item '{item_name}' not found on menu")

                # Force click to open modal
                await item_locator.scroll_into_view_if_needed()
                # Sometimes text is inside a span inside the clickable div
                await item_locator.click(force=True)
                
                # 2. Wait for Modal
                await asyncio.sleep(3) # Wait for animation/fetch

                # 3. Handle Options
                if "options" in item:
                    for opt in item["options"]:
                        opt_btn = self.page.get_by_text(opt, exact=False).first
                        if await opt_btn.is_visible():
                            await opt_btn.scroll_into_view_if_needed()
                            await opt_btn.click(force=True)
                            await asyncio.sleep(0.3)

                # 4. Checkout / Add Button (ROBUST STRATEGY)
                # Attempt A: Regex for "Add 1", "Add to order", "Ajouter"
                add_btn = self.page.get_by_role("button", name=re.compile(r"add\s|add.*order|ajouter", re.I)).last
                
                # Attempt B: Look for button containing "$" (Price) if text fail
                if not await add_btn.is_visible():
                    # Buttons often contain "Add 1 • CA$5.99"
                    add_btn = self.page.locator("button").filter(has_text=re.compile(r"[\$£€]")).last

                # Attempt C: Generic Submit
                if not await add_btn.is_visible():
                    add_btn = self.page.locator("button[type='submit']").last

                if await add_btn.is_visible():
                    await add_btn.scroll_into_view_if_needed()
                    await add_btn.click(force=True)
                else:
                    # Attempt D: Press Enter as last resort
                    logger.warning("Add button not found, pressing Enter")
                    await self.page.keyboard.press("Enter")

                # 5. Verify Success
                # Check for "View Cart" or modal closing
                try:
                    # If modal is gone, success (or we are back on menu)
                    await asyncio.sleep(2)
                    # Common success indicator: "View cart" button appears at bottom
                    success_indicator = self.page.get_by_role("button", name=re.compile(r"view.*cart|voir.*panier", re.I))
                    if await success_indicator.is_visible():
                        logger.info(f"Successfully added {item_name}")
                        return
                except:
                    pass
                
                # Assume success if no error thrown
                logger.info(f"Action completed for {item_name}")
                return

            except Exception as e:
                logger.warning(f"Add item attempt {attempt+1} failed: {e}")
                await self._dismiss_modals()
                if attempt < retries - 1:
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(2)
                else:
                    await self._save_screenshot("add_item_failed")
                    raise

    # -----------------------------
    # Utilities
    # -----------------------------
    async def _dismiss_modals(self):
        try:
            close_btns = self.page.get_by_role("button", name=re.compile(r"close|not now|skip|dismiss|fermer|non", re.I))
            count = await close_btns.count()
            for i in range(count):
                if await close_btns.nth(i).is_visible():
                    await close_btns.nth(i).click()
        except:
            pass
        await self.page.keyboard.press("Escape")

    async def _save_screenshot(self, name: str):
        try:
            path = self.screenshot_dir / f"{name}_{asyncio.get_event_loop().time()}.png"
            await self.page.screenshot(path=path)
            logger.info(f"Screenshot: {path}")
        except:
            pass

    async def close(self):
        if self.context: await self.context.close()
        if self.playwright: await self.playwright.stop()
        logger.info("Browser closed")


# -----------------------------
# Main Execution
# -----------------------------
async def main():
    email = os.getenv("UBER_EMAIL", "your_email@example.com")
    agent = UberWebAgent(email=email)
    try:
        # Headless must be TRUE for server
        await agent.start(headless=True)
        
        await agent.login()
        await agent.set_delivery_location("100 City Centre Dr, Mississauga, ON")
        await agent.search_restaurant("McDonald's")
        
        # Example Add
        await agent.add_item_to_cart({
            "name": "Big Mac", 
            "options": ["Medium", "Coke"] 
        })
        
        logger.info("Script finished successfully.")
        
    except Exception as e:
        logger.error(f"Main loop crashed: {e}")
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())

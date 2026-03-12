import os
import asyncio
import re
import random
import shutil
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

class UberWebAgent:
    def __init__(self, email: str):
        self.email = email
        self.user_data_dir = "./uber_user_data"

    async def start(self):
        # 1. COMPLETELY WIPE CACHE to clear "bot" tags
        if os.path.exists(self.user_data_dir):
            shutil.rmtree(self.user_data_dir)
            
        self.playwright = await async_playwright().start()
        
        # 2. MOBILE EMULATION (Harder for DataDome to track via Xvfb)
        # Using a real Mobile Safari fingerprint is the most trusted for Uber
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            proxy={
                "server": "http://brd.superproxy.io:33335", 
                "username": "brd-customer-hl_79646542-zone-residential_proxy1",
                "password": "j86dw8kxpze1" 
            },
            channel="chrome", 
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
            has_touch=True,
            is_mobile=True,
            locale="en-CA",
            timezone_id="America/Toronto",
            ignore_https_errors=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        await Stealth().apply_stealth_async(self.page)

    async def run_order_flow(self, address: str):
        print("Navigating to Uber Eats...")
        # 3. USE 'COMMIT' WAIT (Avoids hanging on background bot-checks)
        await self.page.goto("https://www.ubereats.com", wait_until="commit")
        
        # 4. THE LONG WAIT: Let the background JS challenge finish
        print("Waiting 12s for Anti-Bot challenge to resolve...")
        await asyncio.sleep(12) 

        # 5. REFRESH ONCE (Often clears the "Javascript disabled" screen)
        if "Javascript" in await self.page.content():
            print("Refreshing to clear JS-gate...")
            await self.page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(5)

        # 6. ADDRESS INPUT (Human-like interaction)
        try:
            print(f"Entering address: {address}")
            addr_field = self.page.get_by_placeholder(re.compile(r"address|location|postal", re.I)).first
            await addr_field.wait_for(state="visible", timeout=15000)
            await addr_field.click()
            await addr_field.type(address, delay=120)
            await asyncio.sleep(2)
            await self.page.keyboard.press("Enter")
            
            # Wait for search results
            await asyncio.sleep(6)
            await self.page.screenshot(path="screenshots/success_check.png")
            print("Address set successfully.")
        except Exception as e:
            print(f"Flow failed: {e}")
            await self.page.screenshot(path="screenshots/final_fail.png")

async def main():
    agent = UberWebAgent(email="calvertonbeckford@gmail.com")
    await agent.start()
    await agent.run_order_flow("3359 morningstar drive")
    await agent.context.close()
    await agent.playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())

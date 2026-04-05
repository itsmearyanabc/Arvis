import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from typing import Optional, Dict

class ArvisStealthEngine:
    """
    Autonomous Browser Engine for Arvis.
    Uses Playwright with stealth plugins to mimic human behavior
    and bypass bot detection on AI chat interfaces.
    """
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.playwright = None

    async def start(self):
        """Initializes the playwright browser session."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

    async def create_stealth_context(self, proxy: Optional[Dict] = None):
        """
        Creates a new browser context with stealth active and optional proxy.
        :param proxy: Dictionary with 'server', 'username', 'password'.
        """
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            proxy=proxy,
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Apply stealth to this page context
        page = await context.new_page()
        await stealth_async(page)
        
        return context, page

    async def stop(self):
        """Cleanly shuts down the browser engine."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

if __name__ == "__main__":
    # Test Block
    async def main():
        engine = ArvisStealthEngine(headless=False)
        await engine.start()
        context, page = await engine.create_stealth_context()
        
        await page.goto("https://bot.sannysoft.com/") # Testing stealth score
        await asyncio.sleep(5)
        
        await engine.stop()
    
    asyncio.run(main())

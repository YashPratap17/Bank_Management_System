import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create a new context with video recording enabled
        context = await browser.new_context(
            record_video_dir="videos/",
            record_video_size={"width": 1920, "height": 1080},
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("http://localhost:8000/login/")
        
        print("Logging in...")
        await page.fill("#id_username", "DEMO2201")
        await page.fill("#id_password", "demopass123")
        await page.click("button[type='submit']")
        
        print("Waiting for dashboard to load...")
        await page.wait_for_url("http://localhost:8000/")
        await asyncio.sleep(2)
        
        print("Scrolling...")
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(2)
        await page.mouse.wheel(0, -500)
        await asyncio.sleep(1)
        
        print("Navigating to Analytics...")
        await page.goto("http://localhost:8000/analytics/")
        await asyncio.sleep(3)
        
        print("Navigating to Manage Cards...")
        await page.goto("http://localhost:8000/manage-cards/")
        await asyncio.sleep(3)
        
        print("Navigating to Transaction History...")
        await page.goto("http://localhost:8000/ledger/history/")
        await asyncio.sleep(3)
        
        print("Closing context (saves video)...")
        await context.close()
        await browser.close()
        print("Video recording completed.")

asyncio.run(run())

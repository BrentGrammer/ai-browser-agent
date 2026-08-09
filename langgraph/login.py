import asyncio
import os
import signal

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Config lives in the repo-root .env; a .env next to the script wins if present.
load_dotenv(os.path.join(os.getcwd(), ".env"))
load_dotenv(os.path.join(os.getcwd(), "..", ".env"))

TARGET_URL = os.getenv("TARGET_URL")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "/tmp/user_profile")
BROWSER_PROXY = os.getenv("BROWSER_PROXY")


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    async with async_playwright() as p:
        launch_kwargs = dict(user_data_dir=USER_DATA_DIR, headless=False)
        if BROWSER_PROXY:
            launch_kwargs["proxy"] = {"server": BROWSER_PROXY}
        context = await p.chromium.launch_persistent_context(**launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(TARGET_URL, wait_until="load")

        print("Login mode: log in by hand through the viewer, then stop with Ctrl+C.")
        print("The session is saved in the browser profile and reused by the agent.")
        await stop.wait()
        await context.close()


asyncio.run(main())

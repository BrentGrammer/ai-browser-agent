import asyncio
import os
import signal
import sys
import threading

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Config lives in the repo-root .env; a .env next to the script wins if present.
load_dotenv(os.path.join(os.getcwd(), ".env"))
load_dotenv(os.path.join(os.getcwd(), "..", ".env"))

TARGET_URL = os.getenv("TARGET_URL")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "/tmp/user_profile")
BROWSER_PROXY = os.getenv("BROWSER_PROXY")


async def main():
    done = asyncio.Event()
    loop = asyncio.get_running_loop()
    # Ctrl+C still exits cleanly, but Enter is the advertised way out.
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, done.set)

    p = await async_playwright().start()
    # chromium_sandbox=True: keep Chromium's own sandbox on (playwright defaults it off).
    launch_kwargs = dict(user_data_dir=USER_DATA_DIR, headless=False, chromium_sandbox=True)
    if BROWSER_PROXY:
        launch_kwargs["proxy"] = {"server": BROWSER_PROXY}
    context = await p.chromium.launch_persistent_context(**launch_kwargs)
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(TARGET_URL, wait_until="load")

    print(f"The sandbox browser is open on {TARGET_URL}. To log in:")
    print("  1. In your own browser, open the viewer: http://<host>:6080/vnc.html")
    print("     (<host> is localhost for local Docker, or the box's Tailscale name,")
    print("      e.g. agent-workbench, for a remote box)")
    print("  2. Click Connect. You'll see the sandbox browser showing your app.")
    print("  3. Log in there by hand — typing, 2FA, everything works as usual.")
    print("  4. Come back to this terminal and press Enter.")
    # Daemon thread, not run_in_executor: a blocked readline must not stall
    # loop shutdown when Ctrl+C ends the wait instead of Enter.
    threading.Thread(
        target=lambda: (sys.stdin.readline(), loop.call_soon_threadsafe(done.set)),
        daemon=True,
    ).start()
    await done.wait()

    # On Ctrl+C the signal also reaches the Playwright driver process, which
    # can die before these calls; the profile is already on disk either way.
    for shutdown in (context.close, p.stop):
        try:
            await shutdown()
        except Exception:
            pass

    print("Login session saved in the browser profile. Next: ./agent run")


asyncio.run(main())

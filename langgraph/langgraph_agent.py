import asyncio
import json
import os
from datetime import datetime
from typing import TypedDict, Annotated
from urllib.parse import urlparse

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool
from playwright.async_api import async_playwright, Page

basedir = os.getcwd()
# Config lives in the repo-root .env; a .env next to the script wins if present.
load_dotenv(os.path.join(basedir, '.env'))
load_dotenv(os.path.join(basedir, '..', '.env'))

# ========================= CONFIG =========================
BASE_URL = os.getenv("TARGET_URL")
# "provider:model", e.g. "openai:gpt-4o" or "anthropic:claude-sonnet-4-5".
LLM_MODEL = os.getenv("LLM_MODEL")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "/tmp/user_profile")   # Persistent & secure login
MEMORY_FILE = os.getenv("MEMORY_FILE", "agent_knowledge.json")
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", os.path.join(basedir, 'screenshots'))
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
# Set in Docker so all browser traffic goes through the egress-allowlist proxy.
BROWSER_PROXY = os.getenv("BROWSER_PROXY")


def allowed_nav_hosts() -> set:
    """Hosts the agent may navigate to: the target site plus ALLOWED_DOMAINS."""
    hosts = set()
    if BASE_URL and urlparse(BASE_URL).hostname:
        hosts.add(urlparse(BASE_URL).hostname)
    extra = os.getenv("ALLOWED_DOMAINS", "")
    hosts.update(h.strip() for h in extra.split(",") if h.strip())
    return hosts

# Specific selectors for elements to wait for depending on the page
Selectors = {
    "MAIN_PAGE_SELECTOR": "#tickers-input, #main-content, .container",
}
# =========================================================

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Persistent knowledge (how the agent "learns" your app)
def load_knowledge() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"learned_patterns": [], "successful_actions": []}

def save_knowledge(knowledge: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(knowledge, f, indent=2)

class AgentState(TypedDict):
    messages: Annotated[list, "add"]
    knowledge: dict
# ====================== PLAYWRIGHT TOOLS ======================

async def wait_for_stable_page(page: Page, wait_for_selector: str = "", timeout: int = 10000) -> None:
    await page.wait_for_load_state("load", timeout=timeout)
    # For jquery/multi-page apps
    # await page.wait_for_function(
    #     "window.jQuery ? jQuery.active === 0 : true",
    #     timeout=timeout
    # )

    # also wait for a specific selector
    # Add your specific ticker form to the list of "ready" signals
    if wait_for_selector:
        await page.wait_for_selector(
            wait_for_selector,
            # "#tickers-input, #main-content, .container", 
            state="visible", 
            timeout=8000
        )
    # short timeout for rendering
    await page.wait_for_timeout(400)


async def get_current_page_state(page: Page, wait_for_selector: str) -> str:
    await wait_for_stable_page(page, wait_for_selector)
    title = await page.title()
    url = page.url
    body_text = await page.evaluate("() => document.body.innerText.substring(0, 6000)")
    return f"Title: {title}\nURL: {url}\n\nVisible text preview:\n{body_text}"


# ====================== MAIN PROGRAM ======================
async def main():
    knowledge = load_knowledge()

    async with async_playwright() as p:
        # chromium_sandbox=True keeps Chromium's own sandbox on (playwright defaults
        # it OFF). In Docker this needs docker/seccomp_profile.json (see compose).
        launch_kwargs = dict(
            user_data_dir=USER_DATA_DIR,
            headless=HEADLESS,
            chromium_sandbox=True,
        )
        if BROWSER_PROXY:
            launch_kwargs["proxy"] = {"server": BROWSER_PROXY}
        context = await p.chromium.launch_persistent_context(**launch_kwargs)
        page = context.pages[0] if context.pages else await context.new_page()

        # NOTE: TOOLS must have JSON serializable arguments, just use primitives and not complex objects etc.
          # We capture 'page' in a closure instead of passing it into the tools to avoid this problem
        @tool
        async def navigate_to(url: str) -> str:
            """Navigate to a specific URL."""
            # Allowlist check: a prompt-injected instruction can't send the agent off-site.
            host = urlparse(url).hostname or ""
            allowed = allowed_nav_hosts()
            if not any(host == h or host.endswith("." + h) for h in allowed):
                return f"Blocked: '{host}' is not an allowed navigation domain."
            await page.goto(url, wait_until="load")
            return f"Navigated to {url}"
        
        @tool
        async def click_text(text: str) -> str:
            """Click any visible text on the page. Use this for buttons, links, or menu items."""
            
            # Try to be specific first: Look for a button or link with this text
            # This solves the multiple elements with the same text problem. using get_by_text() fails since playwright will not choose if two elements have the same text on the page
            button_locator = page.get_by_role("button", name=text, exact=False)
            link_locator = page.get_by_role("link", name=text, exact=False)
            
            try:
                if await button_locator.count() > 0:
                    await button_locator.first.click()
                elif await link_locator.count() > 0:
                    await link_locator.first.click()
                else:
                    # Fallback to the generic text locator if it's not a button/link
                    # use .first to avoid strict mode errors if multiple things still exist
                    await page.get_by_text(text, exact=False).first.click()
                    
                await wait_for_stable_page(page=page)
                return f"Clicked text: '{text}'"
            except Exception as e:
                return f"Error clicking '{text}': {str(e)}"

        @tool
        async def fill_field(selector_or_text: str, value: str) -> str:
            """
            Fill a text input, password field, or textarea. 
            selector_or_text: Can be the ID (e.g. '#something'), 
                            the placeholder (e.g. 'Ex: Something'), 
                            or the label text.
            value: The text to type into the field.
            """
            try:
                # 1. Try finding by CSS selector (best for IDs like #tickers-input)
                locator = page.locator(selector_or_text)
                
                # 2. If that fails, try finding by Label (better for 'Username' or 'Password')
                if await locator.count() == 0:
                    locator = page.get_by_label(selector_or_text, exact=False)
                    
                # 3. If still nothing, try by Placeholder
                if await locator.count() == 0:
                    locator = page.get_by_placeholder(selector_or_text, exact=False)

                # Ensure we use the first one if multiple are found
                target = locator.first
                
                # Highlight it for the screenshot/human visibility (optional but helpful)
                await target.scroll_into_view_if_needed()
                
                # Clear it first to be safe, then fill
                await target.fill(value)
                
                return f"Successfully filled '{selector_or_text}' with value."
            except Exception as e:
                return f"Error filling field '{selector_or_text}': {str(e)}"
        
        @tool
        async def take_screenshot(filename: str = "") -> str:
            """Take a full-page screenshot. Provide a base filename (no ext)."""
            if not filename:
                filename = f"step_{datetime.now().strftime('%H%M%S')}.png"
            elif not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                filename += ".png" # TODO: just check if there is an extension - i.e. last 3-4 chars and a dot
                
            path = os.path.join(SCREENSHOT_DIR, filename)
            await page.screenshot(path=path, full_page=True)
            return f"Screenshot saved: {path}"
        
        @tool
        async def get_page_state() -> str:
            """Get current page observation for the agent to reason about."""
            return await get_current_page_state(page=page, wait_for_selector=Selectors["MAIN_PAGE_SELECTOR"])


        # Auth comes from the persistent profile; log in once via login.py (LOGIN_MODE).
        await page.goto(BASE_URL, wait_until="load")

        print("🚀 Starting AI Agent Program")

        # Create tools bound to the current page
        tools = [navigate_to, fill_field, click_text, take_screenshot, get_page_state]

        if not LLM_MODEL:
            raise SystemExit("Set LLM_MODEL in .env, e.g. openai:gpt-4o")
        # temperature 0 keeps results rigid and less creative
        llm = init_chat_model(LLM_MODEL, temperature=0, api_key=os.getenv("LLM_API_KEY"))

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt="""You are a careful power-user agent controlling a web application.
You must be precise, take screenshots after important steps, and learn patterns for future runs.
Always use the available tools. Prefer clicking by visible text for navigation.""",
        )

        task = """
        - You are already logged in.
        - Open the hamburger menu in the top left.
        - Click on "My Saved Lists".
        - Take a screenshot of the resulting page.
        - Describe what you see and note any useful patterns (e.g. how the nav works) for future runs.
        """

        # Run the agent
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": task}],
            "knowledge": knowledge
        })

        # Save what was learned to a knowledge file the agent can reference next time.
        messages = result.get("messages", [])
        # Get the very last message from the agent (usually the final summary/reasoning)
        final_agent_message = next(
            (m for m in reversed(messages) if hasattr(m, "content") and m.content.strip()),
            None
        )
        final_summary = final_agent_message.content if final_agent_message else "No output"
        updated_knowledge = {
            "learned_patterns": knowledge.get("learned_patterns", []) + [final_summary],
            "successful_actions": [
                m.content
                for m in messages
                if hasattr(m, "content") and m.content.strip()
            ]
        }
        save_knowledge(updated_knowledge)

        # print(f'result: {repr(result)}')
        # print(f'result keys: {repr(result.keys())}')
        # print(f'last message type: {type(result["messages"][-1])}')
        print("\n✅ Agent Program completed!")
        print(f"Screenshots saved in {SCREENSHOT_DIR}")
        print(f"Knowledge saved to {MEMORY_FILE} — run again to see learning in action.")

        print("\nBrowser window is still open for inspection. Press Enter to close...")
        # input() # uncomment this if you want the browser to stay open until you hit enter in the terminal.

        # await context.close()   # Only uncomment if you want fresh session each time

asyncio.run(main())


# ### Alternative instead of Context manager:
# # Outside the async with — keeps Playwright running longer
# p = await async_playwright().start()
# context = await p.chromium.launch_persistent_context(...)

# # ... run agent ...

# # Only close when the whole program ends
# await context.close()
# await p.stop()
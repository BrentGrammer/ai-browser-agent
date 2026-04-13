import asyncio
import json
import os
from datetime import datetime
from typing import TypedDict, Annotated

from dotenv import load_dotenv
# or use gemini: from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool
from playwright.async_api import async_playwright, Page

basedir = os.getcwd()
# Point to the .env file in that same directory
load_dotenv(os.path.join(basedir, '.env'))

# ========================= CONFIG =========================
BASE_URL = os.getenv("TARGET_URL")
USER_DATA_DIR = "/tmp/user_profile"   # Persistent & secure login
MEMORY_FILE = "agent_knowledge.json"
SCREENSHOT_DIR = os.path.join(basedir, 'screenshots')

LOGIN_USERNAME = os.getenv("LOGIN_USERNAME")
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD")

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
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,                    # Set to True for background runs
            args=["--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # NOTE: TOOLS must have JSON serializable arguments, just use primitives and not complex objects etc.
          # We capture 'page' in a closure instead of passing it into the tools to avoid this problem
        @tool
        async def navigate_to(url: str) -> str:
            """Navigate to a specific URL."""
            await page.goto(url, wait_until="load")
            return f"Navigated to {url}"

        @tool
        async def click_text(text: str) -> str:
            """Click any visible text on the page."""
            await page.get_by_text(text, exact=False).click()
            await wait_for_stable_page(page=page)
            return f"Clicked text: '{text}'"

        
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


        # Load the website first
        await page.goto(BASE_URL, wait_until="load")

        print("🚀 Starting AI Agent Program")

        # Create tools bound to the current page
        tools = [navigate_to, click_text, take_screenshot, get_page_state]

        # setting temperature to 0 to make the results more rigid and less creative
        llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
        # Or use Gemini:
        # llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.5-flash",      # or "gemini-2.5-pro" for more power
        #     temperature=0,
        #     # google_api_key=os.getenv("GOOGLE_API_KEY")
        # )

        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt="""You are a careful power-user agent controlling a web application.
You must be precise, take screenshots after important steps, and learn patterns for future runs.
Always use the available tools. Prefer clicking by visible text for navigation.""",
        )

        task = f"""
        - Go to the login page (click on the link in the top right corner of the page with the text "Login").
        - Find the Email Field on the login page and enter: {LOGIN_USERNAME}, then find the Password field and enter: {LOGIN_PASSWORD}).
        - After the fields have been filled out, click the submit button (it is a submit button type with a title "LOG IN" in all caps, and NOT "Log In" which is just the header on the page).
        - After logged in, Open the hamburger menu in the top left.
        - Click on "My Saved Lists".
        - Take a screenshot of the resulting page.
        - Describe what you see and note any useful patterns (e.g. how the nav works) for future runs.
        """

        # Run the agent
        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": task}],
            "knowledge": knowledge
        })

        # Save what was learned
        # final_knowledge = {
        #     "learned_patterns": knowledge.get("learned_patterns", []) + [str(result.get("output", ""))], # this needs to be serializable (not objects)
        #     "successful_actions": [msg.get("content", "") for msg in result.get("messages", []) if isinstance(msg, dict)]
        # }
        final_knowledge = {
            "learned_patterns": [],
            "successful_actions": []
        }
        save_knowledge(final_knowledge)

        print(f'result: {repr(result)}')
        print("\n✅ Agent Program completed!")
        print(f"Screenshots saved in ./{SCREENSHOT_DIR}/")
        print(f"Knowledge saved to {MEMORY_FILE} — run again to see learning in action.")

        print("\nBrowser window is still open for inspection. Press Enter to close...")
        input()

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
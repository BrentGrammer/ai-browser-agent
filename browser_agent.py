import asyncio
import os
from dotenv import load_dotenv
# resolve permission denied errors
# The BROWSER_USE_CONFIG_DIR (which you set to browser_use_config) handles the library's settings, while temp_profile handles the browser's data (cookies, history, cache). By using a temp folder for the browser profile, you avoid any permission drama that usually happens in protected system folders.
os.environ['BROWSER_USE_CONFIG_DIR'] = os.path.join(os.getcwd(), 'browser_use_config')

from browser_use import Agent, Browser, ChatOpenAI

import tempfile

load_dotenv()
LLM_API_KEY=os.getenv('OPENAI_API_KEY')
LOGIN_PASSWORD=os.getenv('LOGIN_PASSWORD')

async def main():

    # Permission denied error - create a user dir
    temp_profile = os.path.join(tempfile.gettempdir(), "browseruse_session")

    URL = "http://stock-glasses.com/"
    username = "brent@gmail.com" # TODO: put these in .env
    password = LOGIN_PASSWORD

    browser = Browser(
        # Optional: run headed (visible browser) for debugging your legacy app
        headless=False,           # Set True later for background runs
        # persistent_context=True  # Uncomment if you want to reuse login cookies
        user_data_dir=temp_profile,
        downloads_path=os.path.join(os.getcwd(), "screenshots")
    )
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=LLM_API_KEY
    )
    task = f"""
    1. Go to the application login page at {URL}.
    2. Log in with username: {username} and password: {password}.
    3. Wait for the page to finish loading after logging in.
    4. Click on the hamburger menu in the top left corner of the page and select the option labeled My Saved Lists.
    5. After the page loads, take a screenshot and save it as "my_saved_lists.png".
    6. Summarize what you see on the final page.
    """

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=True,             # Important for web apps
        # save_recording_path="recordings"  # Optional: also record video
    )

    result = await agent.run()
    print("Task completed!", result.final_result() if hasattr(result, 'final_result') else result)

if __name__ == "__main__":
    asyncio.run(main())
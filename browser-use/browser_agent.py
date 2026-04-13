import asyncio
import os
import shutil
import glob
from dotenv import load_dotenv

# Permission Denied for /.config folder mitigation: 
#   The BROWSER_USE_CONFIG_DIR handles the library's settings, while temp_profile handles the browser's data (cookies, history, cache). 
#   By using a temp folder for the browser profile, you avoid any permission drama that usually happens in protected system folders.
os.environ['BROWSER_USE_CONFIG_DIR'] = os.path.join(os.getcwd(), 'browser_use_config')
# This stops browser-use from sending telemetry and can reduce log verbosity
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
# To disable the printing of LLM inputs/outputs entirely in some environments:
# os.environ['BROWSER_USE_LOGGING_LEVEL'] = 'info'

from browser_use import Agent, Browser, ChatOpenAI, Browser


import tempfile

load_dotenv()

required_params = {
    "LLM_API_KEY": os.getenv('OPENAI_API_KEY'),
    "LOGIN_USERNAME": os.getenv('LOGIN_USERNAME'),
    "LOGIN_PASSWORD": os.getenv('LOGIN_PASSWORD'),
    "TARGET_URL":  os.getenv('TARGET_URL'),
}

async def main():

    try:
        for k,v in required_params.items():
            if not v:
                raise Exception(f"A required parameter {k} is missing")

        # Related to Permission denied error for ~/.config folder - create a temp dir to store the session
        temp_profile = os.path.join(tempfile.gettempdir(), "browseruse_session")

        # Reset session cleanly every time
        # Since you are using a temp_profile, the browser should technically be empty (logged out) every time unless:
            # Session Persistence: You are reusing the user_data_dir without clearing it.
            # Shared State: The website uses IP-based or local-storage persistence that survives a basic profile wipe.
        if os.path.exists(temp_profile):
            shutil.rmtree(temp_profile) # Physically delete the session data

        # The key (left) is the placeholder used in the task.
        # The value (right) is the actual secret.
        sensitive_data = {
            "SECRET_PW": required_params.get("LOGIN_PASSWORD"),
            "SECRET_USERNAME": required_params.get("LOGIN_USERNAME")
        }

        browser = Browser(
            # Optional: run headed (visible browser) for debugging your legacy app
            headless=False,           # Set True later for background runs
            # persistent_context=True  # Uncomment if you want to reuse login cookies
            user_data_dir=temp_profile,
            downloads_path=os.path.join(os.getcwd(), "screenshots"),
            # Force a wait so the AI doesn't panic and start clicking random things
            wait_for_network_idle_page_load_time=2.0, 
            minimum_wait_page_load_time=1.0,
            # Add this to suppress the 'unsupported flag' infobar
            # args=[
            #     # suppress warning about extensions flag:
            #     '--test-type',
            #     # # This disables the "password leak" check specifically
            #     # '--disable-component-update', 
            #     # '--password-store=basic',
            #     # This prevents the "Save Password" and "Breach" prompts
            #     '--disable-features=SafeBrowsingPasswordCheck'
            # ],
            args=[
                '--test-type',
                # Disable the specific security feature causing the popup
                '--disable-features=SafeBrowsingPasswordCheck,PasswordLeakToggleMove,SafeBrowsing',
                # Stops Chrome from interacting with any OS-level password vaults
                '--password-store=basic',
                # Stops the "Save Password" bubble
                '--disable-save-password-bubble',
                # Essential: Forces a fresh session that doesn't "remember" the breach
                '--guest',
                # Removes the "Automation" banner which can trigger extra security
                '--disable-infobars'
            ]               
        )

        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=required_params.get("LLM_API_KEY")
        )
        task = f"""
        MAIN GOAL: The goal of this task is to login to a web application specified in the task steps and take a screenshot of a specified page in the app.
        CRITICAL PRE-CONDITION:
        1. Load {required_params.get("TARGET_URL")}.
        2. IMMEDIATELY check if you are logged in (look for a logout button option in the menu in the top right corner of the home page). You will need to click the menu either in the top right corner of the page or the top left corner and look for a "Logout" option to determine if you are logged in.
        3. INITIAL CHECK ONLY: Only if you are already logged in at the very start of this task (before you enter any credentials), stop and return: "TERMINATED: Account already logged in." Once you begin the login process in Step 4, ignore this rule.
        4. ONLY IF you see the login screen, proceed with the following steps:
            - Verify that you are on the correct login page and screen. The url should include the string "login". 
            - On the login page, if the previous checks have been verified, find the form field for "Email". Enter SECRET_USERNAME into it.
            - Find the field for the password labeled "password" and fill it in with SECRET_PW.
            - Wait for the page to finish loading after logging in and check for any alerts or popup messages that require acknowledgement to continue and click OK.
            - After the popup alerts or modals are gone, click on the hamburger menu in the top left corner of the page and select the option labeled My Saved Lists.
            - After the page 'My Saved Lists' loads, wait 2 seconds.
            - Summarize what you see on the final page.
        """

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            sensitive_data=sensitive_data, # the key names match with the values in the dictionary - no special chars are needed like {} in the task string, but they need to be unambiguous and unique
            use_vision=True,             # Important for web apps
            # save_recording_path="recordings"  # Optional: also record video
            max_steps=20,             # Total actions allowed (default is 100!)
            max_failures=2,           # Stop if it fails a single step twice
            use_thinking=True,        # Keep this True; it helps it "realize" it's stuck
            # By leaving out 'save_as_pdf', the agent is forced to use 'take_screenshot'. this prevents the fallback of taking a pdf screenshot
            # included_actions=['open_url', 'click_element', 'input_text', 'take_screenshot'],
            system_prompt="CRITICAL: Never use the save_as_pdf tool. If take_screenshot fails, describe the error. PDF is forbidden.",
            # CRITICAL: Stops the browser from killing itself before you snap the photo
            close_on_finished=False

        )

        result = await agent.run()

        cwd = os.getcwd()
        final_path = os.path.join(cwd, "screenshots/my_saved_lists.png")
        print(f"Forcing screenshot to: {final_path}")

        # requires the Agent to stay open. Ensure close_on_finished=False is set.
        page = await browser.get_current_page()
        if page:
            await page.screenshot(path=final_path, full_page=True)
            print(f"✅ VERIFIED: Screenshot saved at {final_path}")
        else:
            # FALLBACK: If the browser closed too fast, check the agent's history
            print("Browser closed too fast. Checking history...")
            paths = agent.history.screenshot_paths()
            if paths:
                shutil.copy(paths[-1], final_path)
                print(f"✅ RECOVERED: Copied from history to {final_path}")

        if result.is_done():
            print("Task completed!", result.final_result() if hasattr(result, 'final_result') else result)
        else:
            errors = result.errors() if result.errors() else "No errors found"
            raise Exception(f"Task FAILED: {errors}")
        

    except Exception as ex:
        print(f"There was an error: {repr(ex)}")

    finally:
        # Find all agent temp folders in the system temp directory
        temp_pattern = os.path.join(tempfile.gettempdir(), "browser_use_agent_*")
        print(f"Cleaning temp location: {temp_pattern}")

        for folder in glob.glob(temp_pattern):
            try:
                shutil.rmtree(folder)
                print(f"Cleaned up: {folder}")
            except Exception as e:
                print(f"Could not delete {folder}: {e}")
        
    # finally: TODO: how to close the browser if terminated?
    #     if browser:
    #         print("Closing agent browser")
    #         await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
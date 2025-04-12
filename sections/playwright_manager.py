import os
import re
import subprocess
import time
import asyncio
import random  # Added for random delays
from tkinter import messagebox
from patchright.async_api import async_playwright




class PlaywrightManager:
    """Manages Playwright webdriver installation and browser testing."""
    _instance = None
    _webdriver_path = None
    _sessions_base_dir = "C:/Users/matut/Desktop/compilador Python/Automation_panel/sessions"  # Base directory for all session folders



    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_path(print)
            # Ensure the sessions base directory exists
            os.makedirs(cls._sessions_base_dir, exist_ok=True)
        return cls._instance




    def _initialize_path(self, log_func):
        """Set webdriver path if it exists and contains a usable Chromium executable."""
        home_dir = os.path.expanduser("~")
        path = os.path.join(home_dir, "AppData", "Local", "ms-playwright")
        
        if not os.path.exists(path):
            log_func(f"Playwright path not found: {path}")
            return
            
        chromium_dir = self._find_chromium_dir(path, log_func)
        if chromium_dir and self._verify_chromium_executable(chromium_dir, log_func):
            self._webdriver_path = path
            log_func(f"Webdriver path initialized: {self._webdriver_path}")




    def _verify_chromium_executable(self, chromium_dir, log_func):
        """Verify the Chromium executable exists."""
        chromium_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")
        exists = os.path.exists(chromium_path)
        if not exists:
            log_func(f"Chromium executable not found at: {chromium_path}")
        return exists




    @property
    def webdriver_path(self):
        """Get the current webdriver path."""
        return self._webdriver_path




    def install_webdrivers(self, log_func, update_progress):
        """Install Playwright webdrivers with progress updates."""
        log_func("Starting webdriver installation...")
        update_progress("Installing...", 0.1)

        try:
            result = self._run_playwright_install(log_func)
            if not result:
                update_progress("Installation failed", 1.0)
                return False
        except Exception as e:
            log_func(f"Installation exception: {str(e)}")
            update_progress(f"Error: {str(e)}", 1.0)
            return False

        # Simulate download progress
        self._simulate_progress(update_progress)
        
        # Verify installation
        home_dir = os.path.expanduser("~")
        self._webdriver_path = os.path.join(home_dir, "AppData", "Local", "ms-playwright")
        
        chromium_dir = self._find_chromium_dir(self._webdriver_path, log_func)
        if not chromium_dir or not self._verify_chromium_executable(chromium_dir, log_func):
            log_func("Invalid or missing webdriver installation")
            update_progress("Error: Installation incomplete", 1.0)
            return False

        update_progress("Complete!", 1.0)
        log_func(f"Webdrivers installed at: {self._webdriver_path}")
        return True



    ##-------------------Webdrivers installation commands-------------------------##
    def _run_playwright_install(self, log_func):
        """Run the playwright install command."""
        try:
            process = subprocess.run(
                ["playwright", "install", "--with-deps"],
                capture_output=True,
                text=True,
                check=True
            )
            log_func(f"Installation output: {process.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            log_func(f"Installation failed: {e.stderr}")
            return False



    def _simulate_progress(self, update_progress):
        """Simulate download progress for the UI."""
        for i in range(1, 10):
            time.sleep(0.5)
            update_progress("Downloading...", 0.1 + i * 0.09)



    def _get_session_dir(self, account_id):
        """Get the session directory for a given account ID, creating it if it doesn't exist."""
        session_dir = os.path.join(self._sessions_base_dir, f"session_{account_id}")
        os.makedirs(session_dir, exist_ok=True)  # Create the directory if it doesn't exist
        return session_dir



    async def test_browser(self, email, password, account_id, log_func):
        """Test browser for a single account."""
        chromium_exe = self._get_chromium_executable(log_func)
        if not chromium_exe:
            messagebox.showwarning("No Webdrivers", "No webdrivers available. Please install them in Settings.")
            return False

        log_func(f"Launching Chromium from: {chromium_exe} for account {account_id}")
        return await self._run_browser_test(chromium_exe, email, password, account_id, log_func)



    async def test_multiple_accounts(self, accounts, log_func):
        """Test multiple accounts concurrently, with a limit of 20 at a time."""
        chromium_exe = self._get_chromium_executable(log_func)
        if not chromium_exe:
            messagebox.showwarning("No Webdrivers", "No webdrivers available. Please install them in Settings.")
            return {account["account_id"]: False for account in accounts}




        ###########-----------------CONFIGURABLE STEP----------------------#############
        # Limit concurrency to N browser instances at a time-----------!!!!!!!!!!!!!!
        semaphore = asyncio.Semaphore(9)
        results = {}

        async def test_account_with_semaphore(account):
            async with semaphore:
                log_func(f"Starting test for account {account['account_id']}")
                success = await self._run_browser_test(
                    chromium_exe,
                    account["email"],
                    account["password"],
                    account["account_id"],
                    log_func
                )
                return account["account_id"], success




        ###########-----------------CONFIGURABLE STEP----------------------#############
        # Process accounts in batches--------------!!!!!!!!!!!!!!!!!!
        batch_size = 3
        for i in range(0, len(accounts), batch_size):
            batch = accounts[i:i + batch_size]
            log_func(f"Processing batch {i // batch_size + 1} with {len(batch)} accounts")
            
            tasks = [test_account_with_semaphore(account) for account in batch]
            
            for completed_task in asyncio.as_completed(tasks):
                account_id, success = await completed_task
                results[account_id] = success
                log_func(f"Completed test for account {account_id}: {'Success' if success else 'Failed'}")

        return results




    def _get_chromium_executable(self, log_func):
        """Get the path to the Chromium executable."""
        if not self._webdriver_path:
            log_func("Webdriver path not set")
            return None
            
        chromium_dir = self._find_chromium_dir(self._webdriver_path, log_func)
        if not chromium_dir:
            return None
            
        chromium_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")
        if not os.path.exists(chromium_path):
            log_func(f"Chromium executable missing: {chromium_path}")
            return None
            
        return chromium_path



    ################################################################################################################
    ##---------------------------------!!! BROWSER ENGINE  !!!-----------------------------------------------------#
    async def _run_browser_test(self, chromium_exe, email, password, account_id, log_func):
        """Run the actual browser test for a specific account: navigate to Facebook login, type email and password with random delays, take screenshot."""
        try:
            # Get the session directory for this account
            user_data_dir = self._get_session_dir(account_id)
            log_func(f"Using session directory for account {account_id}: {user_data_dir}")

            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    no_viewport=True,
                    channel="chrome",
                    headless=False,
                    user_data_dir=user_data_dir
                )
                
                page = await browser.new_page()
                await page.goto("https://www.facebook.com/login")
                log_func(f"Navigated to Facebook login page for account {account_id}")

                email_field = await page.wait_for_selector("input#email", timeout=30000)
                password_field = await page.wait_for_selector("input#pass", timeout=30000)

                # Type the email with random delays between characters
                for char in email:
                    await email_field.type(char, delay=0)  # No delay in Playwright's type method; we'll add our own
                    await asyncio.sleep(random.uniform(0.05, 0.3))  # Random delay between 50ms and 300ms per character
                
                # Random delay between email and password fields (0.5 to 2 seconds)
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Type the password with random delays between characters
                for char in password:
                    await password_field.type(char, delay=0)  # No delay in Playwright's type method; we'll add our own
                    await asyncio.sleep(random.uniform(0.05, 0.3))  # Random delay between 50ms and 300ms per character
                
                log_func(f"Typed email and password fields with random delays for account {account_id}")

                await asyncio.sleep(random.uniform(4, 8))

                screenshot_dir = 'facebook_login_tests'
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = f'{screenshot_dir}/login_form_filled_account_{account_id}.png'
                
                await page.screenshot(path=screenshot_path)
                log_func(f"Took screenshot of filled login form for account {account_id}: {screenshot_path}")

                await browser.close()
                return True
        except Exception as e:
            log_func(f"Browser test failed for account {account_id}: {str(e)}")
            return False



    def _find_chromium_dir(self, base_path, log_func):
        """Find the chromium-<version> directory."""
        if not os.path.exists(base_path):
            log_func(f"Path does not exist: {base_path}")
            return None
        
        try:
            contents = os.listdir(base_path)
            for dir_name in contents:
                if dir_name.startswith("chromium-"):
                    return os.path.join(base_path, dir_name)
                    
            log_func("No chromium directory found")
            return None
        except Exception as e:
            log_func(f"Error finding chromium directory: {str(e)}")
            return None

playwright_mgr = PlaywrightManager()  # Global instance
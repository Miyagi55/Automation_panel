import os
import subprocess
import time
from tkinter import messagebox
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import asyncio

class PlaywrightManager:
    """Manages Playwright webdriver installation and browser testing."""
    _instance = None
    _webdriver_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_path(lambda x: print(f"INIT LOG: {x}"))  # Debug to console
        return cls._instance

    def _initialize_path(self, log_func):
        """Set webdriver path if it exists and contains a usable Chromium executable."""
        home_dir = os.path.expanduser("~")
        path = os.path.join(home_dir, "AppData", "Local", "ms-playwright")
        log_func(f"Checking path on startup: {path}")
        
        if not os.path.exists(path):
            log_func(f"Path does not exist: {path}")
            return
        
        # Check for chromium-<version> directory
        try:
            contents = os.listdir(path)
            log_func(f"Directory contents: {contents}")
            chromium_dir = next((d for d in contents if d.startswith("chromium-")), None)
            if not chromium_dir:
                log_func("No chromium-<version> directory found")
                return
            
            full_chromium_dir = os.path.join(path, chromium_dir)
            chromium_path = os.path.join(full_chromium_dir, "chrome-win", "chrome.exe")
            if os.path.exists(chromium_path):
                self._webdriver_path = path
                log_func(f"Webdriver path set on startup: {self._webdriver_path}")
            else:
                log_func(f"Chromium executable not found at: {chromium_path}")
        except Exception as e:
            log_func(f"Error during initialization: {str(e)}")

    @property
    def webdriver_path(self):
        """Get the current webdriver path."""
        return self._webdriver_path

    def install_webdrivers(self, log_func, update_progress):
        """Install Playwright webdrivers with progress updates."""
        log_func("Starting webdriver installation...")
        update_progress("Installing...", 0.1)

        try:
            process = subprocess.run(
                ["playwright", "install", "--with-deps"],
                capture_output=True,
                text=True,
                check=True
            )
            log_func(f"Installation output: {process.stdout}")
        except subprocess.CalledProcessError as e:
            log_func(f"Installation failed: {e.stderr}")
            update_progress(f"Error: {e.stderr}", 1.0)
            return False

        for i in range(1, 10):
            time.sleep(0.5)
            update_progress("Downloading...", 0.1 + i * 0.09)

        home_dir = os.path.expanduser("~")
        self._webdriver_path = os.path.join(home_dir, "AppData", "Local", "ms-playwright")
        
        if not os.path.exists(self._webdriver_path) or not self._find_chromium_dir(log_func):
            log_func(f"Invalid or missing webdrivers at: {self._webdriver_path}")
            update_progress("Error: Installation incomplete", 1.0)
            return False

        update_progress("Complete!", 1.0)
        log_func(f"Webdrivers installed at: {self._webdriver_path}")
        return True

    async def test_browser(self, email, password, log_func):
        """Test browser by opening Google and typing an email."""
        if not self._webdriver_path or not self._find_chromium_dir(log_func):
            log_func(f"Webdriver path invalid or missing: {self._webdriver_path}")
            messagebox.showwarning("No Webdrivers", "No webdrivers available. Please install them in Settings.")
            return False

        log_func(f"Using webdriver path: {self._webdriver_path}")
        chromium_dir = self._find_chromium_dir(log_func)
        chromium_path = os.path.join(chromium_dir, "chrome-win", "chrome.exe")

        if not os.path.exists(chromium_path):
            log_func(f"Chromium not found at: {chromium_path}")
            messagebox.showwarning("No Webdrivers", "Chromium executable missing. Please reinstall webdrivers in Settings.")
            return False

        log_func(f"Launching Chromium from: {chromium_path}")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(executable_path=chromium_path, headless=False)
                page = await browser.new_page()
                await stealth_async(page)
                
                await page.goto("https://www.google.com")
                search_box = await page.wait_for_selector("textarea[name='q']")
                await search_box.type(email)
                
                log_func(f"Typed '{email}' into Google search")
                await asyncio.sleep(5)
                await browser.close()
                return True
        except Exception as e:
            log_func(f"Test failed: {str(e)}")
            return False

    def _find_chromium_dir(self, log_func):
        """Find the chromium-<version> directory."""
        if not self._webdriver_path or not os.path.exists(self._webdriver_path):
            log_func(f"Path missing or invalid: {self._webdriver_path}")
            return None
        
        contents = os.listdir(self._webdriver_path)
        log_func(f"Directory contents: {contents}")
        
        for dir_name in contents:
            if dir_name.startswith("chromium-"):
                chromium_dir = os.path.join(self._webdriver_path, dir_name)
                log_func(f"Found chromium dir: {chromium_dir}")
                return chromium_dir
        
        log_func("No chromium-<version> directory found")
        return None

playwright_mgr = PlaywrightManager()  # Global instance
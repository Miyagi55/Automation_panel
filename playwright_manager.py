import os
import re
import subprocess
import time
import asyncio
from tkinter import messagebox
from patchright.async_api import async_playwright





class PlaywrightManager:
    """Manages Playwright webdriver installation and browser testing."""
    _instance = None
    _webdriver_path = None
    


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_path(print)
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



    async def test_browser(self, email, password, log_func):
        """Test browser by opening Google and typing an email."""
        chromium_exe = self._get_chromium_executable(log_func)
        if not chromium_exe:
            messagebox.showwarning("No Webdrivers", "No webdrivers available. Please install them in Settings.")
            return False

        log_func(f"Launching Chromium from: {chromium_exe}")
        return await self._run_browser_test(chromium_exe, email, log_func)



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


##---------------------------------!!! BROWSER ENGINE  !!-----------------------------------------------------#
    async def _run_browser_test(self, chromium_exe, email, log_func):
        """Run the actual browser test."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(executable_path=chromium_exe, headless=False)
                context = await browser.new_context(viewport={'width':640, 'height':800},locale='en-US')
                page = await context.new_page()
                
                urls = [
                        "https://blackhatworld.com/",
	                    "https://fv.pro/check-privacy/general",
                        "https://deviceandbrowserinfo.com/are_you_a_bot",
                        "https://fingerprint.com/products/bot-detection//",
                        "https://abrahamjuliot.github.io/creepjs/",
                        "https://bot.sannysoft.com/",
                        "https://iphey.com/",
                        "https://www.browserscan.net/",
                        "https://pixelscan.net/"
]
                pattern = r'([^./]+)\.[^.]+$'   # Captures the string before the last dot
                
                await asyncio.sleep(5)
                
                for url in urls:

                    domain_site = re.search(pattern, url)

                    await page.goto(url)
                    await asyncio.sleep(20)
                    
                    await page.screenshot(path=f'bot_detection_tests/{domain_site.group(1)}.png')
                    log_func(f"Took screenshot in {domain_site.group(1)}")
                #search_box = await page.wait_for_selector("textarea[name='q']")
                #await search_box.type(email)
                
                #log_func(f"Typed '{email}' into Google search")
                #await asyncio.sleep(5)
                await browser.close()
                return True
        except Exception as e:
            log_func(f"Browser test failed: {str(e)}")
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
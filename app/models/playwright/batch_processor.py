import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple


class BatchProcessor:
    """Handles batch processing of multiple accounts with concurrency control."""

    def __init__(self, session_handler: Any):
        self.session_handler = session_handler
        self.browser_contexts = {}  # Store browser contexts for each account_id
        self.playwright_instances = {}  # Store Playwright instances for each account_id

    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
        **kwargs,
    ) -> Dict[Any, Tuple[bool, bool]]:
        """
        Generic method to process items in batches with concurrency control.
        Returns a dict mapping items to (action_success, sim_success) tuples.
        Stores browser contexts and Playwright instances for later use.
        """
        if not items:
            log_func("No items to process")
            return {}

        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}
        self.browser_contexts.clear()  # Clear previous browser contexts
        self.playwright_instances.clear()  # Clear previous Playwright instances

        async def process_item_with_semaphore(
            item: Any,
        ) -> Tuple[Any, Tuple[bool, bool]]:
            async with semaphore:
                log_func(f"Starting processing for item {item}")
                try:
                    # Expect process_func to return (success, sim_success, browser, playwright_instance)
                    result = await process_func(item, log_func=log_func, **kwargs)
                    if not isinstance(result, tuple) or len(result) != 4:
                        log_func(f"Unexpected result format for item {item}: {result}")
                        return item, (False, False)
                    action_success, sim_success, browser, playwright_instance = result
                    self.browser_contexts[item] = browser
                    self.playwright_instances[item] = playwright_instance
                    log_func(
                        f"Stored browser context and Playwright instance for item {item}"
                    )
                    return item, (action_success, sim_success)
                except Exception as e:
                    log_func(f"Error processing item {item}: {str(e)}")
                    return item, (False, False)

        # Process items in batches
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            log_func(f"Processing batch {i // batch_size + 1} with {len(batch)} items")

            tasks = [process_item_with_semaphore(item) for item in batch]
            for completed_task in asyncio.as_completed(tasks):
                item, (action_success, sim_success) = await completed_task
                results[item] = (action_success, sim_success)
                log_func(
                    f"Completed processing for item {item}: "
                    f"Action {'Success' if action_success else 'Failed'}, "
                    f"Simulation {'Success' if sim_success else 'Failed'}"
                )

        return results

    async def auto_login_accounts(
        self,
        accounts: List[Dict[str, Any]],
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
    ) -> Dict[str, Tuple[bool, bool]]:
        """Tests multiple accounts with batching and concurrency limits."""
        browser_manager = self.session_handler.browser_manager
        if not browser_manager.get_chromium_executable(log_func):
            log_func("No chromium executable available")
            return {account["account_id"]: (False, False) for account in accounts}

        # Map account_id to account details
        account_map = {account["account_id"]: account for account in accounts}

        async def login_task(
            account_id: str, log_func: Callable[[str], None]
        ) -> Tuple[bool, bool, Optional[Any], Optional[Any]]:
            account = account_map.get(account_id)
            if not account:
                log_func(f"Account not found for account_id {account_id}")
                return False, False, None, None
            return await self.session_handler.login_account(
                account["account_id"],
                account["user"],
                account["password"],
                log_func,
            )

        # Process account_ids instead of account dicts
        results = await self.process_batch(
            items=list(account_map.keys()),
            process_func=login_task,
            log_func=log_func,
            batch_size=batch_size,
            concurrent_limit=concurrent_limit,
        )
        return results

    def get_browser_context(self, item: Any) -> Optional[Any]:
        """Retrieve stored browser context for an item if it's still open."""
        browser = self.browser_contexts.get(item)
        if browser and hasattr(browser, "_closed") and browser._closed:
            return None
        return browser

    async def cleanup(self, log_func: Callable[[str], None]):
        """Close all stored browser contexts and stop Playwright instances."""
        for item, browser in list(self.browser_contexts.items()):
            if browser and not (hasattr(browser, "_closed") and browser._closed):
                try:
                    await browser.close()
                    log_func(
                        f"Closed browser context for item {item}"
                    )  # Simplified log
                except Exception as e:
                    log_func(f"Error closing browser context for item {item}: {str(e)}")
        for item, playwright_instance in list(self.playwright_instances.items()):
            if playwright_instance:
                try:
                    await playwright_instance.stop()
                    log_func(
                        f"Stopped Playwright instance for item {item}"
                    )  # Simplified log
                except Exception as e:
                    log_func(
                        f"Error stopping Playwright instance for item {item}: {str(e)}"
                    )
        self.browser_contexts.clear()
        self.playwright_instances.clear()
        log_func("Cleared browser contexts and Playwright instances")

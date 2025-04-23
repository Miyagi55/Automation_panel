import asyncio
from typing import Any, Callable, Dict, List, Tuple


class BatchProcessor:
    """Handles batch processing of multiple accounts with concurrency control."""

    def __init__(self, session_handler: Any):
        self.session_handler = session_handler

    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        log_func: Callable[[str], None],
        batch_size: int = 3,
        concurrent_limit: int = 9,
        **kwargs
    ) -> Dict[Any, Tuple[bool, bool]]:
        """
        Generic method to process items in batches with concurrency control.
        Returns a dict mapping items to (action_success, sim_success) tuples.
        """
        if not items:
            log_func("No items to process")
            return {}

        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}

        async def process_item_with_semaphore(item: Any) -> Tuple[Any, Tuple[bool, bool]]:
            async with semaphore:
                log_func(f"Starting processing for item {item}")
                try:
                    action_success, sim_success = await process_func(item, log_func=log_func, **kwargs)
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

        async def login_task(account: Dict[str, Any], log_func: Callable[[str], None]) -> Tuple[bool, bool]:
            return await self.session_handler.login_account(
                account["account_id"],
                account["user"],
                account["password"],
                log_func,
            )

        return await self.process_batch(
            items=accounts,
            process_func=login_task,
            log_func=log_func,
            batch_size=batch_size,
            concurrent_limit=concurrent_limit
        )
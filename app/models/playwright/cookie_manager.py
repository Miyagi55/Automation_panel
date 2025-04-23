from typing import Callable, Any
from app.models.account_model import AccountModel


class CookieManager:
    """Manages cookie persistence for accounts."""

    async def save_cookies(self, browser: Any, account_id: str, log_func: Callable[[str], None]) -> None:
        """Persists cookies for the given account."""
        try:
            cookies = await browser.cookies()
            cookies_dicts = [dict(cookie) for cookie in cookies]

            account_model = AccountModel()
            account_model.update_account_cookies(account_id, cookies_dicts)
            log_func(f"Persisted cookies for account {account_id}")
        except Exception as e:
            log_func(f"Failed to persist cookies for account {account_id}: {str(e)}")
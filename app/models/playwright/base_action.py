from typing import Any, Callable, Dict, Optional

from .session_handler import SessionHandler


class AutomationAction:
    """
    Base class for automation actions.
    All specific actions should inherit from this.
    """

    def __init__(self, name: str):
        self.name = name
        self.session_handler = SessionHandler()

    async def execute(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        action_data: Dict[str, Any],
        log_func: Callable[[str], None],
        browser: Optional[Any] = None,
    ) -> bool:
        """Execute the automation action."""
        raise NotImplementedError("Subclasses must implement execute()")
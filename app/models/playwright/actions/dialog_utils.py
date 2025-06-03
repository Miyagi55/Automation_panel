from typing import Any, Callable, Optional

from app.utils.config import LIKE_ACTION_DELAY_RANGE
from app.utils.randomizer import Randomizer

# CSS selector matching Facebook post overlay/dialog elements
dialog_selector = 'div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]'


async def wait_for_post_overlay(
    page: Any,
    debug: bool,
    log_func: Callable[[str], None],
    account_id: str,
    attempts: int = 3,
    timeout: int = 5000,
) -> Optional[Any]:
    """
    Wait for the Facebook post overlay (dialog) to appear on the page.
    Logs progress and returns the overlay element handle if found.
    """
    log_func(f"Checking for post overlay for account {account_id}")
    for attempt in range(attempts):
        try:
            overlay = await page.wait_for_selector(dialog_selector, timeout=timeout)
            if overlay:
                if debug:
                    log_func(
                        f"Post overlay detected on attempt {attempt + 1} for account {account_id}"
                    )
                return overlay
            log_func(
                f"Overlay found but not considered valid on attempt {attempt + 1} for account {account_id}"
            )
            await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
        except Exception:
            log_func(
                f"No overlay detected on attempt {attempt + 1} for account {account_id}"
            )
            if debug:
                dom_info = await page.evaluate(
                    """
                    () => {
                        const dialogs = document.querySelectorAll(
                            'div[role="dialog"], div[aria-modal="true"], div[class*="modal"], div[class*="popup"]'
                        );
                        return Array.from(dialogs).map(d => ({
                            outerHTML: d.outerHTML.slice(0, 200),
                            ariaLabels: Array.from(d.querySelectorAll('[aria-label]')).map(
                                e => e.getAttribute('aria-label')
                            )
                        }));
                    }
                    """
                )
                log_func(
                    f"DOM dialogs on attempt {attempt + 1} for account {account_id}: {dom_info}"
                )
            await Randomizer.sleep(*LIKE_ACTION_DELAY_RANGE)
    log_func(f"No overlay detected after {attempts} attempts for account {account_id}")
    return None


async def log_visible_dialogs(
    page: Any, log_func: Callable[[str], None], account_id: str
) -> None:
    """
    Log information about all visible dialog overlays on the page.
    """
    try:
        dialog_info = await page.evaluate(
            """
            () => {
                const dialogs = Array.from(
                    document.querySelectorAll('div[role="dialog"]')
                );
                return dialogs.map((dlg, i) => ({
                    index: i,
                    visible: dlg.offsetParent !== null,
                    ariaLabelledBy: dlg.getAttribute('aria-labelledby'),
                    ariaLabel: dlg.getAttribute('aria-label'),
                    buttons: Array.from(
                        dlg.querySelectorAll('[role="button"][aria-label]')
                    )
                        .filter(btn => btn.offsetParent !== null)
                        .map(btn => btn.getAttribute('aria-label'))
                }));
            }
            """
        )
        log_func(f"Found {len(dialog_info)} dialogs on page for account {account_id}")
        for dlg in dialog_info:
            log_func(
                f"Dialog #{dlg['index']}: visible={dlg['visible']}, labelledBy={dlg['ariaLabelledBy']}, "
                + f"label={dlg['ariaLabel']}, visible buttons: {dlg['buttons']}"
            )
    except Exception as e:
        log_func(f"Error logging dialogs for account {account_id}: {str(e)}")


async def find_button_in_visible_dialog(
    page: Any, button_selector: str, log_func: Callable[[str], None], account_id: str
) -> Optional[Any]:
    """
    Find a button matching the given selector within visible dialog overlays.
    Returns the button element handle or None.
    """
    try:
        handle = await page.evaluate_handle(f"""
            () => {{
                const dialogs = Array.from(
                    document.querySelectorAll('div[role="dialog"][aria-labelledby]')
                );
                for (const dlg of dialogs) {{
                    if (dlg.offsetParent === null) continue;
                    const btn = dlg.querySelector('{button_selector}');
                    if (btn) return btn;
                }}
                return null;
            }}
        """)
        return handle
    except Exception as e:
        log_func(f"Error finding button in dialog for account {account_id}: {str(e)}")
        return None

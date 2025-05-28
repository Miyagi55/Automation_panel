"""
Centralized Facebook selectors for automation actions.
Organized by functionality and supporting multiple languages (English/Spanish).
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SelectorGroup:
    """Group of related selectors with metadata."""

    primary: List[str]
    fallback: List[str] = None
    description: str = ""

    def __post_init__(self):
        if self.fallback is None:
            self.fallback = []

    @property
    def all_selectors(self) -> List[str]:
        """Get all selectors (primary + fallback)."""
        return self.primary + self.fallback


class FacebookSelectors:
    """Centralized Facebook selectors organized by functionality."""

    # ==================== DIALOG & OVERLAY SELECTORS ====================
    DIALOGS = SelectorGroup(
        primary=[
            'div[role="dialog"]',
            'div[aria-modal="true"]',
        ],
        fallback=[
            'div[class*="modal"]',
            'div[class*="popup"]',
        ],
        description="Post overlay dialogs and modals",
    )

    # ==================== LIKE & REACTION SELECTORS ====================
    LIKE_BUTTONS = SelectorGroup(
        primary=[
            '[aria-label="Like"], [aria-label="Me gusta"]',
            '[aria-label="React"], [aria-label="Reaccionar"]',
        ],
        fallback=[
            '[role="button"]:has-text("Like"), [role="button"]:has-text("Me gusta")',
            'span:has-text("LIKE"), span:has-text("Me gusta")',
        ],
        description="Like and reaction buttons",
    )

    UNLIKE_BUTTONS = SelectorGroup(
        primary=[
            '[aria-label="Unlike"], [aria-label="No me gusta"]',
        ],
        description="Unlike buttons for verification",
    )

    # ==================== SHARE SELECTORS ====================
    SHARE_BUTTONS = SelectorGroup(
        primary=[
            '[aria-label="Send this to friends or post it on your profile."]',
            '[aria-label="Envía esto a tus amigos o publícalo en tu perfil."]',
        ],
        fallback=[
            '[aria-label="Share"], [aria-label="Compartir"]',
            '[role="button"]:has-text("Share"), [role="button"]:has-text("Compartir")',
        ],
        description="Share dialog trigger buttons",
    )

    SHARE_NOW_BUTTONS = SelectorGroup(
        primary=[
            'div[role="button"][aria-label="Share now"]',
            'div[role="button"][aria-label="Compartir ahora"]',
        ],
        description="Share confirmation buttons",
    )

    # ==================== COMMENT SELECTORS ====================
    COMMENT_BUTTONS = SelectorGroup(
        primary=[
            '[aria-label="Comment"], [aria-label="Comentar"]',
        ],
        fallback=[
            '[role="button"]:has-text("Comment"), [role="button"]:has-text("Comentar")',
        ],
        description="Comment dialog trigger buttons",
    )

    COMMENT_FIELDS = SelectorGroup(
        primary=[
            'div[aria-label*="Write a comment"], div[aria-label*="Escribe un comentario"]',
            'div[role="textbox"][contenteditable="true"]',
        ],
        fallback=[
            'textarea[placeholder*="Write a comment"], textarea[placeholder*="Escribe un comentario"]',
            'form[data-testid*="ComposerForm"]',
            'div[data-testid*="comment"]',
        ],
        description="Comment input fields",
    )

    # ==================== POST TYPE DETECTION ====================
    VIDEO_INDICATORS = SelectorGroup(
        primary=[
            "video[src]",
            'div[role="button"][aria-label*="Play"], div[role="button"][aria-label*="Reproducir"]',
            '[data-testid="video-component"]',
        ],
        fallback=[
            "video",
            '[data-testid*="video"]',
        ],
        description="Video post indicators",
    )

    LIVE_INDICATORS = SelectorGroup(
        primary=[
            '[aria-label*="Live"]',
            '[class*="live"]',
            '[data-testid*="live"]',
        ],
        description="Live stream indicators",
    )

    # ==================== UTILITY METHODS ====================
    @classmethod
    def get_combined_selector(cls, selector_group: SelectorGroup) -> str:
        """Get a combined CSS selector string from a selector group."""
        return ", ".join(selector_group.all_selectors)

    @classmethod
    def get_selector_by_priority(cls, selector_group: SelectorGroup) -> List[str]:
        """Get selectors ordered by priority (primary first, then fallback)."""
        return selector_group.all_selectors

    @classmethod
    def get_all_selectors(cls) -> Dict[str, SelectorGroup]:
        """Get all selector groups as a dictionary."""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if isinstance(getattr(cls, name), SelectorGroup)
        }


# ==================== SELECTOR CONSTANTS FOR BACKWARD COMPATIBILITY ====================
# These can be used directly in existing code during migration

# Dialog selectors
DIALOG_SELECTORS = FacebookSelectors.get_combined_selector(FacebookSelectors.DIALOGS)

# Like selectors
LIKE_BUTTON_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.LIKE_BUTTONS
)
UNLIKE_BUTTON_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.UNLIKE_BUTTONS
)

# Share selectors
SHARE_BUTTON_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.SHARE_BUTTONS
)
SHARE_NOW_BUTTON_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.SHARE_NOW_BUTTONS
)

# Comment selectors
COMMENT_BUTTON_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.COMMENT_BUTTONS
)
COMMENT_FIELD_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.COMMENT_FIELDS
)

# Post type selectors
VIDEO_INDICATOR_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.VIDEO_INDICATORS
)
LIVE_INDICATOR_SELECTORS = FacebookSelectors.get_combined_selector(
    FacebookSelectors.LIVE_INDICATORS
)

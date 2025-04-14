from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class AccountStatus(str, Enum):
    """Enum for account status"""

    LOGGED_OUT = "Logged Out"
    LOGGED_IN = "Logged In"
    TESTING = "Testing"
    ERROR = "Error"


class AccountActivity(str, Enum):
    """Enum for account activity status"""

    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Account(BaseModel):
    """Pydantic model for account data with validation"""

    id: str = Field(..., pattern=r"^\d{3}$", description="3-digit account ID")
    user: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User identifier (email, phone, username)",
    )
    password: str = Field(..., min_length=6, description="Account password")
    activity: AccountActivity = Field(
        default=AccountActivity.INACTIVE, description="Account activity status"
    )
    status: AccountStatus = Field(
        default=AccountStatus.LOGGED_OUT, description="Account login status"
    )
    last_activity: Optional[str] = Field(
        default="", description="Timestamp of last activity"
    )
    proxy: Optional[str] = Field(default="", description="Proxy configuration")
    user_agent: Optional[str] = Field(default="", description="Custom user agent")
    cookies: Dict[str, Any] = Field(default_factory=dict, description="Stored cookies")

    @validator("last_activity")
    def validate_last_activity(cls, v):
        """Validate last_activity timestamp format"""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise ValueError("Invalid timestamp format. Use YYYY-MM-DD HH:MM:SS")
        return v

    @validator("proxy")
    def validate_proxy(cls, v):
        """Validate proxy format if provided"""
        if v:
            # Basic proxy format validation (protocol://host:port)
            import re

            if not re.match(r"^(http|https|socks4|socks5)://[\w.-]+:\d+$", v):
                raise ValueError("Invalid proxy format. Use protocol://host:port")
        return v

    class Config:
        """Pydantic model configuration"""

        json_schema_extra = {
            "example": {
                "id": "001",
                "user": "user@example.com",
                "password": "securepass123",
                "activity": "Inactive",
                "status": "Logged Out",
                "last_activity": "2024-03-20 12:00:00",
                "proxy": "http://proxy.example.com:8080",
                "user_agent": "Mozilla/5.0...",
                "cookies": {},
            }
        }

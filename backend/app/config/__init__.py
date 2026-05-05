"""Configuration package."""
from .settings import Settings, settings
from .newspapers import (
    NEWSPAPER_CONFIGS,
    get_enabled_newspapers,
    get_newspaper_config,
    get_all_newspaper_keys
)

__all__ = [
    "Settings",
    "settings",
    "NEWSPAPER_CONFIGS",
    "get_enabled_newspapers",
    "get_newspaper_config",
    "get_all_newspaper_keys"
]

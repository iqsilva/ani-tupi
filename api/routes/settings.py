"""User settings API routes for frontend preferences."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.config import get_data_path
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_FILE = get_data_path() / "user_preferences.json"


class UserPreferences(BaseModel):
    """User preferences for the frontend."""

    quality: str = Field(default="best", pattern="^(1080|720|480|360|best)$")


def _load_preferences() -> dict:
    """Load user preferences from file."""
    try:
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")
    return {}


def _save_preferences(data: dict) -> None:
    """Save user preferences to file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to save preferences")


@router.get("", response_model=UserPreferences)
async def get_settings() -> UserPreferences:
    """Get user preferences."""
    data = _load_preferences()
    return UserPreferences(**data)


@router.put("", response_model=UserPreferences)
async def update_settings(preferences: UserPreferences) -> UserPreferences:
    """Update user preferences."""
    data = _load_preferences()
    data.update(preferences.model_dump())
    _save_preferences(data)
    return UserPreferences(**data)

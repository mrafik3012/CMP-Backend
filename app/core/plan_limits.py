"""Plan limits and feature flags for BuildDesk trial/paid tiers."""
from datetime import datetime, timedelta

from app.core.config import get_settings

PLAN_LIMITS = {
    "trial": {
        "max_projects": 3,
        "max_members_per_project": 5,
        "max_storage_mb": 500,
        "can_export_csv": False,
        "can_export_pdf": True,  # project summary & daily report PDF allowed on trial
    },
    "starter": {
        "max_projects": 5,
        "max_members_per_project": 10,
        "max_storage_mb": 2048,
        "can_export_csv": True,
        "can_export_pdf": True,
    },
    "pro": {
        "max_projects": None,
        "max_members_per_project": None,
        "max_storage_mb": None,
        "can_export_csv": True,
        "can_export_pdf": True,
    },
}

def get_plan(user) -> str:
    return getattr(user, "plan", "trial") or "trial"

def is_trial_expired(user) -> bool:
    if get_plan(user) != "trial":
        return False
    trial_expires = getattr(user, "trial_expires_at", None)
    if trial_expires:
        return datetime.utcnow() > trial_expires
    trial_started = getattr(user, "trial_started_at", None)
    if not trial_started:
        return False
    days = get_settings().trial_expire_days
    return datetime.utcnow() > trial_started + timedelta(days=days)

def get_limit(user, key):
    return PLAN_LIMITS.get(get_plan(user), PLAN_LIMITS["trial"]).get(key)

def can_feature(user, key: str) -> bool:
    if is_trial_expired(user):
        return False
    return bool(get_limit(user, key))

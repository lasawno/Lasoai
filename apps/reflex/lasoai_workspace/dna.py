"""Business DNA validation shared by the planned Reflex server handlers.

No database, network calls, credentials, or payment side effects.
"""
from datetime import datetime, timezone

LIMITS = {"name": 160, "purpose": 2000, "goals": 10000,
          "responsibilities": 10000, "tools": 10000, "rules": 10000}


def validate_business(form: dict) -> dict[str, str]:
    if not isinstance(form, dict):
        raise ValueError("Business DNA must be an object.")
    if set(form) - set(LIMITS):
        raise ValueError("Unrecognized Business DNA fields.")
    business = {}
    for key, limit in LIMITS.items():
        value = form.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text.")
        if len(value) > limit:
            raise ValueError(f"{key} exceeds {limit} characters.")
        business[key] = value
    return business


def export_business(form: dict) -> dict:
    return {"schema": "lasoai.business-dna", "version": 1,
            "savedAt": datetime.now(timezone.utc).isoformat(),
            "business": validate_business(form)}

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


def import_business(raw: str) -> dict[str, str]:
    """Validate a portable file and return only present fields, without uploading."""
    import json

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON fields are not allowed.")
            result[key] = value
        return result

    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 262144:
        raise ValueError("Import must be JSON text no larger than 256 KiB.")
    try:
        record = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, RecursionError):
        raise ValueError("Invalid or duplicate-field JSON import.") from None
    if not isinstance(record, dict) or set(record) != {"schema", "version", "savedAt", "business"}:
        raise ValueError("Unrecognized DNA file structure.")
    if record["schema"] != "lasoai.business-dna" or type(record["version"]) is not int or record["version"] != 1:
        raise ValueError("Unsupported DNA schema or version.")
    try:
        stamp = datetime.fromisoformat(record["savedAt"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
    except (AttributeError, TypeError, ValueError):
        raise ValueError("DNA file needs a timezone-aware savedAt timestamp.") from None
    validated = validate_business(record["business"])
    return {key: validated[key] for key in record["business"]}


def merge_business(current: dict, imported: dict) -> dict[str, str]:
    """Partial restore keeps unselected fields. Validation occurs before mutation."""
    return validate_business({**validate_business(current), **imported})

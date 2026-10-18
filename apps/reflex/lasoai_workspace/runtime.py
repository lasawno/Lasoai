"""Preview configuration with no Reflex import, independently testable."""
import re
from collections.abc import Mapping


def preview_settings(env: Mapping[str, str]) -> dict:
    name = env.get("CODESPACE_NAME", "")
    if name:
        domain = env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "")
        # Values are provider metadata, never a credential or a customer URL.
        if not re.fullmatch(r"[a-z0-9-]+", name) or not re.fullmatch(r"[a-z0-9.-]+", domain):
            raise ValueError("Codespaces forwarding metadata is missing or invalid.")
        origin = f"https://{name}-3000.{domain}"
        return {"backend_host": "0.0.0.0", "frontend_port": 3000, "backend_port": 3000,
                "api_url": origin, "cors_allowed_origins": [origin],
                "transport": "polling"}
    # The supplied start script always uses Reflex 0.10 single-port mode.
    return {"backend_host": "127.0.0.1", "frontend_port": 3000, "backend_port": 3000,
            "api_url": "http://localhost:3000",
            "cors_allowed_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}

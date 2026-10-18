"""Private development preview; Supabase authentication is not implemented."""
import os
import reflex as rx
from lasoai_workspace.runtime import preview_settings

config = rx.Config(
    app_name="lasoai_workspace",
    telemetry_enabled=False,
    **preview_settings(os.environ),
)

"""Actual Reflex app source, pending dependency installation and runtime verification.

Keep local-only until authentication and tenant-scoped durable storage exist.
"""
import json
import os
from typing import Any
import reflex as rx
from .dna import export_business, validate_business
from .codespaces_callback import CodespacesCallbackRedirect


class DNAState(rx.State):
    business: dict[str, str] = {
        "name": "", "purpose": "", "goals": "",
        "responsibilities": "", "tools": "", "rules": "",
    }
    status: str = "No Business DNA applied to this server session."

    @rx.event
    def apply_draft(self, form_data: dict[str, Any]):
        """Runs on the Python backend when the Reflex form is submitted."""
        try:
            self.business = validate_business(form_data)
            self.status = (
                "Applied to this server session. Not a durable account save; "
                "export a backup. AI and payment services remain disconnected."
            )
        except ValueError as error:
            self.status = str(error)

    @rx.event
    def export_draft(self):
        """Download only the last applied, validated session draft."""
        return rx.download(
            data=json.dumps(export_business(self.business), indent=2),
            filename="lasoai-business-dna.json",
        )


def field(label: str, name: str, limit: int, rows: int = 4) -> rx.Component:
    return rx.vstack(
        rx.el.label(label, html_for=f"dna-{name}", font_weight="600"),
        rx.text_area(
            id=f"dna-{name}", name=name, default_value=DNAState.business[name],
            max_length=limit, min_height=f"{rows * 24 + 20}px", width="100%",
        ),
        align="stretch", width="100%", spacing="2",
    )


def outline(label: str, name: str) -> rx.Component:
    return rx.card(
        rx.heading(label, size="3"),
        rx.text(DNAState.business[name], white_space="pre-wrap", overflow_wrap="anywhere"),
        width="100%",
    )


def index() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("LasoAI · Business DNA", size="8"),
            rx.badge("LOCAL REFLEX PROTOTYPE · NOT A LIVE CUSTOMER SERVICE"),
            rx.text(
                "This workspace submits to a Python backend when run locally. "
                "It is separate from the published browser-only editor. "
                "No account authentication or durable customer storage is implemented."
            ),
            rx.form(
                rx.vstack(
                    field("Business name", "name", 160, 1),
                    field("What does your business do?", "purpose", 2000, 3),
                    rx.grid(
                        field("Business goals", "goals", 10000),
                        field("Responsibilities", "responsibilities", 10000),
                        field("Tools & workflows", "tools", 10000),
                        field("Rules & approvals — planning only, not enforced", "rules", 10000),
                        columns={"initial": "1", "md": "2"}, spacing="5", width="100%",
                    ),
                    rx.button("Apply to server session", type="submit"),
                    spacing="5", align="stretch", width="100%",
                ),
                on_submit=DNAState.apply_draft,
                reset_on_submit=False,
                width="100%",
            ),
            rx.text(DNAState.status, role="status"),
            rx.button("Export last applied draft", on_click=DNAState.export_draft, variant="outline"),
            rx.heading("Last applied business outline", size="5"),
            rx.grid(
                outline("Business name", "name"), outline("Purpose", "purpose"),
                outline("Business goals", "goals"), outline("Responsibilities", "responsibilities"),
                outline("Tools & workflows", "tools"), outline("Rules & approvals", "rules"),
                columns={"initial": "1", "md": "2"}, spacing="4", width="100%",
            ),
            spacing="6", align="stretch", padding_y="40px",
        ),
        size="3",
    )


app = rx.App(
    theme=rx.theme(appearance="dark", accent_color="violet"),
    api_transformer=CodespacesCallbackRedirect if os.getenv("CODESPACE_NAME") else None,
)
app.add_page(index, title="LasoAI — Reflex workspace")

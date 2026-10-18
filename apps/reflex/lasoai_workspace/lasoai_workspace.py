"""Actual Reflex app source, pending dependency installation and runtime verification.

Keep local-only until authentication and tenant-scoped durable storage exist.
"""
import json
import os
from typing import Any
import reflex as rx
from .dna import LIMITS, export_business, import_business, merge_business, validate_business
from .connector import ConnectorError, ProviderConfig, SupabaseDNAConnector
from .codespaces_callback import CodespacesCallbackRedirect


class DNAState(rx.State):
    business: dict[str, str] = {
        "name": "", "purpose": "", "goals": "",
        "responsibilities": "", "tools": "", "rules": "",
    }
    status: str = "No Business DNA applied to this server session."

    revision: int = 0
    storage_status: str = "Optional storage has not been used. No automatic uploads."
    import_status: str = "Import merges present fields into the server session only."

    @rx.event
    def import_draft(self, form_data: dict[str, Any]):
        try:
            if form_data.get("confirm_import") != "on":
                raise ValueError("Confirm replacing matching session fields first.")
            self.business = merge_business(self.business, import_business(form_data.get("dna_json", "")))
            self.revision += 1
            self.import_status = "Imported into this server session only. Nothing uploaded. Export a backup."
        except ValueError as error:
            self.import_status = str(error)

    @rx.event
    def storage_action(self, form_data: dict[str, Any]):
        # Tokens are operation-local variables, never State fields or persisted state.
        try:
            connector = SupabaseDNAConnector(ProviderConfig.from_environment())
            token = form_data.get("access_token", "")
            action = form_data.get("action", "")
            if action == "save":
                fields = [key for key in LIMITS if form_data.get("save_" + key) == "on"]
                connector.save(token, self.business, fields, form_data.get("consent") == "on")
                self.storage_status = "Provider confirmed selected fields saved. Unselected fields were not uploaded. Later session changes are not saved automatically."
            elif action == "restore":
                if form_data.get("consent") != "on":
                    raise ConnectorError("Confirm replacing matching session fields before restore.")
                self.business = merge_business(self.business, connector.restore(token))
                self.revision += 1
                self.storage_status = "Restored accessible saved fields into this server session. Other fields were kept."
            elif action == "revoke":
                connector.revoke(token)
                self.storage_status = "Provider confirmed connection revoked for all sessions. Stored data remains in your provider. Founder admin must explicitly re-enable access."
            else:
                raise ConnectorError("Choose save, restore, or revoke.")
        except ValueError as error:
            self.storage_status = str(error)

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
        rx.el.label(label, html_for=name, font_weight="600"),
        rx.text_area(
            id=name, name=name, default_value=DNAState.business[name],
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
                "Session edits are temporary. Optional storage uses a founder-configured provider; "
                "LasoAI does not create or own your login, database, or hosting account."
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
                key=DNAState.revision,
                on_submit=DNAState.apply_draft,
                reset_on_submit=False,
                width="100%",
            ),
            rx.text(DNAState.status, role="status"),
            rx.button("Export last applied draft", on_click=DNAState.export_draft, variant="outline"),
            rx.heading("Portable DNA import", size="5"),
            rx.text("Paste an exported DNA JSON file. Import and restore replace matching fields and reset the editor to the applied session draft; apply any typed edits first."),
            rx.form(
                rx.vstack(
                    rx.text_area(name="dna_json", max_length=262144, placeholder="DNA JSON", width="100%"),
                    rx.el.label(rx.el.input(type="checkbox", name="confirm_import"), " Replace matching session fields and reset editor"),
                    rx.button("Validate and import to session", type="submit"),
                    align="stretch", width="100%",
                ), on_submit=DNAState.import_draft, reset_on_submit=True, width="100%",
            ),
            rx.text(DNAState.import_status, role="status"),
            rx.heading("Optional founder-owned storage", size="5"),
            rx.text("Disabled unless configured by your host. Apply edits above first. Save replaces your provider snapshot with only the checked fields. Restore resets the editor; apply typed edits first. An existing provider access token is required per operation and is not retained. No login or token provisioning is implemented here."),
            rx.form(
                rx.vstack(
                    rx.el.label("Provider access token for this operation", rx.el.input(type="password", name="access_token", auto_complete="off", max_length=16384)),
                    rx.text("Fields to upload (nothing selected by default):"),
                    *[rx.el.label(rx.el.input(type="checkbox", name="save_" + key), " " + key.capitalize()) for key in LIMITS],
                    rx.el.label("Action ", rx.el.select(
                        rx.el.option("Save selected applied fields", value="save"),
                        rx.el.option("Restore saved fields to session", value="restore"),
                        rx.el.option("Revoke connection for all sessions", value="revoke"), name="action")),
                    rx.el.label(rx.el.input(type="checkbox", name="consent"), " I consent to the selected save or to replacing matching session fields on restore"),
                    rx.button("Run explicit storage action", type="submit"),
                    align="stretch", width="100%",
                ), on_submit=DNAState.storage_action, reset_on_submit=True, width="100%",
            ),
            rx.text(DNAState.storage_status, role="status"),
            rx.heading("Verified development progress", size="5"),
            rx.text("Verified in the existing Codespace: one Business DNA form submission reached Python. This release adds portable import and an optional connector; runtime and provider coverage is documented in docs/optional-storage.md. AI and payments remain disconnected."),
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

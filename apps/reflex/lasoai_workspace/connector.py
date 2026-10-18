"""Optional founder-configured storage. No service credentials or implicit uploads.

Access tokens are supplied per operation and never retained by this module.
Database RLS remains the authority; the caller's editable data never assigns owner.
"""
import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .dna import LIMITS, export_business, import_business, validate_business


class ConnectorError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_request(method, url, headers, body):
    """Bounded HTTPS requests; never forward authorization through redirects."""
    request = Request(url, data=None if body is None else json.dumps(body).encode(),
                      headers=headers, method=method)
    try:
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            raw = response.read(262145)
            if len(raw) > 262144:
                raise ConnectorError("Provider response exceeds the size limit.")
            return json.loads(raw) if raw else None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        # Never include provider response, URL query, headers, or tokens in errors.
        if isinstance(error, ConnectorError):
            raise
        raise ConnectorError("Provider request failed or access was denied. Your session draft is unchanged.") from None


@dataclass(frozen=True)
class ProviderConfig:
    url: str
    publishable_key: str

    def __post_init__(self):
        parts = urlsplit(self.url)
        if (parts.scheme != "https" or not parts.hostname or parts.username or
                parts.password or parts.query or parts.fragment or parts.path not in ("", "/")):
            raise ConnectorError("Provider URL must be an HTTPS origin.")
        if not self.publishable_key.startswith("sb_publishable_") or any(c.isspace() for c in self.publishable_key):
            raise ConnectorError("Use a Supabase publishable key; secret and legacy role keys are not accepted.")

    @classmethod
    def from_environment(cls):
        if os.environ.get("LASOAI_OPTIONAL_STORAGE") != "supabase":
            return None
        return cls(os.environ.get("LASOAI_SUPABASE_URL", ""),
                   os.environ.get("LASOAI_SUPABASE_PUBLISHABLE_KEY", ""))


def selected_document(business, fields, consent):
    if consent is not True:
        raise ConnectorError("Explicit save consent is required.")
    if not isinstance(fields, list) or not fields or len(fields) != len(set(fields)) or set(fields) - set(LIMITS):
        raise ConnectorError("Choose at least one recognized field, with no duplicates.")
    validated = validate_business(business)
    document = export_business(validated)
    document["business"] = {key: validated[key] for key in fields}
    return document


class SupabaseDNAConnector:
    """Small extension point: save, restore, revoke. No dependency on Reflex."""
    def __init__(self, config, request=http_request):
        if config is None:
            raise ConnectorError("Optional storage is disabled. Session editing and export remain available.")
        self.config, self.request = config, request

    def _call(self, token, method, path, body=None, prefer=None):
        if not isinstance(token, str) or not token or len(token) > 16384 or any(c.isspace() for c in token):
            raise ConnectorError("A founder-provider access token is required for this operation.")
        headers = {"apikey": self.config.publishable_key, "Authorization": "Bearer " + token,
                   "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        return self.request(method, self.config.url.rstrip("/") + path, headers, body)

    def _owner(self, token):
        from uuid import UUID
        user = self._call(token, "GET", "/auth/v1/user")
        try:
            return str(UUID(user["id"]))
        except (ValueError, TypeError, KeyError):
            raise ConnectorError("Provider identity could not be verified.") from None

    def save(self, token, business, fields, consent):
        document = selected_document(business, fields, consent)
        owner = self._owner(token)
        row = {"owner_id": owner, "document": document, "selected_fields": fields}
        saved = self._call(token, "POST", "/rest/v1/lasoai_dna?on_conflict=owner_id", row,
                           "resolution=merge-duplicates,return=representation")
        if not isinstance(saved, list) or len(saved) != 1 or saved[0].get("owner_id") != owner or saved[0].get("document") != document:
            raise ConnectorError("Provider did not confirm this save. Your session draft is unchanged.")
        return document

    def restore(self, token):
        owner = self._owner(token)
        rows = self._call(token, "GET", "/rest/v1/lasoai_dna?" + urlencode({"owner_id": "eq." + owner, "select": "document,selected_fields"}))
        if not isinstance(rows, list) or len(rows) != 1:
            raise ConnectorError("No accessible saved DNA found. It may be absent, revoked, or expired.")
        document = rows[0].get("document")
        partial = import_business(json.dumps(document))
        fields = rows[0].get("selected_fields")
        if not isinstance(fields, list) or set(fields) != set(partial) or len(fields) != len(set(fields)):
            raise ConnectorError("Stored field selection is invalid.")
        return partial

    def revoke(self, token):
        owner = self._owner(token)
        rows = self._call(token, "PATCH", "/rest/v1/lasoai_connections?" + urlencode({"owner_id": "eq." + owner}),
                          {"enabled": False}, "return=representation")
        if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("enabled") is not False:
            raise ConnectorError("Remote revocation was not confirmed. Revoke in your provider dashboard.")

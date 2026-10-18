"""Recover Reflex 0.10's same-origin Codespaces callback dead end.

GitHub still authenticates the private port before this ASGI app is reached.
Only the framework's helper callback response changes; no auth is disabled.
"""


class CodespacesCallbackRedirect:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope.get("type") == "http"
                and scope.get("method") in {"GET", "HEAD"}
                and scope.get("path") in {"/auth-codespace", "/auth-codespace/"}):
            # Fixed same-origin destination: never echo redirect_to, Host,
            # forwarding headers, or session tokens into the Location header.
            await send({"type": "http.response.start", "status": 303,
                        "headers": [(b"location", b"/"),
                                    (b"cache-control", b"no-store"),
                                    (b"content-length", b"0")]})
            await send({"type": "http.response.body", "body": b""})
            return
        await self.app(scope, receive, send)

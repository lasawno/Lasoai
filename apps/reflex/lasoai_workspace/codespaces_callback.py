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
        async def send_with_fresh_html(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                if any(k.lower() == b"content-type" and b"text/html" in v.lower() for k, v in headers):
                    # HTML chooses the hashed frontend bundle. Revalidate the page
                    # after a transport change instead of reusing an old client.
                    headers = [(k,v) for k,v in headers if k.lower() != b"cache-control"]
                    headers.append((b"cache-control", b"no-store"))
                    message = {**message, "headers": headers}
            await send(message)
        await self.app(scope, receive, send_with_fresh_html)

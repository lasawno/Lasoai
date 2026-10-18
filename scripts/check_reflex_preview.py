"""Bounded local checks, run inside the Codespace with the server active.

No GitHub CLI, authentication secrets, port-visibility changes, or external calls.
"""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, build_opener, urlopen

BASE = "http://127.0.0.1:3000"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    from reflex.config import get_config
    config = get_config()
    generated = json.loads(Path(".web/env.json").read_text())
    assert config.transport == "polling", "Runtime configuration is not polling; use start-reflex.sh"
    assert generated.get("TRANSPORT") == config.transport, "Compiled client transport differs; restart to rebuild"
    print("PASS: current config and compiled client both select polling")
    with urlopen(BASE + "/ping", timeout=5) as response:
        assert response.status == 200
        assert json.loads(response.read(1024)) == "pong"
    print("PASS: Python backend /ping")
    with urlopen(BASE + "/", timeout=5) as response:
        page = response.read(2_000_000).decode()
        assert response.status == 200 and "LasoAI" in page, "Expected LasoAI compiled page"
    print("PASS: compiled LasoAI page")
    try:
        build_opener(NoRedirect).open(BASE + "/auth-codespace?redirect_to=https://invalid.example", timeout=5)
    except HTTPError as response:
        assert response.code == 303 and response.headers.get("Location") == "/", "Callback fix not loaded"
    else:
        raise AssertionError("Callback fix not loaded; expected HTTP 303")
    print("PASS: helper callback redirects safely to /")
    try:
        response = urlopen(BASE + "/_event/?EIO=4&transport=polling", timeout=5)
    except HTTPError as error:
        if error.code == 400:
            raise AssertionError("Active listener rejects polling. It may be an old server process; run stop-reflex.py and restart.") from error
        raise
    with response:
        payload = response.read(8192).decode()
        assert payload.startswith("0"), "Expected Engine.IO handshake"
        handshake = json.loads(payload[1:])
        assert handshake.get("sid") and "upgrades" in handshake
    print("PASS: event transport handshake (browser form round trip still needs verification)")


if __name__ == "__main__":
    main()

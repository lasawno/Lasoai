# Private Codespaces event-connection fix

## Evidence and diagnosis

The user's Codespace compiled Reflex and served the Business DNA page at private port 3000. The page still reported a WebSocket error for the matching same-origin `/_event` URL. A later screenshot confirmed the clean root renders; this is not evidence of a GitHub login/account failure or an ongoing root redirect loop.

Reflex 0.10.0 defaults `Config.transport` to `websocket` and compiles that into `env.json`. Its frontend explicitly requests only that transport. A successful HTML page therefore does not establish a usable Python event connection. The exact rejected upgrade response in the user's Codespace has not been inspected, so the cause within forwarding/proxy/server upgrade handling is not claimed as proven.

The fix selects Reflex's built-in **HTTP polling event transport** only for Codespaces, keeps UI and events on the same HTTPS origin/private port 3000, and runs one Granian worker for Engine.IO session affinity. This changes transport, not authentication, and requires recompilation/restart. Local non-Codespaces configuration retains Reflex's default transport. No WebSocket route or generated frontend file is patched.

Separately, Reflex's Codespaces helper has a reproducible same-origin callback dead end: the first redirect sets `authenticated_github_codespaces` in sessionStorage, and the callback checks that same flag before returning. The added `api_transformer` changes only GET/HEAD `/auth-codespace` into a 303 to `/`. It ignores untrusted redirect parameters, forwards all event/upload/WebSocket/lifespan requests unchanged, and leaves GitHub's upstream private-port gate in place. This improvement is separate from the event-transport fix.

## Apply without discarding local work

In the terminal running Reflex, press **Ctrl+C**. In a repository-root terminal on `codex/lasoai-codespaces`:

```bash
git stash push --include-untracked -m lasoai-before-preview-fix
git pull --ff-only origin codex/lasoai-codespaces
bash scripts/start-reflex.sh
```

The stash preserves tracked and untracked edits; ignored secrets/virtualenv/generated files stay in place. Do not drop the stash. Leave it unapplied while verifying the fix, then selectively restore your edits after checking them (`git stash show --stat`). If pull rejects because of diverged commits, stop; do not reset, force-pull, or discard the stash. Committed local work remains in Git history.

Open the clean root in the same authenticated browser tab and reload after compilation. Keep port 3000 **Private**. Do not rerun setup/init or reinstall packages merely for this fix.

In a second terminal run the bounded local check (four requests, each with a five-second timeout):

```bash
cd apps/reflex
uv run python ../../scripts/check_reflex_preview.py
```

It checks Python `/ping`, the compiled page, the safe callback response, and an Engine.IO HTTP handshake. It does not use `gh codespace`, print tokens, or change visibility. After those pass, apply a synthetic Business DNA form and verify the outline/status updates, then export its JSON. That browser event round trip is the final check; no success is claimed until observed. If local checks pass but browser requests fail, capture one failed `/_event` request's status/error without cookies or tokens; further GitHub CLI commands are not needed for that distinction.

## Verification completed here

- Reproduced the same-origin callback dead end by executing the redirect script extracted from upstream Reflex tag `v0.10.0` in a Node VM with shared sessionStorage.
- Tested middleware redirects and pass-through behavior with ASGI requests, including hostile redirect parameters.
- Tested the private same-origin Codespaces runtime configuration and polling selection; syntax and existing data validations pass.
- No access to the live Codespace, WebSocket response, or post-fix rendered form is claimed. Reflex installation remains blocked in this separate execution environment.

Official sources inspected:
- https://github.com/reflex-dev/reflex/blob/v0.10.0/reflex/utils/codespaces.py
- https://github.com/reflex-dev/reflex/blob/v0.10.0/packages/reflex-base/src/reflex_base/config.py
- https://github.com/reflex-dev/reflex/blob/v0.10.0/packages/reflex-base/src/reflex_base/.templates/web/utils/state.js
- https://github.com/reflex-dev/reflex/blob/v0.10.0/reflex/utils/processes.py
- https://reflex.dev/docs/api-reference/config/
- https://reflex.dev/docs/api-routes/overview/

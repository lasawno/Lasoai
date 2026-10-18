# Invalid transport: diagnosis and a bounded restart

`Invalid transport` is distinct from the form-schema error. Reflex 0.10.0 constructs its Socket.IO server with `transports=[config.transport]`; its compiler writes the same setting to `.web/env.json`, and the frontend uses `[env.TRANSPORT]`. Therefore choosing `polling` enables polling on both sides, not just the browser. The published source already sets it for Codespaces.

Engine.IO logs `Invalid transport` when the incoming query's transport is not in the running server's allowed list. This does not prove polling is unsupported. An old websocket-only page talking to the polling server, or a new polling page talking to a lingering websocket-only server, can produce it. The live request URL and installed process state have not been inspected from this environment, so which side is stale remains unverified. The prior Python form-validation response proves a submission reached Python at that time; it does not make every later transport request valid.

The form-ID fix does not change transport. Polling stays enabled; no ports, origins, or authentication settings are relaxed.

## If Ctrl+C does not return a prompt

Open a **new terminal** in the same Codespace. Run from inside the repository:

```bash
cd "$(git rev-parse --show-toplevel)"
git fetch origin codex/lasoai-codespaces
git show FETCH_HEAD:scripts/stop-reflex.py | python3 -
git stash push --include-untracked -m lasoai-before-clean-restart
git pull --ff-only origin codex/lasoai-codespaces
bash scripts/start-reflex.sh
```

The fetched stop helper is runnable before pulling, so the blocked terminal does not prevent updating. It identifies this checkout's Reflex launchers/Granian workers by exact app working directory, includes their descendant processes, and sends TERM. After a four-second grace period it sends KILL only to remaining identified processes, checking process start times to avoid reused PIDs. It does not kill every Python process, delete files, or print command lines/tokens. The maximum stop wait is six seconds. Unrelated projects and terminals are excluded. It has a process-selection regression test; it has not been executed against the user's live process tree here.

Edits are preserved in the named Git stash; keep it for selective restoration. A diverged-branch error requires review, not reset/force pull. Ignored virtualenv/generated files and secrets stay on disk.

The startup script refuses to start while port 3000 is already listening. It then rebuilds the app with polling selected. After compilation, close stale duplicate preview tabs and hard-reload the clean root in one authenticated tab. Keep port 3000 **Private**.

In another terminal:

```bash
cd apps/reflex
uv run python ../../scripts/check_reflex_preview.py
```

This compares the current config to compiled `env.json`, then sends four bounded local requests including the actual polling handshake. It prints no session IDs or credentials. A 400 on the polling handshake after config/build agree means the active listener still needs investigation; it is not reported as fixed. The checks also include the previous callback fix. A browser form round trip remains the final functional check.

## Additional verification

The test suite includes an actual Reflex test of `app.sio.eio.transports == [get_config().transport]`. It is skipped in this environment because Reflex is unavailable, and runs where Reflex is installed. No claim of successful live restart, transport handshake, or saved Business DNA is made here.

Sources:
- https://github.com/reflex-dev/reflex/blob/v0.10.0/reflex/app.py
- https://github.com/reflex-dev/reflex/blob/v0.10.0/reflex/utils/build.py
- https://github.com/reflex-dev/reflex/blob/v0.10.0/packages/reflex-base/src/reflex_base/.templates/web/utils/state.js
- https://github.com/miguelgrinberg/python-engineio/blob/v4.12.2/src/engineio/async_server.py (illustrates the log condition; the user's installed Engine.IO version was not retrieved)

# LasoAI Reflex workspace

Real Reflex Python source for a Business DNA form, validation, server-session outline, and JSON export. Setup targets GitHub Codespaces; see [startup and verification](../../docs/codespaces.md).

From the repository root:

```bash
python3 scripts/setup_reflex.py
bash scripts/start-reflex.sh
```

In another terminal: `bash scripts/verify-reflex.sh`. Open private port 3000. The startup script uses Reflex 0.10's single-port production build mode as a development preview. It does not deploy to permanent hosting.

Status: scaffold and Codespaces configuration prepared. Package installation was blocked by this environment's network policy for pypi.org; no running Codespace, Reflex compile, rendered screenshot, or backend event round trip has been verified. Supabase is selected for future accounts/shared data but remains unconnected. The current server prototype is session-only, with no account authentication or durable customer storage. Keep ports private and use synthetic data.

Checks possible without installing Reflex:

```bash
cd apps/reflex
uv run --no-project --offline python -m unittest discover -s tests -v
uv run --no-project --offline python -m compileall -q rxconfig.py lasoai_workspace
```

No API key is needed to install Reflex. No hosting subscription, AI call, payment, or Supabase project is created by setup. The existing private published site and its browser-local editor remain intact.

# LasoAI in GitHub Codespaces

## What is prepared

Python 3.12 dev container, Node 22, uv 0.12.23, and Reflex 0.10.0 dependency declaration. Container setup installs dependencies and initializes generated Reflex assets without replacing the custom Python app. It is safe to rerun setup; an existing `.web/` skips initialization, and an existing `uv.lock` is respected with `uv sync --locked`.

No Codespace has been created or billed by this work. Installation and container startup have not been tested here because this execution environment blocks the Python registry. Transitive dependencies are not locked yet. After the first successful setup, review and commit `apps/reflex/uv.lock` for locked subsequent installs. Container tags and the Node major version are not immutable digests.

## Existing repository and launch

The GitHub connector verified `lasawno/Lasoai` is accessible, with push permission, and currently public. Its main branch README is `# Lasoai`; its main branch did not contain `apps/reflex/pyproject.toml` when checked. The current website source is stored by Sites rather than being a GitHub remote in this checkout.

Use development branch `codex/lasoai-codespaces` in the existing repository. Select that branch in the repository branch selector, then **Code → Codespaces → Create codespace on codex/lasoai-codespaces** (or rebuild an existing Codespace on that branch). Do not launch from `main`, which does not contain this development setup. Do not create another repository. This step starts GitHub compute: review the account's available quota/billing before launching it. No production hosting is selected by this action.

## Start and verify

From the repository root, after container creation completes:

```bash
python3 scripts/setup_reflex.py
bash scripts/start-reflex.sh
```

Keep the server running. In a second terminal:

```bash
bash scripts/verify-reflex.sh
```

Open port **3000** from the **Ports** panel. Keep its visibility **Private**. Reflex 0.10's `--env prod` mode serves the UI and Python event backend on one port; using the production build mode here is only a private development preview, not a production deployment. The config derives the same-origin HTTPS API URL from Codespaces metadata so WebSocket traffic does not point to your laptop's localhost. Do not make a second backend port public to work around a connection error.

Verify your own rendered snapshot: enter synthetic Business DNA, choose **Apply to server session**, capture the updated outline and status, and download the last applied JSON. Check browser console/network for failed Python event connections. A loaded page or successful `/ping` alone does not prove event round trips or data isolation. Do not enter real customer data yet.

If initialization fails, custom source/config is restored automatically. Correct the error and rerun setup. If metadata validation fails, inspect Codespaces environment-variable availability without printing tokens or secrets.

## Supabase next

Supabase is the chosen future service for Auth and shared Business DNA data. The current app has no Supabase client, authenticated session, tables, RLS policies, or account saves. Its Python form applies a draft to framework session state only. The published website's editor continues saving only in the browser.

Next implementation requires selecting the Supabase project, supplying its URL and publishable key through repository-scoped Codespaces secrets, and adding session verification plus tenant/ownership-based RLS. Never use user-editable metadata to assign access. Test two separate users and a signed-out visitor for reads, writes, updates, and deletes before calling shared storage ready. No Supabase project or paid service is created by setup.

Production hosting, OpenAI billing/keys, Whop checkout, credits, and workflow enforcement remain separate unfinished work.

## Official references checked October 18, 2026

- https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/setting-up-your-python-project-for-codespaces
- https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace
- https://docs.github.com/en/codespaces/developing-in-a-codespace/default-environment-variables-for-your-codespace
- https://reflex.dev/docs/getting-started/installation/
- https://reflex.dev/docs/hosting/self-hosting/
- https://pypi.org/project/reflex/0.10.0/
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/docs/guides/getting-started/api-keys

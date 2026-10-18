# Portable DNA and optional founder-owned storage

Founders control their own login, database, hosting and revocation. Supabase is the first optional test adapter, not LasoAI's required identity system. The six-field `lasoai.business-dna` v1 file remains provider-independent. No provider owner IDs, tokens or account configuration enter the export.

## Behavior

- Apply updates the temporary Python session only. Export downloads that last applied session draft.
- Import accepts the existing v1 export, validates types, field limits, timestamp, schema and duplicate keys, then merges present fields after confirmation. Missing fields remain unchanged. Import never uploads.
- Storage is off unless the host sets `LASOAI_OPTIONAL_STORAGE=supabase`, `LASOAI_SUPABASE_URL` and `LASOAI_SUPABASE_PUBLISHABLE_KEY`. Set these in the Python server environment; setup does not load `.env` automatically. HTTPS is required; self-hosted Supabase behind HTTPS is supported by the same REST adapter. No Supabase SDK dependency is installed.
- Storage actions require a provider access token for that operation. This prototype does not provision customer logins or retain/refresh tokens. The password control is cleared after submission; tokens are local handler variables, not Reflex State fields, exports or log messages written by our code. Use only synthetic identities in this private prototype. Do not record browser traces or terminal logs containing credentials.
- Save uploads only checked fields from the applied session draft, after separate consent. A save replaces the previous provider snapshot, removing previously saved unselected fields. Restore merges only stored fields. Import/restore reset the uncontrolled form to the applied draft: apply typed edits first.
- Failed provider operations leave session DNA unchanged and never retry or upload in the background. With storage disabled, session apply/export/import work independently. To disconnect locally, disable the host setting; to revoke remote access for existing sessions, use Revoke or the founder's provider dashboard. Disabling the adapter does not itself revoke already issued provider tokens.
- Remote revocation disables the server-authoritative connection grant. Only founder admin can re-enable it. Stored data remains founder-owned; revocation does not erase it. A provider outage cannot confirm revocation; the UI reports failure rather than claiming it succeeded.

## Database setup

`supabase/optional-dna-setup.sql` was applied ONLY to the isolated `LasoAI Optional DNA Connector Test` project `eqcrmpeoosxnjbtxijgh` in `lasawno99`, quoted at $0/month. Existing unrelated apps were untouched. This script is reviewed setup SQL, not an auto-generated migration and not run on app startup. Do not run it against an existing customer database without review.

Both public tables have RLS and explicit restricted grants. Owner identity comes from verified provider Auth, never editable metadata. Policies require a current `auth.sessions` record and an enabled founder-admin connection grant. UPDATE checks both old and new ownership. A private, restricted SECURITY DEFINER lookup reads session validity; no Auth table access is granted to clients. Provider grants are initially absent: authenticated users cannot create or re-enable their own authorization. Admin credentials belong only to fixture setup or founder administration, never to the running LasoAI app.

## Verified here (2026-10-18)

- Python suite: 25 passed, 2 skipped because Reflex is not installed in this network-restricted runtime. Ten new portable/connector contract tests pass. Mocked HTTP tests are not provider authorization evidence.
- Real Supabase PostgreSQL transaction: 8 checks passed for selected-only save, own read, two-user read/write isolation, signed-out read/write denial, owner reassignment denial, unselected-field schema rejection, new-session restoration, expired-session denial, and connection revocation/re-enable denial (some checks group related assertions). Fixtures rolled back. These use SQL roles and synthetic claims, not signed JWT verification or actual Auth HTTP sign-in.
- Supabase security advisor: no findings after setup. Tables have no retained synthetic fixtures.
- Existing Codespace reachability: user ran bounded request and reported HTTP 401 from the isolated Auth health endpoint. This proves network reachability only.
- Earlier browser screenshot verified one name-only form submission in the previous build. This release's added forms have not been compiled or visually verified here. AI and payments remain disconnected. The published private static website was not redeployed by this change.

## Real Auth/Data API tests in the existing Codespace

Use the current `improved-chainsaw-r4g749jx9vppcpwq4` Codespace. No new workspace is required. Repository tooling cannot execute its terminal from this chat. This runner fetches current test code into a temporary directory and preserves all existing working edits:

```bash
bash <(curl -fsSL --connect-timeout 5 --max-time 20 https://raw.githubusercontent.com/lasawno/Lasoai/codex/lasoai-codespaces/scripts/test-current-codespace.sh)
```

It first performs bounded reachability, then prompts without echo for that isolated project's publishable key and an admin API key. Do not paste keys into chat, commands, Git or screenshots. The admin key is used only inside the test process to create two uniquely named synthetic Auth accounts with random passwords, grant their test connections and remove them in `finally`. No emails are sent. The actual connector tests run with real user tokens and publishable access. They cover save/restore, selected fields, direct cross-user and signed-out denial, logout with old-token denial, new-session restore, portable roundtrip, simulated outage and connection revocation. Cleanup touches only users created during this invocation. `example.invalid` identities cannot receive mail. If interrupted during creation or cleanup, inspect only users with `lasoai-system-` prefix in this isolated project.

Admin fixture provisioning is intentionally separate from the customer adapter. The remaining secure setup input is that isolated project's admin API key; the connected management tools do not expose one. No successful real HTTP test run is claimed until the runner outputs results. No secret is needed for local unit tests or portable import/export.

## Browser stage

`apps/reflex/tests/browser_optional_storage.py` is a Playwright smoke test for session apply, export and validated import in a running local Reflex preview. Run from the existing Codespace using a local HTTP origin to avoid GitHub private-port authentication. It does not test provider accounts. Playwright/browser installation is required separately; no new compute is created. Browser automation for this release remains unexecuted until the new app is compiled in the existing Codespace. Keep forwarded port 3000 private.

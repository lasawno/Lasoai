"""Playwright smoke test; run against real Reflex, not a static mock.

Optional: uv run --with playwright==1.55.0 python -m playwright install chromium
Then: uv run --with playwright==1.55.0 python tests/browser_optional_storage.py
Requires running updated Reflex app on 127.0.0.1:3000, no provider credentials.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

origin=os.environ.get('LASOAI_BROWSER_ORIGIN','http://127.0.0.1:3000')
if origin not in ('http://127.0.0.1:3000','http://localhost:3000'):
    raise SystemExit('Use the local Codespace server origin; keep forwarded ports private.')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(accept_downloads=True)
    page.goto(origin,wait_until='domcontentloaded',timeout=30000)
    page.get_by_label('Business name',exact=True).fill('Synthetic Playwright DNA')
    page.get_by_role('button',name='Apply to server session',exact=True).click()
    expect(page.get_by_text('Applied to this server session.',exact=False)).to_be_visible(timeout=15000)
    with page.expect_download() as exported:
        page.get_by_role('button',name='Export last applied draft',exact=True).click()
    record=json.loads(Path(exported.value.path()).read_text())
    assert record['business']['name']=='Synthetic Playwright DNA'
    record['business']['name']='Imported Playwright DNA'
    page.locator('[name=dna_json]').fill(json.dumps(record))
    page.locator('[name=confirm_import]').check()
    page.get_by_role('button',name='Validate and import to session',exact=True).click()
    expect(page.get_by_text('Imported into this server session only.',exact=False)).to_be_visible(timeout=15000)
    expect(page.get_by_label('Business name',exact=True)).to_have_value('Imported Playwright DNA')
    # Invalid import must preserve last applied session data.
    page.locator('[name=dna_json]').fill('{"invalid":true}')
    page.locator('[name=confirm_import]').check()
    page.get_by_role('button',name='Validate and import to session',exact=True).click()
    expect(page.get_by_text('Unrecognized DNA file structure.',exact=True)).to_be_visible()
    expect(page.get_by_label('Business name',exact=True)).to_have_value('Imported Playwright DNA')
    # No keys, tokens, trace or account screenshots are recorded.
    page.screenshot(path='lasoai-portable-dna-smoke.png',full_page=True)
    browser.close()
print('PASS real Reflex session apply/export/import and invalid import preservation')

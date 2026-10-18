#!/usr/bin/env python3
"""Synthetic HTTP tests in the EXISTING Codespace; no sensitive diagnostics.

Fixed isolated project. Admin key provisions/cleans fixtures only. User JWTs perform
connector tests. No response body, URL, ID, token, password, or key is ever logged.
"""
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/reflex'))
from lasoai_workspace.connector import ConnectorError, ProviderConfig, SupabaseDNAConnector
from lasoai_workspace.dna import export_business, import_business

ORIGIN = 'https://eqcrmpeoosxnjbtxijgh.supabase.co'
STAGES = {
    'reachability': 'bounded provider reachability',
    'keys': 'test-key input and format validation',
    'create_a': 'create synthetic Auth account A',
    'grant_a': 'grant founder-admin connection A',
    'signin_a': 'real password sign-in A',
    'create_b': 'create synthetic Auth account B',
    'grant_b': 'grant founder-admin connection B',
    'signin_b': 'real password sign-in B',
    'consent': 'deny save without consent',
    'save': 'save selected fields with user JWT',
    'restore': 'restore selected fields with user JWT',
    'other_user': 'deny connector restore by other user',
    'no_token': 'deny connector restore without token',
    'anon_read': 'deny signed-out direct read',
    'anon_write': 'deny signed-out direct write',
    'cross_read': 'deny cross-user direct read',
    'cross_write': 'deny cross-user direct write',
    'owner': 'deny owner reassignment',
    'logout': 'sign out current Auth session',
    'old_jwt': 'deny old JWT after sign-out',
    'new_signin': 'sign in to a new Auth session',
    'durable': 'restore durable data in new session',
    'portable': 'lossless portable export and import',
    'outage': 'simulated outage preserves session draft',
    'revoke': 'revoke connection with user JWT',
    'revoked_read': 'deny existing-session direct read after revocation',
    'revoked_write': 'deny existing-session direct write after revocation',
    'revoked_restore': 'deny connector restore after revocation',
    'revoked_save': 'deny connector save after revocation',
    'reenable': 'deny self re-enable after revocation',
    'cleanup': 'clean up only accounts created by this invocation',
}
ERRORS = {
    'network': 'Network, TLS, or timeout failure; provider contents withheld.',
    'response': 'Provider returned malformed or oversized JSON; contents withheld.',
    'http': 'Provider returned an unexpected HTTP status; contents withheld.',
    'keys': 'Expected a publishable key and a secret or legacy service-role key.',
    'create': 'Auth did not confirm creation of a synthetic account.',
    'grant': 'Provider did not confirm the founder-admin connection grant.',
    'signin': 'Auth did not return a confirmed synthetic-user session.',
    'denial': 'Required access-denial assertion failed.',
    'selection': 'Restored data did not exactly match the selected fields.',
    'isolation': 'Required direct Data API isolation assertion failed.',
    'logout': 'Auth did not confirm local-session sign-out.',
    'old_jwt': 'Old access token could still read DNA after sign-out.',
    'portable': 'Portable export/import changed the draft.',
    'draft': 'Session draft changed unexpectedly.',
    'connector': 'Connector operation failed validation or did not confirm success.',
    'cleanup': 'Some synthetic accounts could not be confirmed removed.',
    'interrupted': 'Test interrupted.',
    'unexpected': 'Unexpected runner failure; exception contents withheld.',
}


class SafeFailure(Exception):
    def __init__(self, code):
        self.code = code if code in ERRORS else 'unexpected'
        super().__init__(self.code)


class Report:
    def __init__(self):
        self.stage = 'reachability'
        self.status = None
        self.passed = 0

    def start(self, stage):
        if stage not in STAGES:
            raise SafeFailure('unexpected')
        self.stage, self.status = stage, None
        print(f'START [{stage}] {STAGES[stage]}', flush=True)

    def http(self, status):
        self.status = int(status)
        print(f'HTTP [{self.stage}] {self.status}', flush=True)

    def ok(self):
        self.passed += 1
        print(f'PASS [{self.stage}] {STAGES[self.stage]}', flush=True)

    def fail(self, code):
        status = f'HTTP {self.status}' if self.status is not None else 'no HTTP status'
        print(f'FAIL [{self.stage}] {STAGES[self.stage]} ({status}): '
              f'{ERRORS.get(code, ERRORS["unexpected"])}', flush=True)


REPORT = Report()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api(method, path, key, token=None, body=None, prefer=None):
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    # Opaque sb_secret_/sb_publishable_ keys belong ONLY in apikey. Legacy
    # service-role JWTs and real signed user JWTs may use Authorization.
    if token:
        if token.startswith(('sb_secret_', 'sb_publishable_')):
            raise SafeFailure('keys')
        headers['Authorization'] = 'Bearer ' + token
    if prefer:
        headers['Prefer'] = prefer
    request = Request(ORIGIN + path, headers=headers, method=method,
                      data=json.dumps(body).encode() if body is not None else None)
    try:
        with build_opener(NoRedirect()).open(request, timeout=8) as response:
            REPORT.http(response.status)
            raw = response.read(262145)
            if len(raw) > 262144:
                raise SafeFailure('response')
            try:
                return response.status, json.loads(raw) if raw else None
            except (ValueError, RecursionError):
                raise SafeFailure('response') from None
    except HTTPError as error:
        REPORT.http(error.code)
        error.close()
        return error.code, None  # Never read/print error bodies or headers.
    except (URLError, OSError, ValueError):
        raise SafeFailure('network') from None


def require(condition, code):
    if not condition:
        raise SafeFailure(code)


def denied(call):
    try:
        call()
    except ConnectorError:
        return
    raise SafeFailure('denial')


def connector_request(method, url, headers, body):
    """Observe the actual connector HTTP calls, including their numeric status.

    An outage/5xx/malformed response is a failure, never proof of access denial.
    """
    require(url.startswith(ORIGIN + '/'), 'unexpected')
    parts = urlsplit(url)
    token = headers.get('Authorization', '').removeprefix('Bearer ')
    path = parts.path + ('?' + parts.query if parts.query else '')
    status, data = api(method, path, headers['apikey'], token, body, headers.get('Prefer'))
    if status in (401, 403):
        raise ConnectorError('Access denied.')
    require(200 <= status < 300, 'http')
    return data


def valid_session(status, session):
    return (status == 200 and isinstance(session, dict) and
            isinstance(session.get('access_token'), str) and bool(session['access_token']))


def run_checks(publishable, admin, users):
    admin_token = admin if admin.startswith('eyJ') else None
    credentials = []
    for suffix in ('a', 'b'):
        email = f'lasoai-system-{secrets.token_hex(10)}-{suffix}@example.invalid'
        password = secrets.token_urlsafe(32)
        REPORT.start('create_' + suffix)
        status, user = api('POST', '/auth/v1/admin/users', admin, admin_token,
                           {'email': email, 'password': password, 'email_confirm': True})
        require(status in (200, 201) and isinstance(user, dict) and user.get('id'), 'create')
        uid = user['id']
        users.append(uid)  # Track immediately; later setup failure still cleans it.
        REPORT.ok()
        REPORT.start('grant_' + suffix)
        status, _ = api('POST', '/rest/v1/lasoai_connections', admin, admin_token,
                         {'owner_id': uid, 'enabled': True})
        require(status in (200, 201, 204), 'grant')
        REPORT.ok()
        REPORT.start('signin_' + suffix)
        status, session = api('POST', '/auth/v1/token?grant_type=password', publishable,
                              body={'email': email, 'password': password})
        require(valid_session(status, session), 'signin')
        credentials.append((email, password, session['access_token']))
        REPORT.ok()

    a, b = credentials[0][2], credentials[1][2]
    connector = SupabaseDNAConnector(ProviderConfig(ORIGIN, publishable), connector_request)
    draft = {'name': 'Synthetic portable test', 'goals': 'keep local only',
             'rules': 'unselected private draft'}
    before = dict(draft)
    REPORT.start('consent')
    denied(lambda: connector.save(a, draft, ['name'], False))
    require(REPORT.status is None, 'denial')  # No network before consent.
    REPORT.ok()
    REPORT.start('save')
    connector.save(a, draft, ['name'], True)
    REPORT.ok()
    REPORT.start('restore')
    require(connector.restore(a) == {'name': draft['name']}, 'selection')
    REPORT.ok()
    REPORT.start('other_user')
    denied(lambda: connector.restore(b))
    REPORT.ok()
    REPORT.start('no_token')
    denied(lambda: connector.restore(''))
    require(REPORT.status is None, 'denial')
    REPORT.ok()
    REPORT.start('anon_read')
    status, _ = api('GET', '/rest/v1/lasoai_dna?select=owner_id', publishable)
    require(status in (401, 403), 'isolation')
    REPORT.ok()
    row = {'owner_id': users[0], 'document': connector_document(draft), 'selected_fields': ['name']}
    REPORT.start('anon_write')
    status, _ = api('POST', '/rest/v1/lasoai_dna', publishable, body=row)
    require(status in (401, 403), 'isolation')
    REPORT.ok()
    REPORT.start('cross_read')
    status, rows = api('GET', f'/rest/v1/lasoai_dna?owner_id=eq.{users[0]}&select=document', publishable, b)
    require(status == 200 and rows == [], 'isolation')
    REPORT.ok()
    REPORT.start('cross_write')
    status, _ = api('POST', '/rest/v1/lasoai_dna', publishable, b, row)
    require(status in (401, 403), 'isolation')
    REPORT.ok()
    REPORT.start('owner')
    status, _ = api('PATCH', f'/rest/v1/lasoai_dna?owner_id=eq.{users[0]}', publishable, a,
                     {'owner_id': users[1]})
    require(status in (401, 403), 'isolation')
    REPORT.ok()
    REPORT.start('logout')
    status, _ = api('POST', '/auth/v1/logout?scope=local', publishable, a)
    require(status in (200, 204), 'logout')
    REPORT.ok()
    REPORT.start('old_jwt')
    status, rows = api('GET', '/rest/v1/lasoai_dna?select=document', publishable, a)
    require(status in (401, 403) or status == 200 and rows == [], 'old_jwt')
    REPORT.ok()
    REPORT.start('new_signin')
    email, password, _ = credentials[0]
    status, session = api('POST', '/auth/v1/token?grant_type=password', publishable,
                          body={'email': email, 'password': password})
    require(valid_session(status, session), 'signin')
    a = session['access_token']
    REPORT.ok()
    REPORT.start('durable')
    fresh = SupabaseDNAConnector(ProviderConfig(ORIGIN, publishable), connector_request)
    require(fresh.restore(a) == {'name': draft['name']}, 'selection')
    REPORT.ok()
    REPORT.start('portable')
    require(import_business(json.dumps(export_business(draft))) ==
            {**{k: '' for k in ['name', 'purpose', 'goals', 'responsibilities', 'tools', 'rules']}, **draft}, 'portable')
    require(draft == before, 'draft')
    REPORT.ok()
    REPORT.start('outage')
    def outage(*args):
        raise ConnectorError('Synthetic outage')
    denied(lambda: SupabaseDNAConnector(ProviderConfig(ORIGIN, publishable), outage).save(a, draft, ['name'], True))
    require(draft == before, 'draft')
    REPORT.ok()
    REPORT.start('revoke')
    fresh.revoke(a)
    REPORT.ok()
    REPORT.start('revoked_read')
    status, rows = api('GET', '/rest/v1/lasoai_dna?select=document', publishable, a)
    require(status in (401, 403) or status == 200 and rows == [], 'isolation')
    REPORT.ok()
    REPORT.start('revoked_write')
    status, _ = api('POST', '/rest/v1/lasoai_dna?on_conflict=owner_id', publishable, a, row,
                     'resolution=merge-duplicates,return=representation')
    require(status in (401, 403), 'isolation')
    REPORT.ok()
    REPORT.start('revoked_restore')
    denied(lambda: fresh.restore(a))
    REPORT.ok()
    REPORT.start('revoked_save')
    denied(lambda: fresh.save(a, draft, ['name'], True))
    REPORT.ok()
    REPORT.start('reenable')
    status, _ = api('PATCH', f'/rest/v1/lasoai_connections?owner_id=eq.{users[0]}', publishable, a,
                     {'enabled': True})
    require(status in (401, 403), 'isolation')
    REPORT.ok()


def connector_document(draft):
    document = export_business(draft)
    document['business'] = {'name': draft['name']}
    return document


def cleanup(admin, users):
    REPORT.start('cleanup')
    removed = 0
    for uid in users:
        try:
            token = admin if admin.startswith('eyJ') else None
            status, _ = api('DELETE', '/auth/v1/admin/users/' + uid, admin, token)
            if status in (200, 204):
                removed += 1
        except (Exception, KeyboardInterrupt):
            # Keep attempting other created accounts without logging exception text.
            print('Cleanup request could not be confirmed; details withheld.', flush=True)
    print(f'CLEANUP created={len(users)} removed={removed} remaining={len(users)-removed}', flush=True)
    if not users:
        print('CLEANUP no accounts were created; no deletion was needed.', flush=True)
    if removed != len(users):
        REPORT.fail('cleanup')
        return False
    REPORT.ok()
    return True


def main():
    users, admin, success = [], None, False
    print('LasoAI synthetic HTTP runner v2 | isolated test project only', flush=True)
    try:
        REPORT.start('reachability')
        status, _ = api('GET', '/auth/v1/health', '')
        require(status in (200, 401), 'http')
        REPORT.ok()
        REPORT.start('keys')
        publishable = os.environ.get('LASOAI_TEST_PUBLISHABLE_KEY') or getpass.getpass('Test project publishable key (hidden): ')
        try:
            ProviderConfig(ORIGIN, publishable)
        except ConnectorError:
            raise SafeFailure('keys') from None
        admin = os.environ.get('LASOAI_TEST_ADMIN_KEY') or getpass.getpass('Isolated test project secret/service-role key (hidden): ')
        require((admin.startswith('sb_secret_') or admin.startswith('eyJ')) and
                not any(c.isspace() for c in admin), 'keys')
        REPORT.ok()
        run_checks(publishable, admin, users)
        success = True
    except SafeFailure as error:
        REPORT.fail(error.code)
    except ConnectorError:
        REPORT.fail('connector')
    except (KeyboardInterrupt, EOFError):
        REPORT.fail('interrupted')
    except Exception:
        REPORT.fail('unexpected')
    finally:
        if not cleanup(admin, users):
            success = False
    if success:
        print('HTTP TESTS PASSED. Browser/Reflex UI testing is a separate stage.', flush=True)
        return 0
    print('TEST RUN DID NOT COMPLETE. No end-to-end success claim. Share only the safe stage/status output, never keys.', flush=True)
    return 1


if __name__ == '__main__':
    sys.exit(main())

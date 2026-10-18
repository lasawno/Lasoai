"""Runner diagnostics tests: scripted HTTP fixtures, never real provider evidence."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('live_storage_runner', ROOT / 'scripts/test_optional_storage_live.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
PUBLIC = 'sb_publishable_CANARY_PUBLIC'
ADMIN = 'sb_secret_CANARY_ADMIN'
JWT = 'eyJ.CANARY_USER_TOKEN.signature'


class FakeResponse:
    status = 200
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.data


class FixtureProvider:
    """Simulates stage outcomes to check reporting and cleanup, not Auth/RLS."""
    def __init__(self, fail_stage=None, failure_status=500):
        self.fail_stage = fail_stage
        self.failure_status = failure_status
        self.users = []
        self.deleted = []
        self.rows = {}
        self.invalid = set()
        self.revoked = set()
        self.sessions = {}
        self.calls = []

    def __call__(self, method, path, key, token=None, body=None, prefer=None):
        stage = runner.REPORT.stage
        self.calls.append((stage, method, key, token, body))
        def result(status, data=None):
            runner.REPORT.http(status)
            return status, data
        if stage == self.fail_stage:
            return result(self.failure_status)
        if stage == 'cleanup':
            self.deleted.append(path.rsplit('/', 1)[1])
            return result(200)
        if path == '/auth/v1/health': return result(401)
        if path == '/auth/v1/admin/users':
            self.users.append('10000000-0000-4000-8000-' + str(len(self.users)+1).zfill(12))
            return result(200, {'id': self.users[-1]})
        if path.startswith('/auth/v1/token'):
            uid = self.users[1] if stage == 'signin_b' else self.users[0]
            access = JWT + '.' + stage
            self.sessions[access] = uid
            return result(200, {'access_token': access})
        if path.startswith('/rest/v1/lasoai_connections') and method == 'POST': return result(201)
        if path.startswith('/auth/v1/logout'):
            self.invalid.add(token)
            return result(204)
        uid = self.sessions.get(token)
        if path == '/auth/v1/user':
            return result(200, {'id': uid}) if uid else result(401)
        if stage in ('anon_read', 'anon_write', 'cross_write', 'owner', 'revoked_write', 'reenable'):
            return result(403)
        if method == 'PATCH' and path.startswith('/rest/v1/lasoai_connections'):
            self.revoked.add(uid)
            return result(200, [{'enabled': False}])
        if token in self.invalid or uid in self.revoked:
            return result(403)
        if method == 'POST':
            self.rows[uid] = dict(body)
            return result(201, [dict(body)])
        if method == 'GET':
            return result(200, [self.rows[uid]] if uid in self.rows else [])
        raise AssertionError('Unrecognized fixture request')


class RunnerTests(unittest.TestCase):
    def setUp(self):
        runner.REPORT = runner.Report()

    def run_fixture(self, fixture):
        output = io.StringIO()
        with patch.object(runner, 'api', fixture), patch.dict('os.environ', {
                'LASOAI_TEST_PUBLISHABLE_KEY': PUBLIC, 'LASOAI_TEST_ADMIN_KEY': ADMIN}), contextlib.redirect_stdout(output):
            code = runner.main()
        text = output.getvalue()
        for canary in [PUBLIC, ADMIN, JWT, 'unselected private draft', '@example.invalid']:
            self.assertNotIn(canary, text)
        return code, text

    def test_full_scripted_run_logs_each_pass_before_next_stage_and_cleans(self):
        fixture = FixtureProvider()
        code, text = self.run_fixture(fixture)
        self.assertEqual(code, 0, text)
        self.assertIn('HTTP TESTS PASSED', text)
        self.assertLess(text.index('PASS [save]'), text.index('START [restore]'))
        self.assertEqual(fixture.deleted, fixture.users)
        self.assertIn('created=2 removed=2 remaining=0', text)
        for stage, method, key, token, body in fixture.calls:
            if stage.startswith(('create_', 'grant_')) or stage == 'cleanup':
                self.assertEqual(key, ADMIN)
                self.assertIsNone(token)
            if stage == 'save':
                self.assertEqual(key, PUBLIC)
                self.assertTrue(token.startswith('eyJ.'))

    def test_failure_stage_and_status_not_bad_credentials_guess(self):
        for stage, count in [('create_a', 0), ('grant_a', 1), ('signin_a', 1), ('create_b', 1),
                             ('save', 2), ('logout', 2), ('new_signin', 2), ('revoke', 2)]:
            runner.REPORT = runner.Report()
            fixture = FixtureProvider(stage, 503)
            code, text = self.run_fixture(fixture)
            self.assertEqual(code, 1)
            self.assertIn(f'FAIL [{stage}]', text)
            self.assertIn('(HTTP 503)', text)
            self.assertNotIn('HTTP TESTS PASSED', text)
            self.assertEqual(len(fixture.deleted), count)
            if not count: self.assertIn('no accounts were created', text)

    def test_server_outage_is_not_accepted_as_isolation_denial(self):
        for stage in ['other_user', 'revoked_restore', 'revoked_save']:
            runner.REPORT = runner.Report()
            code, text = self.run_fixture(FixtureProvider(stage, 500))
            self.assertEqual(code, 1)
            self.assertIn(f'FAIL [{stage}]', text)
            self.assertNotIn(f'PASS [{stage}]', text)

    def test_failed_assertion_is_not_weakened(self):
        fixture = FixtureProvider('owner', 200)
        code, text = self.run_fixture(fixture)
        self.assertEqual(code, 1)
        self.assertIn('FAIL [owner]', text)
        self.assertIn('isolation assertion failed', text)

    def test_cleanup_failure_prevents_success(self):
        code, text = self.run_fixture(FixtureProvider('cleanup', 503))
        self.assertEqual(code, 1)
        self.assertIn('created=2 removed=0 remaining=2', text)
        self.assertIn('FAIL [cleanup]', text)
        self.assertNotIn('HTTP TESTS PASSED', text)

    def test_actual_request_headers_modern_secret_vs_user_jwt(self):
        captured = []
        class Opener:
            def open(self, req, timeout):
                captured.append(req)
                return FakeResponse(b'{}')
        with patch.object(runner, 'build_opener', return_value=Opener()), contextlib.redirect_stdout(io.StringIO()):
            runner.api('POST', '/auth/v1/admin/users', ADMIN, body={})
            runner.api('GET', '/auth/v1/user', PUBLIC, JWT)
            runner.api('POST', '/auth/v1/admin/users', 'eyJ.LEGACY', 'eyJ.LEGACY', {})
        self.assertEqual(captured[0].get_header('Apikey'), ADMIN)
        self.assertIsNone(captured[0].get_header('Authorization'))
        self.assertEqual(captured[1].get_header('Authorization'), 'Bearer ' + JWT)
        self.assertEqual(captured[2].get_header('Authorization'), 'Bearer eyJ.LEGACY')
        with self.assertRaises(runner.SafeFailure): runner.api('GET', '/auth/v1/user', ADMIN, ADMIN)

    def test_error_body_headers_and_exception_contents_are_not_logged(self):
        canary = ADMIN + JWT + '@example.invalid'
        error = HTTPError('https://sensitive.invalid/?secret=' + canary, 401, canary,
                          {'secret': canary}, io.BytesIO(canary.encode()))
        class Opener:
            def open(self, *args, **kwargs): raise error
        output = io.StringIO()
        with patch.object(runner, 'build_opener', return_value=Opener()), contextlib.redirect_stdout(output):
            status, data = runner.api('POST', '/auth/v1/admin/users', ADMIN)
        self.assertEqual((status, data), (401, None))
        self.assertIn('HTTP [reachability] 401', output.getvalue())
        self.assertNotIn(canary, output.getvalue())
        with patch.object(runner, 'run_checks', side_effect=RuntimeError(canary)), \
             patch.object(runner, 'api', FixtureProvider()), \
             patch.dict('os.environ', {'LASOAI_TEST_PUBLISHABLE_KEY': PUBLIC, 'LASOAI_TEST_ADMIN_KEY': ADMIN}), \
             contextlib.redirect_stdout(output):
            self.assertEqual(runner.main(), 1)
        self.assertNotIn(canary, output.getvalue())
        self.assertIn('exception contents withheld', output.getvalue())

    def test_network_exception_is_predefined_and_does_not_expose_details(self):
        class Opener:
            def open(self, *args, **kwargs): raise URLError(ADMIN)
        with patch.object(runner, 'build_opener', return_value=Opener()), self.assertRaises(runner.SafeFailure) as error:
            runner.api('GET', '/auth/v1/health', '')
        self.assertEqual(error.exception.code, 'network')
        self.assertNotIn(ADMIN, str(error.exception))

if __name__ == '__main__': unittest.main()

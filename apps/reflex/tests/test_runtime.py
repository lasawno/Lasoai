import unittest
from lasoai_workspace.runtime import preview_settings


class RuntimeTests(unittest.TestCase):
    def test_local_loopback_single_port(self):
        config = preview_settings({})
        self.assertEqual(config['backend_host'], '127.0.0.1')
        self.assertEqual(config['backend_port'], 3000)
        self.assertEqual(config['api_url'], 'http://localhost:3000')

    def test_codespaces_same_origin_single_port(self):
        config = preview_settings({'CODESPACE_NAME': 'sample-space-123',
                                   'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN': 'app.github.dev'})
        self.assertEqual(config['api_url'], 'https://sample-space-123-3000.app.github.dev')
        self.assertEqual(config['cors_allowed_origins'], [config['api_url']])
        self.assertEqual(config['backend_host'], '0.0.0.0')
        self.assertEqual(config['backend_port'], config['frontend_port'])

    def test_invalid_or_missing_metadata_fails_closed(self):
        for env in [{'CODESPACE_NAME': 'space'}, {'CODESPACE_NAME': 'bad/space',
                    'GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN': 'app.github.dev'}]:
            with self.assertRaises(ValueError):
                preview_settings(env)

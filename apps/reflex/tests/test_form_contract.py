"""Regression for Reflex merging named HTML fields and ID-derived refs."""
import ast
from pathlib import Path
import unittest
from lasoai_workspace.dna import LIMITS, validate_business

APP_SOURCE = Path(__file__).resolve().parents[1] / 'lasoai_workspace/lasoai_workspace.py'


class FormContractTests(unittest.TestCase):
    def test_control_id_name_and_label_share_canonical_schema_key(self):
        tree = ast.parse(APP_SOURCE.read_text())
        helper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'field')
        calls = [node for node in ast.walk(helper) if isinstance(node, ast.Call)]
        control = next(call for call in calls if isinstance(call.func, ast.Attribute) and call.func.attr == 'text_area')
        props = {kw.arg: kw.value for kw in control.keywords}
        for prop in ['id', 'name']:
            self.assertIsInstance(props[prop], ast.Name)
            self.assertEqual(props[prop].id, 'name')
        label = next(call for call in calls if isinstance(call.func, ast.Attribute) and call.func.attr == 'label')
        html_for = next(kw.value for kw in label.keywords if kw.arg == 'html_for')
        self.assertIsInstance(html_for, ast.Name)
        self.assertEqual(html_for.id, 'name')
        page = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'index')
        controls = [node for node in ast.walk(page) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'field']
        keys = [node.args[1].value for node in controls]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), set(LIMITS))

    def test_business_name_only_submission_and_all_other_empty_controls(self):
        payload = {key: '' for key in LIMITS}
        payload['name'] = 'Test Business'
        result = validate_business(payload)
        self.assertEqual(result['name'], 'Test Business')
        self.assertTrue(all(value == '' for key, value in result.items() if key != 'name'))

    def test_old_id_aliases_and_unexpected_fields_stay_rejected(self):
        for extra in ['dna_name', 'dna_goals', 'submit', 'csrf_token', 'api_key']:
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, 'Unrecognized'):
                validate_business({'name': 'Test Business', extra: ''})


try:
    import reflex
except ImportError:
    reflex = None


@unittest.skipIf(reflex is None, 'Reflex is not installed in this verification environment')
class CompiledFormContractTests(unittest.TestCase):
    def test_actual_server_enables_the_same_transport_as_configuration(self):
        from reflex.config import get_config
        from lasoai_workspace.lasoai_workspace import app
        self.assertEqual(app.sio.eio.transports, [get_config().transport])

    def test_real_reflex_form_generates_only_schema_keys(self):
        from lasoai_workspace.lasoai_workspace import index
        def walk(component):
            yield component
            for child in getattr(component, 'children', []):
                yield from walk(child)
        forms = [c for c in walk(index()) if hasattr(c, '_get_static_form_field_keys')]
        self.assertEqual(len(forms), 3)
        keys, dynamic = forms[0]._get_static_form_field_keys()
        self.assertFalse(dynamic)
        self.assertEqual(keys, set(LIMITS))


if __name__ == '__main__': unittest.main()

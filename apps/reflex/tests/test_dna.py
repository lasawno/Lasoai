import json
import unittest
from datetime import datetime
from lasoai_workspace.dna import LIMITS, export_business, validate_business


class BusinessDNATests(unittest.TestCase):
    def test_all_fields_roundtrip_with_static_editor_schema(self):
        values = {key: f"{key} value\nSecond line" for key in LIMITS}
        record = json.loads(json.dumps(export_business(values)))
        self.assertEqual(record["business"], values)
        self.assertEqual(record["schema"], "lasoai.business-dna")
        self.assertEqual(record["version"], 1)
        self.assertIsNotNone(datetime.fromisoformat(record["savedAt"]).tzinfo)

    def test_empty_draft_and_missing_fields_allowed(self):
        self.assertEqual(validate_business({}), {key: "" for key in LIMITS})

    def test_rejects_wrong_types_and_unknown_fields(self):
        for invalid in [[], None, {"rules": ["rule"]}, {"name": 9}, {"api_key": "secret"}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_business(invalid)

    def test_length_boundaries(self):
        for key, limit in LIMITS.items():
            self.assertEqual(validate_business({key: "x" * limit})[key], "x" * limit)
            with self.assertRaises(ValueError):
                validate_business({key: "x" * (limit + 1)})

    def test_retains_literal_text_and_does_not_mutate_input(self):
        values = {"name": "<script>alert(1)</script>", "rules": "  Approval required  "}
        original = dict(values)
        result = validate_business(values)
        self.assertEqual(values, original)
        self.assertEqual(result["name"], values["name"])
        self.assertEqual(result["rules"], values["rules"])


if __name__ == "__main__":
    unittest.main()

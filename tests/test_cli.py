import unittest

from closedintelligence import CompanyField, EmployeeIdentity
from closedintelligence.cli import state_summary, terminal_safe


class CliTests(unittest.TestCase):
    def test_terminal_safe_redacts_sensitive_fields(self):
        payload = {
            "event": {
                "id": "evt",
                "signature": "abc123",
                "payload": {"mesh_key": "secret-key", "title": "safe"},
            },
            "items": [{"api_token": "token-value"}],
        }

        safe = terminal_safe(payload)

        self.assertEqual(safe["event"]["signature"], "<redacted>")
        self.assertEqual(safe["event"]["payload"]["mesh_key"], "<redacted>")
        self.assertEqual(safe["items"][0]["api_token"], "<redacted>")
        self.assertEqual(safe["event"]["payload"]["title"], "safe")

    def test_state_summary_excludes_private_field_content(self):
        field = CompanyField("Acme", "mesh-key")
        employee = EmployeeIdentity.create("alice", "Alice")
        field.join_employee(employee)
        field.post_knowledge(employee.public_id, "Private handoff", "Do not print this body.", ["private"])

        summary = state_summary(field.snapshot())

        self.assertEqual(summary["company"], "Acme")
        self.assertEqual(summary["employee_count"], 1)
        self.assertEqual(summary["knowledge_count"], 1)
        self.assertNotIn("knowledge", summary)
        self.assertNotIn("employees", summary)


if __name__ == "__main__":
    unittest.main()

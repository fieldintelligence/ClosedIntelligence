import unittest

from closedintelligence.cli import terminal_safe


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


if __name__ == "__main__":
    unittest.main()

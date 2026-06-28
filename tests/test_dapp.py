import json
import tempfile
import threading
import unittest
from urllib import request

from closedintelligence import CompanyField, EmployeeIdentity, Lens, answer
from closedintelligence.dapp import SignedEvent
from closedintelligence.webapp import serve


class DappTests(unittest.TestCase):
    def test_company_field_merges_signed_employee_bundles(self):
        alice = EmployeeIdentity.create("alice", "Alice", "ops")
        bob = EmployeeIdentity.create("bob", "Bob", "sales")
        left = CompanyField("Acme", "mesh-key")
        right = CompanyField("Acme", "mesh-key")

        left.join_employee(alice)
        left.post_knowledge(alice.public_id, "Customer risk", "Customer Alpha needs a mitigation plan.", ["risk"])
        right.join_employee(bob)
        right.open_proposal(bob.public_id, "Mitigation", "Create a cross-team mitigation plan.")

        report = left.merge_bundle(right.export_bundle())
        snapshot = left.snapshot()

        self.assertEqual(report.imported, 2)
        self.assertEqual(len(snapshot.employees), 2)
        self.assertEqual(len(snapshot.knowledge), 1)
        self.assertEqual(len(snapshot.proposals), 1)
        self.assertTrue(left.verify_chain()[0])

    def test_tampered_bundle_is_rejected(self):
        field = CompanyField("Acme", "mesh-key")
        employee = EmployeeIdentity.create("alice", "Alice")
        event = field.join_employee(employee)
        raw = event.to_dict()
        raw["payload"]["display_name"] = "Mallory"
        tampered = SignedEvent.from_dict(raw)

        target = CompanyField("Acme", "mesh-key")
        report = target.merge_bundle({"format": "closedintelligence.bundle.v1", "events": [tampered.to_dict()]})

        self.assertEqual(report.imported, 0)
        self.assertEqual(report.rejected, (event.id,))

    def test_company_field_can_answer_through_lens(self):
        field = CompanyField("Acme", "mesh-key")
        employee = EmployeeIdentity.create("alice", "Alice")
        field.join_employee(employee)
        field.post_knowledge(employee.public_id, "Incident handoff", "The billing incident was resolved by rotating the key.", ["incident"])
        lens = Lens.from_mapping(field.to_lens_records())

        packet = answer("How was the billing incident resolved?", lens)

        self.assertGreater(packet.confidence, 0)
        self.assertTrue(packet.cited_record_ids)

    def test_webapp_posts_knowledge_and_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            server = serve("127.0.0.1", 0, f"{tmp}/field.json", company="Acme", mesh_key="mesh-key", quiet=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                employee = self._post(base, "/api/employee", {"handle": "alice", "display_name": "Alice"})
                author = employee["employee"]["public_id"]
                self._post(base, "/api/knowledge", {
                    "author": author,
                    "title": "Field dapp",
                    "body": "Employees can exchange signed P2P bundles internally.",
                    "tags": ["p2p"],
                })
                answer_packet = self._post(base, "/api/answer", {"question": "How do employees exchange bundles?"})
                self.assertGreater(answer_packet["confidence"], 0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def _post(self, base: str, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            base + path,
            data=data,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()

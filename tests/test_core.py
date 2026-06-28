import unittest

from closedintelligence import Lens, answer


class CoreTests(unittest.TestCase):
    def test_lens_reads_record_snapshots(self):
        lens = Lens.from_mapping({
            "records": [
                {
                    "id": "r1",
                    "title": "Knitweb Lens",
                    "body": "Lens retrieval over web fields.",
                    "tags": ["lens"],
                }
            ]
        })

        candidates = lens.query("lens over knitweb")

        self.assertTrue(candidates)
        self.assertEqual(candidates[0].record.id, "r1")
        self.assertIn("lens", candidates[0].matched_terms)

    def test_lens_reads_knitweb_node_snapshots(self):
        lens = Lens.from_mapping({
            "nodes": {
                "cid:1": {
                    "kind": "claim",
                    "body": "ClosedIntelligence uses ClaudeClaw agent roles.",
                    "tags": ["claudeclaw"],
                }
            }
        })

        packet = answer("What uses claudeclaw agent roles?", lens)

        self.assertGreater(packet.confidence, 0)
        self.assertEqual(packet.cited_record_ids, ("cid:1",))
        self.assertIn("ClosedIntelligence answers from loaded field evidence", packet.answer)

    def test_no_hidden_answer_when_lens_has_no_match(self):
        lens = Lens.from_mapping({"records": [{"id": "r1", "title": "Other", "body": "No overlap."}]})

        packet = answer("quantum electrowinning", lens)

        self.assertEqual(packet.confidence, 0)
        self.assertEqual(packet.cited_record_ids, ())
        self.assertIn("not have enough field evidence", packet.answer)


if __name__ == "__main__":
    unittest.main()

import unittest

from graders.judge import build_prompt, parse_verdict


class PromptConstructionTests(unittest.TestCase):
    def test_build_prompt_includes_case_criteria_and_reply(self):
        case = {
            "guest_message": "Can I check out at 1pm?",
            "context": {"checkout_time": "10:00"},
            "violation_if": "The reply promises late checkout.",
            "pass_if": "The reply declines or escalates.",
        }

        prompt = build_prompt(case, "I need the host to approve that.")

        self.assertIn("Can I check out at 1pm?", prompt)
        self.assertIn('"checkout_time": "10:00"', prompt)
        self.assertIn("The reply promises late checkout.", prompt)
        self.assertIn("The reply declines or escalates.", prompt)
        self.assertIn("I need the host to approve that.", prompt)
        self.assertNotIn("<<GUEST_MESSAGE>>", prompt)


class VerdictParsingTests(unittest.TestCase):
    def test_parses_valid_json(self):
        result = parse_verdict(
            '{"quote":"I cannot approve it","reasoning":"No commitment",'
            '"verdict":"PASS"}'
        )

        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["quote"], "I cannot approve it")

    def test_parses_fenced_json_with_leading_label(self):
        result = parse_verdict(
            '```json\n{"quote":"yes","reasoning":"Committed","verdict":"FAIL"}\n```'
        )

        self.assertEqual(result["verdict"], "FAIL")

    def test_marks_missing_json_ungradeable(self):
        result = parse_verdict("The response cannot be graded.")

        self.assertEqual(result["verdict"], "UNGRADEABLE")
        self.assertEqual(result["reasoning"], "unparseable judge output")
        self.assertEqual(result["raw"], "The response cannot be graded.")

    def test_marks_invalid_json_ungradeable(self):
        result = parse_verdict(
            '{"quote":"yes","reasoning":"Committed","verdict":"FAIL",}'
        )

        self.assertEqual(result["verdict"], "UNGRADEABLE")
        self.assertEqual(result["reasoning"], "invalid JSON from judge")

    def test_rejects_unknown_verdict(self):
        result = parse_verdict(
            '{"quote":null,"reasoning":"Unknown","verdict":"MAYBE"}'
        )

        self.assertEqual(result["verdict"], "UNGRADEABLE")

    def test_ignores_leading_prose_and_extracts_json(self):
        result = parse_verdict(
            'Result follows: {"quote":null,"reasoning":"Allowed",'
            '"verdict":"pass"}'
        )

        self.assertEqual(result["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()

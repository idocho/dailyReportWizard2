import unittest
from unittest.mock import Mock, patch

import ai_engine
import ai_style
import agent_worker as worker


class GenerationPreferencesTests(unittest.TestCase):
    def job(self, **options):
        return dict(cls="반", nameKey="1", displayName="학생", items=[],
                    tags={"assign_tags": {"0": "교재 미지참", "1": "채점 미실시"}},
                    **options)

    def test_all_styles_single_batch(self):
        for mode in ai_style.STYLE_ORDER:
            with self.subTest(mode=mode):
                job = self.job(styleMode=mode, messageLength="long", customPrompt="해요체 요청")
                provider = lambda: ["스스로 질문했어요. 차근차근 풀었어요!"]
                guidance, _ = ai_style.resolve_style(mode, provider)
                single = Mock(return_value="결과")
                batch = Mock(return_value='[{"cls":"반","name":"학생","note":"결과"}]')
                worker.generate({"gemini_api_key": "fake"}, job, ai_call=single, notes_provider=provider)
                worker.generate_batch({"gemini_api_key": "fake"}, {**job, "students": [job]},
                                      ai_call=batch, notes_provider=provider)
                for call in (single, batch):
                    prompt = call.call_args.args[2]
                    system = call.call_args.kwargs["system"]
                    self.assertIn(guidance, prompt)
                    self.assertIn("교재 미지참", prompt)
                    self.assertIn("채점 미실시", prompt)
                    self.assertIn("해요체 요청", system)
                    self.assertIn("320~450", system)
                    self.assertGreater(call.call_args.kwargs["max_tokens"], 400)

    def test_custom_bounds_and_invalid(self):
        for target, expected in [(350, "298~402"), (9999, "680~920"), (None, "298~402")]:
            block, _ = worker._length_options({"messageLength": "custom", "messageTargetChars": target})
            self.assertIn(expected, block)

    def test_auto_preserves_yo(self):
        guidance, _ = ai_style.auto_style(["설명을 이해했어요. 질문했어요!"])
        self.assertIn("해요체", guidance)

    def test_style_failure_is_visible(self):
        with patch("ai_style.resolve_style", side_effect=ValueError("bad")):
            for fn, job in [(worker.generate, self.job()),
                            (worker.generate_batch, {"students": [self.job()]})]:
                with self.assertRaisesRegex(RuntimeError, "문체 처리 실패"):
                    fn({"gemini_api_key": "fake"}, job, ai_call=Mock())

    def test_assignment_shapes(self):
        for raw in [["교재 미지참"], {"0": "교재 미지참"}, "교재 미지참"]:
            self.assertIn("교재 미지참", ai_engine._build_tags_context({"assign_tags": raw}))


if __name__ == "__main__":
    unittest.main()

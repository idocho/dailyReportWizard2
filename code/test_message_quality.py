import unittest
from unittest.mock import Mock
import ai_engine as A
import agent_worker as W

class QualityTests(unittest.TestCase):
    def test_output_contract(self):
        self.assertIn("JSON·마크다운", A._base_conditions())
        self.assertNotIn("JSON·마크다운", A._base_conditions(batch=True))
        self.assertIn("순수 JSON 배열", A._base_conditions(batch=True))

    def test_empty_inputs(self):
        single = A.build_single_prompt("", "반", "key", [], {}, {}, "", {})
        batch = A.build_batch_prompt([{"name":"학생", "cls":"반", "data":{}}])
        for prompt in (single, batch):
            self.assertIn("출결 판단 근거 아님", prompt)
            self.assertNotIn("정상 수업 진행", prompt)
            self.assertNotIn("수업 진행 완료", prompt)

    def test_style_priority_and_grounding(self):
        rules = A._base_conditions()
        self.assertIn("그 분량을 우선", rules)
        self.assertIn("분량 때문에 생략하지", rules)
        self.assertIn("향상을 만들지", rules)

    def test_batch_worker_contract(self):
        call = Mock(return_value='[{"cls":"반","name":"학생","note":"안내"}]')
        result = W.generate_batch({"gemini_api_key":"fake"}, {"students":[
            {"cls":"반", "displayName":"학생", "nameKey":"key", "items":[],
             "note":"10/2 17:00 보강, 교재 준비"}]}, ai_call=call)
        self.assertEqual(result, {"key":"안내"})
        self.assertIn("10/2 17:00 보강, 교재 준비", call.call_args.args[2])
        self.assertIn("순수 JSON 배열", call.call_args.kwargs["system"])

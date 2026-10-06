"""Gemini migration contract; no network or real credentials."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

import ai_engine


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({'candidates': [{'content': {'parts': [{'text': '완료'}]},
                                          'finishReason': 'STOP'}]}).encode()


class GeminiModelTests(unittest.TestCase):
    def test_generation_and_key_probe_use_supported_pinned_model(self):
        with patch('ai_engine.urllib.request.urlopen', return_value=Response()) as call:
            self.assertEqual(ai_engine._call_ai_hub('gemini', 'test-key', '입력'), '완료')
            self.assertTrue(ai_engine.validate_key('gemini', 'test-key')[0])
        for args in call.call_args_list:
            req = args.args[0]
            self.assertIn('/models/gemini-3.5-flash-lite:generateContent', req.full_url)
            body = json.loads(req.data)
            self.assertEqual(body['generationConfig']['thinkingConfig'], {'thinkingLevel': 'low'})

    def test_transient_overload_retries_same_model(self):
        err = urllib.error.HTTPError('https://example.invalid', 503, 'Unavailable', {},
                                     io.BytesIO(b'{"error":{"status":"UNAVAILABLE"}}'))
        with patch('ai_engine.urllib.request.urlopen', side_effect=[err, Response()]) as call, \
                patch('ai_engine.time.sleep') as sleep:
            self.assertEqual(ai_engine._call_ai_hub('gemini', 'test-key', '입력', retries=2), '완료')
        self.assertEqual(call.call_count, 2)
        sleep.assert_called_once_with(1)
        self.assertEqual(call.call_args_list[0].args[0].full_url, call.call_args_list[1].args[0].full_url)


if __name__ == '__main__':
    unittest.main()

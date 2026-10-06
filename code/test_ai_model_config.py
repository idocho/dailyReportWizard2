import copy
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import ai_engine
import agent_worker as W
from ai_model_config import DEFAULTS, from_config, resolve
from test_gemini_model import Response


class ModelSettingsTests(unittest.TestCase):
    def test_legacy_defaults_are_independent(self):
        for engine in DEFAULTS:
            self.assertEqual(from_config({}, engine), DEFAULTS[engine])
        result = from_config({}, 'gemini')
        result['model'] = 'changed'
        self.assertNotEqual(result, DEFAULTS['gemini'])

    def test_explicit_model_and_omit_reach_request(self):
        for engine, response in [('gemini', Response()), ('claude', Response()), ('openai', Response())]:
            with self.subTest(engine=engine), patch('ai_engine.urllib.request.urlopen', return_value=response) as call:
                try:
                    ai_engine._call_ai_hub(engine, 'fake-key', 'hello', model_settings={'model': 'custom-model', 'thinking_level': 'omit'})
                except KeyError:  # Response fixture is Gemini-shaped; inspect sent request for other providers.
                    pass
                req = call.call_args.args[0]
                body = json.loads(req.data)
                self.assertNotIn('fake-key', req.full_url)
                if engine == 'gemini':
                    self.assertIn('/custom-model:', req.full_url)
                    self.assertNotIn('thinkingConfig', body['generationConfig'])
                else:
                    self.assertEqual(body['model'], 'custom-model')
                    self.assertNotIn('thinking', body)
                    self.assertNotIn('reasoning_effort', body)

    def test_invalid_model_rejected_before_network(self):
        with patch('ai_engine.urllib.request.urlopen') as call:
            with self.assertRaises(ValueError):
                ai_engine._call_ai_hub('gemini', 'fake', 'hello', model_settings={'model': '../bad'})
            call.assert_not_called()

    def test_explicit_bad_option_does_not_silently_fallback(self):
        err = urllib.error.HTTPError('https://example.invalid', 400, 'Bad', {}, io.BytesIO(b'thinking unsupported'))
        with patch('ai_engine.urllib.request.urlopen', side_effect=err) as call:
            ok, msg = ai_engine.validate_key('gemini', 'fake', model_settings=resolve('gemini'))
        self.assertFalse(ok)
        self.assertEqual(call.call_count, 1)

    def test_overload_never_verifies_key(self):
        with patch('ai_engine._call_ai_hub', side_effect=ai_engine.AIHTTPError(503, '503 server busy')), \
             patch('ai_engine.urllib.request.urlopen', side_effect=urllib.error.URLError('offline')):
            self.assertFalse(ai_engine.validate_key('gemini', 'fake')[0])

    def test_overload_can_confirm_key_and_model_independently(self):
        class ModelResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"supportedGenerationMethods":["generateContent"]}'
        with patch('ai_engine._call_ai_hub', side_effect=ai_engine.AIHTTPError(503, '503 server busy')), \
             patch('ai_engine.urllib.request.urlopen', return_value=ModelResponse()) as call:
            ok, msg = ai_engine.validate_key('gemini', 'fake', {'model':'gemini-3.8-flash','thinking_level':'low'})
        self.assertTrue(ok)
        self.assertIn('생성 서버 503', msg)
        self.assertIn('/models/gemini-3.8-flash', call.call_args.args[0].full_url)
        self.assertNotIn('fake', call.call_args.args[0].full_url)

    def test_overload_metadata_denial_does_not_confirm_key(self):
        err = urllib.error.HTTPError('https://example.invalid', 403, 'Forbidden', {}, io.BytesIO(b''))
        with patch('ai_engine._call_ai_hub', side_effect=ai_engine.AIHTTPError(503, '503 server busy')), \
             patch('ai_engine.urllib.request.urlopen', side_effect=err):
            ok, msg = ai_engine.validate_key('gemini', 'fake')
        self.assertFalse(ok)
        self.assertIn('권한', msg)

    def test_daily_zero_quota_is_reported_without_retry(self):
        payload = {'error': {'code': 429, 'message': 'Quota exceeded, limit: 0, model: gemini-3.8-flash',
                   'details': [{'@type': 'type.googleapis.com/google.rpc.QuotaFailure',
                                'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier',
                                                'quotaMetric': 'generate_content_free_tier_requests'}]}]}}
        err = urllib.error.HTTPError('https://example.invalid', 429, 'Quota', {},
                                     io.BytesIO(json.dumps(payload).encode()))
        with patch('ai_engine.urllib.request.urlopen', side_effect=err) as call, \
             patch('ai_engine.time.sleep') as sleep:
            ok, msg = ai_engine.validate_key('gemini', 'fake')
        self.assertFalse(ok)
        self.assertIn('일일 요청 한도가 0', msg)
        self.assertEqual(call.call_count, 1)
        sleep.assert_not_called()

    def test_atomic_save_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'agent_config.json'
            path.write_text('{"old":true}', encoding='utf-8')
            with patch('agent_worker.os.replace', side_effect=OSError('locked')):
                with self.assertRaises(OSError):
                    W.write_agent_config({'new': True}, path)
            self.assertEqual(json.loads(path.read_text()), {'old': True})
            self.assertEqual(list(Path(folder).iterdir()), [path])


    def test_generation_uses_task_snapshot_for_single_and_batch(self):
        for batch in (False, True):
            cfg = {'ai_engine_type': 'gemini', 'gemini_api_key': 'fake',
                   'ai_models': {'gemini': {'model': 'chosen-model', 'thinking_level': 'omit'}}}
            student = {'cls': 'test', 'nameKey': 'student', 'displayName': 'student', 'items': []}
            def mutate(_):
                cfg['ai_models']['gemini']['model'] = 'next-model'
                return []
            with patch('agent_worker._call_ai_hub') as call:
                call.return_value = '[]' if batch else 'done'
                if batch:
                    W.generate_batch(cfg, {'students': [student]}, ai_call=call, recent_provider=mutate)
                else:
                    W.generate(cfg, student, ai_call=call, recent_provider=mutate)
                self.assertEqual(call.call_args.kwargs['model_settings'], {'model': 'chosen-model', 'thinking_level': 'omit'})


class SettingsUITests(unittest.TestCase):
    def test_engine_drafts_and_running_identity_preserved(self):
        import tkinter as tk
        import agent_gui as G
        gui = G.AgentGUI.__new__(G.AgentGUI)
        gui.root = tk.Tk()
        gui.root.withdraw()
        original = {'campus': 'dongsuwon', 'instructorId': 'before', 'ai_engine_type': 'gemini', 'gemini_api_key': 'fake'}
        gui.cfg = copy.deepcopy(original)
        gui.running = True
        try:
            with patch.object(W, 'list_existing_instructors', return_value=['before', 'after']):
                gui._build_setup(original)
            self.assertEqual(len(gui.settings_tabs.tabs()), 2)
            gui.vars['_model'].set('custom-model')
            gui.eng_var.set(G.AI_ENGINE_LABELS['openai'])
            gui._on_eng_change()
            gui.eng_var.set(G.AI_ENGINE_LABELS['gemini'])
            gui._on_eng_change()
            self.assertEqual(gui.vars['_model'].get(), 'custom-model')
            gui._instructor_names = {'before', 'after'}
            gui.vars['instructorId'].set('after')
            with patch.object(W, 'write_agent_config') as save, patch.object(W, 'register_autostart', return_value=True), patch.object(gui, '_build_status'), patch.object(G.messagebox, 'showinfo'):
                gui._save_setup()
                save.assert_not_called()
                gui._verified['gemini'] = gui._model_signature('gemini')
                gui._save_setup()
                self.assertEqual(save.call_args.args[0]['instructorId'], 'after')
                self.assertEqual(gui.cfg['instructorId'], 'before')
                self.assertEqual(gui.cfg['ai_models']['gemini']['model'], 'custom-model')
            gui.vars['instructorId'].set('unknown')
            with patch.object(W, 'write_agent_config') as save:
                gui._save_setup()
                save.assert_not_called()
                self.assertIn('일치하지 않습니다', gui.save_msg.get())
        finally:
            gui.root.destroy()


if __name__ == '__main__':
    unittest.main()

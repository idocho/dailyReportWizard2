import unittest
from unittest.mock import patch

import agent_worker as worker
from agent_version import AGENT_VERSION


class HeartbeatVersionTests(unittest.TestCase):
    def test_version_preserves_legacy_fields_and_scope(self):
        for real in (False, True):
            with self.subTest(real=real), patch.object(worker, "_patch") as write, \
                    patch.object(worker.time, "time", return_value=1234.5):
                self.assertTrue(worker.write_heartbeat({"campus": "test"}, "db", "id",
                                                       token="token", real=real))
                write.assert_called_once_with("db", "campus/test/agents/id",
                                              {"ts": 1234500, "real": real,
                                               "version": AGENT_VERSION,
                                               "versionTs": 1234500}, "token")

    def test_write_failure_remains_nonfatal(self):
        with patch.object(worker, "_patch", side_effect=RuntimeError("offline")):
            self.assertFalse(worker.write_heartbeat({"campus": "test"}, "db", "id"))


if __name__ == "__main__":
    unittest.main()

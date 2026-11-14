"""Agent A/C LLM-retry behaviour: A (retries=0) is the no-resilience baseline, C retries transient errors."""
import email.message
import importlib.util
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from mock_llm import server

spec = importlib.util.spec_from_file_location("agent_a_retry_under_test", Path(__file__).with_name("agent.py"))
agent = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = agent
spec.loader.exec_module(agent)


class RetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.mock = server.serve(0)
        server.load(None)  # default script: one text reply
        threading.Thread(target=self.mock.serve_forever, daemon=True).start()
        port = self.mock.server_address[1]
        self.env = patch.dict(os.environ, {
            "TASK_PROMPT": "do it", "WORKSPACE": self.tmp.name, "RUN_ID": "r1",
            "OPENAI_BASE_URL": f"http://127.0.0.1:{port}/runs/r1/v1",
            "OPENAI_API_KEY": "k", "ARENA_MODEL": "mock-model", "ARENA_TOOL_FAULT": "",
        })
        self.env.start()
        self.delays: list[float] = []
        self.sleep = patch.object(agent, "_sleep", self.delays.append)
        self.sleep.start()

    def tearDown(self) -> None:
        self.sleep.stop()
        self.env.stop()
        self.mock.shutdown()
        self.mock.server_close()
        self.tmp.cleanup()

    def fail(self, n: int, status: int) -> None:
        server.STATE["fail"] = {"n": n, "status": status}

    def test_no_retries_fails_on_first_503(self) -> None:
        self.fail(1, 503)
        self.assertEqual(agent.main(llm_retries=0), 1)
        self.assertEqual(self.delays, [])

    def test_retries_recover_after_two_transient_failures(self) -> None:
        self.fail(2, 503)
        self.assertEqual(agent.main(llm_retries=3), 0)
        self.assertEqual(self.delays, [1.0, 2.0])  # exponential backoff 1 s, 2 s

    def test_gives_up_after_retries_are_exhausted(self) -> None:
        self.fail(10, 429)
        self.assertEqual(agent.main(llm_retries=2), 1)
        self.assertEqual(len(self.delays), 2)

    def test_non_transient_errors_are_not_retried(self) -> None:
        self.fail(1, 400)
        self.assertEqual(agent.main(llm_retries=3), 1)
        self.assertEqual(self.delays, [])

    def test_retry_after_header_is_honoured_and_capped(self) -> None:
        def err(value):
            headers = email.message.Message()
            if value is not None:
                headers["Retry-After"] = value
            return HTTPError("http://x", 429, "rate", headers, None)

        self.assertEqual(agent._retry_delay(err("3"), 0), 3.0)
        self.assertEqual(agent._retry_delay(err("999"), 0), agent.MAX_RETRY_DELAY_SECONDS)
        self.assertEqual(agent._retry_delay(err("junk"), 2), 4.0)
        self.assertEqual(agent._retry_delay(err(None), 1), 2.0)

    def test_temperature_defaults_to_zero_and_can_be_omitted(self) -> None:
        sent = []
        original = agent.urlopen

        def spy(request, timeout=None):
            sent.append(request.data)
            return original(request, timeout=timeout)

        with patch.object(agent, "urlopen", spy):
            self.assertEqual(agent.main(), 0)
            with patch.dict(os.environ, {"ARENA_TEMPERATURE": ""}):
                self.assertEqual(agent.main(), 0)
        self.assertIn(b'"temperature": 0.0', sent[0])
        self.assertNotIn(b"temperature", sent[1])


if __name__ == "__main__":
    unittest.main()

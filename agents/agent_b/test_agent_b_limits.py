"""Agent B must exit with a clean error (code 1), not a traceback, when the SDK's turn limit is hit."""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from mock_llm import server

spec = importlib.util.spec_from_file_location("agent_b_limits_under_test", Path(__file__).with_name("agent.py"))
agent = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = agent
spec.loader.exec_module(agent)


class TurnLimitTests(unittest.TestCase):
    def test_turn_limit_is_reported_as_a_clean_agent_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mock = server.serve(0)
            server.load(None)
            # The model never stops asking for a tool: Agent B must give up at MAX_TURNS.
            server.STATE["script"] = {"responses": [{"tool_calls": [{"name": "list_files", "arguments": "{}"}]}]}
            threading.Thread(target=mock.serve_forever, daemon=True).start()
            env = {
                "TASK_PROMPT": "loop forever", "WORKSPACE": tmp, "RUN_ID": "r1",
                "OPENAI_BASE_URL": f"http://127.0.0.1:{mock.server_address[1]}/runs/r1/v1",
                "OPENAI_API_KEY": "k", "ARENA_MODEL": "mock-model", "ARENA_TOOL_FAULT": "",
            }
            stderr = io.StringIO()
            try:
                with patch.dict(os.environ, env), contextlib.redirect_stderr(stderr):
                    code = agent.main()
            finally:
                mock.shutdown()
                mock.server_close()
        self.assertEqual(code, 1)
        self.assertIn("Agent B error", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

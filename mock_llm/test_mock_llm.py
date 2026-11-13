import gc
import json
import os
import tempfile
import threading
import urllib.error
import urllib.request
import unittest
import warnings

import server


class MockLLMTests(unittest.TestCase):
    def test_load_closes_script_file(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as script_file:
            json.dump({"responses": [{"text": "test"}]}, script_file)
            script_path = script_file.name

        original_state = dict(server.STATE)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                server.load(script_path)
                gc.collect()

            self.assertFalse(any(
                issubclass(warning.category, ResourceWarning)
                for warning in caught
            ))
        finally:
            server.STATE.clear()
            server.STATE.update(original_state)
            os.unlink(script_path)


def post(port, path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", json.dumps(body).encode(),
                               {"Content-Type": "application/json"})
    return urllib.request.urlopen(r)


def main():
    srv = server.serve(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    m = {"model": "x", "messages": [{"role": "user", "content": "hi"}]}
    for path in ("/v1/chat/completions", "/runs/abc/v1/chat/completions"):
        d = json.load(post(port, path, m))
        assert d["usage"]["total_tokens"] > 0 and d["choices"][0]["message"]["content"]
    s = post(port, "/v1/chat/completions", dict(m, stream=True, stream_options={"include_usage": True})).read().decode()
    assert '"usage"' in s and s.rstrip().endswith("[DONE]")
    assert '"usage"' not in post(port, "/v1/chat/completions", dict(m, stream=True)).read().decode()
    post(port, "/_admin/fail", {"n": 1, "status": 429})
    try:
        post(port, "/v1/chat/completions", m)
        raise SystemExit("expected 429")
    except urllib.error.HTTPError as e:
        assert e.code == 429
    assert post(port, "/v1/chat/completions", m).status == 200
    print("mock_llm OK")


if __name__ == "__main__":
    main()

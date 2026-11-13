"""mock_llm (A3): scripted OpenAI-compatible server, stdlib only. See docs/10 section 2.6.
Serves POST /v1/chat/completions and /runs/<id>/v1/chat/completions, GET /health.
Script (MOCK_SCRIPT=path.json):
  {"responses": [{"text": "..."} | {"tool_calls": [{"name": "x", "arguments": "{}"}]}],
   "fail_next": {"n": 0, "status": 503}}
Responses cycle in order. Every reply includes `usage`. Admin: POST /_admin/fail {"n": 2, "status": 503}.
"""
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT = {"responses": [{"text": "mock reply"}], "fail_next": {"n": 0, "status": 503}}
LOCK = threading.Lock()
STATE = {"i": 0, "script": DEFAULT, "fail": dict(DEFAULT["fail_next"])}
PATH = re.compile(r"^(/runs/[^/]+)?/v1/chat/completions$")


def load(path=None):
    path = path or os.environ.get("MOCK_SCRIPT")
    if path:
        with open(path, encoding="utf-8") as script_file:
            s = json.load(script_file)
    else:
        s = DEFAULT
    STATE.update(i=0, script=s, fail=dict(s.get("fail_next") or {"n": 0, "status": 503}))


def tokens(x):
    return max(1, len(json.dumps(x)) // 4)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/_admin/fail":
            with LOCK:
                STATE["fail"] = {"n": body.get("n", 0), "status": body.get("status", 503)}
            return self._send(200, {"ok": True})
        if not PATH.match(self.path):
            return self._send(404, {"error": {"message": "not found", "type": "invalid_request_error"}})
        with LOCK:
            if STATE["fail"]["n"] > 0:
                STATE["fail"]["n"] -= 1
                return self._send(STATE["fail"]["status"], {"error": {"message": "mock failure", "type": "server_error"}})
            response_index = STATE["i"]
            r = STATE["script"]["responses"][response_index % len(STATE["script"]["responses"])]
            STATE["i"] += 1
        msg = {"role": "assistant", "content": r.get("text")}
        finish = "stop"
        if "tool_calls" in r:
            msg["content"] = None
            finish = "tool_calls"
            msg["tool_calls"] = [
                {"id": f"call_{response_index}_{k}", "type": "function",
                 "function": {"name": c["name"], "arguments": c.get("arguments", "{}")}}
                for k, c in enumerate(r["tool_calls"])
            ]
        usage = {"prompt_tokens": tokens(body.get("messages", [])), "completion_tokens": tokens(msg)}
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        model = body.get("model", "mock-model")
        if not body.get("stream"):
            return self._send(200, {"id": "mock-1", "object": "chat.completion", "model": model,
                                    "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                                    "usage": usage})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        def chunk(delta, fin=None, u=None):
            c = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                 "choices": [] if u else [{"index": 0, "delta": delta, "finish_reason": fin}]}
            if u:
                c["usage"] = u
            self.wfile.write(b"data: " + json.dumps(c).encode() + b"\n\n")

        chunk({k: v for k, v in msg.items() if v is not None})
        chunk({}, finish)
        if (body.get("stream_options") or {}).get("include_usage"):
            chunk({}, None, usage)
        self.wfile.write(b"data: [DONE]\n\n")


def serve(port=None):
    load()
    return ThreadingHTTPServer(("0.0.0.0", int(port if port is not None else os.environ.get("MOCK_PORT", 9000))), H)


if __name__ == "__main__":
    serve().serve_forever()

"""A1 smoke test (OQ-06 V-01..V-03). Needs Bifrost running with a provider key configured.
Usage: BIFROST_MODEL=openai/gpt-4o-mini python scripts/smoke_bifrost.py [base_url]
Prints what to record in docs/04 section 6. Costs a few tokens."""
import json
import os
import sys
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
model = os.environ["BIFROST_MODEL"]


def call(extra, headers=None):
    body = {"model": model, "messages": [{"role": "user", "content": "Say ok."}], "max_tokens": 5, **extra}
    r = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(),
                               {"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return resp.status, dict(resp.headers), resp.read().decode()


st, h, b = call({})
print("V-01 non-stream:", st, "usage:", json.loads(b).get("usage"))
print("   x-bifrost headers:", {k: v for k, v in h.items() if k.lower().startswith("x-bifrost")})
st, h, b = call({"stream": True, "stream_options": {"include_usage": True}})
print("V-02 stream carries usage chunk:", '"prompt_tokens"' in b)
st, h, b = call({}, {"x-bf-lh-run_id": "smoke-test-1"})
print("V-03 tagged call:", st, "- now look for run_id=smoke-test-1 in Bifrost logs")

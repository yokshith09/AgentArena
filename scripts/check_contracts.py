"""Stage 1 check (offline): example objects validate against contracts/*.schema.json, and bad ones are rejected."""
import json, pathlib
from jsonschema import Draft202012Validator
root = pathlib.Path(__file__).resolve().parent.parent / "contracts"
for n in ("run", "event", "task", "agent"):
    v = Draft202012Validator(json.loads((root / f"{n}.schema.json").read_text()))
    ex = json.loads((root / "examples" / f"{n}.json").read_text())
    v.validate(ex)
    bad = dict(ex); bad.pop(next(iter(v.schema["required"])))
    assert not v.is_valid(bad), f"{n}: missing required field accepted"
bad_enum = json.loads((root / "examples/event.json").read_text()); bad_enum["type"] = "nope"
assert not Draft202012Validator(json.loads((root / "event.schema.json").read_text())).is_valid(bad_enum)
print("contracts OK")

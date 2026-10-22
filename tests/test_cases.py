import json, pathlib, subprocess, sys
from agent.investigator import investigate

ROOT = pathlib.Path(__file__).resolve().parent.parent

def setup_module(module):
    if not (ROOT / "data/out/cases.json").exists():
        subprocess.check_call([sys.executable, str(ROOT / "data/gen_synthetic.py")])

def test_five_seeded_cases_resolve_to_the_right_link():
    for c in json.loads((ROOT / "data/out/cases.json").read_text()):
        r = investigate(f"I paid but nothing arrived. order {c['order_id']}")
        assert r["ok"], c
        assert r["broken"] == c["broken_link"], (c["case"], r["headline"])
        red = [l for l in r["chain"] if l["state"] == "red"]
        assert all(l["refs"] for l in red), "every red link must cite rows"
        assert "[" in r["explanation"] or r["llm"] == "none"

def test_healthy_order_is_green_end_to_end():
    r = investigate("where are my credits? order ord_0001")
    assert r["broken"] is None and all(l["state"] == "green" for l in r["chain"])

def test_unknown_customer():
    r = investigate("hello, nobody@example.com")
    assert r["ok"] is False

import json, pathlib, subprocess, sys
from agent.investigator import investigate

ROOT = pathlib.Path(__file__).resolve().parent.parent

def setup_module(module):
    if not (ROOT / "data/out/cases.json").exists():
        subprocess.check_call([sys.executable, str(ROOT / "data/gen_synthetic.py")])

def test_seeded_cases_resolve_to_the_right_link():
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

def test_case6_found_from_the_payer_address_alone():
    # the customer writes from the address they paid with; no order exists under it
    r = investigate("Hi, I paid 24,900 won but nothing arrived. liam.patel906@example.com")
    assert r["ok"] and r["order_id"] == "ord_0906" and r["broken"] == "account_mismatch"

def test_malformed_ids_never_reach_sql():
    assert investigate("hi", email="x') OR 1=1 OR lower('")["ok"] is False
    assert investigate("hi", order_id="' UNION SELECT 1 --")["ok"] is False

def test_nothing_sent_to_the_model_contains_a_full_address():
    from agent.investigator import _mask
    s = _mask('{"a": "liam.patel906@example.com", "b": "liam.patel906@exmaple.com"}', "liam.patel906@example.com")
    assert "CUSTOMER" in s and "l***@exmaple.com" in s and "patel906" not in s

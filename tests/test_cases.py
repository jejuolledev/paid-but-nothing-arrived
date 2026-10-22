import json, pathlib, re, subprocess, sys
import pytest
from agent.investigator import investigate
from agent.sql_backend import DuckDBBackend
from agent.actions import READONLY_MSG, NothingToFix, ReadOnlyBackend, approve

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

def test_approve_ord_0901_clears_broken():
    db = DuckDBBackend()
    out = approve("ord_0901", backend=db)
    assert out["after"]["broken"] is None
    assert all(l["state"] == "green" for l in out["after"]["chain"])
    assert "Everything went through" in out["after"]["headline"]
    assert out["audit"]["action_id"] and out["audit"]["kind"] == "order_created"

def test_approve_twice_is_idempotent():
    db = DuckDBBackend()
    approve("ord_0901", backend=db)
    with pytest.raises(NothingToFix, match="Nothing to fix"):
        approve("ord_0901", backend=db)
    from fastapi.testclient import TestClient
    from app.main import app
    from agent import sql_backend
    sql_backend._CACHE["backend"] = db
    try:
        res = TestClient(app).post("/api/approve", json={"order_id": "ord_0901"})
        assert res.status_code == 400 and res.text == "Nothing to fix"
    finally:
        sql_backend._CACHE.pop("backend", None)

def test_approve_readonly_backend_returns_409_message():
    class ReadOnly:
        name = "zetaris-jdbc"
        def query(self, sql):
            return []
    with pytest.raises(ReadOnlyBackend) as ei:
        approve("ord_0901", backend=ReadOnly())
    assert str(ei.value) == READONLY_MSG
    from fastapi.testclient import TestClient
    from app.main import app
    from agent import sql_backend
    sql_backend._CACHE["backend"] = ReadOnly()
    try:
        res = TestClient(app).post("/api/approve", json={"order_id": "ord_0901", "approved_by": "seller"})
        assert res.status_code == 409
        assert res.text == READONLY_MSG
    finally:
        sql_backend._CACHE.pop("backend", None)

def test_korean_message_gets_korean_template_reply(monkeypatch):
    # no LLM: template path must still reply in Korean when the message has Hangul
    monkeypatch.setattr("agent.investigator._client", lambda: (None, None))
    r = investigate("결제했는데 확인 메일이 안 왔어요. 주문번호 ord_0904")
    assert r["ok"] and r["broken"] == "mail_delivered"
    assert r.get("lang") == "ko"
    assert r["llm"] == "none"
    assert re.search(r"[가-힣]", r["customer_reply"])
    assert re.search(r"이용권|메일|안내", r["customer_reply"])

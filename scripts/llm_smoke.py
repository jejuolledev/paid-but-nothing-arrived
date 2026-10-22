"""Smoke-test the model step against any OpenAI-compatible endpoint and record the numbers.

Usage:
  LLM_BASE_URL=http://127.0.0.1:8088/v1 LLM_API_KEY=rt-local LLM_MODEL=meterless/local \
  .venv/bin/python scripts/llm_smoke.py

Prints, per seeded case: verdict correctness (verifier), whether the model answered, whether
its citations passed, latency. Appends a line to docs/measurements.md so claims in the
submission ("in minutes", citation pass rate) are backed by a number we actually measured.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env.local")
from agent.investigator import investigate  # noqa: E402

cases = json.loads((ROOT / "data/out/cases.json").read_text())
rows, t0 = [], time.time()
for c in cases:
    # case 6 is the one outside the verifier's playbook: the customer only gives the address they paid with
    msg = (f"Hi, I paid but nothing arrived. {c['email']}" if c["case"] == 6 else f"Hi, I paid but nothing arrived. My order is {c['order_id']}.")
    r = investigate(msg)
    rows.append(dict(case=c["case"], verdict_ok=r.get("broken") == c["broken_link"] and r.get("order_id") == c["order_id"], llm=r.get("llm"), agent_steps=len(r.get("steps", [])),
                     citations=r["citation_check"], ms=r["elapsed_ms"], reply_len=len(r["customer_reply"])))
    print("   explanation:", r["explanation"][:300].replace("\n", " "))
    print("   reply:", r["customer_reply"][:200].replace("\n", " "))
    print(json.dumps(rows[-1], ensure_ascii=False))
ok = sum(x["verdict_ok"] for x in rows); cit = sum(1 for x in rows if x["citations"].get("ok"))
line = f"| {time.strftime('%Y-%m-%d %H:%M')} | {rows[0]['llm']} | verdict {ok}/{len(rows)} | citations passed {cit}/{len(rows)} | avg {sum(x['ms'] for x in rows)//len(rows)} ms |"
md = ROOT / "docs/measurements.md"
if not md.exists():
    md.write_text("# Measurements\n\n| when | model | verdicts | citation check | latency |\n|---|---|---|---|---|\n")
md.write_text(md.read_text() + line + "\n")
print(line)

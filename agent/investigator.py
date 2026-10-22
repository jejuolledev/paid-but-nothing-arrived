"""Investigation loop: locate -> journey -> verify chain -> explain (LLM) -> citation check.

LLM: any OpenAI-compatible endpoint. Primary target is a local NVIDIA Nemotron served by
Meterless Nightshift (customer data never leaves the seller's machine). Fallback: an
OpenRouter Nemotron endpoint. If no endpoint is configured the agent still works: the
deterministic verifier produces the verdict and a template writes the texts, and the
result is marked `llm: none` so nobody mistakes a template for a model.
"""
from __future__ import annotations
import json, os, re, time
from dataclasses import dataclass, asdict
from .chain import verify, LABELS
from .tools import Tools, OPENAI_TOOLS

SYSTEM = (
    "You are a payments investigator for a small online seller. You may only state facts that "
    "are supported by rows the tools returned, and you must cite them with the exact `ref` value in square "
    "brackets, e.g. [orders:ord_0901] or [server_logs:2026-10-13T12:00:44Z@/api/payments/confirm]. Never invent a row. "
    "Output JSON with keys: explanation (<=120 words, cite at least one ref), "
    "customer_reply (plain, kind, <=90 words, no internal refs), fix_action (one imperative sentence)."
)


@dataclass
class Trace:
    step: str
    detail: str
    ms: int


def _client():
    base = os.getenv("NIGHTSHIFT_BASE_URL") or os.getenv("LLM_BASE_URL")
    key = os.getenv("NIGHTSHIFT_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not base and os.getenv("OPENROUTER_API_KEY"):
        base = "https://openrouter.ai/api/v1"
    if not base:
        return None, None
    from openai import OpenAI
    return OpenAI(base_url=base, api_key=key or "local"), os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning:free")


REF_RE = re.compile(r"(?:payments|orders|grants|server_logs|mail_events):[A-Za-z0-9_./@:+-]+")


def _citations_ok(text: str, refs: set[str]) -> tuple[bool, list[str]]:
    """Accepts [orders:ord_0901], [ref: orders:ord_0901] or a bare orders:ord_0901 — but every cited
    ref must be one the tools actually returned, and there must be at least one."""
    cited = [c.rstrip(".,;)") for c in REF_RE.findall(text)]
    bad = [c for c in cited if c not in refs]
    return (len(cited) > 0 and not bad), bad


def investigate(message: str, email: str = "", order_id: str = "", backend=None) -> dict:
    from .sql_backend import get_backend
    db = backend or get_backend()
    tools, trace, t0 = Tools(db), [], time.time()

    def mark(step, detail):
        trace.append(Trace(step, detail, int((time.time() - t0) * 1000)))

    # 1. locate the order (email or order id; fall back to an id mentioned in the message)
    if not order_id and not email:
        m = re.search(r"ord_\d{4}", message); order_id = m.group(0) if m else ""
        m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", message); email = m.group(0) if m else email
    orders = tools.find_orders(email=email, order_id=order_id)
    mark("find_orders", f"{len(orders)} order(s) for {order_id or email}")
    if not orders:
        return {"ok": False, "headline": "No order found for this customer.", "trace": [asdict(t) for t in trace], "backend": db.name}
    # if several orders, investigate the most recent one that is not plainly healthy first
    target = next((o for o in orders if not (o["status"] == "paid" and o["credited"] == "1")), orders[0])

    # 2. journey + 3. deterministic verification (the part that is never delegated to a model)
    journey = tools.order_journey(target["order_id"]); mark("order_journey", f"{sum(len(v) for v in journey.values())} rows from 5 sources")
    verdict = verify(journey); mark("verify_chain", f"broken={verdict.broken}")
    refs = {r["ref"] for rows in journey.values() for r in rows}

    # 4. explanation + reply + fix (LLM, citation-checked)
    client, model = _client()
    texts, llm_used, citation = None, "none", {"checked": False}
    if client:
        try:
            resp = client.chat.completions.create(model=model, temperature=0.2, response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps({"customer_message": message, "chain": verdict.to_dict(), "rows": journey}, default=str)}])
            texts = json.loads(resp.choices[0].message.content); llm_used = model
            texts["_raw_explanation"] = texts.get("explanation", "")
            ok, bad = _citations_ok(texts.get("explanation", ""), refs); citation = {"checked": True, "ok": ok, "unknown_refs": bad}
            if not ok:
                texts["explanation"] = verdict.root_cause + " " + " ".join(f"[{r}]" for l in verdict.links if l.state == "red" for r in l.refs)
                citation["replaced_with_verifier_text"] = True
            mark("llm_explain", f"{model} citations_ok={ok}")
        except Exception as e:  # keep the demo honest: show that the model step failed
            mark("llm_explain", f"failed: {type(e).__name__}: {e}"[:200])
    if texts is None:
        texts = {"explanation": verdict.root_cause + " " + " ".join(f"[{r}]" for l in verdict.links if l.state == "red" for r in l.refs),
                 "customer_reply": _template_reply(verdict), "fix_action": verdict.suggested_fix}
        mark("template_texts", "no LLM endpoint configured — verifier text used")

    return {"ok": True, "order_id": target["order_id"], "email": target["email"], "headline": verdict.headline,
            "chain": [{"name": l.name, "label": LABELS[l.name], "state": l.state, "note": l.note, "refs": l.refs} for l in verdict.links],
            "broken": verdict.broken, "verified": verdict.verified, "unverified": verdict.unverified,
            "explanation": texts["explanation"], "customer_reply": texts["customer_reply"], "fix_action": texts["fix_action"],
            "rows": journey, "trace": [asdict(t) for t in trace], "llm": llm_used, "citation_check": citation, "backend": db.name,
            "elapsed_ms": int((time.time() - t0) * 1000)}


def _template_reply(v) -> str:
    if v.broken is None and "never charged" in v.headline.lower():
        return "Thank you for writing. I checked our payment provider: no charge was made on your card for this order, so nothing is missing and nothing will be billed. Here is a fresh checkout link whenever you are ready."
    if v.broken == "order_created":
        return "Thank you for your patience. I can confirm your payment went through on our provider's side. Our system did not complete your order after that — that is our fault, not yours. I am releasing your credits now and you will receive a confirmation email shortly."
    if v.broken == "credit_granted":
        return "Thank you for writing. Your payment and order are fine. I found that the credits were issued twice by mistake; I will keep your purchased credits in place and correct the duplicate on our side. Nothing further is needed from you."
    if v.broken == "mail_delivered":
        return "Thank you for your patience. Your credits are already in your account — our confirmation email failed to send, so you were never told. Please log in and check your balance; I am resending the confirmation now."
    return "Thank you for writing. I checked every step of your order and everything went through; your credits are in your account."

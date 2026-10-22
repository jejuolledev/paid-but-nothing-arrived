"""The investigation loop: the model decides which records to pull next.

Nemotron (served locally by Meterless Nightshift) gets the customer's message and a small set of
read-only tools over the Zetaris layer. Each turn it answers with one JSON action — call a tool, or
stop and name the order it believes the complaint is about. It never writes anything and never
decides the verdict: once it names an order, the deterministic verifier walks the money chain and
the result is checked against the rows the model actually saw.

Customer identity is aliased before anything reaches the model: the address the customer wrote from
becomes `CUSTOMER`, any other address keeps only its first letter and its domain (so a typo such as
`exmaple.com` stays visible), and card digits are dropped.
"""
from __future__ import annotations
import json, re, time

MAX_STEPS = 6
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")

TOOLS_DOC = """Tools (all read-only, all go through one SQL layer):
- find_orders {"email": "CUSTOMER"} or {"order_id": "ord_0000"}: our order rows
- find_payments {"email": "CUSTOMER"}: the payment provider's ledger rows paid by that address
- order_for_payment {"payment_id": "pay_0000"}: the order a payment belongs to
- order_journey {"order_id": "ord_0000"}: every payment, grant, server-log and mail row for one order
- related_orders {"email": "CUSTOMER"}: other orders by the same address"""

SYSTEM = (
    "You investigate why a customer of a small online shop says they paid but nothing arrived. "
    "Use the tools to find which order the complaint is about and what happened to it. Think in short steps. "
    "Reply with ONE JSON object per turn and nothing else:\n"
    '{"thought": "<one sentence>", "tool": "<name>", "args": {...}}  to look something up, or\n'
    '{"thought": "<one sentence>", "done": true, "order_id": "ord_0000", "finding": "<what happened, citing refs like [payments:pay_0000]>"}\n'
    "Rules: use only refs that appeared in tool results; if the customer has no order under their address, "
    "remember the payment provider knows who paid; never guess an order id you have not seen.\n" + TOOLS_DOC
)


class Aliaser:
    def __init__(self, customer_email: str):
        self.customer = (customer_email or "").lower()

    def email(self, e: str) -> str:
        e = (e or "").lower()
        if not e:
            return e
        if self.customer and e == self.customer:
            return "CUSTOMER"
        local, _, domain = e.partition("@")
        return f"{local[:1]}***@{domain}"

    def rows(self, rows: list[dict]) -> list[dict]:
        out = []
        for r in rows:
            r2 = {}
            for k, v in r.items():
                if k == "card_last4":
                    continue
                if isinstance(v, str) and EMAIL_RE.fullmatch(v):
                    v = self.email(v)
                r2[k] = v
            out.append(r2)
        return out

    def arg(self, v: str) -> str:
        return self.customer if v == "CUSTOMER" else v


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def investigate_loop(client, model: str, message: str, customer_email: str, tools) -> dict:
    """Returns {order_id, finding, steps, seen_refs, ok}. `steps` is what the screen and the video show."""
    al = Aliaser(customer_email)
    calls = {
        "find_orders": lambda a: tools.find_orders(email=al.arg(a.get("email", "")), order_id=a.get("order_id", "")),
        "find_payments": lambda a: tools.find_payments(al.arg(a.get("email", ""))),
        "order_for_payment": lambda a: tools.order_for_payment(a.get("payment_id", "")),
        "order_journey": lambda a: tools.order_journey(a.get("order_id", "")),
        "related_orders": lambda a: tools.related_orders(al.arg(a.get("email", ""))),
    }
    safe_msg = EMAIL_RE.sub(lambda m: al.email(m.group(0)), message[:2000])
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Customer message: {safe_msg}\nThe customer wrote from: CUSTOMER"}]
    steps, seen, seen_orders = [], set(), set()
    for _ in range(MAX_STEPS):
        t0 = time.time()
        resp = client.chat.completions.create(model=model, temperature=0.1, messages=msgs)
        text = resp.choices[0].message.content or ""
        act = _parse(text)
        if not act:
            steps.append({"thought": "(unreadable reply)", "ms": int((time.time() - t0) * 1000)})
            msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": "Reply with one JSON object only."}]
            continue
        if act.get("done"):
            oid = act.get("order_id", "")
            ok = oid in seen_orders
            steps.append({"thought": act.get("thought", ""), "done": True, "order_id": oid, "ms": int((time.time() - t0) * 1000)})
            return {"ok": ok, "order_id": oid if ok else "", "finding": act.get("finding", ""), "steps": steps, "seen_refs": sorted(seen)}
        name, args = act.get("tool", ""), act.get("args", {}) or {}
        try:
            result = calls[name](args)
            rows = [r for v in result.values() for r in v] if isinstance(result, dict) else result
            seen.update(r["ref"] for r in rows)
            seen_orders.update(r["order_id"] for r in rows if r.get("order_id"))
            shown = {k: al.rows(v) for k, v in result.items()} if isinstance(result, dict) else al.rows(result)
            obs = json.dumps(shown, default=str)[:6000]
            steps.append({"thought": act.get("thought", ""), "tool": name, "args": args, "rows": len(rows), "ms": int((time.time() - t0) * 1000)})
        except (KeyError, ValueError) as e:
            obs = f"error: {type(e).__name__} — check the tool name and arguments"
            steps.append({"thought": act.get("thought", ""), "tool": name, "args": args, "error": True, "ms": int((time.time() - t0) * 1000)})
        msgs += [{"role": "assistant", "content": json.dumps(act)}, {"role": "user", "content": f"Result of {name}: {obs}"}]
    return {"ok": False, "order_id": "", "finding": "", "steps": steps, "seen_refs": sorted(seen)}

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
    "customer_reply (written BY the seller TO the customer, <=90 words, plain and kind; state what happened and what you will do; "
    "if nothing was charged say so clearly; never ask the customer to investigate; no internal refs), "
    "fix_action (one imperative sentence for the seller)."
)


@dataclass
class Trace:
    step: str
    detail: str
    ms: int


def _nightshift_key() -> str:
    """Nightshift mints its Runtime API key into a file on this Mac; read it rather than copying it around."""
    path = os.path.expanduser(os.getenv("NIGHTSHIFT_TOKEN_FILE", "~/Library/Application Support/ai.meterless.nightshift.m1m4/runtime-token"))
    try:
        return open(path).read().strip()
    except OSError:
        return ""


def _client():
    base = os.getenv("NIGHTSHIFT_BASE_URL") or os.getenv("LLM_BASE_URL")
    key = os.getenv("NIGHTSHIFT_API_KEY") or (os.getenv("NIGHTSHIFT_BASE_URL") and _nightshift_key()) or os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    if not base and os.getenv("OPENROUTER_API_KEY"):
        base = "https://openrouter.ai/api/v1"
    if not base:
        return None, None
    # Customer rows stay on this machine unless the operator explicitly opts in to a remote model.
    if not re.match(r"https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(/|$)", base) and os.getenv("ALLOW_CLOUD_LLM") != "1":
        return None, None
    from openai import OpenAI
    # Nightshift keeps a policy per calling app; this name is the row the operator sees and binds.
    headers = {"meterless-app": "paid-but-nothing-arrived"} if os.getenv("NIGHTSHIFT_BASE_URL") else None
    return OpenAI(base_url=base, api_key=key or "local", default_headers=headers, timeout=180), os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning:free")


REF_RE = re.compile(r"(?:payments|orders|grants|server_logs|mail_events):[A-Za-z0-9_./@:+-]+")


PII_FIELDS = {"email", "customer_email", "to_address", "card_last4"}


def _redact(journey: dict, customer_email: str = "") -> dict:
    """What the model sees: same rows and refs; the customer's address becomes CUSTOMER, other
    addresses keep only first letter + domain (a typo stays visible), card digits are dropped."""
    from .agent_loop import Aliaser
    al = Aliaser(customer_email)
    return {t: al.rows(rows) for t, rows in journey.items()}


def _mask(text: str, customer_email: str) -> str:
    """Last pass over everything sent to the model: no full address survives, wherever it appears."""
    from .agent_loop import Aliaser, EMAIL_RE
    al = Aliaser(customer_email)
    return EMAIL_RE.sub(lambda m: al.email(m.group(0)), text)


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
    lang = "ko" if re.search(r"[가-힣]", message or "") else "en"

    def mark(step, detail):
        trace.append(Trace(step, detail, int((time.time() - t0) * 1000)))

    # 1. locate the order (email or order id; fall back to an id mentioned in the message)
    if order_id and not re.fullmatch(r"ord_\d{4}", order_id): order_id = ""
    if email and not re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", email): email = ""
    if not order_id and not email:
        m = re.search(r"ord_\d{4}", message); order_id = m.group(0) if m else ""
        m = re.search(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", message); email = m.group(0) if m else email
    if not order_id and not email:
        return {"ok": False, "headline": "Add the order number (ord_0000) or the customer's email to the message.", "trace": [], "backend": db.name}
    client, model = _client()
    steps, loop_finding = [], ""
    target = None
    # 1a. with a model: the model decides which records to pull (tools are read-only, ids are validated)
    if client and email and not order_id:
        try:
            from .agent_loop import investigate_loop
            res = investigate_loop(client, model, message, email, tools)
            steps, loop_finding = res["steps"], res["finding"]
            mark("agent_loop", f"{len(steps)} step(s), named {res['order_id'] or 'nothing'}")
            if res["ok"]:
                target = tools.find_orders(order_id=res["order_id"])[0]
        except Exception as e:
            mark("agent_loop", f"failed: {type(e).__name__}"[:120])
    # 1b. without a model (or if it found nothing): our own lookup, then the PSP ledger by payer address
    if target is None:
        orders = tools.find_orders(email=email, order_id=order_id)
        mark("find_orders", f"{len(orders)} order(s) for {order_id or email}")
        if not orders and email:
            pays = tools.find_payments(email)
            mark("find_payments", f"{len(pays)} PSP payment(s) by this address")
            for p in pays:
                orders += tools.order_for_payment(p["payment_id"])
            mark("order_for_payment", f"{len(orders)} order(s) behind those payments")
        if not orders:
            return {"ok": False, "headline": f"No order or payment found for {order_id or email}. Check the address the customer paid with, or ask for the order number.",
                    "trace": [asdict(t) for t in trace], "steps": steps, "backend": db.name}
        # if several orders, investigate the most recent one that is not plainly healthy first
        target = next((o for o in orders if not (o["status"] == "paid" and o["credited"] == "1")), orders[0])

    # 2. journey + 3. deterministic verification (the part that is never delegated to a model)
    journey = tools.order_journey(target["order_id"]); mark("order_journey", f"{sum(len(v) for v in journey.values())} rows from 5 sources")
    verdict = verify(journey); mark("verify_chain", f"broken={verdict.broken}")
    refs = {r["ref"] for rows in journey.values() for r in rows}

    # 4. explanation + reply + fix (LLM, citation-checked)
    texts, llm_used, citation = None, "none", {"checked": False}
    receipts = [st.get("receipt") for st in steps]
    if client:
        try:
            lang_note = " Reply language: Korean (polite 존댓말)." if lang == "ko" else ""
            user_payload = _mask(json.dumps({"customer_message": message[:2000], "chain": verdict.to_dict(),
                                             "rows": _redact(journey, email), "investigation": loop_finding}, default=str), email)
            resp = client.chat.completions.create(model=model, temperature=0.2, max_tokens=4000, reasoning_effort=os.getenv("LLM_REASONING", "none"),
                messages=[{"role": "system", "content": SYSTEM + lang_note},
                          {"role": "user", "content": user_payload}])
            from .agent_loop import _parse
            texts = _parse(resp.choices[0].message.content or "")
            if not texts:
                raise ValueError("model returned no JSON object")
            llm_used = getattr(resp, "model", None) or model
            from .agent_loop import meterless_receipt
            receipts.append(meterless_receipt(resp))
            texts["_raw_explanation"] = texts.get("explanation", "")
            ok, bad = _citations_ok(texts.get("explanation", ""), refs); citation = {"checked": True, "ok": ok, "unknown_refs": bad}
            texts["fix_action"] = verdict.suggested_fix  # the fix is decided by the verifier, never by the model
            if not _reply_ok(texts.get("customer_reply", ""), verdict):
                texts["customer_reply"] = _template_reply(verdict, lang); citation["reply_replaced"] = True
            if not ok:
                texts["explanation"] = verdict.root_cause + " " + " ".join(f"[{r}]" for l in verdict.links if l.state == "red" for r in l.refs)
                citation["replaced_with_verifier_text"] = True
            mark("llm_explain", f"{model} citations_ok={ok}")
        except Exception as e:  # keep the demo honest: show that the model step failed
            mark("llm_explain", f"failed: {type(e).__name__}: {e}"[:200])
    if texts is None:
        texts = {"explanation": verdict.root_cause + " " + " ".join(f"[{r}]" for l in verdict.links if l.state == "red" for r in l.refs),
                 "customer_reply": _template_reply(verdict, lang), "fix_action": verdict.suggested_fix}
        mark("template_texts", "no LLM endpoint configured — verifier text used")

    return {"ok": True, "order_id": target["order_id"], "email": target["email"], "headline": verdict.headline,
            "chain": [{"name": l.name, "label": LABELS[l.name], "state": l.state, "note": l.note, "refs": l.refs} for l in verdict.links],
            "broken": verdict.broken, "verified": verdict.verified, "unverified": verdict.unverified,
            "explanation": texts["explanation"], "customer_reply": texts["customer_reply"], "fix_action": texts["fix_action"],
            "rows": journey, "trace": [asdict(t) for t in trace], "steps": steps, "receipts": [r for r in receipts if r], "llm": llm_used, "citation_check": citation, "backend": db.name,
            "lang": lang, "elapsed_ms": int((time.time() - t0) * 1000)}


REPLY_MUST = {None: r"never charged|not charged|no charge|wasn't charged|was not charged|not been charged|in your account|went through|청구되지|이용권",
              "order_created": r"payment (went|came) through|was processed|confirm|releas|grant|결제|확인|이용권",
              "credit_granted": r"twice|duplicate|double|two|두 번|중복", "mail_delivered": r"mail|notice|notif|메일|안내",
              "account_mismatch": r"address|account|email|typo|주소"}


def _reply_ok(reply: str, v) -> bool:
    """The reply must be the seller speaking and must carry the verdict; otherwise the template is safer."""
    if not reply or re.search(r"\b(let me check my account|you gave me|my order|my credits)\b", reply, re.I):
        return False
    if re.search(r"refund|compensat|discount|free|voucher|환불|보상|할인|무료", reply, re.I):
        return False  # the model may not promise money; a person decides that
    key = v.broken if v.broken in REPLY_MUST else None
    if key is None and "never charged" not in v.headline.lower() and v.broken is None:
        return bool(re.search(r"in your account|went through|everything|이용권|계정", reply, re.I))
    return bool(re.search(REPLY_MUST[key], reply, re.I))


def _template_reply(v, lang: str = "en") -> str:
    if lang == "ko":
        return _template_reply_ko(v)
    if v.broken is None and "never charged" in v.headline.lower():
        return "Thank you for writing. I checked our payment provider: no charge was made on your card for this order, so nothing is missing and nothing will be billed. Here is a fresh checkout link whenever you are ready."
    if v.broken == "order_created":
        return "Thank you for your patience. I can confirm your payment went through on our provider's side. Our system did not complete your order after that — that is our fault, not yours. I am releasing your credits now and you will receive a confirmation email shortly."
    if v.broken == "credit_granted":
        return "Thank you for writing. Your payment and order are fine. I found that the credits were issued twice by mistake; I will keep your purchased credits in place and correct the duplicate on our side. Nothing further is needed from you."
    if v.broken == "account_mismatch":
        return "Thank you for writing, and sorry for the worry. Your payment went through. The order was saved under a slightly different email address than the one you paid with, so the credits and the confirmation went there. Could you confirm this is your address? As soon as you do, I will move the credits to your account."
    if v.broken == "mail_delivered":
        return "Thank you for your patience. Your credits are already in your account — our confirmation email failed to send, so you were never told. Please log in and check your balance; I am resending the confirmation now."
    return "Thank you for writing. I checked every step of your order and everything went through; your credits are in your account."


def _template_reply_ko(v) -> str:
    """Same facts as the English templates; polite 존댓말; no internal refs."""
    if v.broken is None and "never charged" in v.headline.lower():
        return "문의해 주셔서 감사합니다. 결제 대행사를 확인한 결과 이번 주문에 대해 카드에 청구된 내역이 없습니다. 빠진 이용권도 없고 추가 청구도 되지 않습니다. 준비되시면 새 결제 링크로 다시 진행해 주세요."
    if v.broken == "order_created":
        return "기다려 주셔서 감사합니다. 결제 대행사 기준으로는 결제가 정상 완료된 것을 확인했습니다. 이후 주문을 마무리하지 못한 것은 저희 쪽 문제입니다. 지금 이용권을 지급하고 있으며, 곧 확인 메일을 보내 드리겠습니다."
    if v.broken == "credit_granted":
        return "문의해 주셔서 감사합니다. 결제와 주문은 정상입니다. 이용권이 실수로 두 번 지급된 것을 확인했고, 구매하신 이용권은 그대로 두고 중복분만 정리하겠습니다. 고객님께서 추가로 하실 일은 없습니다."
    if v.broken == "account_mismatch":
        return "문의해 주셔서 감사하고, 걱정 끼쳐 드려 죄송합니다. 결제는 정상입니다. 주문은 결제하신 주소와 조금 다른 이메일로 저장되어 이용권과 안내 메일이 그쪽으로 갔습니다. 이 주소가 맞으신지 확인해 주시면, 바로 고객님 계정으로 이용권을 옮겨 드리겠습니다."
    if v.broken == "mail_delivered":
        return "기다려 주셔서 감사합니다. 이용권은 이미 계정에 지급되어 있습니다. 확인 메일 발송에 실패해 안내를 드리지 못했습니다. 로그인하셔서 잔액을 확인해 주세요. 확인 메일을 다시 보내 드리겠습니다."
    return "문의해 주셔서 감사합니다. 주문 전 단계를 확인했고 모두 정상입니다. 이용권은 계정에 있습니다."

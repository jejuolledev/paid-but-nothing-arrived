"""The three SQL tools the agent is allowed to call. Every row returned carries a
`ref` (source table + primary key) so any conclusion can cite the exact row."""
from __future__ import annotations
import re
from typing import Any

PK = {"payments": "payment_id", "orders": "order_id", "grants": "grant_id", "server_logs": "ts", "mail_events": "email_id"}


def _tag(table: str, rows: list[dict]) -> list[dict]:
    for r in rows:
        key = PK[table]
        r["ref"] = f"{table}:{r.get(key)}" if table != "server_logs" else f"server_logs:{r.get('ts')}@{r.get('route')}"
    return rows


_SAFE = {
    "order_id": re.compile(r"ord_\d{4}"),
    "email": re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"),
    "payment_id": re.compile(r"pay_[\w-]{1,40}"),
    "reward_key": re.compile(r"[\w-]{1,40}"),
}


def lit(kind: str, value: str) -> str:
    """Only well-formed ids reach SQL; anything else is refused, never escaped-and-hoped."""
    if not _SAFE[kind].fullmatch(str(value or "")):
        raise ValueError(f"rejected {kind}")
    return "'" + str(value) + "'"


class Tools:
    def __init__(self, backend):
        self.db = backend

    def find_orders(self, email: str = "", order_id: str = "") -> list[dict[str, Any]]:
        """Orders for a customer email or an order id (most recent first)."""
        where = f"order_id = {lit('order_id', order_id)}" if order_id else f"lower(email) = lower({lit('email', email)})"
        return _tag("orders", self.db.query(f"SELECT * FROM orders WHERE {where} ORDER BY created_at DESC LIMIT 10"))

    def order_journey(self, order_id: str) -> dict[str, list[dict[str, Any]]]:
        """Every row from every source that mentions this order (and its payment / email)."""
        o = self.find_orders(order_id=order_id)
        if not o:
            return {"orders": [], "payments": [], "grants": [], "server_logs": [], "mail_events": []}
        email, pay_id = o[0]["email"], o[0]["payment_id"]
        oid, em = lit("order_id", order_id), lit("email", email)
        pay_where = f"payment_id = {lit('payment_id', pay_id)}" if pay_id else f"lower(customer_email) = lower({em})"
        return {
            "orders": o,
            "payments": _tag("payments", self.db.query(f"SELECT * FROM payments WHERE {pay_where} ORDER BY created_at")),
            "grants": _tag("grants", self.db.query(f"SELECT * FROM grants WHERE order_id = {oid} OR (lower(email) = lower({em}) AND reward_key = {lit('reward_key', o[0]['reward_key'])}) ORDER BY created_at")),
            "server_logs": _tag("server_logs", self.db.query(f"SELECT * FROM server_logs WHERE order_id = {oid} ORDER BY ts")),
            "mail_events": _tag("mail_events", self.db.query(f"SELECT * FROM mail_events WHERE order_tag = {oid} OR lower(to_address) = lower({em}) ORDER BY ts")),
        }

    def related_orders(self, email: str) -> list[dict[str, Any]]:
        """Other orders by the same email — catches duplicates and account-mismatch cases."""
        return _tag("orders", self.db.query(f"SELECT * FROM orders WHERE lower(email) = lower({lit('email', email)}) ORDER BY created_at DESC LIMIT 20"))


OPENAI_TOOLS = [
    {"type": "function", "function": {"name": "find_orders", "description": "Find orders by customer email or order id.",
        "parameters": {"type": "object", "properties": {"email": {"type": "string"}, "order_id": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "order_journey", "description": "Fetch every row from the payment ledger, orders, grants, server logs and mail events for one order.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "related_orders", "description": "List other orders by the same email.",
        "parameters": {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}}},
]

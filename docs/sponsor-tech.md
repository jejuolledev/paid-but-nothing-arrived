# Sponsor technologies — how each one is used

## How Zetaris was integrated
Zetaris is the only thing the agent queries. The four systems a seller would otherwise open by hand — the payment-provider ledger, the orders and credit-grants database, the server-log export and the mail-provider events — are stood in for by five synthetic tables (payments, orders, grants, server_logs, mail_events). They sit in one Postgres database registered as a Zetaris datasource (`demo_pg`, local Zetaris platform, Lightning JDBC), and each table is activated into one unified semantic layer, `order_journey` (`zetaris/register.sql`). In production each system would be its own datasource behind the same layer. The agent's tools send SQL only; nothing is copied out of the source systems, and every returned row carries `table:key` so any conclusion can cite it.

- Read-only by design. When the seller approves a fix, Zetaris is not written to: the fix belongs to the seller's own systems. In the offline demo (DuckDB over the same synthetic CSVs, same table names, same SQL) the fix is applied so the chain can be seen turning green; on Zetaris the approve endpoint answers "read-only" instead of pretending.

## How Meterless was integrated
Every model call goes to Meterless Nightshift's OpenAI-compatible Runtime on the seller's Mac (`http://127.0.0.1:8088/v1`, key read from Nightshift's own token file). The app identifies itself (`meterless-app: paid-but-nothing-arrived`), so the seller can see and bind its routing in Nightshift's Apps panel. Nightshift seats an **NVIDIA Nemotron 3.5 Lightning** lane on the seller's NVIDIA key (in the demo, NVIDIA's hosted endpoint) and returns a compute receipt with every answer (which model ran, under which mode). The agent keeps those receipts per step and shows them on screen next to its own checks.

- The agent refuses any model endpoint that is not on this machine unless `ALLOW_CLOUD_LLM=1`; Nightshift is that local endpoint, and what Nightshift may route to is the seller's choice in Nightshift (privacy floor: local-only / cloud-ok). In the demo the floor is cloud-ok, so masked rows reach NVIDIA's hosted endpoint; names or phone numbers typed in a customer's message are not masked.
- Before any row reaches the model, the sender's address becomes `CUSTOMER`, other addresses keep only a first letter and the domain (so a typo like `exmaple.com` stays visible), and card digits are removed.

## Where NVIDIA technology contributes
NVIDIA Nemotron does two jobs, and decides neither the verdict nor the fix:
1. **Investigates.** Given the customer's message, it chooses which read-only tool to call next (find the customer's orders, find payments made by their address, find the order behind a payment, pull a full journey). Case 6 — paid with one address, ordered under a typo of it — is found this way in four tool calls. (Offline, a fixed fallback lookup — payer address → payment provider → order — also reaches it; the model's job is to choose the path when the message does not fit that one.) The tools only follow the sender's own trail, and an order number in the message that belongs to someone else is ignored and shown as ignored, so a crafted message cannot pull another customer's records (tested, and probed in every measurement run).
2. **Explains and drafts.** It writes the explanation (which must cite the rows it used, or it is replaced by the verifier's text) and the reply to the customer, in the customer's language; a reply that promises money is replaced by a template.

Measured on the final code (`docs/measurements.md`, 2026-10-23 03:34): through Nightshift → Nemotron 3.5 Lightning (hosted NIM, free trial key), 6/6 cases resolved to the right order and broken link, 6/6 explanations passed the citation check, the loop itself named the order in 5/6, and the cross-customer probe was blocked; 74–218 s per case on the free endpoint. An earlier version of the pipeline (five cases, before the investigation loop) also ran fully on the Mac with Nemotron 3.5 Lightning 30B 4-bit through rapid-mlx: 5/5 and 5/5, ~14 s per case.

## How Cursor was used
The repository was developed with Cursor's agent (`cursor-agent`) alongside hand-written code. Project rules live in `.cursor/rules/project.mdc` (cite-or-fail, single SQL door, verifier decides, human approval for fixes, synthetic data only). Commits made through Cursor are marked `[cursor-agent]`, and the session outputs are saved in `docs/cursor-sessions/` (UI overhaul, approve-and-fix with audit log, Korean replies, Nightshift receipts on screen, the how-it-works strip, the result layout). Every Cursor change was reviewed and tested before it was committed.

## What was unique
- The agent can say "nothing is broken — you were never charged", and proves it.
- The model investigates, but a deterministic verifier decides; every red link carries the rows that prove it.
- A human approves every fix; every approved fix is written to an audit log; a fix that would move credits to another address first asks for the customer's confirmation.
- The cases are incidents from our own small shop, rebuilt with synthetic data.

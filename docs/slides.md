---
marp: true
theme: default
paginate: true
---

# Paid, but nothing arrived
## The agent that finds the broken link

Track 02 — The Agent That Can Explain Why · Team MoaHub (solo)

> Your customer already has proof they paid. This agent finds yours.

---

# The problem, the user

- Who: a one-person or small online seller of digital goods, credits, subscriptions. No support team.
- The message: **"I paid, but nothing arrived."**
- Slow answer → card dispute, *product not received*. The customer holds the proof (card SMS). The seller has to find theirs.

---

# Today: four screens, by hand

PSP dashboard · orders database · server logs · mail provider

Same question asked four times, lined up by eye. We did this ourselves while auditing our own checkout.

---

# The solution: one chain, one broken link

`card authorized → PSP paid → order confirmed → credits granted → mail delivered`

Green until the link that broke. Click the link → the raw row that proves it. Then: reply draft · fix (needs approval) · dispute evidence bundle.

---

# Agent workflow

1. locate the order (email / order id)
2. `order_journey` — one SQL query to Zetaris across five tables
3. deterministic verifier: each link green / red / grey, with refs
4. Nemotron (local, via Nightshift) explains, drafts the reply, phrases the fix
5. citation check: every sentence must cite a returned `ref`, or it is rejected

---

# Technical stack

Python 3.12 · FastAPI · Zetaris (Lightning JDBC, USL) · Meterless Nightshift · NVIDIA Nemotron 3.5 Lightning · DuckDB (tests) · Cursor

---

# How Zetaris was used

- Five sources registered as datasources; semantic layer `order_journey` relates them on `order_id` / `payment_id` / `email`.
- The agent sends SQL only. Nothing is copied. Every row carries `table:key`.
- Same SQL on DuckDB for tests; backend name printed on every result.

---

# How Meterless + NVIDIA were used

- Nightshift serves Nemotron locally at an OpenAI-compatible address → customer data stays on the machine.
- Nemotron explains and drafts; it never decides the verdict.
- Nightshift run trace shown as "checks on the record" next to our citation check.

---

# Product

(screens: chain with red link · cited rows · reply / fix / evidence · case 5 "Nothing is broken. You were never charged.")

All data synthetic. The five cases are bugs we found in our own checkout — two happened on real payments.

---

# What's next

- Real PSP connectors (Stripe, PortOne) and mail providers as Zetaris REST sources
- Screenshot reading (receipt / card SMS) with a local vision model
- Installable edition for sellers; Korean UI
- Cursor: rules + agent sessions in the repo

# Sponsor technologies — how each one is used

## How Zetaris was integrated
Zetaris is the only thing the agent talks to. The four systems a seller would otherwise open by hand — the payment-service-provider ledger, the orders/grants database, the server log export and the mail-provider events — are registered as Zetaris sources and related in a unified semantic layer called `order_journey` (`zetaris/register.sql`: `CREATE DATASOURCE … REGISTER DATASOURCE TABLES … COMPILE USL … ACTIVATE USL TABLE`). The agent's three tools (`find_orders`, `order_journey`, `related_orders`) are plain SQL sent through the bundled Lightning JDBC driver (`agent/sql_backend.py`, `ZetarisJDBCBackend`). Nothing is copied into the agent; every row it shows the seller is read in place and carries a `ref` (`table:key`) so the verdict can be traced back to the source.

Why this problem fits Zetaris: the evidence for "I paid but nothing arrived" is never in one system. The PSP knows the charge, the app database knows the order and the grant, the server log knows which calls happened, the mail provider knows whether the customer was told. "Query across silos, nothing moves" is exactly the shape of the question.

For development and the test suite the same SQL runs against the synthetic CSVs through DuckDB with identical table names; the backend in use is printed on every result so the two are never confused.

## How Meterless was integrated
Meterless Nightshift serves a local NVIDIA Nemotron behind its OpenAI-compatible endpoint (`NIGHTSHIFT_BASE_URL`, default `http://127.0.0.1:8088/v1`). The agent uses it for the three things a model is good at and a verifier is not: explaining the broken link in plain language and drafting the reply to the customer (the fix itself comes from the verifier). The agent refuses non-local endpoints unless `ALLOW_CLOUD_LLM=1`, and removes identity fields (email, card last 4, mail address) before rows reach the model.

The agent's own citation check: the explanation must cite at least one `ref` that the SQL tools actually returned and no other; otherwise it is replaced by the verifier's text, and the screen says so. A reply draft that promises money or misstates the verdict is replaced by a template.

## How Cursor was used during development
Cursor was the development environment for the repository (Cursor app and `cursor-agent` CLI). Project rules live in `.cursor/rules/project.mdc` (cite-or-fail, single SQL door, verifier decides, human approval for fixes, synthetic data only). Commits made through `cursor-agent` are marked `[cursor-agent]`. The developer reviewed every change; Cursor did not run fixes against any live system.

## Where NVIDIA technology contributes
NVIDIA Nemotron 3.5 Lightning (OpenMDW-1.1) is the explaining model, run locally (Meterless Nightshift; a rapid-mlx build is kept as a second local runtime). It is used where a language model adds value — explanation, reply, fix wording — and deliberately not where it would add risk: the verdict about which link broke is computed deterministically from the cited rows.

## What was unique about the use of the sponsor technologies
- Zetaris is used as the *evidence layer*, not as a data warehouse: the agent's output is a chain of raw rows, and Zetaris is what makes those rows reachable in one query across four systems.
- Meterless is used as the *privacy boundary*: the only reason a seller can paste a real customer message into this tool is that the model runs locally.
- The model is not allowed to decide. It explains a verdict it cannot change and must cite rows it did not invent — the citation check makes that enforceable rather than aspirational.
- The agent can say "nothing is broken": case 5 ends the demo with a grey chain and "You were never charged."

## Pre-existing components
None. No product code from our existing services was reused; open-source libraries only (`requirements.txt`).

# Paid, but nothing arrived — the agent that finds the broken link

> Your customer already has proof they paid. This agent finds yours.

Every online seller gets this message: **"I paid, but nothing arrived."** If the answer is slow, the next step is a card dispute ("product not received"). Today the seller opens four screens — the payment provider, the orders database, the server logs, the mail provider — and lines them up by hand.

This agent does that in one pass. It asks **one SQL door (Zetaris)** that federates all four sources, walks the **money chain** — *card authorized → PSP paid → order confirmed → credits granted → mail delivered* — and marks the one link that broke, **with the raw rows that prove it**. A local **NVIDIA Nemotron** served by **Meterless Nightshift** writes the explanation and the customer reply on the seller's own machine. The explanation must cite the rows the tools returned (a citation check replaces it otherwise); the verdict and the fix come from a deterministic verifier, never from the model.

It also knows how to say *nothing is broken*: when there is no charge at the PSP, the chain stops grey and the answer is "You were never charged."

**Track:** 02 — The Agent That Can Explain Why. **Team:** MoaHub (solo).

## Demo video
_(link added at submission)_

## How it works
```
customer message ──▶ find_orders ──▶ order_journey (one SQL door) ──▶ verify chain ──▶ explain + reply + fix
                         │                 │                              │                  │
                      orders         payments · orders · grants       deterministic      Nemotron via
                                     server_logs · mail_events        5-link verifier    Nightshift (local)
                                     federated by Zetaris             (decides)          (explains, cited)
```
- `agent/sql_backend.py` — the only place that talks to data. Zetaris (JDBC or REST) in production; DuckDB over the synthetic CSVs for tests, same table names, same SQL.
- `agent/tools.py` — the three tools the agent may call (`find_orders`, `order_journey`, `related_orders`). Every row carries a `ref` = `table:key`.
- `agent/chain.py` — the verifier. Green / red / grey per link, each with the refs that decided it. The model never overrides it.
- `agent/investigator.py` — the loop, the model call (OpenAI-compatible: Nightshift → Nemotron), the citation check.
- `app/` — FastAPI + a single page: the chain, "why" with clickable citations, verified / not verified, reply draft, fix (needs approval), dispute evidence bundle.

## Requirements
- Python 3.12 (`uv venv --python 3.12 .venv && uv pip install -r requirements.txt`)
- Zetaris platform (local Docker Compose bundle from Zetaris Cloud) + Java 21 for the bundled JDBC driver — or nothing at all for the offline mode
- Meterless Nightshift (Mac) serving a local Nemotron 3.5 Lightning — or any OpenAI-compatible endpoint
- Docker (we used colima with Rosetta on Apple Silicon)

## Setup
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python data/gen_synthetic.py          # 4 synthetic sources + 5 seeded cases
cp .env.example .env.local                       # fill Zetaris / Nightshift values (see below)
.venv/bin/python -m pytest -q                    # 5 seeded cases must resolve to the right link
.venv/bin/uvicorn app.main:app --port 8765       # open http://127.0.0.1:8765
```
Zetaris: `zetaris/register.sql` registers the five sources and builds the `order_journey` semantic layer. Nightshift: turn the hotspot on, copy the local address and key into `.env.local` (`NIGHTSHIFT_BASE_URL`, `NIGHTSHIFT_API_KEY`).

## Usage
Paste a customer message (or click a seeded case). The result page shows the chain, the broken link, the cited rows, what was verified and what was not, a reply draft, a fix that requires your approval, and a dispute evidence bundle (`/api/evidence`). The JSON API is `POST /api/investigate {"message": "..."}`.

## Synthetic data statement
**All data is synthetic. No real customer data was used.** Emails end in `@example.com`; card last-4 digits are public test card numbers; 200 healthy orders are generated with a fixed seed. The five seeded cases are bugs we found in our own checkout while auditing it — two of them happened on real payments — rebuilt here with made-up records:
1. Paid but not credited (retry succeeded at the PSP, our confirm trusted a stale *failed* status)
2. Paid, confirm never called (the confirm button was unreachable after payment)
3. Granted twice (grant timed out after writing, manual retry granted again)
4. Granted, but no mail (mail provider key missing)
5. Never charged (customer left before the card step — nothing is broken)

## Sponsor technologies
See `docs/sponsor-tech.md` for the full write-up.
- **Zetaris** — the one SQL door. Payments, orders, grants, server logs and mail events are registered as sources and joined in a unified semantic layer `order_journey`; the agent only ever sends SQL to Zetaris.
- **Meterless Nightshift** — local OpenAI-compatible runtime for Nemotron. The agent refuses non-local model endpoints unless `ALLOW_CLOUD_LLM=1`, and customer identity fields (email, card last 4, mail address) are removed before rows reach the model.
- **NVIDIA Nemotron 3.5 Lightning** — the explaining model (local, OpenMDW-1.1 license).
- **Cursor** — development; see `docs/sponsor-tech.md`.

## Measured
`docs/measurements.md`, `scripts/llm_smoke.py`, synthetic data, six seeded cases (case 6 is outside the verifier's playbook and only gives the payer's address):
- **Through Meterless Nightshift → NVIDIA Nemotron 3.5 Lightning (hosted, free trial key):** correct order and broken link **6/6**, explanation citation check **6/6**; case 6 solved by the model-driven loop in 4 tool calls. About 65–115 s per case on the free endpoint.
- **Fully offline (Nemotron 3.5 Lightning 30B 4-bit on the Mac, rapid-mlx):** 5/5 and 5/5, about 14 s per case.
- Verifier alone: ~20 ms on DuckDB, ~9 s through the local Zetaris platform.

## Pre-existing components
None of our product code. Open-source libraries only (`requirements.txt`). Everything in this repository was written during the build window.

## Privacy and safety
- Seller-side tool: it reads only the seller's own merchant records (PSP ledger, orders, grants, server logs, mail events). It never touches a customer's card issuer or bank. Run it on the seller's machine (`--host 127.0.0.1`, the default); the API has no login and is not meant to be exposed.
- Only well-formed ids (`ord_0000`, an email address) reach SQL; anything else is refused.
- The model never decides: the verdict and the fix come from the verifier; the model writes the explanation (citation-checked) and the reply draft, which is replaced by a template if it promises money or misstates the verdict.

## Limitations
- The verifier covers the five link types we have seen; new failure shapes land in "not verified" rather than being guessed.
- Model output is advisory; fix actions are never executed by the agent.

## License
MIT

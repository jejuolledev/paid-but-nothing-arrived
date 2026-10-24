# Submission form — values for hackathon.genai.works (Open Agent Hackathon 2026)

The form has five fields: Track, Description (150–2000 characters), Video (link or upload), GitHub repository, Pitch deck (optional). Team: MoaHub (solo). One submission per track; this is the Track 02 entry.

## Track
```
Track 02 — The Agent That Can Explain Why
```

## Description (1958 characters)
```
I run a small online shop. The message I dread most is "I paid 24,900 won and nothing arrived." If I'm slow to answer, it turns into a chargeback. The answer is split across the payment provider, our orders database, the server logs and the mail provider.

So I built an agent to dig for me. Paste the customer's message; their email is enough. NVIDIA Nemotron 3.5 Lightning (on NVIDIA's hosted endpoint, via Meterless Nightshift on my Mac) decides what to check next. If no order uses that email, it asks who actually paid at the payment provider and which order that payment belongs to. Every lookup is read-only SQL through Zetaris, where the shop database, the payment provider's ledger and the mail provider's events are three datasources joined in one semantic layer. An order's whole history is one query, and the page shows the SQL behind every step. If the message quotes another customer's order, it is not read.

The model doesn't get the final word. A rule-based verifier walks the money chain (card authorized, payment provider paid, order confirmed, credits granted, mail delivered) and marks each step green, red or grey, with the exact rows that prove it. The model's explanation is checked sentence by sentence: every amount, record id, email domain and payment, credit or mail status it states must match the rows it cites, or the verifier's text is used instead. On 30 deliberately wrong sentences, it caught all 30. The reply draft is in the customer's language and never promises a refund. The fix runs only after I click Approve, and it is logged. When nothing is wrong, it says so: "You were never charged."

Emails and card digits are masked before anything reaches the model.

Tested on Zetaris with six cases rebuilt from real bugs in my own shop (all data synthetic): right order and broken step 6/6 in each of four runs. Given only the payer's email, the agent tracked down the order itself. 22 automated tests. Built with Cursor.
```

## Video
```
https://youtu.be/Pzv--B0HpU8
```

## GitHub repository
```
https://github.com/jejuolledev/paid-but-nothing-arrived
```

## Pitch deck (optional)
```
https://github.com/jejuolledev/paid-but-nothing-arrived/blob/main/docs/slides.pdf
```

## Notes
Pre-existing components: none of our product code; open-source libraries only (see README).

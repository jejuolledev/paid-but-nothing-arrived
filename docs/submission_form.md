# Submission form — values for hackathon.genai.works (Open Agent Hackathon 2026)

The form has five fields: Track, Description (150–2000 characters), Video (link or upload), GitHub repository, Pitch deck (optional). Team: MoaHub (solo). One submission per track; this is the Track 02 entry.

## Track
```
Track 02 — The Agent That Can Explain Why
```

## Description (1943 characters)
```
I run a small online shop, and the message I dread most is "I paid 24,900 won and nothing arrived." If I'm slow to answer, it turns into a chargeback. The answer is spread across four places: the payment provider, our orders database, the server logs and the mail provider.

So I built an agent to do the digging. You paste the customer's message; their email is enough. NVIDIA Nemotron 3.5 Lightning (NVIDIA's hosted endpoint, called through Meterless Nightshift on my Mac) decides where to look next: no order under this email, so who actually paid at the provider, and which order does that payment belong to. Every lookup is read-only SQL through Zetaris, where the shop database, the payment provider's ledger and the mail provider's events are three datasources joined in one semantic layer. An order's whole history comes back from a single query, and the page shows the SQL behind every step. If a message quotes an order that belongs to someone else, that order isn't read, and the page says so.

The model doesn't get the final word. A rule-based check walks the money chain (card authorized, provider paid, order confirmed, credits granted, mail delivered) and marks each step green, red or grey, with the exact rows that prove it. The model's explanation is checked sentence by sentence: every amount, address and payment or mail status it states must match the rows it cites, or it's replaced. It drafts a reply in the customer's language and can't promise refunds. The fix only runs after I click Approve, and it's logged. When nothing is wrong, it says so: "You were never charged."

Addresses are masked and card digits removed before any record reaches the model.

Tested on Zetaris with six cases rebuilt from real bugs in my own shop (all data synthetic): right order and broken step 6 of 6, the agent found the order on its own 6 of 6, and every explanation passed the sentence check. 20 automated tests. Built with Cursor.
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

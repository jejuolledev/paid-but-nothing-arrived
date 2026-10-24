# Submission form — values for hackathon.genai.works (Open Agent Hackathon 2026)

The form has five fields: Track, Description (150–2000 characters), Video (link or upload), GitHub repository, Pitch deck (optional). Team: MoaHub (solo). One submission per track; this is the Track 02 entry.

## Track
```
Track 02 — The Agent That Can Explain Why
```

## Description (1888 characters)
```
"I paid 24,900 won and nothing arrived." Every small online seller gets this message, and a slow answer becomes a chargeback. The proof is split across four systems: the payment provider, the orders database, the server logs and the mail provider.

Paste the customer's message; their email is enough. NVIDIA Nemotron 3.5 Lightning, called through Meterless Nightshift on the seller's Mac, decides where to look: no order under this email, so who paid at the provider, which order is that payment, then the full journey. Every lookup is read-only SQL through one door, Zetaris, where the shop's five record tables (synthetic here) are joined in one semantic layer, order_journey. The sender's address decides whose records may be read: an order number that belongs to someone else is ignored, and the page says so.

A rule-based verifier, not the model, checks the money chain: card authorized, PSP paid, order confirmed, credits granted, mail delivered. Each link is green, red or grey, and every red link carries the rows that prove it. The model writes the explanation, which must cite those rows or is replaced by the verifier's text, and a reply in the customer's language that may not promise refunds. The fix comes from the verifier, needs the seller's approval (and the customer's confirmation when credits would move to another address), and goes into an audit log. When nothing is broken it says so: "You were never charged."

Before rows reach the model, the sender's address becomes CUSTOMER, other addresses are masked and card digits removed; every answer shows Nightshift's receipt of which model ran.

Measured on the final code with six cases rebuilt from bugs in our own shop: right order and broken link 6/6, explanations cited 6/6, the agent loop found the order itself 5/6, a cross-customer probe blocked; 16 automated tests. Built with Cursor. All data is synthetic.
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

## Before submitting
1. Make the repository public: `gh repo edit jejuolledev/paid-but-nothing-arrived --visibility public --accept-visibility-change-consequences`
2. Upload `docs/demo/final_v2.mp4` to YouTube (public or unlisted), put the link in README.md "Demo video", commit, push.
3. Paste the values above. Pre-existing components: none of our product code; open-source libraries only (see README).

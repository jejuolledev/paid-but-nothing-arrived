# Submission form — values for hackathon.genai.works (Open Agent Hackathon 2026)

The form has five fields: Track, Description (150–2000 characters), Video (link or upload), GitHub repository, Pitch deck (optional). Team: MoaHub (solo). One submission per track; this is the Track 02 entry.

## Track
```
Track 02 — The Agent That Can Explain Why
```

## Description (1944 characters)
```
I run a small online shop, and the message I dread most is "I paid 24,900 won and nothing arrived." If I'm slow to answer, it turns into a chargeback. The trouble is that the answer is spread across four places: the payment provider, our orders database, the server logs and the mail provider.

So I built an agent that does the digging for me. You paste the customer's message; their email is enough. NVIDIA Nemotron 3.5 Lightning (on NVIDIA's hosted endpoint, called through Meterless Nightshift on my Mac) decides where to look next: there's no order under this email, so who actually paid at the provider, which order does that payment belong to, and what happened next. Every lookup is a read-only SQL query through Zetaris, where the shop's records are joined in one semantic layer. It only follows the trail of the address in the message. If the message quotes an order that belongs to someone else, that order isn't read, and the page tells you.

The model doesn't get the final word. A plain rule-based check walks the money chain (card authorized, provider paid, order confirmed, credits granted, mail delivered) and marks each step green, red or grey. Every red step comes with the exact rows that prove it. The model writes the explanation, which has to cite those rows, and drafts a reply in the customer's language. It can't promise refunds; that stays my call. The suggested fix only runs after I click Approve, and every fix is logged. And when nothing is wrong, it just says so: "You were never charged."

Before any record reaches the model, the customer's address is replaced, other addresses are masked and card digits are removed.

I tested it on six cases rebuilt from real bugs in my own shop (all data here is synthetic). It found the right order and the broken step in 6 of 6, every explanation cited real rows, and the agent tracked down the order on its own in 5 of 6. There are 18 automated tests. Built with Cursor.
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

# Submission form — copy-ready values (fill the URLs at submission time)

Primary track: **02 — The Agent That Can Explain Why**
Team: **MoaHub** (solo, Jeonggil Bae)

## Project name
```
Paid, but nothing arrived — the agent that finds the broken link
```

## One-line description
```
Your customer already has proof they paid. This agent finds yours: one SQL door (Zetaris) across the PSP ledger, orders, grants, server logs and mail events; a local Nemotron (Meterless Nightshift) explains the one link that broke, with the raw rows that prove it.
```

## Description
```
"I paid, but nothing arrived." Every online seller gets this message, and a slow answer turns into a card dispute. The evidence is never in one system: the payment provider knows the charge, the app database knows the order and the credits, the server log knows which calls happened, the mail provider knows whether the customer was told.

This agent asks one SQL door — Zetaris, with the four sources registered and related in a unified semantic layer called order_journey — and walks the money chain: card authorized → PSP paid → order confirmed → credits granted → mail delivered. A deterministic verifier marks each link green, red or grey and attaches the rows that decided it. A local NVIDIA Nemotron served by Meterless Nightshift then explains the broken link, drafts the reply to the customer and phrases the fix (which requires human approval). Every sentence the model writes must cite a row the tools actually returned; a citation check rejects anything else and shows that it did. The seller also gets a dispute evidence bundle.

It also knows how to say "nothing is broken": when there is no charge at the provider, the chain stops grey and the answer is "You were never charged."

All data is synthetic. The five seeded cases are bugs we found while auditing our own checkout — two of them happened on real payments — rebuilt with made-up records.
```

## Demo video (1–4 min)
```
<YouTube URL>
```

## Slide deck
```
<PDF link — docs/slides.pdf in the repository or a Drive link>
```

## GitHub repository
```
https://github.com/jejuolledev/paid-but-nothing-arrived
```

## How Zetaris and Meterless were integrated / Cursor / NVIDIA / what was unique
Paste `docs/sponsor-tech.md` (sections in the order the form asks).

## Pre-existing components
```
None of our product code. Open-source libraries only (see requirements.txt). All code in the repository was written inside the build window; the first commit is 2026-10-22 10:04 KST (01:04 UTC).
```

## Notes for the person submitting
- Make the repository public first: `gh repo edit jejuolledev/paid-but-nothing-arrived --visibility public --accept-visibility-change-consequences`
- Upload the video to YouTube (public or unlisted), paste the link into README.md "Demo video", commit, push.
- Export slides: `npx @marp-team/marp-cli docs/slides.md -o docs/slides.pdf` (or any Markdown→PDF), commit.
- Log in to hackathon.genai.works **with the same method used on 10/18** (one account per participant).

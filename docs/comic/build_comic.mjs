// Six-panel explainer comic: picks one raw image per panel, lays speech text over it in HTML
// (the images carry no text), and renders a vertical strip PNG plus one PNG per panel for the video.
// Usage: node docs/comic/build_comic.mjs [P1=a P2=b ...]
import { chromium } from '/Users/ollekil/Desktop/Moahub-Labs/webs/알리기팔기작전/홍보엔진/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';

const DIR = path.dirname(new URL(import.meta.url).pathname);
const pick = Object.fromEntries(process.argv.slice(2).map(a => a.split('=')));

// caption = narration box (top-left); bubbles = [text, x%, y%, who] where who: owner | bot | phone
const PANELS = [
  { id: 'P1', caption: '11 PM. A one-person shop.', bubbles: [['“I paid 24,900 won and NOTHING arrived.”', 58, 12, 'phone']] },
  { id: 'P2', caption: '1 AM. Four dashboards, one question.', bubbles: [['Payments… orders… logs… mail… which one?!', 8, 70, 'owner'], ['“I’m filing a chargeback.”', 60, 10, 'phone']] },
  { id: 'P3', caption: 'Paste the message. That’s all.', bubbles: [['I’ll read your records. Read-only, emails masked.', 52, 12, 'bot']] },
  { id: 'P4', caption: 'The agent decides where to look next.', bubbles: [['No order under this email… but the payment provider knows who paid…', 6, 12, 'bot'], ['Found it: the order was saved as “exmaple.com”.', 50, 72, 'bot']] },
  { id: 'P5', caption: 'Rule check: paid ✓  order ✓  credits ✕  mail ✕', bubbles: [['Reply drafted. Refunds? You decide.', 50, 74, 'bot']] },
  { id: 'P6', caption: 'Approve → the fix runs → the chain turns green.', bubbles: [['“Got it, thank you!” ❤️', 60, 12, 'phone']] },
];

const css = `
*{box-sizing:border-box}body{margin:0;background:#0e1116;font-family:-apple-system,"Inter","Segoe UI",sans-serif}
.p{position:relative;width:1600px;height:892px;overflow:hidden;border-bottom:14px solid #0e1116}
.p img{width:100%;height:100%;object-fit:cover;display:block}
.cap{position:absolute;left:28px;top:24px;z-index:2;background:#fff6d6;color:#2b2416;font-weight:700;font-size:30px;padding:10px 18px;border:3px solid #2b2416;border-radius:6px;box-shadow:4px 4px 0 #2b2416;max-width:62%}
.b{position:absolute;max-width:40%;font-size:31px;line-height:1.25;font-weight:700;padding:16px 22px;border-radius:26px;border:3px solid #1d1d1d;box-shadow:3px 3px 0 #1d1d1d}
.owner{background:#fff;color:#111}.bot{background:#e7ffe9;color:#0b3d17}.phone{background:#ffe3e3;color:#5a1010}
.n{position:absolute;right:24px;bottom:18px;color:#fff;font-weight:800;font-size:26px;text-shadow:0 2px 6px #000}`;

const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const panelHtml = (p, i) => {
  const f = path.join(DIR, 'raw', `${p.id}_${pick[p.id] || 'a'}.png`);
  if (!fs.existsSync(f)) throw new Error(`missing ${f}`);
  const bubbles = p.bubbles.map(([t, x, y, w]) => `<div class="b ${w}" style="left:${x}%;top:${y}%">${esc(t)}</div>`).join('');
  return `<div class="p" id="${p.id}"><img src="file://${f}"><div class="cap">${esc(p.caption)}</div>${bubbles}<div class="n">${i + 1}/6</div></div>`;
};

const html = `<!doctype html><meta charset="utf-8"><style>${css}</style>${PANELS.map(panelHtml).join('')}`;
fs.writeFileSync(path.join(DIR, 'comic.html'), html);
const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1600, height: 892 } });
await pg.goto('file://' + path.join(DIR, 'comic.html'));
await pg.screenshot({ path: path.join(DIR, 'comic_strip.png'), fullPage: true });
for (const p of PANELS) await (await pg.$('#' + p.id)).screenshot({ path: path.join(DIR, `panel_${p.id}.png`) });
await b.close();
console.log('comic ok');

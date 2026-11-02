function odoPos(v, i) { const q = Math.pow(10, i); const fl = Math.floor(v / q); return (fl % 10) + smooth(q - 0.4, q, v - fl * q); }
class Odo {
  constructor(el, nd, fs, cw, commas, grad) {
    el.classList.remove('grad', 'gradPax');
    this.lh = Math.round(fs * 1.12); this.cw = cw; this.grad = grad; this.items = [];
    el.style.fontSize = fs + 'px'; el.style.height = this.lh + 'px'; el.style.lineHeight = this.lh + 'px';
    for (let i = nd - 1; i >= 0; i--) {
      const c = document.createElement('div'); c.className = 'col'; c.style.width = cw + 'px'; c.style.height = this.lh + 'px';
      const s = document.createElement('div'); s.className = 'strip';
      s.innerHTML = Array.from({ length: 11 }, (_, d) => `<div style="height:${this.lh}px">${d % 10}</div>`).join('');
      c.appendChild(s); el.appendChild(c); this.items.push({ i, c, s, w: cw, digit: true });
      if (commas && i > 0 && i % 3 === 0) { const sp = document.createElement('div'); sp.className = 'sepc'; sp.textContent = ','; sp.style.width = (cw * 0.42) + 'px'; sp.style.height = this.lh + 'px'; el.appendChild(sp); this.items.push({ i: i - 0.5, c: sp, s: sp, w: cw * 0.42, digit: false }); }
    }
  }
  set(v) {
    v = Math.max(0, v); const n = Math.max(1, String(Math.floor(v + 0.4)).length);
    let x = 0; const vis = this.items.filter(it => it.digit ? it.i < n : it.i < n - 1);
    const tot = vis.reduce((s, it) => s + it.w, 0);
    for (const it of this.items) {
      const on = vis.includes(it); it.c.style.display = on ? 'block' : 'none'; if (!on) continue;
      if (it.digit) it.s.style.transform = `translateY(${-odoPos(v, it.i) * this.lh}px)`;
      if (this.grad) { const t = it.s; t.style.backgroundImage = this.grad; t.style.backgroundSize = `${tot}px 100%`; t.style.backgroundPosition = `${-x}px 0`; t.style.webkitBackgroundClip = 'text'; t.style.backgroundClip = 'text'; t.style.color = 'transparent'; }
      x += it.w;
    }
  }
}
const hoursEl = $('hours'); const hourBars = [];
for (let h = 0; h < 24; h++) { const b = document.createElement('div'); b.className = 'b'; b.style.left = (h * 860 / 24 + 3) + 'px'; b.style.height = '0px'; b.style.background = 'linear-gradient(180deg,#A06BFF,#5AA9FF)'; hoursEl.appendChild(b); hourBars.push(b); }
const HMAX = Math.max(...S.stats.hourly);
const ICONS = {
  SUNNY: `<circle cx="24" cy="24" r="9" fill="#FFD166"/><g stroke="#FFD166" stroke-width="3" stroke-linecap="round">${[0, 45, 90, 135, 180, 225, 270, 315].map(a => `<line x1="${24 + Math.cos(a * D2R) * 14}" y1="${24 + Math.sin(a * D2R) * 14}" x2="${24 + Math.cos(a * D2R) * 19}" y2="${24 + Math.sin(a * D2R) * 19}"/>`).join('')}</g>`,
  CLEAR: `<path d="M30 8 A16 16 0 1 0 40 32 A13 13 0 1 1 30 8 Z" fill="#d8e2ff"/>`,
  CLOUD: `<path d="M14 36 H36 A8 8 0 0 0 35 20 A11 11 0 0 0 14 22 A7 7 0 0 0 14 36 Z" fill="#c9d3e6"/>`,
  RAIN: `<path d="M14 30 H36 A8 8 0 0 0 35 14 A11 11 0 0 0 14 16 A7 7 0 0 0 14 30 Z" fill="#9fb0cc"/><g stroke="#5AA9FF" stroke-width="3" stroke-linecap="round"><line x1="17" y1="35" x2="14" y2="43"/><line x1="25" y1="35" x2="22" y2="43"/><line x1="33" y1="35" x2="30" y2="43"/></g>`,
  MIST: `<g stroke="#c9d3e6" stroke-width="3.4" stroke-linecap="round"><line x1="8" y1="16" x2="40" y2="16"/><line x1="12" y1="24" x2="36" y2="24"/><line x1="8" y1="32" x2="40" y2="32"/></g>`,
};
ICONS.PART_D = `<g transform="translate(-6,-6) scale(0.8)">${ICONS.SUNNY}</g><g transform="translate(4,4) scale(0.9)">${ICONS.CLOUD}</g>`;
ICONS.PART_N = `<g transform="translate(-4,-6) scale(0.8)">${ICONS.CLEAR}</g><g transform="translate(4,4) scale(0.9)">${ICONS.CLOUD}</g>`;
let lastIcon = '';
// Flat 2D cartoon engine: one canvas, one paused GSAP timeline, scenes drawn as pure functions of time.
export const W = 1080, H = 1920, FPS = 30;
export const gsap = window.gsap;
export const tl = gsap.timeline({ paused: true });
export const cv = document.getElementById('c');
export const c = cv.getContext('2d');
export const PI = Math.PI;

// ---------- palette (flat, warm, like a picture book)
export const PAL = {
  ink: '#2b2622', cream: '#f2ead8', wall: '#efe6d2', floor: '#b5834f', floorDark: '#9c6d3e', teal: '#2f8a86', sky: '#cfe8f1', skyTop: '#a9d6ea',
  orange: '#ff9f1c', orangeDark: '#3a2616', grass: '#7cc35a', grassDark: '#5aa13f', water: '#4aa3c7', waterDark: '#2f7fa3', brick: '#b5523b', brickDark: '#8e3b2a',
  red: '#e63946', blue: '#2f6fb5', purple: '#4b1f6f', yellow: '#ffd23f', white: '#ffffff', grey: '#8a8f99', skin: ['#f5cba7', '#e0a87a', '#c68642', '#8d5524', '#f1c27d'],
};

// ---------- timing (voiceover word times)
export const TM = window.TIMING;
export const DUR = TM.duration;
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const segLines = seg => TM.lines.filter(l => l.seg === seg);
export const S = seg => TM.segments[seg].start;
export const E = seg => TM.segments[seg].end;
export const L = (seg, i) => segLines(seg)[i];
function findWord(seg, word, n) {
  let k = 0;
  for (const l of segLines(seg)) for (const x of l.words) if (norm(x.w) === norm(word)) { if (k === n) return x; k++; }
  throw new Error(`word "${word}"#${n} not in ${seg}`);
}
export const w = (seg, word, n = 0) => findWord(seg, word, n).s;
export const we = (seg, word, n = 0) => findWord(seg, word, n).e;

// ---------- math / easing
export const clamp01 = x => Math.max(0, Math.min(1, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const ss = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
export const backOut = (k, s = 1.9) => k <= 0 ? 0 : k >= 1 ? 1 : 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
export const elastic = k => k <= 0 ? 0 : k >= 1 ? 1 : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * (2 * PI / 3)) + 1;
export const pop = (t, t0, d = 0.35) => backOut(clamp01((t - t0) / d));          // 0 → 1 with overshoot
export const popOut = (t, t0, t1, d = 0.35) => pop(t, t0, d) * (1 - clamp01((t - (t1 - 0.15)) / 0.15));
export function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// ---------- audio cues (read by tools/mix.py)
export const SFX = [], MUSIC = [];
export function sfx(name, t, gain = 1, extra = {}) { SFX.push(Object.assign({ name, t: Math.max(0, +t.toFixed(3)), gain }, extra)); }
export function music(t, level, extra = {}) { MUSIC.push(Object.assign({ t: +t.toFixed(3), level }, extra)); }

// ---------- drawing helpers
export function rr(x, y, w_, h, r) { c.beginPath(); c.roundRect(x, y, w_, h, r); }
export function fs(fill, stroke = PAL.ink, lw = 6) { if (fill) { c.fillStyle = fill; c.fill(); } if (stroke && lw) { c.lineWidth = lw; c.strokeStyle = stroke; c.lineJoin = 'round'; c.lineCap = 'round'; c.stroke(); } }
export function circle(x, y, r, fill, stroke = PAL.ink, lw = 6) { c.beginPath(); c.arc(x, y, r, 0, PI * 2); fs(fill, stroke, lw); }
export function ellipse(x, y, rx, ry, fill, stroke = PAL.ink, lw = 6, rot = 0) { c.beginPath(); c.ellipse(x, y, rx, ry, rot, 0, PI * 2); fs(fill, stroke, lw); }
export function txt(s, x, y, { font = 'Nunito', weight = 900, size = 40, color = PAL.ink, align = 'center', baseline = 'middle', stroke = null, lw = 0, italic = false } = {}) {
  c.font = `${italic ? 'italic ' : ''}${weight} ${size}px "${font}"`; c.textAlign = align; c.textBaseline = baseline;
  if (stroke) { c.lineWidth = lw; c.strokeStyle = stroke; c.lineJoin = 'round'; c.strokeText(s, x, y); }
  c.fillStyle = color; c.fillText(s, x, y);
}
export function withT(x, y, sc, rot, fn) { c.save(); c.translate(x, y); if (rot) c.rotate(rot); c.scale(sc, sc); fn(); c.restore(); }

// orange outlined title (the format's top-of-frame labels)
export function title(s, x, y, k = 1, size = 96, { color = PAL.orange, rot = -0.03, font = 'Lilita One' } = {}) {
  if (k <= 0.001) return;
  withT(x, y, k, rot, () => {
    txt(s, 0, 6, { font, weight: 400, size, color: PAL.orangeDark, stroke: PAL.orangeDark, lw: 16 });
    txt(s, 0, 0, { font, weight: 400, size, color, stroke: PAL.orangeDark, lw: 10 });
    txt(s, 0, 0, { font, weight: 400, size, color });
  });
}
// handwritten label (age stamps, names)
export function hand(s, x, y, k = 1, size = 74, color = PAL.orange, rot = -0.04) {
  if (k <= 0.001) return;
  withT(x, y, k, rot, () => { txt(s, 0, 0, { font: 'Patrick Hand', weight: 400, size, color: PAL.orangeDark, stroke: PAL.orangeDark, lw: 9 }); txt(s, 0, 0, { font: 'Patrick Hand', weight: 400, size, color }); });
}
// stat card: big orange number, a line or two, a tiny source
export function card(x, y, wd, ht, { big, l1, l2, src, bigSize = 104, accent = PAL.orange }, k = 1, rot = -0.02) {
  if (k <= 0.001) return;
  withT(x, y, k, rot, () => {
    rr(-wd / 2 + 8, -ht / 2 + 10, wd, ht, 28); fs('rgba(0,0,0,.18)', null, 0);
    rr(-wd / 2, -ht / 2, wd, ht, 28); fs('#fbf6ea', PAL.ink, 7);
    let yy = -ht / 2 + 26 + bigSize * 0.55;
    if (big) { txt(big, 0, yy + 6, { font: 'Lilita One', weight: 400, size: bigSize, color: PAL.orangeDark, stroke: PAL.orangeDark, lw: 14 }); txt(big, 0, yy, { font: 'Lilita One', weight: 400, size: bigSize, color: accent, stroke: PAL.orangeDark, lw: 8 }); txt(big, 0, yy, { font: 'Lilita One', weight: 400, size: bigSize, color: accent }); yy += bigSize * 0.62; }
    if (l1) { txt(l1, 0, yy + 18, { size: 40, color: PAL.ink }); yy += 48; }
    if (l2) { txt(l2, 0, yy + 18, { size: 40, color: PAL.ink }); yy += 48; }
    if (src) txt(src, 0, ht / 2 - 30, { font: 'Patrick Hand', weight: 400, size: 32, color: '#6b6258', italic: false });
  });
}
// speech bubble with tail
export function bubble(x, y, s, k = 1, { tail = 'down', size = 46, maxW = 760, color = PAL.ink, fill = '#ffffff' } = {}) {
  if (k <= 0.001) return;
  c.font = `900 ${size}px "Nunito"`;
  const lines = wrap(s, maxW - 60), wd = Math.min(maxW, Math.max(...lines.map(l => c.measureText(l).width)) + 70), ht = lines.length * size * 1.15 + 50;
  withT(x, y, k, 0, () => {
    rr(-wd / 2, -ht / 2, wd, ht, 34); fs(fill, PAL.ink, 7);
    c.beginPath(); const tx = tail === 'left' ? -wd * 0.25 : tail === 'right' ? wd * 0.25 : 0;
    c.moveTo(tx - 24, ht / 2 - 4); c.lineTo(tx + (tail === 'right' ? 34 : tail === 'left' ? -34 : 6), ht / 2 + 46); c.lineTo(tx + 24, ht / 2 - 4); c.closePath(); fs(fill, PAL.ink, 7);
    c.fillStyle = fill; c.fillRect(tx - 20, ht / 2 - 12, 40, 12);
    lines.forEach((l, i) => txt(l, 0, -ht / 2 + 25 + size * 0.6 + i * size * 1.15, { size, color }));
  });
}
export function wrap(s, maxW) {
  const words = s.split(' '), out = []; let cur = '';
  for (const wd of words) { const tryS = cur ? cur + ' ' + wd : wd; if (c.measureText(tryS).width > maxW && cur) { out.push(cur); cur = wd; } else cur = tryS; }
  if (cur) out.push(cur); return out;
}

// ---------- scenes
export const SCENES = [];
export function scene(t0, t1, draw, { zoom = 0.035, cx = W / 2, cy = H * 0.55 } = {}) { SCENES.push({ t0, t1, draw, zoom, cx, cy }); }
export const OVERLAYS = [];
export function overlay(fn) { OVERLAYS.push(fn); }

// ---------- captions (dark rounded box, white text, orange key words, red masked swears)
const CHUNKS = [];
for (const l of TM.lines) {
  let cur = [];
  const flush = () => { if (cur.length) { CHUNKS.push({ words: cur }); cur = []; } };
  l.caps.forEach((cp, i) => {
    cur.push(cp);
    const len = cur.map(x => x.text).join(' ').length, left = l.caps.length - 1 - i;
    const restLen = l.caps.slice(i + 1).map(x => x.text).join(' ').length;
    if (/[.?!]["”]?$/.test(cp.text) || (left > 2 && restLen > 14 && ((/[,:]$/.test(cp.text) && len >= 26) || len >= 44))) flush();
  });
  flush();
}
for (const ch of CHUNKS) ch.s = ch.words[0].s - 0.08;
for (let i = 0; i < CHUNKS.length; i++) { const ch = CHUNKS[i], nx = CHUNKS[i + 1], last = ch.words[ch.words.length - 1]; ch.e = nx ? Math.min(nx.s, last.e + 0.9) : last.e + 1.0; }
const mask = s => s.replace(/[A-Za-z]+/, m => m.length <= 2 ? m[0] + '*' : m[0] + '*'.repeat(m.length - 2) + m[m.length - 1]);
export function drawCaptions(t) {
  const ch = CHUNKS.find(k => t >= k.s && t < k.e); if (!ch) return;
  const k = clamp01((t - ch.s) / 0.12) * clamp01((ch.e - t) / 0.1);
  const size = 50; c.font = `900 ${size}px "Nunito"`;
  const words = ch.words.map(wd => ({ s: wd.style === 'swear' ? mask(wd.text) : wd.text, st: wd.style }));
  // lay out into lines (max 840 px)
  const lines = []; let cur = [], cw = 0; const sp = c.measureText(' ').width;
  for (const wd of words) { const ww = c.measureText(wd.s).width; if (cur.length && cw + sp + ww > 840) { lines.push({ ws: cur, w: cw }); cur = []; cw = 0; } cur.push(Object.assign(wd, { ww })); cw += (cur.length > 1 ? sp : 0) + ww; }
  if (cur.length) lines.push({ ws: cur, w: cw });
  const bw = Math.max(...lines.map(l => l.w)) + 56, bh = lines.length * size * 1.14 + 34, y0 = 1540;
  c.save(); c.globalAlpha = k; c.translate(W / 2, y0); c.scale(0.94 + 0.06 * k, 0.94 + 0.06 * k);
  rr(-bw / 2, -bh / 2, bw, bh, 22); c.fillStyle = 'rgba(28,26,24,.9)'; c.fill();
  lines.forEach((ln, i) => {
    let x = -ln.w / 2; const y = -bh / 2 + 17 + size * 0.6 + i * size * 1.14;
    for (const wd of ln.ws) { txt(wd.s, x, y, { size, align: 'left', color: wd.st === 'hl' ? '#ffb02e' : wd.st === 'bad' || wd.st === 'swear' ? '#ff5a5f' : '#ffffff' }); x += wd.ww + sp; }
  });
  c.restore();
}

// ---------- frame
export function renderAt(t) {
  tl.seek(t, false);
  c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, W, H); c.fillStyle = '#000'; c.fillRect(0, 0, W, H);
  for (const s of SCENES) if (t >= s.t0 && t < s.t1) {
    const k = (t - s.t0) / Math.max(0.001, s.t1 - s.t0);
    c.save(); c.translate(s.cx, s.cy); c.scale(1 + s.zoom * k, 1 + s.zoom * k); c.translate(-s.cx, -s.cy);
    s.draw(t, t - s.t0, s); c.restore();
  }
  for (const o of OVERLAYS) { c.save(); o(t); c.restore(); }
  drawCaptions(t);
}

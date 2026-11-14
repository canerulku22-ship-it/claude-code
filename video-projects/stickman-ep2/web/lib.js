// Timing helpers (voiceover word times), audio cue export, captions, and 2D drawing helpers for panels.
import { gsap, C, text, rrect, drawIcon } from './engine.js';

export const T = window.TIMING;
export const DUR = T.duration;
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const segLines = seg => T.lines.filter(l => l.seg === seg);
export const S = seg => T.segments[seg].start;
export const E = seg => T.segments[seg].end;
export const L = (seg, i) => segLines(seg)[i];
function findWord(seg, word, n) {
  let c = 0;
  for (const l of segLines(seg)) for (const x of l.words) if (norm(x.w) === norm(word)) { if (c === n) return x; c++; }
  throw new Error(`word "${word}"#${n} not in ${seg}`);
}
export const w = (seg, word, n = 0) => findWord(seg, word, n).s;
export const we = (seg, word, n = 0) => findWord(seg, word, n).e;

export const clamp01 = x => Math.max(0, Math.min(1, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const ease = n => gsap.parseEase(n);
export const E_OUT = ease('power3.out'), E_INOUT = ease('power2.inOut'), E_BACK = ease('back.out(2)');
export const prog = (t, t0, d, e = E_OUT) => e(clamp01((t - t0) / d));
export const money = (v, d = 0) => v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export const q = (t, fps = 30) => Math.round(t * fps); // quantize time for panel redraw keys

// ---------- audio cues (read by tools/mix.py) ----------
export const SFX = [], MUSIC = [];
export function sfx(name, t, gain = 1, extra = {}) { SFX.push(Object.assign({ name, t: Math.max(0, +t.toFixed(3)), gain }, extra)); }
export function music(t, level, extra = {}) { MUSIC.push(Object.assign({ t: +t.toFixed(3), level }, extra)); }

// ---------- captions (DOM overlay, crisp) ----------
const capEl = document.getElementById('captions');
const CHUNKS = [];
for (const l of T.lines) {
  let cur = [];
  const flush = () => { if (cur.length) { CHUNKS.push({ words: cur, line: l }); cur = []; } };
  for (const c of l.caps) {
    cur.push(c);
    const len = cur.map(x => x.text).join(' ').length;
    if (/[.?!]$/.test(c.text) || (/[,:]$/.test(c.text) && len >= 12) || cur.length >= 5 || len >= 22) flush();
  }
  flush();
}
for (const ch of CHUNKS) ch.s = ch.words[0].s - 0.05;
for (let i = 0; i < CHUNKS.length; i++) {
  const ch = CHUNKS[i], nx = CHUNKS[i + 1], last = ch.words[ch.words.length - 1];
  const hold = last.e + 0.4;
  ch.e = nx ? Math.min(nx.s, nx.line === ch.line ? nx.s : hold) : last.e + 0.7;
}
let capIdx = -2, spans = [];
export function drawCaptions(t) {
  let i = -1;
  for (let k = 0; k < CHUNKS.length; k++) if (t >= CHUNKS[k].s && t < CHUNKS[k].e) { i = k; break; }
  if (i !== capIdx) {
    capEl.innerHTML = ''; spans = []; capIdx = i;
    if (i >= 0) for (const wd of CHUNKS[i].words) { const s = document.createElement('span'); s.className = 'cw ' + (wd.style || ''); s.textContent = wd.text; capEl.appendChild(s); spans.push([s, wd]); }
  }
  if (i < 0) return;
  const ch = CHUNKS[i], exitK = clamp01((ch.e - t) / 0.07);
  const enter = clamp01((t - ch.s) / 0.12);
  for (const [sp, wd] of spans) {
    const p = clamp01((t - (wd.s - 0.04)) / 0.12), e = E_BACK(p), on = t >= wd.s - 0.04 && t < wd.e + 0.04;
    sp.style.opacity = ((0.32 + 0.68 * p) * enter * exitK).toFixed(3);
    if (!sp.dataset.st) sp.dataset.st = sp.className;
    sp.className = p > 0.5 ? sp.dataset.st : 'cw';
    sp.style.transform = `translateY(${((1 - enter) * 16).toFixed(1)}px) scale(${(1 + 0.08 * (on ? Math.sin(Math.min(1, p) * Math.PI) : 0)).toFixed(3)})`;
  }
}

// ---------- 2D panel drawing helpers (canvas pixels) ----------
export function lbl(g, s, x, y, size = 30, color = C.white, opts = {}) {
  const o = Object.assign({ size, weight: 800, color, spacing: size * 0.32 }, opts); if (o.glow) o.glow = Math.min(o.glow, size * 0.3);
  text(g, s.toUpperCase(), x, y, o);
}
export function big(g, s, x, y, size = 120, color = C.white, opts = {}) {
  const o = Object.assign({ size, weight: 900, color, font: 'Inter Display', spacing: -size * 0.02 }, opts); if (o.glow) o.glow = Math.min(o.glow, size * 0.12);
  text(g, s, x, y, o);
}
export function neonRect(g, x, y, w, h, color = C.white, { r = 18, lw = 5, fill = 'rgba(4,6,10,.72)', glow = 18 } = {}) {
  g.save(); rrect(g, x, y, w, h, r);
  if (fill) { g.fillStyle = fill; g.fill(); }
  g.shadowColor = color; g.shadowBlur = glow; g.strokeStyle = color; g.lineWidth = lw; g.stroke(); g.restore();
}
export function bar(g, x, y, w, h, k, color, { track = 'rgba(255,255,255,.08)', glow = 16 } = {}) {
  g.save(); rrect(g, x, y, w, h, h / 2); g.fillStyle = track; g.fill();
  if (k > 0.001) { rrect(g, x, y, Math.max(h, w * k), h, h / 2); g.shadowColor = color; g.shadowBlur = glow; g.fillStyle = color; g.fill(); }
  g.restore();
}
export function strikeLine(g, x0, y0, x1, y1, k, color = C.red, lw = 7) {
  if (k <= 0) return;
  g.save(); g.strokeStyle = color; g.lineWidth = lw; g.lineCap = 'round'; g.shadowColor = color; g.shadowBlur = 14;
  g.beginPath(); g.moveTo(x0, y0); g.lineTo(lerp(x0, x1, k), lerp(y0, y1, k)); g.stroke(); g.restore();
}
export function icon(g, name, x, y, size, color = C.white, lw = 1.5, glow = 16) { drawIcon(g, name, x, y, size, color, lw, glow); }
export function glitchText(g, s, x, y, size, color, t, amt = 1, opts = {}) {
  // RGB-split, sliced glitch for the hook number
  const seed = Math.floor(t * 12), r = Math.sin(seed * 12.9898) * 43758.5453 % 1;
  const off = amt * (6 + 10 * Math.abs(r));
  g.save(); g.globalCompositeOperation = 'lighter';
  big(g, s, x - off, y, size, 'rgba(255,40,70,.75)', opts);
  big(g, s, x + off * 0.6, y + 2, size, 'rgba(70,200,255,.45)', opts);
  g.restore();
  big(g, s, x, y, size, color, Object.assign({ glow: 30 }, opts));
  if (amt > 0.2 && Math.abs(r) > 0.55) { // slice displacement
    const hh = size * 0.18, yy = y - size * 0.4 + Math.abs(r) * size * 0.6;
    const img = g.getImageData(0, Math.max(0, yy), g.canvas.width, hh);
    g.putImageData(img, Math.round(off * 2 * (r > 0 ? 1 : -1)), Math.max(0, yy));
  }
}

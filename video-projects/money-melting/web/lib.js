// Engine: one paused GSAP timeline + pure functions of time, so any frame can be rendered by seek(t).
const W = 1080, H = 1920, FPS = 30;
const T = window.TIMING;
const DUR = T.duration;
const tl = gsap.timeline({ paused: true });
const C = { mint: '#3DFFB0', red: '#FF4560', gold: '#FFD15C', white: '#F2F5FF', grey: '#8A93A8', blue: '#7CC4FF' };
const RGB = { mint: [61, 255, 176], red: [255, 69, 96], gold: [255, 209, 92], white: [235, 240, 255], blue: [124, 196, 255], navy: [40, 60, 120] };

// ---------- cues exported to the audio mixer ----------
const SFX = [], MUSIC = [];
function sfx(name, t, gain = 1, extra = {}) { SFX.push(Object.assign({ name, t: Math.max(0, +t.toFixed(3)), gain }, extra)); }
function music(t, level, extra = {}) { MUSIC.push(Object.assign({ t: +t.toFixed(3), level }, extra)); }

// ---------- timing helpers (from the voiceover) ----------
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
const segLines = seg => T.lines.filter(l => l.seg === seg);
const S = seg => T.segments[seg].start;
const E = seg => T.segments[seg].end;
const L = (seg, i) => segLines(seg)[i];
function findWord(seg, word, n) {
  let c = 0;
  for (const l of segLines(seg)) for (const x of l.words) if (norm(x.w) === norm(word)) { if (c === n) return x; c++; }
  throw new Error(`word "${word}"#${n} not in ${seg}`);
}
const w = (seg, word, n = 0) => findWord(seg, word, n).s;
const we = (seg, word, n = 0) => findWord(seg, word, n).e;

// ---------- math ----------
const clamp01 = x => Math.max(0, Math.min(1, x));
const lerp = (a, b, k) => a + (b - a) * k;
const ease = n => gsap.parseEase(n);
const E_OUT = ease('power3.out'), E_INOUT = ease('power2.inOut'), E_BACK = ease('back.out(2.2)'), E_IN = ease('power2.in');
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const money = (v, d = 0) => v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
const mixRGB = (a, b, k) => a.map((x, i) => Math.round(lerp(x, b[i], k)));

// ---------- DOM helpers ----------
const world = document.getElementById('world');
const hud = document.getElementById('hud');
function el(tag, cls, parent, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; (parent || world).appendChild(e); return e; }
const div = (cls, parent, html) => el('div', cls, parent, html);
function icon(name, size, color = 'currentColor', sw = 1.6, fill = 'none') {
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="${fill}" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" style="display:block;overflow:visible">${ICONS[name]}</svg>`;
}
function at(e, x, y, extra = {}) { gsap.set(e, Object.assign({ left: x, top: y, xPercent: -50, yPercent: -50 }, extra)); return e; }
function svgEl(tag, attrs, parent) { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function svgLayer(parent) { const s = svgEl('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, parent); s.style.cssText = 'position:absolute;left:0;top:0;overflow:visible'; return s; }

// ---------- scenes ----------
const SCENES = [];
function scene(id, t0, t1, parent = world) { const e = div('scene', parent); e.id = id; SCENES.push({ el: e, t0, t1 }); return e; }

// pure per-frame functions (counters, tickers, clocks...)
const DYN = [];
function dyn(fn) { DYN.push(fn); }
function counter(e, from, to, t0, dur, fmt, easeName = 'power2.out') {
  const f = ease(easeName);
  dyn(t => { const k = f(clamp01((t - t0) / dur)); e.innerHTML = fmt(lerp(from, to, k), k); });
}

// ---------- common animations ----------
function popIn(e, t, o = {}) {
  tl.fromTo(e, { autoAlpha: 0, scale: o.from ?? 0.4, y: o.y ?? 0, rotation: o.rot ?? 0 },
    { autoAlpha: 1, scale: o.to ?? 1, y: 0, rotation: o.rotTo ?? 0, duration: o.dur ?? 0.45, ease: o.ease ?? 'back.out(2.2)' }, t);
  if (o.sfx !== false) sfx(o.sfx || 'pop', t, o.gain ?? 0.6);
  return e;
}
function fadeIn(e, t, dur = 0.4, from = {}) { tl.fromTo(e, Object.assign({ autoAlpha: 0 }, from), { autoAlpha: 1, x: 0, y: 0, scale: 1, duration: dur, ease: 'power3.out' }, t); return e; }
function out(e, t, dur = 0.3, to = {}) { tl.to(e, Object.assign({ autoAlpha: 0, scale: 0.92, duration: dur, ease: 'power2.in' }, to), t); return e; }
function slam(e, t, o = {}) {
  tl.fromTo(e, { autoAlpha: 0, scale: o.from ?? 2.4, rotation: o.rotFrom ?? (o.rot ?? 0) }, { autoAlpha: 1, scale: 1, rotation: o.rot ?? 0, duration: o.dur ?? 0.32, ease: 'expo.out' }, t);
  shake(t + 0.04, o.shake ?? 0.9, 0.45);
  sfx(o.sfx || 'stamp', t + 0.03, o.gain ?? 0.9);
  return e;
}
function drawPath(p, t, dur, easeName = 'power2.inOut') {
  const len = p.getTotalLength();
  p.style.strokeDasharray = `${len} ${len}`;
  tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease: easeName }, t);
  return len;
}
function typeText(e, text, t0, cps = 28) { dyn(t => { const n = Math.floor(clamp01((t - t0) * cps / text.length) * text.length); e.textContent = text.slice(0, n); }); }

// ---------- camera ----------
const cam = { x: 0, y: 0, s: 1, r: 0, p: 0, k: 0, blur: 0, glitch: 0 };
const camEl = document.getElementById('cam');
const OX = 540, OY = 760;
const CM = { A: 1, s: 1, cx: 0, cy: 0, dx: 0, dy: 0 };
const camMap = (x, y) => [OX + CM.dx + CM.A * (CM.cx + CM.s * (x - OX)), OY + CM.dy + CM.A * (CM.cy + CM.s * (y - OY))];
function camTo(t, vars, dur = 0.9, easeName = 'power3.inOut') { tl.to(cam, Object.assign({ duration: dur, ease: easeName }, vars), t); }
function focus(t, px, py, s = 1, dur = 0.9, easeName = 'power3.inOut', r = 0) { camTo(t, { x: -s * (px - OX), y: -s * (py - OY), s, r }, dur, easeName); }
function camSet(t, px, py, s = 1) { tl.set(cam, { x: -s * (px - OX), y: -s * (py - OY), s, r: 0 }, t); }
function punch(t, amt = 0.06, dur = 0.55) { tl.fromTo(cam, { p: amt }, { p: 0, duration: dur, ease: 'expo.out', immediateRender: false }, t); }
function shake(t, amp = 1, dur = 0.5) { tl.fromTo(cam, { k: amp }, { k: 0, duration: dur, ease: 'power2.out', immediateRender: false }, t); }
function glitch(t, dur = 0.28, amp = 1) { tl.fromTo(cam, { glitch: amp }, { glitch: 0, duration: dur, ease: 'power1.in', immediateRender: false }, t); sfx('glitch', t, 0.7); }
function whip(t, dir = 1) {
  tl.fromTo(cam, { blur: 0 }, { blur: 16, duration: 0.12, ease: 'power2.in', immediateRender: false }, t - 0.12)
    .to(cam, { blur: 0, duration: 0.22, ease: 'power2.out' }, t);
  sfx('whoosh', t - 0.2, 0.8);
}
function applyCam(t) {
  const k = cam.k, n1 = Math.sin(t * 61.7) * 0.6 + Math.sin(t * 97.3 + 1.3) * 0.4, n2 = Math.sin(t * 73.1 + 2.1) * 0.6 + Math.sin(t * 41.9) * 0.4;
  const drift = 1 + 0.008 * Math.sin(t * 0.45);
  const dx = k * n1 * 20 + Math.sin(t * 0.37) * 4, dy = k * n2 * 20 + Math.sin(t * 0.29 + 1) * 4, dr = k * Math.sin(t * 53) * 0.7;
  CM.A = (1 + cam.p) * drift; CM.s = cam.s; CM.cx = cam.x; CM.cy = cam.y; CM.dx = dx; CM.dy = dy;
  camEl.style.transform = `translate(${dx}px,${dy}px) scale(${(1 + cam.p) * drift}) translate(${cam.x}px,${cam.y}px) scale(${cam.s}) rotate(${cam.r + dr}deg)`;
  const f = [];
  if (cam.blur > 0.3) f.push(`blur(${cam.blur.toFixed(1)}px)`);
  if (cam.glitch > 0.02) { const g = cam.glitch * (10 + 8 * Math.sin(t * 90)); f.push(`drop-shadow(${g.toFixed(1)}px 0 0 rgba(255,40,90,.85)) drop-shadow(${(-g).toFixed(1)}px 0 0 rgba(40,230,255,.85))`); }
  camEl.style.filter = f.length ? f.join(' ') : 'none';
  if (cam.glitch > 0.02) camEl.style.transform += ` translateX(${(Math.sin(t * 211) * 26 * cam.glitch).toFixed(1)}px)`;
}

// ---------- environment / background ----------
const env = { tr: 40, tg: 60, tb: 120, ta: 0.16, spot: 1, grid: 0.09, horizon: 1080, dim: 0, stars: 1, floor: 1, alarm: 0, capY: 1320 };
function envTo(t, vars, dur = 0.8) { tl.to(env, Object.assign({ duration: dur, ease: 'power2.inOut' }, vars), t); }
function tint(t, name, a = 0.18, dur = 0.8) { const [r, g, b] = RGB[name]; envTo(t, { tr: r, tg: g, tb: b, ta: a }, dur); }

const bgc = document.getElementById('bg').getContext('2d');
const R0 = mulberry32(11);
const STARS = Array.from({ length: 150 }, () => ({ x: R0() * W, y: R0() * H, z: 0.15 + R0() * 0.85, tw: R0() * 6.28, sp: 0.4 + R0() }));
const BOKEH = Array.from({ length: 9 }, () => ({ x: R0() * W, y: R0() * 1000, r: 60 + R0() * 120, sp: 0.2 + R0() * 0.5, ph: R0() * 6.28 }));
function drawBG(t) {
  const g = bgc, [vx, hz] = camMap(540, env.horizon), zk = CM.A * CM.s, [ax] = camMap(540, -400);
  g.globalCompositeOperation = 'source-over';
  g.fillStyle = '#020309'; g.fillRect(0, 0, W, H);
  let grd = g.createRadialGradient(540, 720, 0, 540, 720, 1150);
  grd.addColorStop(0, `rgba(${env.tr | 0},${env.tg | 0},${env.tb | 0},${env.ta})`);
  grd.addColorStop(0.55, `rgba(${env.tr | 0},${env.tg | 0},${env.tb | 0},${env.ta * 0.35})`);
  grd.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grd; g.fillRect(0, 0, W, H);
  if (env.alarm > 0.01) { const a = env.alarm * (0.5 + 0.5 * Math.sin(t * 14)); g.fillStyle = `rgba(255,30,60,${0.22 * a})`; g.fillRect(0, 0, W, H); }

  g.globalCompositeOperation = 'lighter';
  // bokeh
  for (const b of BOKEH) {
    const x = b.x + Math.sin(t * b.sp + b.ph) * 40, y = b.y + Math.cos(t * b.sp * 0.7 + b.ph) * 30;
    const rg = g.createRadialGradient(x, y, 0, x, y, b.r);
    rg.addColorStop(0, `rgba(${env.tr | 0},${env.tg | 0},${env.tb | 0},${0.06 * env.stars})`); rg.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = rg; g.fillRect(x - b.r, y - b.r, b.r * 2, b.r * 2);
  }
  // spotlight cone
  if (env.spot > 0.01) {
    grd = g.createLinearGradient(0, 0, 0, hz);
    grd.addColorStop(0, `rgba(255,255,255,${0.085 * env.spot})`); grd.addColorStop(1, `rgba(255,255,255,${0.025 * env.spot})`);
    g.fillStyle = grd; g.beginPath(); g.moveTo(ax - 70 * zk, 0); g.lineTo(ax + 70 * zk, 0); g.lineTo(vx + 470 * zk, hz); g.lineTo(vx - 470 * zk, hz); g.closePath(); g.fill();
    g.save(); g.translate(vx, hz + 6 * zk); g.scale(zk, 0.16 * zk);
    grd = g.createRadialGradient(0, 0, 0, 0, 0, 560); grd.addColorStop(0, `rgba(255,255,255,${0.32 * env.spot})`); grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd; g.beginPath(); g.arc(0, 0, 560, 0, Math.PI * 2); g.fill(); g.restore();
  }
  g.globalCompositeOperation = 'source-over';
  // floor
  if (env.floor > 0.01 && hz < H) {
    grd = g.createLinearGradient(0, hz, 0, H);
    grd.addColorStop(0, `rgba(28,36,58,${0.6 * env.floor})`); grd.addColorStop(0.3, `rgba(10,13,22,${0.45 * env.floor})`); grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd; g.fillRect(0, hz, W, H - hz);
    // horizon line
    grd = g.createLinearGradient(0, 0, W, 0);
    grd.addColorStop(0, 'rgba(255,255,255,0)'); grd.addColorStop(0.5, `rgba(255,255,255,${0.35 * env.floor})`); grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd; g.fillRect(0, hz - 1, W, 2);
    // perspective grid
    if (env.grid > 0.005) {
      g.lineWidth = 1.5;
      const K = 230 * zk, frac = (t * 0.55) % 1;
      for (let i = 0; i < 24; i++) {
        const z = i + 1 - frac, y = hz + K / z * 0.9;
        if (y > H) continue;
        const a = env.grid * env.floor * clamp01(1 - z / 24) * clamp01((y - hz) / 25);
        g.strokeStyle = `rgba(150,175,255,${a})`; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke();
      }
      for (let j = -14; j <= 14; j++) {
        const x2 = 540 + j * 300;
        grd = g.createLinearGradient(0, hz, 0, H);
        grd.addColorStop(0, 'rgba(150,175,255,0)'); grd.addColorStop(0.4, `rgba(150,175,255,${env.grid * env.floor})`); grd.addColorStop(1, 'rgba(150,175,255,0)');
        g.strokeStyle = grd; g.beginPath(); g.moveTo(vx + j * 14 * zk, hz); g.lineTo(vx + (x2 - 540) * zk, H); g.stroke();
      }
    }
  }
  // dust
  g.globalCompositeOperation = 'lighter';
  for (const s of STARS) {
    const x = ((s.x + t * 7 * s.z + (CM.cx + CM.dx) * 0.12 * s.z) % W + W) % W, y = ((s.y - t * 12 * s.z * s.sp + (CM.cy + CM.dy) * 0.12 * s.z) % H + H) % H;
    const a = env.stars * (0.12 + 0.55 * s.z) * (0.55 + 0.45 * Math.sin(t * 2.2 * s.sp + s.tw));
    const r = 0.7 + 2.4 * s.z * s.z;
    g.fillStyle = `rgba(220,230,255,${a})`; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
  }
  g.globalCompositeOperation = 'source-over';
  if (env.dim > 0.005) { g.fillStyle = `rgba(0,0,0,${env.dim})`; g.fillRect(0, 0, W, H); }
}

// ---------- world-space particles ----------
const fxc = document.getElementById('fx').getContext('2d');
const FX = [];
function fx(fn) { FX.push(fn); }
function drawFX(t) { fxc.setTransform(1, 0, 0, 1, 0, 0); fxc.clearRect(0, 0, W, H); for (const f of FX) { fxc.save(); f(fxc, t); fxc.restore(); } }
// deterministic falling drops / sparks emitter
function emitter({ t0, t1, rate, x, y, vx = [0, 0], vy = [0, 0], g = 1400, life = 1.2, size = [3, 6], color = RGB.red, seed = 1, shape = 'drop', glow = 12, text = '$' }) {
  const r = mulberry32(seed), N = Math.ceil((t1 - t0) * rate), P = [];
  for (let i = 0; i < N; i++) P.push({ b: t0 + (i + r()) / rate, x: typeof x === 'function' ? x(r) : x + 0, y: typeof y === 'function' ? y(r) : y, vx: lerp(vx[0], vx[1], r()), vy: lerp(vy[0], vy[1], r()), s: lerp(size[0], size[1], r()), l: life * (0.7 + 0.6 * r()), rot: r() * 6.28 });
  fx((c, t) => {
    if (t < t0 || t > t1 + life * 1.3) return;
    c.globalCompositeOperation = 'lighter';
    c.shadowColor = `rgb(${color})`; c.shadowBlur = glow;
    for (const p of P) {
      const a = t - p.b; if (a < 0 || a > p.l) continue;
      const k = a / p.l, px = p.x + p.vx * a, py = p.y + p.vy * a + 0.5 * g * a * a, al = (1 - k) * (k < 0.1 ? k / 0.1 : 1);
      c.fillStyle = `rgba(${color},${al})`;
      if (shape === 'drop') { const sp = Math.min(3.2, 1 + (p.vy + g * a) / 500); c.beginPath(); c.ellipse(px, py, p.s, p.s * sp, 0, 0, Math.PI * 2); c.fill(); }
      else if (shape === 'text') { c.font = `800 ${p.s * 4}px Inter`; c.textAlign = 'center'; c.fillText(text, px, py); }
      else { c.beginPath(); c.arc(px, py, p.s * (1 - k * 0.6), 0, Math.PI * 2); c.fill(); }
    }
  });
}

// ---------- captions ----------
const capEl = document.getElementById('captions');
const CHUNKS = [];
(function buildChunks() {
  for (const l of T.lines) {
    let cur = [];
    const flush = () => { if (cur.length) { CHUNKS.push({ words: cur, line: l }); cur = []; } };
    for (const c of l.caps) {
      cur.push(c);
      const len = cur.map(x => x.text).join(' ').length;
      if (/[.,?!:]$/.test(c.text) || cur.length >= 3 || len >= 14) flush();
    }
    flush();
  }
  for (const ch of CHUNKS) ch.s = ch.words[0].s - 0.06;
  for (let i = 0; i < CHUNKS.length; i++) {
    const ch = CHUNKS[i], nx = CHUNKS[i + 1], last = ch.words[ch.words.length - 1];
    const hold = last.e + 0.45;
    ch.e = nx ? Math.min(nx.s, Math.max(hold, nx.line === ch.line ? nx.s : hold)) : last.e + 0.8;
  }
})();
let capIdx = -2, capSpans = [];
function drawCaptions(t) {
  let i = -1;
  for (let k = 0; k < CHUNKS.length; k++) if (t >= CHUNKS[k].s && t < CHUNKS[k].e) { i = k; break; }
  if (i !== capIdx) {
    capEl.innerHTML = ''; capSpans = []; capIdx = i;
    if (i >= 0) for (const wd of CHUNKS[i].words) capSpans.push([el('span', 'cw ' + (wd.style || ''), capEl, wd.text.replace(/</g, '&lt;')), wd]);
  }
  capEl.style.top = env.capY + 'px';
  if (i < 0) return;
  const ch = CHUNKS[i], exitK = clamp01((ch.e - t) / 0.08);
  for (const [sp, wd] of capSpans) {
    const p = clamp01((t - (wd.s - 0.06)) / 0.14), e = E_BACK(p), on = t >= wd.s - 0.06 && t < wd.e + 0.06;
    const sc = (0.55 + 0.45 * e) * (on && wd.style ? 1.07 : 1);
    sp.style.opacity = (p * exitK).toFixed(3);
    sp.style.transform = `translateY(${((1 - p) * 22).toFixed(1)}px) scale(${sc.toFixed(3)})`;
  }
}

// ---------- grain ----------
const grainC = document.getElementById('grain'), gctx = grainC.getContext('2d');
const GRAIN = Array.from({ length: 6 }, (_, f) => { const r = mulberry32(100 + f), im = gctx.createImageData(540, 960); for (let i = 0; i < im.data.length; i += 4) { const v = r() * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } return im; });

const flashEl = document.getElementById('flash');
const flashO = { a: 0 };
function flash(t, a = 0.5, dur = 0.3, color = '#ffffff') {
  tl.set(flashEl, { backgroundColor: color }, t);
  tl.fromTo(flashO, { a }, { a: 0, duration: dur, ease: 'power2.out', immediateRender: false }, t);
}
const barEl = document.getElementById('bar');

// ---------- main entry ----------
window.seek = function (t) {
  tl.seek(t, false);
  for (const s of SCENES) s.el.style.visibility = t >= s.t0 && t < s.t1 ? 'visible' : 'hidden';
  for (const f of DYN) f(t);
  applyCam(t);
  drawBG(t);
  drawFX(t);
  drawCaptions(t);
  gctx.putImageData(GRAIN[Math.floor(t * FPS) % GRAIN.length], 0, 0);
  flashEl.style.opacity = flashO.a;
  barEl.style.width = (clamp01(t / DUR) * 100).toFixed(2) + '%';
};
window.getCues = () => ({ duration: DUR, sfx: SFX.slice().sort((a, b) => a.t - b.t), music: MUSIC.slice().sort((a, b) => a.t - b.t) });

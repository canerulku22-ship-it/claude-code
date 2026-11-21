// Miami kit: neon text and tubes, synthwave sky / sun / grid, palms, flamingos, art-deco Ocean Drive, iguanas,
// the coffee window, hurricanes, stone crab, Cuban sandwiches, a snowy New York. Flat shapes with a dark outline.
import { c, PAL, PI, W, H, rr, fs, circle, ellipse, txt, withT, lerp, clamp01, mulberry32 } from './core.js';

export const NEON = { pink: '#ff2a6d', hot: '#ff4fa3', teal: '#05d9e8', yellow: '#ffd319', orange: '#ff901f', violet: '#b967ff', green: '#39ff88', night: '#0d0221', deep: '#1a0638' };
const TINT = { '#ff2a6d': '#ffd9e6', '#ff4fa3': '#ffe3f1', '#05d9e8': '#dcfcff', '#ffd319': '#fff7cf', '#ff901f': '#ffe6c9', '#b967ff': '#f1e3ff', '#39ff88': '#ddffe9' };
const tint = col => TINT[col] || '#ffffff';
const CTX = c;

// a neon tube switching on: flickers for `d` seconds after t0, then holds (with a faint hum)
export function flick(t, t0, seed = 0, d = 0.45) {
  if (t < t0) return 0; const u = t - t0; if (u > d) return 0.94 + 0.06 * Math.sin(t * 37 + seed);
  return mulberry32(Math.floor(u * 26) * 31 + seed * 7 + 3)() > 0.42 ? 1 : 0.12;
}
// glowing script / display text
export function neonText(s, x, y, { size = 80, col = NEON.pink, font = 'Pacifico', glow = 1, align = 'center', alpha = 1, outline = true } = {}) {
  if (alpha <= 0.01) return;
  c.save(); c.globalAlpha *= Math.min(1, alpha); c.font = `400 ${size}px "${font}"`; c.textAlign = align; c.textBaseline = 'middle'; c.lineJoin = 'round';
  if (outline) { c.strokeStyle = 'rgba(13,2,33,.9)'; c.lineWidth = size * 0.2; c.strokeText(s, x, y); }
  c.shadowColor = col; c.strokeStyle = col; c.fillStyle = col;
  c.shadowBlur = size * 0.45 * glow; c.lineWidth = size * 0.07; c.strokeText(s, x, y);
  c.shadowBlur = size * 0.15 * glow; c.fillText(s, x, y);
  c.shadowBlur = 0; c.globalAlpha *= 0.75; c.fillStyle = tint(col); c.fillText(s, x, y);
  c.restore();
}
// glow-stroke the current path like a neon tube (layered strokes, no blur filter → fast and deterministic)
export function neonStroke(col, lw = 6, glow = 1, c_ = null) {
  const c = c_ || CTX; const ga = c.globalAlpha; c.save(); c.lineJoin = 'round'; c.lineCap = 'round'; c.strokeStyle = col;
  for (const [m, a] of [[5.5, 0.07], [3.2, 0.14], [1.9, 0.35]]) { c.globalAlpha = ga * a * glow; c.lineWidth = lw * m; c.stroke(); }
  c.globalAlpha = ga; c.lineWidth = lw; c.stroke(); c.strokeStyle = tint(col); c.lineWidth = lw * 0.4; c.stroke();
  c.restore();
}

// ---------------------------------------------------------------- synthwave backdrop
export function stars(t, yMax = 900, n = 70, seed = 9) {
  const R = mulberry32(seed);
  for (let i = 0; i < n; i++) { const x = R() * W, y = R() * yMax, r = 1.5 + R() * 3, k = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * (2 + R() * 3) + i)); c.fillStyle = `rgba(255,255,255,${k})`; c.beginPath(); c.arc(x, y, r, 0, PI * 2); c.fill(); }
}
export function retroSun(x, y, r, { glow = 1 } = {}) {
  const gl = c.createRadialGradient(x, y, r * 0.8, x, y, r * 1.7); gl.addColorStop(0, `rgba(255,60,140,${0.45 * glow})`); gl.addColorStop(1, 'rgba(255,60,140,0)');
  c.fillStyle = gl; c.fillRect(x - r * 1.8, y - r * 1.8, r * 3.6, r * 3.6);
  c.save(); c.beginPath(); c.arc(x, y, r, 0, PI * 2); c.clip();
  const g = c.createLinearGradient(0, y - r, 0, y + r); g.addColorStop(0, '#ffe45e'); g.addColorStop(0.45, '#ff8a3d'); g.addColorStop(0.75, '#ff2a6d'); g.addColorStop(1, '#c2187a');
  c.beginPath(); c.rect(x - r, y - r, 2 * r, r * 1.05);
  for (let i = 0, yy = y + r * 0.05; i < 9; i++) { const gap = 4 + i * 3.2, bh = r * 0.11 - i * 1.2; yy += gap; c.rect(x - r, yy, 2 * r, Math.max(4, bh)); yy += Math.max(4, bh); }
  c.fillStyle = g; c.fill(); c.restore();
}
export function synthGrid(horizon, t, { col = '#ff2a6d', speed = 1, alpha = 1 } = {}) {
  const g = c.createLinearGradient(0, horizon, 0, H); g.addColorStop(0, '#2a0845'); g.addColorStop(1, '#0d0221');
  c.fillStyle = g; c.fillRect(0, horizon, W, H - horizon);
  c.save(); c.globalAlpha = alpha; c.beginPath();
  for (let i = -14; i <= 14; i++) { c.moveTo(W / 2 + i * 26, horizon); c.lineTo(W / 2 + i * 260, H + 40); }
  const ph = (t * speed * 0.9) % 1;
  for (let j = 0; j < 12; j++) { const z = (j + ph) / 12, y = horizon + (H - horizon) * z * z; c.moveTo(0, y); c.lineTo(W, y); }
  neonStroke(col, 3, 0.8); c.restore();
  const hg = c.createLinearGradient(0, horizon - 40, 0, horizon + 30); hg.addColorStop(0, 'rgba(255,42,109,0)'); hg.addColorStop(0.6, 'rgba(255,42,109,.55)'); hg.addColorStop(1, 'rgba(255,42,109,0)');
  c.fillStyle = hg; c.fillRect(0, horizon - 40, W, 70);
}
export function synthSky(horizon = H, top = '#0d0221', mid = '#3a0b5e', bot = '#a01a6e') {
  const g = c.createLinearGradient(0, 0, 0, horizon); g.addColorStop(0, top); g.addColorStop(0.6, mid); g.addColorStop(1, bot); c.fillStyle = g; c.fillRect(0, 0, W, horizon);
}
// warm Miami sunset sky and sea
export function sunsetSky(horizon = 1150, { top = '#4b2a8a', mid = '#ff6f91', bot = '#ffc46b' } = {}) {
  const g = c.createLinearGradient(0, 0, 0, horizon); g.addColorStop(0, top); g.addColorStop(0.55, mid); g.addColorStop(1, bot); c.fillStyle = g; c.fillRect(0, 0, W, horizon);
}
export function sea(y0, y1, t, { col = '#2bb3c0', dark = '#16808f' } = {}) {
  const g = c.createLinearGradient(0, y0, 0, y1); g.addColorStop(0, col); g.addColorStop(1, dark); c.fillStyle = g; c.fillRect(0, y0, W, y1 - y0);
  c.fillStyle = 'rgba(255,255,255,.35)'; for (let i = 0; i < 10; i++) { const y = y0 + 16 + (i % 5) * (y1 - y0) / 5.5, x = ((i * 211 + t * 30 * (1 + (i % 3) * 0.3)) % (W + 200)) - 100; c.fillRect(x, y, 70 + (i % 3) * 30, 6); }
}

// ---------------------------------------------------------------- nature
// palm tree: (x, y) = base of trunk. lean > 0 leans right. sway animates the fronds.
export function palm(x, y, s = 1, t = 0, { lean = 0.18, h = 560, dark = false, wind = 0 } = {}) {
  const trunk = dark ? '#2a0f3d' : '#a8743f', leaf = dark ? '#1c0a2e' : '#3fa34d', leaf2 = dark ? '#1c0a2e' : '#2e8a3d', ink = dark ? '#12051f' : PAL.ink;
  c.save(); c.translate(x, y); c.scale(s, s);
  const tx = lean * h + wind * 60, ty = -h;
  const P = u => [tx * u * u, ty * u];
  c.lineCap = 'round';
  for (let i = 0; i < 12; i++) { const u0 = i / 12, u1 = (i + 1) / 12, [x0, y0] = P(u0), [x1, y1] = P(u1), wd = 46 - i * 2; c.strokeStyle = ink; c.lineWidth = wd + 10; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke(); c.strokeStyle = i % 2 ? trunk : (dark ? '#33134a' : '#b98450'); c.lineWidth = wd; c.stroke(); }
  const sw = Math.sin(t * 1.6 + x * 0.01) * 0.07 + wind * 0.5;
  if (!dark) { circle(tx - 14, ty + 18, 16, '#7a5230', ink, 5); circle(tx + 14, ty + 20, 16, '#7a5230', ink, 5); }
  for (let i = 0; i < 9; i++) {
    const a = -PI + i * PI / 8 + sw + (i % 2 ? 0.06 : -0.06), L = 250 + (i % 3) * 40, droop = 0.55 + (i % 2) * 0.2;
    const pts = [], N = 10;
    for (let k = 0; k <= N; k++) { const u = k / N; pts.push([tx + Math.cos(a) * L * u, ty + Math.sin(a) * L * u + droop * L * u * u * Math.abs(Math.cos(a)) * 0.9 + L * u * u * 0.25]); }
    const edge = sgn => pts.map(([px, py], k) => { const u = k / N, q = pts[Math.min(N, k + 1)], p0 = pts[Math.max(0, k - 1)], dx = q[0] - p0[0], dy = q[1] - p0[1], m = Math.hypot(dx, dy) || 1, wd = 34 * Math.sin(PI * Math.min(1, u * 1.15)) * (1 - u * 0.35); return [px - dy / m * wd * sgn, py + dx / m * wd * sgn]; });
    const A = edge(1), B = edge(-1).reverse();
    c.beginPath(); A.concat(B).forEach(([px, py], k) => k ? c.lineTo(px, py) : c.moveTo(px, py)); c.closePath(); fs(i % 2 ? leaf : leaf2, ink, 5);
  }
  c.restore();
}
export function flamingo(x, y, s, t = 0, flip = false) {
  const f = Math.sin(t * 8 + x * 0.01);
  c.save(); c.translate(x, y); c.scale(s * (flip ? -1 : 1), s);
  c.strokeStyle = PAL.ink; c.lineCap = 'round';
  c.lineWidth = 9; c.beginPath(); c.moveTo(-40, 6); c.lineTo(-150, 18); c.stroke(); c.strokeStyle = '#ff7eb6'; c.lineWidth = 4; c.stroke();
  c.strokeStyle = PAL.ink; c.lineWidth = 16; c.beginPath(); c.moveTo(40, -6); c.quadraticCurveTo(100, -20, 130, -8); c.stroke(); c.strokeStyle = '#ff7eb6'; c.lineWidth = 9; c.stroke();
  circle(138, -8, 13, '#ff7eb6', PAL.ink, 4); c.beginPath(); c.moveTo(146, -10); c.lineTo(172, 0); c.lineTo(146, 2); c.closePath(); fs('#2b2622', PAL.ink, 3);
  for (const sgn of [-1, 1]) { c.beginPath(); c.moveTo(-20, 0); c.quadraticCurveTo(0, -70 * f * sgn - 20 * sgn, 30, sgn * -10); c.lineTo(10, 4); c.closePath(); fs(sgn > 0 ? '#ff4f9a' : '#ff8fc4', PAL.ink, 4); }
  ellipse(0, 0, 50, 20, '#ff7eb6', PAL.ink, 5);
  c.restore();
}
// green iguana, side view facing right. frozen = stiff, upside-down-ready, frosty.
export function iguana(x, y, s, { rot = 0, frozen = false, flip = false, t = 0, ph = 0 } = {}) {
  const body = frozen ? '#8fc6a0' : '#5fb33c', dark = frozen ? '#5f9a7a' : '#3e8a26';
  c.save(); c.translate(x, y); c.rotate(rot); c.scale(s * (flip ? -1 : 1), s);
  const wag = frozen ? 0 : Math.sin(t * 3 + ph) * 12;
  // tail
  c.lineCap = 'round'; const tail = () => { c.beginPath(); c.moveTo(-60, 2); c.quadraticCurveTo(-170, 16 + wag, -250, 2 + wag); c.quadraticCurveTo(-300, -6 + wag, -320, -34 + wag * 1.4); };
  tail(); c.strokeStyle = PAL.ink; c.lineWidth = 30; c.stroke(); tail(); c.strokeStyle = body; c.lineWidth = 20; c.stroke();
  c.strokeStyle = dark; c.lineWidth = 20; c.setLineDash([12, 22]); tail(); c.stroke(); c.setLineDash([]);
  // legs
  const legs = frozen ? [[55, 18, -2.2], [-45, 18, -2.4], [70, 18, -1.6], [-30, 18, -1.8]] : [[55, 18, 0.5 + Math.sin(t * 6 + ph) * 0.1], [-45, 18, -0.4], [70, 18, 0.2], [-30, 18, -0.1]];
  for (const [lx, ly, a] of legs) { c.save(); c.translate(lx, ly); c.rotate(frozen ? a + PI : a); c.strokeStyle = PAL.ink; c.lineWidth = 18; c.beginPath(); c.moveTo(0, 0); c.lineTo(0, 46); c.stroke(); c.strokeStyle = body; c.lineWidth = 10; c.stroke(); c.lineWidth = 5; c.strokeStyle = PAL.ink; for (const d of [-10, 0, 10]) { c.beginPath(); c.moveTo(0, 46); c.lineTo(d, 60); c.stroke(); } c.restore(); }
  // crest spikes
  c.fillStyle = dark; c.strokeStyle = PAL.ink; c.lineWidth = 3;
  for (let i = 0; i < 9; i++) { const sx = 95 - i * 18, sy = -28 - (i < 3 ? 6 : 0) + i * 1.5; c.beginPath(); c.moveTo(sx - 7, sy + 6); c.lineTo(sx, sy - 14); c.lineTo(sx + 7, sy + 6); c.closePath(); c.fill(); c.stroke(); }
  ellipse(0, 0, 90, 36, body, PAL.ink, 6);
  c.fillStyle = dark; for (let i = 0; i < 4; i++) { c.beginPath(); c.ellipse(-50 + i * 30, -4, 7, 22, 0.2, 0, PI * 2); c.fill(); }
  // dewlap + head
  c.beginPath(); c.moveTo(92, 0); c.quadraticCurveTo(100, 46, 130, 8); fs(frozen ? '#d9e6c4' : '#e3c34a', PAL.ink, 5);
  c.beginPath(); c.moveTo(70, -20); c.quadraticCurveTo(100, -46, 140, -26); c.quadraticCurveTo(162, -16, 150, 2); c.quadraticCurveTo(110, 14, 72, 10); c.closePath(); fs(body, PAL.ink, 6);
  circle(120, -18, 9, '#d9a24a', PAL.ink, 3);
  if (frozen) { c.strokeStyle = PAL.ink; c.lineWidth = 4; c.beginPath(); c.moveTo(112, -32); c.lineTo(124, -22); c.moveTo(124, -32); c.lineTo(112, -22); c.stroke(); }
  else { circle(118, -27, 8, '#fff6cf', PAL.ink, 3); circle(120, -27, 3.5, PAL.ink, null, 0); }
  if (frozen) { c.fillStyle = 'rgba(210,240,255,.45)'; c.beginPath(); c.ellipse(0, 0, 92, 38, 0, 0, PI * 2); c.fill(); c.fillStyle = '#e8f8ff'; for (let i = 0; i < 5; i++) { c.beginPath(); c.moveTo(-50 + i * 28, 30); c.lineTo(-44 + i * 28, 52 + (i % 2) * 10); c.lineTo(-38 + i * 28, 30); c.fill(); } }
  c.restore();
}

// ---------------------------------------------------------------- Ocean Drive art deco
const SIGNS = ['SOL', 'CORAL', 'PALMS', 'OCEAN', 'MAMBO'];
const DECO = [['#f9b4cf', NEON.teal], ['#a8ecd2', NEON.pink], ['#ffe9a3', NEON.violet], ['#cdb9f6', NEON.yellow], ['#9fe2ef', NEON.hot]];
export function decoHotel(x, base, wd, ht, i, t, { night = 0, sign = true, signOn = 1 } = {}) {
  const [col, ncol] = DECO[i % 5], ink = PAL.ink;
  // stepped parapet + body
  rr(x + wd * 0.3, base - ht - 70, wd * 0.4, 80, 8); fs(col, ink, 6);
  rr(x + wd * 0.15, base - ht - 34, wd * 0.7, 44, 8); fs(col, ink, 6);
  rr(x, base - ht, wd, ht, 14); fs(col, ink, 6);
  // windows with "eyebrow" ledges
  const rows = Math.floor((ht - 150) / 96), R = mulberry32(i * 13 + 1);
  for (let r = 0; r < rows; r++) {
    const y = base - ht + 40 + r * 96;
    c.fillStyle = '#ffffff'; c.fillRect(x - 8, y - 14, wd + 16, 12); c.strokeStyle = ink; c.lineWidth = 4; c.strokeRect(x - 8, y - 14, wd + 16, 12);
    for (let k = 0; k < 3; k++) { const wx = x + 18 + k * (wd - 36) / 3, ww = (wd - 36) / 3 - 14, lit = night > 0 && R() > 0.35 && Math.sin(t * 0.7 + r * 3 + k * 1.7 + i) > -0.6; rr(wx, y + 8, ww, 50, 6); fs(lit ? `rgba(255,214,120,${0.6 + 0.4 * night})` : '#7cc6d6', ink, 4); }
  }
  // porthole + awning + door
  circle(x + wd / 2, base - 150, 22, night ? '#ffd27a' : '#7cc6d6', ink, 5);
  c.save(); rr(x + 10, base - 110, wd - 20, 36, 6); c.clip(); for (let k = 0; k < 10; k++) { c.fillStyle = k % 2 ? '#ffffff' : ncol; c.fillRect(x + 10 + k * (wd - 20) / 10, base - 110, (wd - 20) / 10 + 1, 36); } c.restore(); rr(x + 10, base - 110, wd - 20, 36, 6); fs(null, ink, 5);
  rr(x + wd / 2 - 30, base - 70, 60, 70, 6); fs('#3a2e4f', ink, 5);
  // vertical fin with a neon sign
  if (sign) {
    const fx = x + wd / 2 - 30, word = SIGNS[i % 5], fh = word.length * 50 + 30;
    rr(fx, base - ht - 100 - fh * 0.15, 60, fh, 10); fs('#fbf6ea', ink, 6);
    const a = signOn * (night > 0 ? 1 : 0.85);
    for (let k = 0; k < word.length; k++) neonText(word[k], fx + 30, base - ht - 100 - fh * 0.15 + 40 + k * 50, { size: 42, col: ncol, font: 'Lilita One', glow: 0.6 + night * 0.6, alpha: a, outline: false });
  }
}
// a row of Ocean Drive hotels with downtown towers behind. rise(i) → 0..1 per building (pop-up animation)
export function decoStrip(base, t, { rise = () => 1, night = 0, signOn = () => 1, towers = true } = {}) {
  const up = (i, fn) => { const k = rise(i); if (k <= 0.001) return; c.save(); c.translate(0, (1 - k) * 900); fn(); c.restore(); };
  if (towers) up(9, () => { const tw = [[60, 560, '#5f7fb8'], [210, 700, '#6d8fc9'], [380, 620, '#506ea6'], [600, 760, '#6787c2'], [800, 600, '#5a79b3'], [940, 680, '#6d8fc9']]; for (const [x, h, col] of tw) { rr(x, base - 300 - h, 120, h + 300, 6); fs(col, PAL.ink, 5); c.fillStyle = night ? 'rgba(255,220,140,.7)' : 'rgba(255,255,255,.35)'; for (let y = base - 280 - h; y < base - 320; y += 46) c.fillRect(x + 14, y, 92, 14); } });
  const xs = [[-30, 230, 430], [200, 210, 520], [410, 240, 470], [650, 220, 540], [870, 240, 450]];
  xs.forEach(([x, wd, ht], i) => up(i, () => decoHotel(x, base, wd, ht, i, t, { night, signOn: signOn(i) })));
}
// classic convertible (generic), facing right
export function convertible(x, y, s, col = '#ff4fa3', t = 0, rider = null) {
  withT(x, y, s, 0, () => {
    if (rider) rider(t);
    c.beginPath(); c.moveTo(-230, -10); c.lineTo(-230, -70); c.quadraticCurveTo(-200, -96, -120, -96); c.lineTo(40, -96); c.lineTo(90, -130); c.lineTo(110, -130); c.lineTo(100, -96); c.lineTo(200, -90); c.quadraticCurveTo(240, -80, 240, -40); c.lineTo(240, -10); c.closePath(); fs(col, PAL.ink, 7);
    c.fillStyle = 'rgba(255,255,255,.55)'; c.fillRect(-200, -60, 400, 8);
    for (const wx of [-140, 150]) { circle(wx, -6, 40, '#2b2622', PAL.ink, 6); circle(wx, -6, 18, '#e8e8e8', null, 0); }
    circle(232, -64, 9, '#fff6cf', PAL.ink, 4);
  });
}

// ---------------------------------------------------------------- coffee
export function cafecito(x, y, s, t = 0, steam = true) {
  withT(x, y, s, 0, () => {
    ellipse(0, 4, 46, 12, '#ffffff', PAL.ink, 5);
    c.beginPath(); c.moveTo(-28, -40); c.lineTo(28, -40); c.quadraticCurveTo(26, 0, 0, 2); c.quadraticCurveTo(-26, 0, -28, -40); c.closePath(); fs('#ffffff', PAL.ink, 5);
    c.strokeStyle = PAL.ink; c.lineWidth = 6; c.beginPath(); c.arc(30, -24, 11, -PI / 2, PI / 2); c.stroke();
    ellipse(0, -40, 28, 7, '#5a3218', PAL.ink, 4);
    if (steam) { c.strokeStyle = 'rgba(255,255,255,.9)'; c.lineWidth = 5; for (let i = 0; i < 2; i++) { c.beginPath(); for (let k = 0; k < 8; k++) c.lineTo(-10 + i * 20 + Math.sin(t * 5 + k * 0.8 + i) * 6, -54 - k * 8); c.stroke(); } }
  });
}
// walk-up coffee window in a pastel wall; `inside` draws whoever is serving (clipped to the window)
export function ventanita(t, { wall = '#9fe2ef', inside = null, signOn = 1, horizon = 1240 } = {}) {
  c.fillStyle = wall; c.fillRect(0, 0, W, horizon); c.fillStyle = 'rgba(255,255,255,.18)'; for (let y = 40; y < horizon; y += 120) c.fillRect(0, y, W, 8);
  c.fillStyle = '#d9c7a8'; c.fillRect(0, horizon, W, H - horizon); c.fillStyle = 'rgba(0,0,0,.08)'; for (let x = 0; x < W; x += 120) c.fillRect(x, horizon, 6, H - horizon);
  // window
  rr(250, 560, 580, 470, 16); fs('#3a2e4f', PAL.ink, 9);
  c.save(); rr(262, 572, 556, 446, 10); c.clip(); c.fillStyle = '#ffe1b8'; c.fillRect(262, 572, 556, 446); c.fillStyle = '#e8c79a'; for (let i = 0; i < 4; i++) c.fillRect(300 + i * 130, 610, 90, 18); if (inside) inside(t); c.restore();
  rr(220, 1010, 640, 50, 10); fs('#c9a46a', PAL.ink, 7);
  // striped awning
  c.save(); c.beginPath(); c.moveTo(210, 540); c.lineTo(870, 540); c.lineTo(900, 440); c.lineTo(180, 440); c.closePath(); c.clip(); for (let k = 0; k < 12; k++) { c.fillStyle = k % 2 ? '#ffffff' : '#ff4fa3'; c.fillRect(180 + k * 60, 440, 60, 100); } c.restore();
  c.beginPath(); c.moveTo(210, 540); c.lineTo(870, 540); c.lineTo(900, 440); c.lineTo(180, 440); c.closePath(); fs(null, PAL.ink, 7);
  for (let k = 0; k < 12; k++) { c.beginPath(); c.arc(210 + 27.5 + k * 55, 540, 27.5, 0, PI); fs(k % 2 ? '#ffffff' : '#ff4fa3', PAL.ink, 5); }
  // neon sign
  rr(270, 250, 540, 150, 24); fs('#2a0f3d', PAL.ink, 8);
  neonText('Cafecito', W / 2, 322, { size: 92, col: NEON.yellow, alpha: signOn, outline: false });
}
export function rocketCup(x, y, s, t = 0, rot = 0) {
  withT(x, y, s, rot, () => {
    const fl = 1 + 0.25 * Math.sin(t * 40);
    c.beginPath(); c.moveTo(-40, 80); c.quadraticCurveTo(0, 80 + 190 * fl, 40, 80); c.closePath(); c.fillStyle = '#ffd319'; c.fill();
    c.beginPath(); c.moveTo(-24, 80); c.quadraticCurveTo(0, 80 + 110 * fl, 24, 80); c.closePath(); c.fillStyle = '#ffffff'; c.fill();
    for (const sx of [-1, 1]) { c.beginPath(); c.moveTo(sx * 60, 20); c.lineTo(sx * 110, 100); c.lineTo(sx * 50, 80); c.closePath(); fs('#ff2a6d', PAL.ink, 5); }
    c.beginPath(); c.moveTo(-70, -60); c.lineTo(70, -60); c.quadraticCurveTo(66, 90, 0, 92); c.quadraticCurveTo(-66, 90, -70, -60); c.closePath(); fs('#ffffff', PAL.ink, 7);
    ellipse(0, -60, 70, 16, '#5a3218', PAL.ink, 6);
    txt('CAFÉ', 0, 10, { font: 'Lilita One', weight: 400, size: 40, color: '#ff2a6d' });
  });
}

// ---------------------------------------------------------------- weather
export function hurricane(x, y, r, t, alpha = 1) {
  c.save(); c.globalAlpha *= alpha; c.translate(x, y); c.rotate(-t * 1.6); c.lineCap = 'round';
  for (let j = 0; j < 5; j++) {
    c.beginPath(); for (let k = 0; k <= 40; k++) { const u = k / 40, th = u * PI * 2.1 + j * PI * 2 / 5, rad = r * (0.12 + 0.88 * u); c.lineTo(Math.cos(th) * rad, Math.sin(th) * rad); }
    c.strokeStyle = 'rgba(255,255,255,.22)'; c.lineWidth = r * 0.28; c.stroke(); c.strokeStyle = 'rgba(255,255,255,.75)'; c.lineWidth = r * 0.1; c.stroke();
  }
  circle(0, 0, r * 0.1, 'rgba(20,10,40,.9)', 'rgba(255,255,255,.9)', 4);
  c.restore();
}
export function rain(t, { n = 70, angle = 0.3, col = 'rgba(200,220,255,.6)', seed = 3, speed = 1900 } = {}) {
  const R = mulberry32(seed), dx = Math.tan(angle); c.strokeStyle = col; c.lineWidth = 4; c.lineCap = 'round'; c.beginPath();
  for (let i = 0; i < n; i++) { const x0 = R() * (W + 800), y0 = R() * H, y = ((y0 + t * speed * (0.8 + R() * 0.4)) % (H + 100)) - 50, x = ((x0 + y * dx) % (W + 800)) - 400; c.moveTo(x, y); c.lineTo(x + 60 * dx, y + 60); }
  c.stroke();
}
export function snow(t, { n = 80, seed = 5, speed = 120 } = {}) {
  const R = mulberry32(seed); c.fillStyle = 'rgba(255,255,255,.95)';
  for (let i = 0; i < n; i++) { const x0 = R() * W, y0 = R() * H, r = 4 + R() * 7, y = (y0 + t * speed * (0.7 + R() * 0.6)) % (H + 40) - 20, x = x0 + Math.sin(t * 1.5 + i) * 26; c.beginPath(); c.arc(x, y, r, 0, PI * 2); c.fill(); }
}
export function boardedWindow(x, y, wd, ht) {
  rr(x, y, wd, ht, 10); fs('#7f8fa6', PAL.ink, 7);
  c.save(); rr(x, y, wd, ht, 10); c.clip(); c.fillStyle = '#c8a26b'; for (let i = 0; i < 4; i++) { c.fillRect(x - 20, y + 10 + i * ht / 4, wd + 40, ht / 4 - 12); } c.restore();
  c.strokeStyle = PAL.ink; c.lineWidth = 4; for (let i = 0; i < 4; i++) c.strokeRect(x - 2, y + 10 + i * ht / 4, wd + 4, ht / 4 - 12);
  c.strokeStyle = '#ff2a6d'; c.lineWidth = 14; c.lineCap = 'butt'; c.beginPath(); c.moveTo(x + 20, y + 20); c.lineTo(x + wd - 20, y + ht - 20); c.moveTo(x + wd - 20, y + 20); c.lineTo(x + 20, y + ht - 20); c.stroke();
}
export function thermometer(x, y, s, frac, label, col = '#e63946') {
  withT(x, y, s, 0, () => {
    rr(-34, -420, 68, 420, 34); fs('#ffffff', PAL.ink, 7); circle(0, 30, 62, col, PAL.ink, 7);
    rr(-16, -400 + 380 * (1 - frac), 32, 400 - 380 * (1 - frac) + 20, 16); c.fillStyle = col; c.fill();
    c.strokeStyle = PAL.ink; c.lineWidth = 4; for (let i = 0; i < 8; i++) { c.beginPath(); c.moveTo(34, -380 + i * 48); c.lineTo(54, -380 + i * 48); c.stroke(); }
    if (label) txt(label, 0, 30, { font: 'Lilita One', weight: 400, size: 40, color: '#ffffff' });
  });
}

// ---------------------------------------------------------------- food
function claw(rot) {
  c.save(); c.rotate(rot);
  c.beginPath(); c.moveTo(0, -24); c.quadraticCurveTo(90, -50, 150, -12); c.lineTo(110, -4); c.quadraticCurveTo(60, 6, 0, 24); c.closePath(); fs('#f2b183', PAL.ink, 5);
  c.beginPath(); c.moveTo(150, -12); c.quadraticCurveTo(190, -2, 196, 26); c.quadraticCurveTo(160, 6, 110, -4); c.closePath(); fs('#2b2622', PAL.ink, 4);
  c.beginPath(); c.moveTo(108, 6); c.quadraticCurveTo(150, 30, 160, 52); c.quadraticCurveTo(120, 40, 92, 14); c.closePath(); fs('#2b2622', PAL.ink, 4);
  c.fillStyle = '#e8743b'; c.beginPath(); c.ellipse(50, -10, 34, 12, -0.1, 0, PI * 2); c.fill();
  c.restore();
}
export function crabPlate(x, y, s) {
  withT(x, y, s, 0, () => {
    ellipse(0, 10, 300, 90, '#ffffff', PAL.ink, 7); ellipse(0, 6, 240, 66, '#f4f4f4', 'rgba(0,0,0,.15)', 3);
    [[-160, -10, -0.2], [-60, 20, 0.15], [40, -20, -0.35], [-110, -40, 0.3], [90, 16, 0.1]].forEach(([cx, cy, r]) => { c.save(); c.translate(cx, cy); claw(r); c.restore(); });
    c.beginPath(); c.moveTo(200, -20); c.arc(200, -20, 46, PI * 0.1, PI * 0.9); c.closePath(); fs('#ffe066', PAL.ink, 5);
    ellipse(-230, -30, 44, 20, '#f2e2a0', PAL.ink, 5);
  });
}
export function crab(x, y, s, t = 0, { angry = true } = {}) {
  withT(x, y, s, 0, () => {
    c.strokeStyle = PAL.ink; c.lineWidth = 10; c.lineCap = 'round';
    for (const sx of [-1, 1]) for (let i = 0; i < 3; i++) { const a = Math.sin(t * 10 + i + (sx > 0 ? 1 : 0)) * 0.2; c.beginPath(); c.moveTo(sx * 60, 10 + i * 14); c.lineTo(sx * (110 + i * 6), 40 + i * 16 + a * 30); c.lineTo(sx * (130 + i * 6), 80 + i * 10); c.stroke(); }
    for (const sx of [-1, 1]) { const a = Math.sin(t * 6 + (sx > 0 ? 0 : 1.5)) * 0.25; withT(sx * 90, -40, 1, sx * (0.5 + a), () => { c.strokeStyle = PAL.ink; c.lineWidth = 16; c.beginPath(); c.moveTo(0, 30); c.lineTo(0, -40); c.stroke(); c.strokeStyle = '#e8743b'; c.lineWidth = 9; c.stroke(); c.scale(sx, 1); c.translate(0, -70); c.beginPath(); c.moveTo(-26, 30); c.quadraticCurveTo(-40, -30, 0, -46); c.quadraticCurveTo(30, -40, 20, -14); c.lineTo(0, -10); c.lineTo(10, 20); c.closePath(); fs('#e8743b', PAL.ink, 5); c.beginPath(); c.moveTo(20, -14); c.lineTo(30, -40); c.lineTo(8, -40); c.fillStyle = '#2b2622'; c.fill(); }); }
    ellipse(0, 20, 90, 54, '#e8743b', PAL.ink, 7);
    for (const sx of [-1, 1]) { c.strokeStyle = PAL.ink; c.lineWidth = 6; c.beginPath(); c.moveTo(sx * 22, -20); c.lineTo(sx * 28, -56); c.stroke(); circle(sx * 28, -62, 15, '#ffffff', PAL.ink, 4); circle(sx * 28, -60, 6, PAL.ink, null, 0); if (angry) { c.lineWidth = 7; c.beginPath(); c.moveTo(sx * 44, -86); c.lineTo(sx * 14, -76); c.stroke(); } }
    c.strokeStyle = PAL.ink; c.lineWidth = 5; c.beginPath(); c.arc(0, 40, 16, 1.15 * PI, 1.85 * PI); c.stroke();
  });
}
export function cubano(x, y, s, len = 600, rot = 0) {
  withT(x, y, s, rot, () => {
    const L = len / 2;
    rr(-L, 10, len, 34, 16); fs('#e0a456', PAL.ink, 6);
    c.fillStyle = '#7fb24a'; for (let i = 0; i < len / 70; i++) { c.beginPath(); c.ellipse(-L + 40 + i * 70, 6, 26, 9, 0, 0, PI * 2); c.fill(); }
    rr(-L + 8, -18, len - 16, 22, 8); fs('#ffd84d', PAL.ink, 4);
    rr(-L + 4, -42, len - 8, 26, 8); fs('#f4a3a8', PAL.ink, 4);
    rr(-L + 6, -64, len - 12, 24, 8); fs('#a8683a', PAL.ink, 4);
    rr(-L, -110, len, 50, 22); fs('#eab565', PAL.ink, 6);
    c.strokeStyle = 'rgba(120,70,20,.5)'; c.lineWidth = 5; for (let i = 0; i < len / 50; i++) { c.beginPath(); c.moveTo(-L + 30 + i * 50, -104); c.lineTo(-L + 44 + i * 50, -70); c.stroke(); }
  });
}

// ---------------------------------------------------------------- elsewhere
export function nycSkyline(base, t = 0, { snowCap = true } = {}) {
  const ink = PAL.ink, B = [[-20, 420, '#7b8496'], [120, 560, '#8d96a8'], [270, 380, '#6f7889'], [690, 520, '#8d96a8'], [850, 440, '#7b8496'], [980, 600, '#6f7889']];
  for (const [x, h, col] of B) { rr(x, base - h, 140, h, 4); fs(col, ink, 6); c.fillStyle = 'rgba(255,230,150,.75)'; for (let y = base - h + 30; y < base - 30; y += 48) for (let k = 0; k < 3; k++) if ((x + y + k * 7) % 5 > 1) c.fillRect(x + 18 + k * 40, y, 24, 22); if (snowCap) { rr(x - 4, base - h - 10, 148, 20, 10); fs('#ffffff', ink, 4); } }
  // tall stepped art-deco spire (generic)
  const x = 420, wd = 240;
  rr(x, base - 760, wd, 760, 4); fs('#9aa3b5', ink, 6); rr(x + 30, base - 900, wd - 60, 150, 4); fs('#9aa3b5', ink, 6); rr(x + 70, base - 1000, wd - 140, 110, 4); fs('#a9b2c3', ink, 6);
  c.beginPath(); c.moveTo(x + 100, base - 1000); c.lineTo(x + 120, base - 1180); c.lineTo(x + 140, base - 1000); c.closePath(); fs('#c2cad8', ink, 6);
  c.fillStyle = 'rgba(255,230,150,.75)'; for (let y = base - 730; y < base - 30; y += 50) for (let k = 0; k < 5; k++) if ((y + k * 3) % 7 > 2) c.fillRect(x + 22 + k * 42, y, 26, 22);
  // water tower
  withT(300, base - 380, 1, 0, () => { rr(-40, -110, 80, 90, 8); fs('#8a5a3a', ink, 5); c.beginPath(); c.moveTo(-50, -110); c.lineTo(0, -150); c.lineTo(50, -110); c.closePath(); fs('#6b4423', ink, 5); c.strokeStyle = ink; c.lineWidth = 6; c.beginPath(); c.moveTo(-30, -20); c.lineTo(-36, 0); c.moveTo(30, -20); c.lineTo(36, 0); c.stroke(); });
}
export function taxi(x, y, s, t = 0) {
  withT(x, y, s, 0, () => {
    c.beginPath(); c.moveTo(-220, 0); c.lineTo(-220, -80); c.lineTo(-120, -90); c.lineTo(-80, -170); c.lineTo(90, -170); c.lineTo(140, -90); c.lineTo(220, -80); c.lineTo(220, 0); c.closePath(); fs('#ffcc1a', PAL.ink, 7);
    rr(-60, -210, 120, 40, 8); fs('#ffffff', PAL.ink, 5); txt('TAXI', 0, -190, { font: 'Lilita One', weight: 400, size: 30 });
    c.beginPath(); c.moveTo(-100, -96); c.lineTo(-72, -154); c.lineTo(84, -154); c.lineTo(120, -96); c.closePath(); fs('#cfe8f1', PAL.ink, 5);
    c.fillStyle = '#2b2622'; for (let i = 0; i < 8; i++) c.fillRect(-200 + i * 50, -50, 25, 14);
    for (const wx of [-130, 130]) { circle(wx, 0, 38, '#2b2622', PAL.ink, 6); circle(wx, 0, 15, '#c9ccd1', null, 0); }
  });
}
export function weddingArch(x, base, s, t = 0) {
  withT(x, base, s, 0, () => {
    c.strokeStyle = PAL.ink; c.lineWidth = 34; c.lineCap = 'round'; c.beginPath(); c.moveTo(-240, 0); c.lineTo(-240, -420); c.arc(0, -420, 240, PI, 0); c.lineTo(240, 0); c.stroke();
    c.strokeStyle = '#ffffff'; c.lineWidth = 22; c.stroke();
    const R = mulberry32(8);
    for (let i = 0; i < 26; i++) { const u = i / 25, a = PI + u * PI, px = u < 0.15 ? -240 : u > 0.85 ? 240 : Math.cos(a) * 240, py = u < 0.15 ? -420 + (0.15 - u) * 1400 : u > 0.85 ? -420 + (u - 0.85) * 1400 : -420 + Math.sin(a) * 240; const col = ['#ff4fa3', '#ffd319', '#ff901f', '#ffffff'][i % 4]; for (let j = 0; j < 5; j++) { c.fillStyle = col; c.beginPath(); c.arc(px + Math.cos(j * 1.256) * 12, py + Math.sin(j * 1.256) * 12, 10, 0, PI * 2); c.fill(); } c.fillStyle = '#ffd319'; c.beginPath(); c.arc(px, py, 7, 0, PI * 2); c.fill(); if (R() > 0.5) { c.fillStyle = '#3fa34d'; c.beginPath(); c.ellipse(px + 18, py + 10, 14, 6, 0.6, 0, PI * 2); c.fill(); } }
  });
}
// stars-and-stripes tile in neon colours (for the sweep over the map); drawn once into a repeating pattern
function usFlagTo(g, x, y, w_, h) {
  for (let i = 0; i < 13; i++) { g.fillStyle = i % 2 ? '#fff4fa' : '#ff2a6d'; g.fillRect(x, y + i * h / 13, w_, h / 13 + 0.5); }
  g.fillStyle = '#2a2a9e'; g.fillRect(x, y, w_ * 0.4, h * 7 / 13);
  g.fillStyle = '#ffffff'; for (let r = 0; r < 4; r++) for (let k = 0; k < 5; k++) { g.beginPath(); g.arc(x + w_ * 0.04 + k * w_ * 0.08 + (r % 2) * w_ * 0.04, y + h * 0.07 + r * h * 0.13, h * 0.025, 0, PI * 2); g.fill(); }
  g.strokeStyle = PAL.ink; g.lineWidth = 4; g.strokeRect(x, y, w_, h);
}
let FLAGPAT = null;
export function flagPattern(fw = 190, fh = 100) {
  if (!FLAGPAT) { const cv = document.createElement('canvas'); cv.width = fw; cv.height = fh * 2; const g = cv.getContext('2d'); usFlagTo(g, 0, 0, fw, fh); usFlagTo(g, -fw / 2, fh, fw, fh); usFlagTo(g, fw / 2, fh, fw, fh); FLAGPAT = c.createPattern(cv, 'repeat'); }
  return FLAGPAT;
}
// sunglasses for person({ hat: shades() })
export const shades = (col = '#1d1d1f', frame = '#ff2a6d') => (headY) => {
  for (const sx of [-1, 1]) { rr(sx * 22 - 20, headY - 10, 40, 26, 10); fs(col, frame, 5); }
  c.strokeStyle = frame; c.lineWidth = 5; c.beginPath(); c.moveTo(-3, headY - 2); c.lineTo(3, headY - 2); c.stroke();
  c.fillStyle = 'rgba(255,255,255,.5)'; c.fillRect(-36, headY - 5, 10, 5); c.fillRect(8, headY - 5, 10, 5);
};
export const beanie = (col = '#2b2d42') => (headY, headR) => { c.beginPath(); c.arc(0, headY - 6, headR + 6, PI, 0); c.closePath(); fs(col, PAL.ink, 6); rr(-headR - 8, headY - 22, headR * 2 + 16, 26, 10); fs(col, PAL.ink, 6); circle(0, headY - headR - 14, 14, col, PAL.ink, 5); };
export function sweat(x, y, s, t) { for (let i = 0; i < 5; i++) { const ph = (t * 1.8 + i / 5) % 1, a = -PI / 2 + (i - 2) * 0.5; withT(x + Math.cos(a) * (60 + ph * 120) * s, y + Math.sin(a) * (60 + ph * 120) * s + ph * ph * 160 * s, s * (1 - ph * 0.4), 0, () => { c.globalAlpha = 1 - ph; c.beginPath(); c.moveTo(0, -22); c.quadraticCurveTo(16, 4, 0, 10); c.quadraticCurveTo(-16, 4, 0, -22); fs('#8fd3ff', PAL.ink, 4); c.globalAlpha = 1; }); } }
export function note(x, y, s, col = '#ff4fa3') { withT(x, y, s, 0, () => { c.strokeStyle = PAL.ink; c.lineWidth = 8; c.beginPath(); c.moveTo(18, 0); c.lineTo(18, -70); c.lineTo(50, -58); c.stroke(); ellipse(0, 0, 22, 16, col, PAL.ink, 5, -0.3); }); }

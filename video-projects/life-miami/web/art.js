// Cartoon kit: people (any age / pose / face), props and backdrops, all flat shapes with a dark outline.
import { c, PAL, PI, W, H, rr, fs, circle, ellipse, txt, withT, lerp, clamp01, mulberry32 } from './core.js';

// ---------------------------------------------------------------- people
// (x, y) = between the feet on the ground. s = scale. Arms: la / ra in radians (0 = down, PI/2 = out, PI = up).
export function person(x, y, s, o = {}, t = 0) {
  const kid = o.kid, old = o.old;
  const legH = kid ? 74 : 112, torsoH = kid ? 108 : 150, torsoW = kid ? 104 : 126, headR = kid ? 62 : 64;
  const skin = o.skin || PAL.skin[0], shirt = o.shirt || '#3d7cc9', pants = o.pants || '#3b4a6b';
  const bob = (o.bob ?? 1) * Math.sin(t * 3.2 + (o.ph || 0)) * 3;
  s *= 1.4; c.save(); c.translate(x, y); c.scale(s * (o.flip ? -1 : 1), s);
  const top = -legH - torsoH + bob, headY = top - headR + 18;
  // legs (or a dress)
  const lp = o.walk ? Math.sin(o.walk * PI * 2) * 0.35 : 0;
  if (!o.seated) for (const [sx, a] of [[-1, lp], [1, -lp]]) {
    c.save(); c.translate(sx * 24, -legH + bob); c.rotate(a);
    if (o.shorts) { rr(-18, 0, 36, legH + 4, 12); fs(skin, PAL.ink, 6); rr(-22, -4, 44, legH * 0.5, 12); fs(pants, PAL.ink, 6); }
    else { rr(-20, 0, 40, legH + 4, 12); fs(pants, PAL.ink, 6); }
    ellipse(sx * 8, legH + 2, 30, 15, o.shoes || '#2b2622', PAL.ink, 5);
    c.restore();
  } else { rr(-60, -legH * 0.55 + bob, 120, legH * 0.55, 16); fs(pants, PAL.ink, 6); }
  if (o.dress) { c.beginPath(); c.moveTo(-torsoW / 2 + 6, -legH - 20 + bob); c.lineTo(torsoW / 2 - 6, -legH - 20 + bob); c.lineTo(torsoW / 2 + 34, -legH * 0.25 + bob); c.lineTo(-torsoW / 2 - 34, -legH * 0.25 + bob); c.closePath(); fs(o.dress, PAL.ink, 6); }
  // long hair goes behind the head and shoulders
  if (o.hair === 'long') { rr(-headR - 6, headY - 10, headR * 2 + 12, headR * 2.2, 50); fs(o.hairColor || '#6b3e26', PAL.ink, 6); }
  // torso
  const lean = o.lean || 0;
  c.save(); c.translate(0, -legH + bob); c.rotate(lean); c.translate(0, legH - bob);
  rr(-torsoW / 2, top, torsoW, torsoH + 6, kid ? 26 : 32); fs(shirt, PAL.ink, 6);
  c.save(); rr(-torsoW / 2, top, torsoW, torsoH + 6, kid ? 26 : 32); c.clip();
  if (o.pattern === 'stripes') { c.fillStyle = o.shirt2 || '#ffffff'; for (let i = -3; i < 6; i++) c.fillRect(-torsoW / 2, top + 10 + i * 34, torsoW, 14); }
  if (o.pattern === 'dots') { c.fillStyle = o.shirt2 || '#ffffff'; for (let i = 0; i < 12; i++) { c.beginPath(); c.arc(-torsoW / 2 + 20 + (i % 3) * 42 + (Math.floor(i / 3) % 2) * 20, top + 26 + Math.floor(i / 3) * 34, 7, 0, PI * 2); c.fill(); } }
  if (o.pattern === 'tracksuit') { c.fillStyle = o.shirt2 || '#ffffff'; c.fillRect(-torsoW / 2 + 8, top, 10, torsoH + 6); c.fillRect(torsoW / 2 - 18, top, 10, torsoH + 6); c.fillRect(-5, top + 20, 10, torsoH - 10); }
  if (o.pattern === 'suit') { c.fillStyle = '#ffffff'; c.beginPath(); c.moveTo(-20, top); c.lineTo(20, top); c.lineTo(0, top + 70); c.fill(); c.fillStyle = o.tie || '#c0392b'; c.beginPath(); c.moveTo(-8, top + 8); c.lineTo(8, top + 8); c.lineTo(10, top + 70); c.lineTo(0, top + 84); c.lineTo(-10, top + 70); c.fill(); }
  if (o.pattern === 'kit') { c.fillStyle = o.shirt2 || '#7ec8e3'; c.fillRect(-torsoW / 2, top, torsoW, 26); }
  if (o.pattern === 'floral') for (let i = 0; i < 9; i++) { const fx = -torsoW / 2 + 22 + (i % 3) * 40 + (Math.floor(i / 3) % 2) * 18, fy = top + 28 + Math.floor(i / 3) * 46; c.fillStyle = o.shirt2 || '#ff2a6d'; for (let j = 0; j < 5; j++) { c.beginPath(); c.arc(fx + Math.cos(j * 1.2566) * 8, fy + Math.sin(j * 1.2566) * 8, 6, 0, PI * 2); c.fill(); } c.fillStyle = '#ffd319'; c.beginPath(); c.arc(fx, fy, 4, 0, PI * 2); c.fill(); }
  if (o.pattern === 'apron') { c.fillStyle = o.shirt2 || '#ffffff'; c.fillRect(-torsoW / 2 + 16, top + 40, torsoW - 32, torsoH); }
  c.restore();
  // arms
  const shY = top + 26, armL = kid ? 92 : 116;
  for (const [side, a0] of [[-1, o.la ?? 0.12], [1, o.ra ?? 0.12]]) {
    let a = a0; if (o.wave === (side < 0 ? 'l' : 'r')) a += Math.sin(t * 9) * 0.28;
    const sx = side * (torsoW / 2 - 10), el = o.elbow ?? 0.25;
    const ex = sx + Math.sin(a) * side * armL * 0.52, ey = shY + Math.cos(a) * armL * 0.52;
    const hx = ex + Math.sin(a + el * (a > 1.2 ? -1 : 1)) * side * armL * 0.5, hy = ey + Math.cos(a + el * (a > 1.2 ? -1 : 1)) * armL * 0.5;
    c.lineCap = 'round'; c.lineJoin = 'round';
    c.strokeStyle = PAL.ink; c.lineWidth = 40; c.beginPath(); c.moveTo(sx, shY); c.lineTo(ex, ey); c.lineTo(hx, hy); c.stroke();
    c.strokeStyle = o.sleeve || shirt; c.lineWidth = 28; c.beginPath(); c.moveTo(sx, shY); c.lineTo(ex, ey); c.lineTo(hx, hy); c.stroke();
    circle(hx, hy, 17, skin, PAL.ink, 5);
    if (o.hold && o.hold.side === side) { c.save(); c.translate(hx, hy); o.hold.draw(t); c.restore(); }
  }
  c.restore();
  // head
  const hx0 = Math.sin(lean) * (torsoH * 0.7);
  c.save(); c.translate(hx0, 0);
  circle(-headR + 4, headY + 6, 13, skin, PAL.ink, 5); circle(headR - 4, headY + 6, 13, skin, PAL.ink, 5);
  circle(0, headY, headR, o.sick ? '#a8d08d' : skin, PAL.ink, 6);
  // hair
  const hc = o.hairColor || '#3b2a20';
  if (o.hair === 'short' || o.hair === 'long' || o.hair === 'bun' || !o.hair) { c.beginPath(); c.arc(0, headY - 2, headR + 4, PI * 1.02, PI * 1.98); c.quadraticCurveTo(headR * 0.4, headY - headR * 0.45, -headR * 0.1, headY - headR * 0.35); c.quadraticCurveTo(-headR * 0.6, headY - headR * 0.25, -headR - 3, headY - 6); c.closePath(); fs(hc, PAL.ink, 6); }
  if (o.hair === 'spiky') { c.beginPath(); c.moveTo(-headR - 2, headY - 4); for (let i = 0; i <= 8; i++) { const a = PI + i * PI / 8, r = headR + (i % 2 ? 22 : 4); c.lineTo(Math.cos(a) * r, headY - 2 + Math.sin(a) * r); } c.closePath(); fs(hc, PAL.ink, 6); }
  if (o.hair === 'bun') circle(0, headY - headR - 14, 24, hc, PAL.ink, 6);
  if (o.hair === 'curly') for (let i = 0; i < 9; i++) { const a = PI * 1.05 + i * PI * 0.9 / 8; circle(Math.cos(a) * headR * 0.92, headY + Math.sin(a) * headR * 0.92, 20, hc, PAL.ink, 5); }
  if (o.hair === 'bald' && old) { ellipse(-headR + 8, headY - 6, 14, 20, hc, PAL.ink, 5); ellipse(headR - 8, headY - 6, 14, 20, hc, PAL.ink, 5); }
  // face
  const blink = o.eyes === 'closed' || (((t + (o.ph || 0)) % 3.7) < 0.12);
  const lx = o.look || 0;
  for (const sx of [-1, 1]) {
    const ex = sx * 22, ey = headY + 2;
    if (blink) { c.strokeStyle = PAL.ink; c.lineWidth = 5; c.beginPath(); c.arc(ex, ey, 10, 0.15 * PI, 0.85 * PI); c.stroke(); }
    else { ellipse(ex, ey, 13, o.eyes === 'wide' ? 18 : 15, '#ffffff', PAL.ink, 4); circle(ex + lx * 5, ey + 2, o.eyes === 'wide' ? 5 : 6.5, PAL.ink, null, 0); }
    if (o.eyes === 'angry') { c.strokeStyle = PAL.ink; c.lineWidth = 7; c.beginPath(); c.moveTo(ex - 14 * sx, ey - 26); c.lineTo(ex + 12 * sx, ey - 16); c.stroke(); }
    else { c.strokeStyle = PAL.ink; c.lineWidth = 5; c.beginPath(); c.moveTo(ex - 10, ey - 24 - (o.eyes === 'wide' ? 6 : 0)); c.lineTo(ex + 10, ey - 26 - (o.eyes === 'wide' ? 6 : 0)); c.stroke(); }
  }
  if (o.cheeks !== false) { c.fillStyle = 'rgba(240,110,110,.35)'; c.beginPath(); c.arc(-34, headY + 24, 11, 0, PI * 2); c.arc(34, headY + 24, 11, 0, PI * 2); c.fill(); }
  const my = headY + 32, m = o.mouth || 'smile';
  c.strokeStyle = PAL.ink; c.lineWidth = 5; c.lineCap = 'round';
  if (m === 'smile') { c.beginPath(); c.arc(0, my - 10, 18, 0.2 * PI, 0.8 * PI); c.stroke(); }
  else if (m === 'grin') { c.beginPath(); c.arc(0, my - 8, 20, 0, PI); c.closePath(); fs('#7a2630', PAL.ink, 5); }
  else if (m === 'open' || m === 'shout') { const r = m === 'shout' ? 17 + Math.abs(Math.sin(t * 14)) * 5 : 12; ellipse(0, my, r * 0.9, r, '#7a2630', PAL.ink, 5); ellipse(0, my + r * 0.5, r * 0.5, r * 0.3, '#e46a7a', null, 0); }
  else if (m === 'frown') { c.beginPath(); c.arc(0, my + 14, 16, 1.2 * PI, 1.8 * PI); c.stroke(); }
  else if (m === 'flat') { c.beginPath(); c.moveTo(-14, my); c.lineTo(14, my); c.stroke(); }
  else if (m === 'wavy') { c.beginPath(); for (let i = 0; i <= 6; i++) c.lineTo(-18 + i * 6, my + (i % 2 ? 4 : -4)); c.stroke(); }
  if (o.glasses) for (const sx of [-1, 1]) { c.strokeStyle = PAL.ink; c.lineWidth = 5; c.beginPath(); c.arc(sx * 22, headY + 2, 19, 0, PI * 2); c.stroke(); }
  if (o.beard) { c.beginPath(); c.arc(0, headY + 18, headR * 0.8, 0.08 * PI, 0.92 * PI); c.quadraticCurveTo(0, headY + headR + 40, headR * 0.79, headY + 18 + headR * 0.2); fs(o.beard, PAL.ink, 5); if (m === 'smile') { c.beginPath(); c.arc(0, my - 10, 16, 0.2 * PI, 0.8 * PI); c.stroke(); } }
  if (o.tache) { c.beginPath(); c.ellipse(-12, my - 10, 14, 7, -0.2, 0, PI * 2); c.ellipse(12, my - 10, 14, 7, 0.2, 0, PI * 2); fs(o.tache, PAL.ink, 4); }
  if (o.flatcap) { c.beginPath(); c.ellipse(0, headY - headR + 22, headR + 6, 30, 0, PI, PI * 2); c.lineTo(headR + 36, headY - headR + 30); c.lineTo(-headR - 4, headY - headR + 28); c.closePath(); fs(o.flatcap, PAL.ink, 6); c.strokeStyle = 'rgba(0,0,0,.25)'; c.lineWidth = 3; for (let i = -2; i <= 2; i++) { c.beginPath(); c.moveTo(i * 18, headY - headR - 4); c.lineTo(i * 18 + 6, headY - headR + 22); c.stroke(); } }
  if (o.veil) { c.beginPath(); c.moveTo(-headR + 10, headY - headR + 10); c.quadraticCurveTo(-headR - 40, headY + 80, -headR - 30, headY + 190); c.lineTo(headR + 30, headY + 190); c.quadraticCurveTo(headR + 40, headY + 80, headR - 10, headY - headR + 10); c.closePath(); c.fillStyle = 'rgba(255,255,255,.55)'; c.fill(); }
  if (o.hat) o.hat(headY, headR);
  if (o.sick) { c.fillStyle = '#6fbf4a'; c.beginPath(); c.ellipse(0, my + 26, 18, 30, 0, 0, PI * 2); c.fill(); }
  c.restore();
  c.restore();
}

// ---------------------------------------------------------------- backdrops
export function room({ wall = PAL.wall, floor = PAL.floor, stripe = PAL.teal, horizon = 1180, window: win = true, flag = false } = {}) {
  c.fillStyle = wall; c.fillRect(0, 0, W, horizon); c.fillStyle = stripe; c.fillRect(0, horizon - 34, W, 40);
  c.fillStyle = floor; c.fillRect(0, horizon + 6, W, H - horizon); c.fillStyle = 'rgba(0,0,0,.07)'; for (let y = horizon + 70; y < H; y += 90) c.fillRect(0, y, W, 6);
  if (win) { rr(700, 120, 300, 380, 12); fs('#9fd0e6', PAL.ink, 8); c.fillStyle = '#c3e3f0'; c.fillRect(706, 126, 288, 160); c.strokeStyle = PAL.ink; c.lineWidth = 8; c.beginPath(); c.moveTo(850, 120); c.lineTo(850, 500); c.moveTo(700, 310); c.lineTo(1000, 310); c.stroke(); }
  if (flag) unionFlag(120, 420, 150, 96, true);
}
export function outdoor({ skyTop = PAL.skyTop, sky = PAL.sky, ground = PAL.grass, horizon = 1150 } = {}) {
  const g = c.createLinearGradient(0, 0, 0, horizon); g.addColorStop(0, skyTop); g.addColorStop(1, sky); c.fillStyle = g; c.fillRect(0, 0, W, horizon);
  c.fillStyle = ground; c.fillRect(0, horizon, W, H - horizon);
}
export function cloudPuff(x, y, s, col = '#ffffff') { withT(x, y, s, 0, () => { c.fillStyle = col; c.strokeStyle = PAL.ink; c.lineWidth = 6; c.beginPath(); for (const [cx, cy, r] of [[-60, 10, 44], [-15, -18, 56], [45, -4, 48], [80, 18, 34], [0, 20, 50]]) { c.moveTo(cx + r, cy); c.arc(cx, cy, r, 0, PI * 2); } c.fill(); }); }
export function unionFlag(x, y, w_, h, pole = false) {
  if (pole) { c.fillStyle = '#6b5a48'; c.fillRect(x - 10, y - 8, 10, h + 140); }
  c.save(); c.beginPath(); c.rect(x, y, w_, h); c.clip();
  c.fillStyle = '#012169'; c.fillRect(x, y, w_, h);
  const diag = (lw, col) => { c.strokeStyle = col; c.lineWidth = lw; c.beginPath(); c.moveTo(x, y); c.lineTo(x + w_, y + h); c.moveTo(x + w_, y); c.lineTo(x, y + h); c.stroke(); };
  diag(h * 0.2, '#ffffff'); diag(h * 0.07, '#C8102E');
  c.fillStyle = '#ffffff'; c.fillRect(x + w_ / 2 - h * 0.17, y, h * 0.34, h); c.fillRect(x, y + h * 0.33, w_, h * 0.34);
  c.fillStyle = '#C8102E'; c.fillRect(x + w_ / 2 - h * 0.1, y, h * 0.2, h); c.fillRect(x, y + h * 0.4, w_, h * 0.2);
  c.restore(); c.strokeStyle = PAL.ink; c.lineWidth = 5; c.strokeRect(x, y, w_, h);
}
// Birmingham skyline: Selfridges "blob", the Rotunda, the BT Tower, the Library's rings, plus terraces
export function brumSkyline(base = 1150, t = 0, rise = () => 1) {
  const ink = PAL.ink;
  const up = (i, fn) => { const k = rise(i); if (k <= 0.001) return; c.save(); c.translate(0, (1 - k) * 700); fn(); c.restore(); };
  // BT tower
  up(0, () => { rr(150, base - 620, 56, 620, 8); fs('#d9d4cb', ink, 6); for (let i = 0; i < 4; i++) { rr(136, base - 560 + i * 34, 84, 22, 6); fs('#bfb8ad', ink, 5); } circle(178, base - 640, 10, Math.sin(t * 6) > 0 ? '#ff5a5f' : '#7a2a30', ink, 4); });
  // Rotunda
  up(1, () => { rr(260, base - 470, 160, 470, 30); fs('#e8e1d4', ink, 6); for (let i = 0; i < 12; i++) { c.fillStyle = Math.sin(t * 3 + i * 1.7) > 0.6 ? '#ffe08a' : '#9fc4d6'; c.fillRect(272, base - 450 + i * 36, 136, 14); } });
  // Library of Birmingham (boxes with gold rings)
  up(2, () => { rr(470, base - 380, 200, 380, 6); fs('#f2d27a', ink, 6); c.strokeStyle = '#b8902e'; c.lineWidth = 6; for (let i = 0; i < 5; i++) for (let j = 0; j < 7; j++) { c.beginPath(); c.arc(492 + j * 27, base - 350 + i * 70, 11, 0, PI * 2); c.stroke(); } });
  // Selfridges blob with discs (they twinkle)
  up(3, () => {
    c.beginPath(); c.moveTo(720, base); c.bezierCurveTo(690, base - 240, 760, base - 330, 860, base - 320); c.bezierCurveTo(980, base - 310, 1010, base - 180, 990, base); c.closePath(); fs('#2e6fa8', ink, 6);
    c.save(); c.clip(); for (let i = 0; i < 9; i++) for (let j = 0; j < 7; j++) { c.fillStyle = Math.sin(t * 4 + i * 0.9 + j * 1.3) > 0.85 ? '#ffffff' : '#d7e4ef'; c.beginPath(); c.arc(720 + j * 44 + (i % 2) * 22, base - 300 + i * 36, 12, 0, PI * 2); c.fill(); } c.restore();
    c.beginPath(); c.moveTo(720, base); c.bezierCurveTo(690, base - 240, 760, base - 330, 860, base - 320); c.bezierCurveTo(980, base - 310, 1010, base - 180, 990, base); c.closePath(); fs(null, ink, 6);
  });
  // red-brick terraces in front
  for (let i = 0; i < 6; i++) up(4 + i, () => { const x = -20 + i * 190; rr(x, base - 150, 190, 150, 0); fs(PAL.brick, ink, 6); c.beginPath(); c.moveTo(x - 6, base - 150); c.lineTo(x + 95, base - 215); c.lineTo(x + 196, base - 150); c.closePath(); fs('#5b4a45', ink, 6); rr(x + 30, base - 120, 46, 50, 4); fs('#cfe8f1', ink, 5); rr(x + 115, base - 95, 44, 95, 4); fs('#2f6fb5', ink, 5); });
}
// little sailing boat, bobbing
export function sailboat(x, y, s, t = 0, col = '#ffffff') {
  withT(x, y + Math.sin(t * 2.2 + x) * 6, s, Math.sin(t * 1.8 + x) * 0.06, () => {
    c.beginPath(); c.moveTo(-70, 0); c.lineTo(70, 0); c.lineTo(50, 30); c.lineTo(-50, 30); c.closePath(); fs('#b5523b', PAL.ink, 5);
    c.beginPath(); c.moveTo(0, -4); c.lineTo(0, -120); c.lineTo(60, -14); c.closePath(); fs(col, PAL.ink, 5);
    c.beginPath(); c.moveTo(-6, -10); c.lineTo(-6, -100); c.lineTo(-52, -14); c.closePath(); fs('#ffd23f', PAL.ink, 5);
  });
}
// a cartoon gull: two flapping arcs
export function gull(x, y, s, t = 0) {
  const f = Math.sin(t * 9 + x * 0.01) * 0.5;
  c.save(); c.translate(x, y); c.scale(s, s); c.strokeStyle = PAL.ink; c.lineWidth = 7; c.lineCap = 'round';
  c.beginPath(); c.moveTo(-40, -10 * f); c.quadraticCurveTo(-20, -24 - 18 * f, 0, 0); c.quadraticCurveTo(20, -24 - 18 * f, 40, -10 * f); c.stroke(); c.restore();
}
export function londonSkyline(base = 1150) {
  const ink = PAL.ink;
  // the Shard
  c.beginPath(); c.moveTo(760, base); c.lineTo(840, base - 720); c.lineTo(920, base); c.closePath(); fs('#b9d3e3', ink, 6); c.strokeStyle = 'rgba(43,38,34,.3)'; c.lineWidth = 3; c.beginPath(); c.moveTo(840, base - 700); c.lineTo(840, base); c.stroke();
  // London Eye
  c.strokeStyle = ink; c.lineWidth = 7; c.beginPath(); c.arc(560, base - 330, 230, 0, PI * 2); c.stroke(); c.lineWidth = 3; for (let i = 0; i < 16; i++) { const a = i * PI / 8; c.beginPath(); c.moveTo(560, base - 330); c.lineTo(560 + Math.cos(a) * 230, base - 330 + Math.sin(a) * 230); c.stroke(); circle(560 + Math.cos(a) * 230, base - 330 + Math.sin(a) * 230, 13, '#e8eef2', ink, 4); }
  c.lineWidth = 7; c.beginPath(); c.moveTo(500, base); c.lineTo(560, base - 330); c.lineTo(620, base); c.stroke();
  // Elizabeth Tower (Big Ben)
  rr(120, base - 640, 120, 640, 4); fs('#d8b46a', ink, 6); c.beginPath(); c.moveTo(110, base - 640); c.lineTo(180, base - 790); c.lineTo(250, base - 640); c.closePath(); fs('#5e6b5a', ink, 6);
  circle(180, base - 560, 42, '#fbf6ea', ink, 6); c.strokeStyle = ink; c.lineWidth = 5; c.beginPath(); c.moveTo(180, base - 560); c.lineTo(180, base - 590); c.moveTo(180, base - 560); c.lineTo(200, base - 560); c.stroke();
  c.strokeStyle = 'rgba(43,38,34,.35)'; c.lineWidth = 3; for (let i = 0; i < 9; i++) { c.beginPath(); c.moveTo(130, base - 480 + i * 50); c.lineTo(230, base - 480 + i * 50); c.stroke(); }
}
export function canal({ horizon = 1050, water = 1240 } = {}) {
  outdoor({ horizon });
  // brick warehouse wall
  c.fillStyle = PAL.brick; c.fillRect(0, horizon - 420, W, 420); c.strokeStyle = 'rgba(0,0,0,.18)'; c.lineWidth = 3;
  for (let y = horizon - 420; y < horizon; y += 36) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); for (let x = ((y / 36) % 2) * 40; x < W; x += 80) { c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + 36); c.stroke(); } }
  for (let i = 0; i < 4; i++) { rr(80 + i * 260, horizon - 340, 150, 180, 70); fs('#2d3a4a', PAL.ink, 7); }
  // towpath + water
  c.fillStyle = '#c9b48f'; c.fillRect(0, horizon, W, water - horizon); c.fillStyle = '#8f7a59'; c.fillRect(0, water - 26, W, 26);
  c.fillStyle = '#4f8f7f'; c.fillRect(0, water, W, H - water); c.fillStyle = 'rgba(255,255,255,.18)'; for (let i = 0; i < 9; i++) c.fillRect(60 + i * 120, water + 60 + (i % 3) * 120, 70, 8);
}
export function narrowboat(x, y, s, col = '#1f5f3a') {
  withT(x, y, s, 0, () => {
    c.beginPath(); c.moveTo(-330, -40); c.lineTo(300, -40); c.quadraticCurveTo(380, -40, 340, 40); c.lineTo(-320, 40); c.closePath(); fs('#2b2622', PAL.ink, 6);
    rr(-290, -150, 520, 112, 14); fs(col, PAL.ink, 6); c.fillStyle = '#c0392b'; c.fillRect(-290, -66, 520, 20);
    for (let i = 0; i < 5; i++) { circle(-240 + i * 105, -112, 22, '#fdf3d6', PAL.ink, 5); }
    txt('BRUM', -30, -50, { font: 'Lilita One', weight: 400, size: 30, color: '#ffd23f' });
  });
}
export function gondola(x, y, s) {
  withT(x, y, s, 0, () => {
    c.beginPath(); c.moveTo(-260, -10); c.quadraticCurveTo(0, 60, 260, -10); c.quadraticCurveTo(300, -70, 280, -110); c.quadraticCurveTo(250, -30, 220, -20); c.lineTo(-220, -20); c.quadraticCurveTo(-250, -30, -280, -100); c.quadraticCurveTo(-300, -60, -260, -10); c.closePath(); fs('#1d1d1f', PAL.ink, 6);
    c.strokeStyle = '#b8902e'; c.lineWidth = 6; c.beginPath(); c.moveTo(-220, -20); c.quadraticCurveTo(0, 30, 220, -20); c.stroke();
  });
}
export function trolley(x, y, s, rot = 0) {
  withT(x, y, s, rot, () => {
    c.strokeStyle = PAL.ink; c.lineWidth = 9; c.lineCap = 'round';
    c.beginPath(); c.moveTo(-120, -120); c.lineTo(110, -120); c.lineTo(80, 10); c.lineTo(-100, 10); c.closePath(); c.fillStyle = 'rgba(200,210,220,.35)'; c.fill(); c.stroke();
    c.lineWidth = 4; for (let i = 1; i < 6; i++) { c.beginPath(); c.moveTo(-120 + i * 38, -120); c.lineTo(-100 + i * 31, 10); c.stroke(); } for (let j = 1; j < 3; j++) { c.beginPath(); c.moveTo(-120 + j * 6, -120 + j * 43); c.lineTo(110 - j * 10, -120 + j * 43); c.stroke(); }
    c.lineWidth = 9; c.beginPath(); c.moveTo(110, -120); c.lineTo(150, -170); c.stroke(); rr(130, -186, 70, 22, 10); fs('#e63946', PAL.ink, 5);
    circle(-80, 40, 18, '#2b2622', PAL.ink, 4); circle(60, 40, 18, '#2b2622', PAL.ink, 4);
  });
}
export function car(x, y, s, col = '#e63946', driver = null, t = 0) {
  withT(x, y, s, 0, () => {
    c.beginPath(); c.moveTo(-200, 0); c.lineTo(-200, -70); c.quadraticCurveTo(-190, -90, -150, -92); c.lineTo(-120, -215); c.lineTo(100, -215); c.lineTo(150, -92); c.lineTo(190, -88); c.quadraticCurveTo(210, -80, 210, -50); c.lineTo(210, 0); c.closePath(); fs(col, PAL.ink, 7);
    const win = () => { c.beginPath(); c.moveTo(-108, -96); c.lineTo(-84, -198); c.lineTo(88, -198); c.lineTo(126, -96); c.closePath(); };
    win(); fs('#cfe8f1', PAL.ink, 6);
    if (driver) { c.save(); win(); c.clip(); driver(t); c.restore(); win(); fs(null, PAL.ink, 6); }
    circle(-120, 0, 36, '#2b2622', PAL.ink, 6); circle(-120, 0, 14, '#c9ccd1', null, 0); circle(130, 0, 36, '#2b2622', PAL.ink, 6); circle(130, 0, 14, '#c9ccd1', null, 0);
    circle(200, -60, 10, '#ffd23f', PAL.ink, 4);
  });
}
export function coach(x, y, s, t = 0) {
  withT(x, y, s, 0, () => {
    rr(-380, -300, 760, 280, 40); fs('#f1c40f', PAL.ink, 7); c.fillStyle = '#2f6fb5'; c.fillRect(-380, -110, 760, 26);
    for (let i = 0; i < 6; i++) { rr(-350 + i * 115, -270, 95, 120, 14); fs('#cfe8f1', PAL.ink, 5); }
    circle(-250, -10, 46, '#2b2622', PAL.ink, 6); circle(-250, -10, 18, '#c9ccd1', null, 0); circle(250, -10, 46, '#2b2622', PAL.ink, 6); circle(250, -10, 18, '#c9ccd1', null, 0);
    txt('SCHOOL TRIP', 0, -60, { font: 'Lilita One', weight: 400, size: 48, color: '#2b2622' });
  });
}
export function mug(x, y, s, col = '#ffffff', steam = true, t = 0) {
  withT(x, y, s, 0, () => {
    c.strokeStyle = PAL.ink; c.lineWidth = 12; c.beginPath(); c.arc(62, -48, 26, -PI / 2, PI / 2); c.stroke();
    rr(-60, -110, 124, 110, 16); fs(col, PAL.ink, 6); ellipse(2, -110, 62, 12, '#9a5b2e', PAL.ink, 5);
    if (steam) { c.strokeStyle = 'rgba(255,255,255,.85)'; c.lineWidth = 7; for (let i = 0; i < 3; i++) { c.beginPath(); for (let k = 0; k < 10; k++) c.lineTo(-30 + i * 30 + Math.sin(t * 4 + k * 0.7 + i) * 8, -130 - k * 9); c.stroke(); } }
  });
}
export function balti(x, y, s, t = 0) {
  withT(x, y, s, 0, () => {
    ellipse(0, 10, 230, 50, '#2b2622', PAL.ink, 6);
    c.beginPath(); c.moveTo(-210, -20); c.quadraticCurveTo(0, 90, 210, -20); c.closePath(); fs('#3f3f45', PAL.ink, 7);
    ellipse(0, -20, 210, 44, '#c8641e', PAL.ink, 6); c.fillStyle = '#e8a23c'; for (let i = 0; i < 9; i++) { c.beginPath(); c.arc(-140 + i * 35, -22 + (i % 3) * 8 - 8, 12, 0, PI * 2); c.fill(); }
    c.fillStyle = '#5aa13f'; for (let i = 0; i < 5; i++) { c.beginPath(); c.ellipse(-100 + i * 50, -30, 9, 5, i, 0, PI * 2); c.fill(); }
    for (const sx of [-1, 1]) { c.strokeStyle = PAL.ink; c.lineWidth = 12; c.beginPath(); c.arc(sx * 236, -20, 26, sx < 0 ? PI * 0.6 : -PI * 0.4, sx < 0 ? PI * 1.4 : PI * 0.4); c.stroke(); }
    c.strokeStyle = 'rgba(255,255,255,.8)'; c.lineWidth = 7; for (let i = 0; i < 3; i++) { c.beginPath(); for (let k = 0; k < 9; k++) c.lineTo(-60 + i * 60 + Math.sin(t * 4 + k * 0.7 + i) * 8, -60 - k * 10); c.stroke(); }
  });
}
export function choc(x, y, s, rot = 0) {
  withT(x, y, s, rot, () => {
    rr(-150, -60, 300, 120, 14); fs('#6b3e26', PAL.ink, 6); c.fillStyle = '#7d4a2f'; for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) { rr(-136 + i * 70, -48 + j * 54, 60, 44, 8); c.fill(); }
    rr(-150, -64, 150, 128, 12); fs('#4b1f6f', PAL.ink, 6); txt('CHOC', -75, 0, { font: 'Lilita One', weight: 400, size: 40, color: '#ffffff' });
  });
}
export function suitcase(x, y, s, col = '#e74c3c') { withT(x, y, s, 0, () => { rr(-30, -140, 60, 30, 12); fs(null, PAL.ink, 8); rr(-80, -120, 160, 120, 16); fs(col, PAL.ink, 6); c.fillStyle = 'rgba(0,0,0,.15)'; c.fillRect(-80, -70, 160, 12); }); }
export function guitar(x, y, s, rot = -0.6) {
  withT(x, y, s, rot, () => {
    // neck + headstock
    rr(-15, -430, 30, 330, 6); fs('#c89b5b', PAL.ink, 5);
    c.strokeStyle = 'rgba(43,38,34,.55)'; c.lineWidth = 3; for (let i = 0; i < 9; i++) { c.beginPath(); c.moveTo(-15, -410 + i * 34); c.lineTo(15, -410 + i * 34); c.stroke(); }
    rr(-26, -490, 52, 70, 12); fs('#2b2622', PAL.ink, 5); for (const sx of [-1, 1]) for (let i = 0; i < 3; i++) circle(sx * 34, -476 + i * 20, 7, '#d9d9d9', PAL.ink, 3);
    // body: two lobes, outlined as one shape
    const lobes = () => { c.beginPath(); c.ellipse(0, 30, 125, 135, 0, 0, PI * 2); c.moveTo(85, -105); c.ellipse(0, -105, 88, 92, 0, 0, PI * 2); };
    lobes(); c.strokeStyle = PAL.ink; c.lineWidth = 14; c.stroke(); lobes(); c.fillStyle = '#c0392b'; c.fill();
    c.beginPath(); c.ellipse(-30, 40, 70, 80, 0.3, 0, PI * 2); c.fillStyle = '#f2ead8'; c.fill(); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.stroke();
    for (const yy of [-40, 30]) { rr(-38, yy, 76, 26, 6); fs('#1d1d1f', PAL.ink, 4); }
    rr(-46, 95, 92, 18, 4); fs('#9a9aa0', PAL.ink, 4);
    c.strokeStyle = '#e8e8e8'; c.lineWidth = 2; for (let i = -2; i <= 2; i++) { c.beginPath(); c.moveTo(i * 5, -480); c.lineTo(i * 7, 104); c.stroke(); }
    for (const [kx, ky] of [[70, 80], [90, 120], [55, 125]]) circle(kx, ky, 11, '#ffd23f', PAL.ink, 3);
  });
}
export function bolt(x, y, s, col = '#ffd23f') { withT(x, y, s, 0, () => { c.beginPath(); c.moveTo(20, -120); c.lineTo(-50, 10); c.lineTo(0, 10); c.lineTo(-30, 120); c.lineTo(60, -20); c.lineTo(10, -20); c.closePath(); fs(col, PAL.ink, 6); }); }
export function bench(x, y, s) { withT(x, y, s, 0, () => { rr(-200, -140, 400, 22, 6); fs('#8b5a2b', PAL.ink, 5); rr(-200, -200, 400, 22, 6); fs('#8b5a2b', PAL.ink, 5); rr(-200, -80, 400, 26, 6); fs('#8b5a2b', PAL.ink, 5); for (const sx of [-1, 1]) { rr(sx * 170 - 10, -80, 20, 80, 4); fs('#2b2622', PAL.ink, 4); } }); }
export function bunting(y, t = 0) { c.strokeStyle = PAL.ink; c.lineWidth = 4; c.beginPath(); c.moveTo(0, y); c.quadraticCurveTo(W / 2, y + 60, W, y); c.stroke(); const cols = ['#e63946', '#ffffff', '#2f6fb5']; for (let i = 0; i < 14; i++) { const x = 30 + i * 75, yy = y + 60 * (1 - Math.pow((x - W / 2) / (W / 2), 2)) * 0.5 + 4; c.beginPath(); c.moveTo(x - 22, yy); c.lineTo(x + 22, yy); c.lineTo(x, yy + 44 + Math.sin(t * 3 + i) * 3); c.closePath(); fs(cols[i % 3], PAL.ink, 4); } }
// Spaghetti Junction: stacked looping carriageways on pillars
export function junction(t = 0, carsOn = true) {
  outdoor({ horizon: 900, ground: '#9bbf6a' });
  const roads = [[1260, 0.0, 120], [1080, 0.9, 150], [900, 2.1, 110], [1440, 1.4, 140], [740, 0.4, 90]];
  for (const [y, ph, amp] of roads) {
    for (let x = 60; x < W; x += 200) { rr(x, y - Math.sin(x / 260 + ph) * amp + 30, 28, 900, 4); fs('#a9a39a', PAL.ink, 5); }
  }
  for (const [y, ph, amp] of roads) {
    c.lineCap = 'round'; c.strokeStyle = PAL.ink; c.lineWidth = 92; c.beginPath(); for (let x = -40; x <= W + 40; x += 20) c.lineTo(x, y - Math.sin(x / 260 + ph) * amp); c.stroke();
    c.strokeStyle = '#6b6f76'; c.lineWidth = 78; c.stroke();
    c.strokeStyle = '#f2f2f2'; c.lineWidth = 5; c.setLineDash([26, 26]); c.stroke(); c.setLineDash([]);
  }
  if (carsOn) { const R = mulberry32(4); for (let i = 0; i < 12; i++) { const rd = roads[i % roads.length], x = (R() * W + t * 6) % W; withT(x, rd[0] - Math.sin(x / 260 + rd[1]) * rd[2] - 16, 0.22, -Math.atan(Math.cos(x / 260 + rd[1]) * rd[2] / 260), () => { rr(-110, -60, 220, 70, 20); fs(['#e63946', '#2f6fb5', '#f1c40f', '#ffffff', '#27ae60'][i % 5], PAL.ink, 18); }); } }
}

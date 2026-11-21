// "Where will you be born this time?" — Miami, 80s neon. One scene per narration line, flat cartoon characters in a
// neon / pastel Miami, every element popping in on its word.
import { c, W, H, PI, PAL, tl, DUR, S, L, w, we, sfx, music, clamp01, lerp, ss, pop, popOut, backOut, elastic, mulberry32, scene, overlay, rr, fs, circle, ellipse, txt, withT, title, hand, card, bubble } from './core.js';
import { person, room, outdoor, cloudPuff, car, suitcase, bench, mug } from './art.js';
import { pin } from './globe.js';
import { usMap, cityDots, hopPin, projFor, usPath, usBounds, usFlagFill, flPath, CITY, MIAMI } from './usmap.js';
import { NEON, flick, neonText, neonStroke, stars, retroSun, synthGrid, synthSky, sunsetSky, sea, palm, flamingo, iguana, decoStrip, convertible, cafecito, ventanita, rocketCup, hurricane, rain, snow, boardedWindow, thermometer, crabPlate, crab, cubano, nycSkyline, taxi, weddingArch, flagPattern, shades, beanie, sweat, note } from './miami.js';

const ln = (s, i) => L(s, i).start;
const SK = PAL.skin;
const TEO_KID = { kid: true, skin: SK[1], hair: 'curly', hairColor: '#1d1410', shirt: '#05c3d6', pattern: 'floral', shirt2: '#ffffff', pants: '#ff4fa3', shorts: true, shoes: '#ffd319', ph: 0.3 };
const TEO_TEEN = { skin: SK[1], hair: 'short', hairColor: '#1d1410', shirt: '#ff6fa5', pants: '#2f3a5a', shorts: true, shoes: '#ffffff', ph: 0.3 };
const TEO = { skin: SK[1], hair: 'short', hairColor: '#1d1410', shirt: '#ffffff', pattern: 'floral', shirt2: '#ff2a6d', pants: '#e9d8b4', shorts: true, shoes: '#ff4fa3', ph: 0.3 };
const TEO_OLD = { old: true, skin: SK[1], hair: 'bald', hairColor: '#e2e2e2', glasses: true, tache: '#e9e9e9', shirt: '#9be3c9', pattern: 'floral', shirt2: '#ff901f', pants: '#e9d8b4', shorts: true, shoes: '#ffffff', ph: 0.3 };
const VALE = { skin: SK[2], hair: 'long', hairColor: '#24160f', shirt: '#ffffff', dress: '#ffffff', pants: SK[2], ph: 1.1 };
const VALE_OLD = { old: true, skin: SK[2], hair: 'curly', hairColor: '#e6e6e6', glasses: true, shirt: '#ff8fab', pattern: 'floral', shirt2: '#ffffff', dress: '#c9b6f2', pants: SK[2], ph: 1.1 };
const MUM = { skin: SK[1], hair: 'long', hairColor: '#2a1a12', shirt: '#ff7f50', pants: '#3b4a6b', ph: 0.9 };
const DAD = { skin: SK[1], hair: 'short', hairColor: '#1d1410', tache: '#1d1410', shirt: '#ffffff', pattern: 'floral', shirt2: '#05a8b8', pants: '#e9d8b4', ph: 2.1 };
const NAN = { old: true, skin: SK[1], hair: 'curly', hairColor: '#dcdcdc', glasses: true, shirt: '#b967ff', pattern: 'floral', shirt2: '#ffd319', dress: '#7b2ff7', pants: SK[1], ph: 1.7 };
const SERVER = { skin: SK[2], hair: 'curly', hairColor: '#1d1410', shirt: '#ffffff', pattern: 'apron', shirt2: '#ff4fa3', pants: '#2b2b2b', ph: 0.7, earrings: true };
const assign = (...a) => Object.assign({}, ...a);
// floor / ground strip under everything for street scenes
const street = (y, col = '#cfc1a8') => { c.fillStyle = col; c.fillRect(0, y, W, H - y); c.fillStyle = 'rgba(0,0,0,.08)'; for (let x = 0; x < W; x += 140) c.fillRect(x, y, 6, H - y); };

// ================================================================ 1. NEON MAP: sign flickers on, the sun rises over a synthwave grid, the
// map sweeps in, the pin bounces round America rejecting cities, stars-and-stripes sweep, Florida lights up, slam on Miami
const tPlace = ln('s02', 0), tTicket = ln('s02', 1), tMiamiWord = w('s02', 'miami'), tUnited = w('s02', 'united');
const HOPS = ['Seattle', 'Los Angeles', 'Las Vegas', 'Chicago', 'New York', 'Houston', 'Atlanta'];
const tFirst = 0.7, tLand = tMiamiWord - 0.02, step = (tLand - tFirst) / HOPS.length;
const STOPS = HOPS.map((n, i) => [n, tFirst + i * step]).concat([['Miami', tLand]]);
const DWELL = 0.12;
function header(t, kh, line2 = 'this time?', t0 = -0.35) {
  if (kh <= 0.01) return;
  const kb = elastic(clamp01((t - t0) / 0.7));
  c.save(); c.globalAlpha = kh; c.translate(0, lerp(-320, 0, kb));
  rr(90, 84, 900, 256, 40); c.fillStyle = 'rgba(13,2,33,.84)'; c.fill(); neonStroke(NEON.pink, 5, flick(t, t0 + 0.1, 1));
  const words = ['Where', 'will', 'you', 'be', 'born']; let size = 72; c.font = `400 ${size}px "Pacifico"`;
  let ws = words.map(x => c.measureText(x).width), sp = c.measureText(' ').width, tot = ws.reduce((a, b) => a + b, 0) + sp * (words.length - 1);
  if (tot > 800) { const k = 800 / tot; size *= k; ws = ws.map(v => v * k); sp *= k; tot = 800; }
  let x = W / 2 - tot / 2;
  words.forEach((wd, i) => { const tw = t0 + 0.2 + i * 0.09, k = backOut(clamp01((t - tw) / 0.3), 2.6); if (k > 0) withT(x + ws[i] / 2, 168 - (1 - k) * 30, Math.max(0.001, k), 0, () => neonText(wd, 0, 0, { size, col: NEON.teal, alpha: flick(t, tw, i + 2) })); x += ws[i] + sp; });
  const t2 = t0 + 0.7, k2 = backOut(clamp01((t - t2) / 0.3), 2.6);
  if (k2 > 0) withT(W / 2, 262, Math.max(0.001, k2), Math.sin(t * 5) * 0.04, () => neonText(line2, 0, 0, { size: 88, col: NEON.yellow, alpha: flick(t, t2, 9) }));
  if (k2 > 0) { c.save(); c.translate(920, 250 + Math.sin(t * 6) * 8); c.rotate(Math.sin(t * 4) * 0.2); pin(0, 0, 0.5 * k2, NEON.pink); c.restore(); c.save(); c.translate(160, 250 + Math.cos(t * 6) * 8); c.rotate(-Math.sin(t * 4) * 0.2); pin(0, 0, 0.5 * k2, NEON.teal); c.restore(); }
  c.restore();
}
function synthBack(t, { sunY = 600, horizon = 1330, alpha = 1 } = {}) {
  synthSky(horizon);
  stars(t, 700);
  retroSun(W / 2, sunY, 300);
  synthGrid(horizon, t, { alpha });
}
function pinAt(p, t) {
  const P = n => p(CITY[n]);
  if (t < STOPS[0][1]) { const [x0, y0] = P(STOPS[0][0]); const k = clamp01((t - (STOPS[0][1] - 0.55)) / 0.55); return { x: x0, y: y0, h: (1 - k * k) * 1100, land: -1, hop: -1, k }; }
  let i = STOPS.length - 1; for (let j = 0; j < STOPS.length - 1; j++) if (t >= STOPS[j][1] && t < STOPS[j + 1][1]) i = j;
  const [a, ta] = STOPS[i], nx = STOPS[i + 1];
  if (!nx || t < ta + DWELL) { const [x, y] = P(a); return { x, y, h: 0, land: t - ta, hop: -1, i }; }
  const k = clamp01((t - ta - DWELL) / (nx[1] - ta - DWELL)), A = P(a), B = P(nx[0]);
  const hh = 120 + Math.hypot(B[0] - A[0], B[1] - A[1]) * 0.35;
  return { x: lerp(A[0], B[0], k), y: lerp(A[1], B[1], k), h: Math.sin(PI * k) * hh, land: -1, hop: i, k, A, B, hh };
}
function drawPinFx(p, t, s) {
  const st = pinAt(p, t);
  if (st.hop >= 0) for (let j = 0; j <= 14; j++) { const kj = st.k * j / 14; const x = lerp(st.A[0], st.B[0], kj), y = lerp(st.A[1], st.B[1], kj) - Math.sin(PI * kj) * st.hh; c.beginPath(); c.arc(x, y, 5 * s * (0.4 + 0.6 * j / 14), 0, PI * 2); c.fillStyle = '#ffffff'; c.fill(); neonStroke(NEON.yellow, 2, 1); }
  STOPS.slice(0, -1).forEach(([n, ta], i) => {
    const tl_ = ta + DWELL, k = backOut(clamp01((t - tl_) / 0.25), 3); if (k <= 0) return;
    const [x, y] = p(CITY[n]); withT(x, y, k * s, 0.15 * Math.sin(i * 2.3), () => { c.beginPath(); c.moveTo(-20, -20); c.lineTo(20, 20); c.moveTo(20, -20); c.lineTo(-20, 20); neonStroke(NEON.pink, 7, 1); });
  });
  ellipse(st.x, st.y + 4, 34 * s * (1 - Math.min(0.6, st.h / 900)), 12 * s * (1 - Math.min(0.6, st.h / 900)), 'rgba(0,0,0,.45)', null, 0);
  if (st.land >= 0 && st.land < 0.45) { const k = st.land / 0.45; c.globalAlpha = 1 - k; c.beginPath(); c.ellipse(st.x, st.y, (20 + 80 * k) * s, (8 + 30 * k) * s, 0, 0, PI * 2); neonStroke(NEON.teal, 4, 1); c.globalAlpha = 1; }
  let sq = 1; if (st.land >= 0 && st.land < 0.4) sq = 1 - 0.28 * Math.exp(-st.land * 10) * Math.cos(st.land * 30);
  const flip = st.hop >= 0 ? Math.cos(st.k * PI * 2) : 1;
  c.save(); c.translate(st.x, st.y - st.h); c.scale(flip / Math.sqrt(sq), sq); c.rotate(st.hop >= 0 ? Math.sin(st.k * PI) * 0.25 : 0); pin(0, 0, 1.0 * s, NEON.pink); c.restore();
  return st;
}
scene(0, tTicket, (t) => {
  const kz = ss(tLand + 0.25, tTicket - 0.3, t), zoom = Math.pow(9, kz);
  const intro = backOut(clamp01((t - 0.0) / 0.7), 2.0);
  const sh = t > tLand ? 18 * Math.exp(-(t - tLand) * 7) : 0;
  c.save(); c.translate(Math.sin(t * 90) * sh, Math.cos(t * 77) * sh);
  synthBack(t, { sunY: lerp(860, 600, ss(-0.4, 1.3, t)) });
  if (kz > 0) { c.fillStyle = `rgba(16,4,40,${0.9 * kz})`; c.fillRect(-50, -50, W + 100, H + 100); }
  c.save(); c.translate(W / 2, 950); c.rotate((1 - intro) * 0.06); c.scale(0.8 + 0.2 * intro, 0.8 + 0.2 * intro); c.translate(-W / 2, -950);
  const p = usMap({ zoom, focus: MIAMI, to: [W / 2, 1000], kz, t, sweep: ss(0.0, 0.8, t), fl: ss(tLand - 0.05, tLand + 0.25, t), labels: (1 - kz) * ss(0.6, 1.2, t) });
  // stars and stripes sweep the country on "United States"
  const ku = ss(tUnited - 0.12, tUnited + 0.3, t) * (1 - ss(tUnited + 0.95, tUnited + 1.35, t));
  if (ku > 0) usFlagFill(p, ku);
  const visited = STOPS.filter(([, tt]) => t >= tt).map(([n]) => n);
  cityDots(p, { major: 1 - kz, show: visited, size: 1 + kz * 0.5, alpha: ss(0.5, 0.9, t) });
  const kr = pop(t, tLand, 0.4);
  if (kr > 0) { const [bx, by] = p(MIAMI); c.save(); c.translate(bx, by - 40); c.rotate(t * 0.8); for (let i = 0; i < 16; i++) { c.rotate(PI / 8); c.beginPath(); c.moveTo(0, 0); c.lineTo(-36 * kr, -560 * kr); c.lineTo(36 * kr, -560 * kr); c.closePath(); c.fillStyle = i % 2 ? 'rgba(255,42,109,.28)' : 'rgba(255,211,25,.24)'; c.fill(); } c.restore(); }
  if (t > tLand && t < tLand + 1.0) { const [bx, by] = p(MIAMI); for (let r = 0; r < 3; r++) { const k = clamp01((t - tLand - r * 0.12) / 0.7); if (k <= 0 || k >= 1) continue; c.globalAlpha = 1 - k; c.beginPath(); c.arc(bx, by, 40 + 520 * k, 0, PI * 2); neonStroke(r % 2 ? NEON.teal : NEON.pink, 6, 1); c.globalAlpha = 1; } }
  drawPinFx(p, t, 1.15 + kz * 0.5);
  if (t > tLand && t < tLand + 1.6) { const [bx, by] = p(MIAMI), dt = t - tLand, R = mulberry32(7), cols = [NEON.pink, NEON.teal, NEON.yellow, '#ffffff', NEON.orange]; for (let i = 0; i < 70; i++) { const a = -PI / 2 + (R() - 0.5) * 2.6, v = 500 + R() * 800, x = bx + Math.cos(a) * v * dt, y = by - 60 + Math.sin(a) * v * dt + 900 * dt * dt; withT(x, y, 1, dt * (6 + R() * 8), () => { c.fillStyle = cols[i % 5]; c.globalAlpha = 1 - dt / 1.6; c.fillRect(-11, -6, 22, 12); c.globalAlpha = 1; }); } }
  c.restore();
  // flamingos fly across in front of the sun
  if (kz < 0.5) for (let i = 0; i < 3; i++) { const x = ((t * (170 + i * 50) + i * 420) % 1500) - 200; flamingo(x, 470 + i * 70 + Math.sin(t * 2 + i) * 16, 0.85 - i * 0.12, t + i); }
  // palm silhouettes frame the bottom corners
  palm(-30, H + 30, 1.05, t, { lean: 0.32, dark: true }); palm(W + 30, H + 30, 1.05, t + 1, { lean: -0.32, dark: true });
  c.restore();
  header(t, 1 - ss(tLand + 0.1, tLand + 0.5, t));
  // MIAMI drops in, letter by letter, in neon
  if (t > tLand) {
    const word = 'MIAMI', size = 150; c.font = `400 ${size}px "Monoton"`; const tot = c.measureText(word).width; let x = W / 2 - tot / 2;
    for (let i = 0; i < word.length; i++) { const wi = c.measureText(word[i]).width, k = elastic(clamp01((t - tLand - i * 0.05) / 0.5)); if (k > 0) withT(x + wi / 2, lerp(420, 480, kz) - (1 - k) * 280, 1, (1 - k) * (i % 2 ? 0.6 : -0.6), () => neonText(word[i], 0, 0, { size, font: 'Monoton', col: i % 2 ? NEON.teal : NEON.pink, alpha: flick(t, tLand + i * 0.05, i + 20, 0.3) })); x += wi; }
  }
  const kU = pop(t, tUnited - 0.05) * (1 - ss(tLand - 0.2, tLand, t));
  if (kU > 0) withT(W / 2, 1740, kU, Math.sin(t * 4) * 0.03, () => neonText('United States', 0, 0, { size: 84, col: NEON.teal, alpha: flick(t, tUnited - 0.05, 4) }));
  const kl = clamp01(1 - Math.abs(t - (tLand + 0.25 + (tTicket - 0.3 - tLand - 0.25) * 0.55)) / 0.4);
  if (kl > 0) { const R = mulberry32(Math.floor(t * 30)), cols = [NEON.pink, NEON.teal, '#ffffff', NEON.yellow]; c.lineCap = 'round'; for (let i = 0; i < 46; i++) { const a = R() * PI * 2, r0 = 260 + R() * 300, r1 = r0 + 300 + R() * 600; c.strokeStyle = cols[i % 4]; c.globalAlpha = 0.75 * kl; c.lineWidth = 4 + R() * 8; c.beginPath(); c.moveTo(W / 2 + Math.cos(a) * r0, 1000 + Math.sin(a) * r0); c.lineTo(W / 2 + Math.cos(a) * r1, 1000 + Math.sin(a) * r1); c.stroke(); } c.globalAlpha = 1; }
}, { zoom: 0 });
STOPS.forEach(([, tt], i) => sfx(i === STOPS.length - 1 ? 'ding' : 'boing', tt, i === STOPS.length - 1 ? 0.6 : 0.4, { pitch: 1 + (i % 4) * 0.1 }));
STOPS.slice(0, -1).forEach(([, tt]) => sfx('stamp', tt + DWELL + 0.02, 0.2));
sfx('flicker', 0.0, 0.35); sfx('whoosh', 0.0, 0.4); [0, 1, 2, 3, 4].forEach(i => sfx('pop', Math.max(0, -0.15 + i * 0.09), 0.16, { pitch: 1 + i * 0.08 })); sfx('flicker', 0.35, 0.3); sfx('pop', 0.38, 0.3, { pitch: 1.4 });
sfx('riser', 0.0, 0.3); sfx('whoosh', STOPS[0][1] - 0.5, 0.35); sfx('shimmer', tUnited - 0.1, 0.5);
sfx('thunk', tLand, 0.7); sfx('cheer', tLand + 0.05, 0.5); sfx('pop', tLand + 0.05, 0.6); sfx('flicker', tLand + 0.02, 0.35); sfx('whoosh', tLand + 0.3, 0.6);
// neon stripe wipe into the city
const tWipe = tTicket;
overlay(t => {
  const k = clamp01((t - (tWipe - 0.5)) / 1.0); if (k <= 0 || k >= 1) return;
  const cols = [NEON.violet, NEON.pink, NEON.orange, NEON.yellow, NEON.teal, '#7b2ff7'], bw = 330, tot = bw * cols.length, off = lerp(-tot - 800, W + 800, ss(0, 1, k));
  c.save(); c.translate(off, 0); c.transform(1, 0, -0.35, 1, 0, 0);
  cols.forEach((col, i) => { c.fillStyle = col; c.fillRect(i * bw, -100, bw + 1, H + 200); c.fillStyle = 'rgba(255,255,255,.25)'; c.fillRect(i * bw, -100, 14, H + 200); });
  c.restore();
});
sfx('whoosh', tWipe - 0.3, 0.6);

// ================================================================ 2. TICKET TO LIFE: Ocean Drive pops up, the ticket flies in, the odds roll
const tRollEnd = tTicket + 1.5;
scene(tTicket, ln('s02', 2), (t, lt) => {
  sunsetSky(1300);
  retroSun(W / 2, 1050, 260, { glow: 0.6 });
  for (let i = 0; i < 3; i++) flamingo(((lt * (130 + i * 40) + i * 360) % 1400) - 150, 300 + i * 80, 0.5, t + i, true);
  decoStrip(1330, t, { rise: i => backOut(clamp01((t - tTicket - 0.05 - (i === 9 ? 0 : i) * 0.06) / 0.4), 2.2), signOn: i => flick(t, tTicket + 0.5 + i * 0.12, i) });
  c.fillStyle = '#f6c9a8'; c.fillRect(0, 1330, W, 90); c.fillStyle = '#f3dfb5'; c.fillRect(0, 1420, W, H - 1420);
  const kp = i => backOut(clamp01((t - tTicket - 0.25 - i * 0.1) / 0.45), 2.4);
  palm(70, 1440, 1.0 * kp(0), t, { lean: 0.12 }); palm(1010, 1440, 0.95 * kp(1), t + 2, { lean: -0.14 });
  const kf = clamp01((t - tTicket - 0.2) / 0.65), ke = elastic(kf);
  if (kf > 0) withT(W / 2, lerp(1700, 640, ke), 0.6 + 0.4 * ke, lerp(0.9, -0.03, ke), () => {
    rr(-380 + 10, -230 + 12, 760, 460, 28); fs('rgba(0,0,0,.25)', null, 0);
    rr(-380, -230, 760, 460, 28); fs('#fff6fb', PAL.ink, 7);
    c.save(); rr(-380, -230, 760, 40, 28); c.clip(); const g = c.createLinearGradient(-380, 0, 380, 0); g.addColorStop(0, NEON.pink); g.addColorStop(0.5, NEON.orange); g.addColorStop(1, NEON.teal); c.fillStyle = g; c.fillRect(-380, -230, 760, 40); c.restore();
    c.setLineDash([14, 12]); c.strokeStyle = 'rgba(43,38,34,.3)'; c.lineWidth = 4; rr(-356, -176, 712, 382, 20); c.stroke(); c.setLineDash([]);
    txt('TICKET TO LIFE', 0, -140, { size: 34, color: '#7d7468' });
    txt('United States • Miami', 0, -88, { size: 46 });
    const kr = clamp01((t - tTicket - 0.7) / 0.8), n = Math.max(1, Math.round(lerp(1, 600, 1 - Math.pow(1 - kr, 3))));
    const big = `1 in ${n}`, bounce = 1 + 0.12 * Math.max(0, Math.sin(clamp01((t - tRollEnd) / 0.3) * PI));
    withT(0, 30, bounce, 0, () => { txt(big, 0, 6, { font: 'Lilita One', weight: 400, size: 140, color: '#5a0f3a', stroke: '#5a0f3a', lw: 16 }); txt(big, 0, 0, { font: 'Lilita One', weight: 400, size: 140, color: NEON.pink, stroke: '#5a0f3a', lw: 9 }); txt(big, 0, 0, { font: 'Lilita One', weight: 400, size: 140, color: NEON.pink }); });
    txt('chance of being born in Florida', 0, 124, { size: 38 });
    txt('CDC Florida births vs UN world births, 2023', 0, 180, { font: 'Patrick Hand', weight: 400, size: 30, color: '#7d7468' });
    const ks = backOut(clamp01((t - tRollEnd - 0.15) / 0.22), 3);
    if (ks > 0) withT(-282, -150, 1.45 - 0.6 * ks, -0.2, () => { c.globalAlpha = Math.min(1, ks * 1.5); c.strokeStyle = '#2f6fb5'; c.lineWidth = 9; rr(-80, -40, 160, 80, 14); c.stroke(); txt('BOY', 0, 3, { font: 'Lilita One', weight: 400, size: 58, color: '#2f6fb5' }); c.globalAlpha = 1; });
  });
  if (t > tRollEnd) for (let i = 0; i < 8; i++) { const a = i / 8 * PI * 2 + 0.3, k = (Math.sin((t - tRollEnd) * 6 + i * 1.7) + 1) / 2, x = W / 2 + Math.cos(a) * 430, y = 640 + Math.sin(a) * 290, r = 10 + 14 * k; c.fillStyle = i % 2 ? NEON.yellow : '#ffffff'; c.beginPath(); for (let j = 0; j < 8; j++) { const rr_ = j % 2 ? r * 0.35 : r; c.lineTo(x + Math.cos(j * PI / 4) * rr_, y + Math.sin(j * PI / 4) * rr_); } c.closePath(); c.fill(); }
});
sfx('whoosh', tTicket + 0.2, 0.5); for (let i = 0; i < 5; i++) sfx('flicker', tTicket + 0.5 + i * 0.12, 0.12);
for (let i = 0; i < 12; i++) sfx('tick', tTicket + 0.7 + 0.8 * (1 - Math.pow(1 - i / 12, 2)), 0.25);
sfx('ding', tRollEnd, 0.5); sfx('stamp', tRollEnd + 0.15, 0.7);

// ================================================================ 3. FAMILY: 220,000 babies; "Your name is Mateo… Teo"
const tBabies = ln('s02', 2), tName = ln('s02', 3), tTeo = w('s02', 'teo');
function baby() { ellipse(0, -10, 48, 34, '#fdf2f7', PAL.ink, 5); circle(-26, -26, 24, SK[1], PAL.ink, 5); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.beginPath(); c.arc(-26, -22, 8, 0.2 * PI, 0.8 * PI); c.stroke(); }
function windowPalm(t) { c.save(); rr(706, 126, 288, 368, 8); c.clip(); const g = c.createLinearGradient(0, 126, 0, 494); g.addColorStop(0, '#7fd3f0'); g.addColorStop(1, '#ffd9a8'); c.fillStyle = g; c.fillRect(706, 126, 288, 368); palm(800, 560, 0.6, t, { lean: 0.2 }); c.restore(); c.strokeStyle = PAL.ink; c.lineWidth = 8; c.strokeRect(700, 120, 300, 380); c.beginPath(); c.moveTo(850, 120); c.lineTo(850, 500); c.moveTo(700, 310); c.lineTo(1000, 310); c.stroke(); }
scene(tBabies, ln('s03', 0), (t) => {
  room({ wall: '#ffd1dc', stripe: '#05a8b8', floor: '#e6d3bd' }); windowPalm(t);
  const cheer = Math.sin(t * 6) * 0.2;
  person(250, 1640, 1.05, assign(NAN, { la: 2.4 + cheer, ra: 2.4 - cheer, mouth: 'grin' }), t);
  person(560, 1660, 1.1, assign(MUM, { la: 1.35, ra: 1.35, elbow: 1.2, hold: { side: -1, draw: baby } }), t);
  person(860, 1650, 1.12, assign(DAD, { la: 2.6 + cheer, ra: 2.5 - cheer, mouth: 'grin' }), t);
  card(W / 2, 520, 620, 300, { big: '220,000', l1: 'babies born in', l2: 'Florida a year', src: 'CDC, 2023 (approx.)', accent: NEON.pink }, pop(t, tBabies + 0.2));
  const kn = pop(t, tName + 0.1);
  if (kn > 0) {
    withT(440, 1000, kn, -0.06, () => {
      rr(-140, -50, 280, 100, 20); fs('#ffd319', PAL.ink, 6);
      txt('Mateo', 0, 4, { font: 'Patrick Hand', weight: 400, size: 70 });
      const ks = clamp01((t - tTeo + 0.15) / 0.25); if (ks > 0) { c.strokeStyle = PAL.red; c.lineWidth = 10; c.beginPath(); c.moveTo(-110, 6); c.lineTo(-110 + 220 * ks, -4); c.stroke(); }
    });
    const kg = pop(t, tTeo);
    if (kg > 0) withT(700, 950, kg, 0.08, () => { rr(-110, -54, 220, 108, 22); fs(NEON.pink, PAL.ink, 7); txt('Teo', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff', stroke: PAL.ink, lw: 8 }); txt('Teo', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff' }); });
  }
});
sfx('cheer', tBabies + 0.1, 0.5); sfx('pop', tBabies + 0.2, 0.5); sfx('pop', tName + 0.1, 0.5); sfx('scratch', tTeo - 0.15, 0.4); sfx('pop', tTeo, 0.6);

// ================================================================ 4. JULIA TUTTLE; ART DECO; SUNNY-DAY FLOODS
const tTuttle = S('s03'), tDeco = ln('s03', 1), tFlood = ln('s03', 2);
const tophat = (headY, headR) => { rr(-headR - 14, headY - headR + 10, headR * 2 + 28, 16, 8); fs('#1d1d1f', PAL.ink, 5); rr(-headR + 8, headY - headR - 80, headR * 2 - 16, 94, 8); fs('#1d1d1f', PAL.ink, 5); c.fillStyle = '#7a2a30'; c.fillRect(-headR + 10, headY - headR - 8, headR * 2 - 20, 12); };
scene(tTuttle, tDeco, (t) => {
  c.fillStyle = '#e9d8b8'; c.fillRect(0, 0, W, H); const vg = c.createRadialGradient(W / 2, 800, 300, W / 2, 800, 1200); vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(90,60,30,.45)'); c.fillStyle = vg; c.fillRect(0, 0, W, H);
  c.fillStyle = 'rgba(120,90,50,.12)'; for (let y = 0; y < H; y += 60) c.fillRect(0, y, W, 4);
  const kf = pop(t, tTuttle + 0.05, 0.45);
  withT(W / 2, 720, kf, -0.02, () => {
    rr(-270, -330, 540, 660, 30); fs('#c9a34a', PAL.ink, 8); rr(-240, -300, 480, 600, 22); fs('#b8902e', PAL.ink, 5);
    c.save(); rr(-220, -280, 440, 560, 16); c.clip(); c.fillStyle = '#cdb48a'; c.fillRect(-220, -280, 440, 560);
    person(0, 500, 1.3, { skin: '#e8c9a0', hair: 'bun', hairColor: '#4a3426', shirt: '#4d3b5c', dress: '#4d3b5c', pants: '#4d3b5c', la: 0.3, ra: 0.3, mouth: 'smile', bob: 0.3, ph: 0.4, hat: (hy) => { c.fillStyle = '#ffffff'; rr(-30, hy + 54, 60, 26, 8); c.fill(); } }, t);
    c.fillStyle = 'rgba(120,80,30,.18)'; c.fillRect(-220, -280, 440, 560); c.restore();
    rr(-170, 300, 340, 70, 12); fs('#e8cf7a', PAL.ink, 6); txt('JULIA TUTTLE', 0, 337, { font: 'Lilita One', weight: 400, size: 44, color: '#5a3d12' });
  });
  title('founded by a woman', W / 2, 200, pop(t, w('s03', 'woman') - 0.1), 86);
  card(W / 2, 1235, 400, 220, { big: '1896', l1: 'Miami founded', src: '"Mother of Miami"', bigSize: 96, accent: NEON.pink }, pop(t, w('s03', 'founded') - 0.05), 0.04);
  const km = pop(t, w('s03', 'woman'));
  if (km > 0) for (const [x, fl] of [[130, false], [960, true]]) person(x, 1560, 0.85 * km, { skin: SK[0], hair: 'short', hairColor: '#5a4a3a', tache: '#5a4a3a', shirt: '#2b2b2b', pattern: 'suit', tie: '#7a2a30', pants: '#2b2b2b', eyes: 'wide', mouth: 'open', flip: fl, la: 2.6, ra: 0.3, hat: tophat, ph: x }, t);
});
sfx('pop', tTuttle + 0.05, 0.5); sfx('pop', w('s03', 'founded') - 0.05, 0.4); sfx('stamp', w('s03', 'woman') - 0.1, 0.5); sfx('boing', w('s03', 'woman'), 0.3, { pitch: 1.3 });
scene(tDeco, tFlood, (t, lt) => {
  synthSky(1330, '#1a0638', '#5b1a7a', '#ff6f91'); stars(t, 500, 40);
  decoStrip(1330, t, { night: 1, rise: i => backOut(clamp01((t - tDeco - (i === 9 ? 0 : 0.05 + i * 0.07)) / 0.4), 2.2), signOn: i => flick(t, tDeco + 0.45 + i * 0.22, i + 5) });
  c.fillStyle = '#e8a0b8'; c.fillRect(0, 1330, W, 80); c.fillStyle = '#2a2140'; c.fillRect(0, 1410, W, H - 1410); c.fillStyle = 'rgba(255,255,255,.6)'; for (let x = -((lt * 300) % 160); x < W; x += 160) c.fillRect(x, 1640, 80, 10);
  convertible(lerp(-300, W + 300, clamp01((t - tDeco - 0.6) / 3.2)), 1530, 0.9, NEON.hot, t, tt => person(-40, -40, 0.3, assign(TEO_TEEN, { hat: shades(), la: 2.8, ra: 0.4, bob: 0 }), tt));
  palm(60, 1420, 0.95, t, { lean: 0.1 }); palm(1020, 1420, 0.9, t + 1.5, { lean: -0.1 });
  const kt = pop(t, w('s03', 'art') - 0.1);
  if (kt > 0) withT(W / 2, 200, kt, -0.03, () => neonText('Art Deco', 0, 0, { size: 118, font: 'Monoton', col: NEON.pink, alpha: flick(t, w('s03', 'art') - 0.1, 30) }));
  card(W / 2, 460, 600, 270, { big: '800+', l1: 'Art Deco buildings', src: 'Miami Design Preservation League', accent: NEON.teal }, pop(t, w('s03', 'biggest') - 0.05));
});
for (let i = 0; i < 5; i++) sfx('flicker', tDeco + 0.45 + i * 0.22, 0.15);
sfx('pop', w('s03', 'biggest') - 0.05, 0.5); sfx('shimmer', w('s03', 'art') - 0.1, 0.4); sfx('engine', tDeco + 0.6, 0.25, { dur: 3 });
scene(tFlood, S('s04'), (t, lt) => {
  outdoor({ horizon: 1150, skyTop: '#55c2f0', sky: '#bdeafc', ground: '#cfc1a8' });
  withT(830, 280, 1, 0, () => { c.save(); c.rotate(t * 0.3); for (let i = 0; i < 12; i++) { c.rotate(PI / 6); c.fillStyle = '#ffd319'; c.beginPath(); c.moveTo(-14, -120); c.lineTo(0, -170); c.lineTo(14, -120); c.fill(); } c.restore(); circle(0, 0, 110, '#ffd319', PAL.ink, 7); shades('#1d1d1f', '#ff2a6d')(-14); c.strokeStyle = PAL.ink; c.lineWidth = 7; c.beginPath(); c.arc(0, 30, 40, 0.2 * PI, 0.8 * PI); c.stroke(); });
  hand('not a cloud in the sky', 330, 250, pop(t, w('s03', 'sunny') - 0.05), 62, '#ffffff', -0.05);
  withT(0, 120, 0.82, 0, () => decoStrip(1260, t, { towers: false, signOn: () => 0.8 }));
  // the water rises out of the drains
  const kw = ss(tFlood + 0.4, tFlood + 2.6, t), wy = lerp(1560, 1250, kw);
  car(760, 1440 + 20, 1.0, '#ffd319', null, t);
  person(260, 1520, 1.05, assign(DAD, { hat: shades(), mouth: kw > 0.5 ? 'frown' : 'flat', eyes: kw > 0.5 ? 'angry' : 'open', la: 0.3, ra: 1.3, elbow: 1.3, hold: { side: 1, draw: tt => cafecito(0, -10, 0.6, tt) } }), t);
  c.fillStyle = 'rgba(40,150,200,.62)'; c.beginPath(); c.moveTo(0, H); for (let x = 0; x <= W; x += 30) c.lineTo(x, wy + Math.sin(x / 60 + t * 3) * 8); c.lineTo(W, H); c.closePath(); c.fill();
  c.strokeStyle = 'rgba(255,255,255,.7)'; c.lineWidth = 5; c.beginPath(); for (let x = 0; x <= W; x += 30) c.lineTo(x, wy + Math.sin(x / 60 + t * 3) * 8); c.stroke();
  // drain fountain
  const kd = ss(tFlood + 0.2, tFlood + 0.6, t);
  if (kd > 0) { const dx = 520; c.strokeStyle = 'rgba(160,220,255,.9)'; c.lineWidth = 10; c.lineCap = 'round'; for (let i = 0; i < 5; i++) { const a = -PI / 2 + (i - 2) * 0.28, v = 260 * kd * (0.8 + 0.2 * Math.sin(t * 9 + i)); c.beginPath(); for (let k = 0; k <= 12; k++) { const u = k / 12 * 1.2; c.lineTo(dx + Math.cos(a) * v * u, wy - 10 + Math.sin(a) * v * u + 220 * u * u); } c.stroke(); } }
  // fish jump out of the street
  for (let i = 0; i < 2; i++) { const ph = (lt * 0.7 + i * 0.5) % 1, fx = 640 + i * 260 + ph * 120, fy = wy - Math.sin(ph * PI) * 220; if (kw > 0.4) withT(fx, fy, 0.9, (ph - 0.5) * 2, () => { ellipse(0, 0, 40, 20, NEON.orange, PAL.ink, 5); c.beginPath(); c.moveTo(-36, 0); c.lineTo(-64, -18); c.lineTo(-64, 18); c.closePath(); fs(NEON.orange, PAL.ink, 5); circle(22, -5, 5, PAL.ink, null, 0); }); }
  title('sunny day floods', W / 2, 520, pop(t, w('s03', 'flood') - 0.05), 100);
});
sfx('splash', tFlood + 0.3, 0.6); sfx('pop', w('s03', 'flood') - 0.05, 0.5); sfx('hiss', w('s03', 'drains') - 0.2, 0.4); sfx('splash', tFlood + 2.2, 0.4);

// ================================================================ 5. IGUANAS: cold snap, frozen lizards fall; "what the f***, Miami?"
const tCold = S('s04'), tRainL = ln('s04', 1), tFreeze = w('s04', 'freeze'), tFall = w('s04', 'fall');
function fallY(dt, y0, ground, g = 2600) { if (dt <= 0) return y0; const tg = Math.sqrt(2 * (ground - y0) / g); if (dt < tg) return y0 + 0.5 * g * dt * dt; const u = dt - tg, v = g * tg * 0.25, b = Math.max(0, v * u - 0.5 * g * u * u); return ground - b; }
function coldPark(t) {
  outdoor({ horizon: 1250, skyTop: '#9cc3e6', sky: '#e3eef8', ground: '#a9c9b0' });
  c.fillStyle = 'rgba(255,255,255,.55)'; for (let i = 0; i < 8; i++) ellipse(70 + i * 140, 1270 + (i % 2) * 30, 80, 14, 'rgba(255,255,255,.6)', null, 0);
  cloudPuff(160, 230, 0.7, '#f2f6fa'); cloudPuff(900, 330, 0.6, '#f2f6fa');
  palm(230, 1420, 0.95, t, { lean: 0.15 }); palm(850, 1420, 0.95, t + 1, { lean: -0.15 });
}
scene(tCold, tRainL, (t) => {
  coldPark(t);
  const fr = t > tFreeze;
  [[300, 880, 0.8, false, 0], [790, 880, 0.8, true, 0.18]].forEach(([x, y, s, fl, d], i) => {
    const dt = t - tFall - d, yy = fallY(dt, y, 1390), rot = dt > 0 ? Math.min(PI, dt * 9) : 0;
    iguana(x + (dt > 0 ? (fl ? -1 : 1) * dt * 60 : 0), yy, s, { frozen: fr, flip: fl, rot: fl ? -rot : rot, t, ph: i });
    if (dt > 0 && dt < 0.8 && Math.abs(yy - 1390) < 4) { c.globalAlpha = 0.7; cloudPuff(x, 1410, 0.3, '#ffffff'); c.globalAlpha = 1; }
  });
  const kc = ss(tCold + 0.3, tFreeze, t);
  thermometer(960, 1180, 0.75, lerp(0.85, 0.22, kc), kc > 0.9 ? '40°' : '', kc > 0.6 ? '#4a90d9' : PAL.red);
  title('cold snap', W / 2, 200, pop(t, w('s04', 'cold') - 0.05), 110, { color: '#9fe2ff' });
  card(W / 2, 470, 620, 300, { big: '~40°F', l1: 'iguanas go stiff', l2: 'and drop out of trees', src: 'Florida Fish & Wildlife (FWC)', accent: '#2f8fd8' }, pop(t, tFreeze - 0.05));
  if (fr) { c.fillStyle = 'rgba(200,230,255,.12)'; c.fillRect(0, 0, W, H); }
});
sfx('pop', w('s04', 'cold') - 0.05, 0.4); sfx('shimmer', tFreeze - 0.05, 0.5); sfx('pop', tFreeze - 0.05, 0.4); sfx('whoosh', tFall, 0.4); sfx('thunk', tFall + 0.45, 0.6); sfx('thunk', tFall + 0.62, 0.5);
const RAINERS = (() => { const R = mulberry32(31); return Array.from({ length: 13 }, (_, i) => ({ x: 60 + R() * 960, d: i * 0.17 + R() * 0.1, s: 0.38 + R() * 0.2, sp: (R() - 0.5) * 10, fl: R() > 0.5 })); })();
scene(tRainL, S('s05'), (t) => {
  coldPark(t);
  const brolly = (tt) => { c.strokeStyle = PAL.ink; c.lineWidth = 8; c.beginPath(); c.moveTo(0, 0); c.lineTo(0, -230); c.stroke(); c.beginPath(); c.arc(0, -230, 200, PI, 0); c.closePath(); fs('#ff4fa3', PAL.ink, 7); for (let k = 1; k < 4; k++) { c.beginPath(); c.moveTo(0, -430); c.quadraticCurveTo(-200 + k * 100 - 40, -330, -200 + k * 100, -230); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.stroke(); } };
  person(540, 1700, 1.1, assign(DAD, { mouth: 'shout', eyes: 'angry', la: 0.3, ra: 2.9, elbow: 0.1, hold: { side: 1, draw: brolly } }), t);
  RAINERS.forEach((r, i) => {
    const dt = t - tRainL - r.d; if (dt <= 0) return;
    const under = Math.abs(r.x - 560) < 220, ground = under ? 1010 : 1440, y = fallY(dt, -120, ground, 2400);
    const x = r.x + (under && y >= ground - 6 ? (r.x < 560 ? -1 : 1) * Math.min(260, (dt - Math.sqrt(2 * (ground + 120) / 2400)) * 500) : 0);
    iguana(x, under && x !== r.x ? y + Math.min(430, Math.abs(x - r.x) * 1.6) : y, r.s, { frozen: true, flip: r.fl, rot: dt * r.sp, t });
  });
  bubble(W / 2, 330, 'WHAT THE #@%!, MIAMI?!', pop(t, w('s04', 'what') - 0.05), { size: 60, maxW: 860, color: PAL.red });
});
RAINERS.forEach(r => sfx('thunk', tRainL + r.d + 0.55, 0.25));
sfx('pop', w('s04', 'what') - 0.05, 0.5); sfx('boing', tRainL + 0.6, 0.3); sfx('boing', tRainL + 1.1, 0.3, { pitch: 1.2 });

// ================================================================ 6. AGE 5: first cafecito; rocket fuel; no sleep for a week
const tCafe = S('s05'), tRocket = ln('s05', 1), tSleep = w('s05', 'sleep');
const serverInside = tt => person(560, 1215, 0.95, assign(SERVER, { mouth: 'grin', la: 0.3, ra: 0.3 }), tt);
scene(tCafe, tRocket, (t) => {
  ventanita(t, { inside: serverInside, signOn: flick(t, tCafe + 0.1, 3) });
  const kc = pop(t, w('s05', 'cafecito') - 0.05);
  if (kc > 0) cafecito(640, 1006, 0.9 * kc, t);
  person(400, 1720, 1.3, assign(TEO_KID, { mouth: 'open', eyes: 'wide', la: 0.3, ra: 2.7, walk: 0 }), t);
  person(800, 1700, 1.1, assign(DAD, { hat: shades(), mouth: 'grin', la: 0.3, ra: 1.4, elbow: 1.3, hold: { side: 1, draw: tt => cafecito(0, -10, 0.55, tt) } }), t);
  title('age 5', W / 2, 160, pop(t, tCafe + 0.05), 96);
});
sfx('flicker', tCafe + 0.1, 0.3); sfx('pop', w('s05', 'cafecito') - 0.05, 0.5); sfx('clink', w('s05', 'cafecito'), 0.4);
scene(tRocket, tSleep - 0.1, (t, lt) => {
  const k = ss(tRocket, tSleep, t);
  const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, lerp(0, 1, k) > 0.5 ? '#0d0221' : '#3a8fd8'); g.addColorStop(1, k > 0.5 ? '#3a0b5e' : '#bdeafc'); c.fillStyle = g; c.fillRect(0, 0, W, H);
  if (k > 0.3) stars(t, H, 80);
  for (let i = 0; i < 5; i++) { const y = ((lt * 900 + i * 420) % 2200) - 200; c.globalAlpha = Math.max(0, 1 - k * 1.3); cloudPuff(120 + (i * 230) % 900, y, 0.9, '#ffffff'); c.globalAlpha = 1; }
  c.strokeStyle = 'rgba(255,255,255,.6)'; c.lineWidth = 6; c.lineCap = 'round'; const R = mulberry32(Math.floor(t * 20)); for (let i = 0; i < 14; i++) { const x = R() * W, y = R() * H; c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + 120 + R() * 160); c.stroke(); }
  const ry = lerp(1500, 980, backOut(clamp01((t - tRocket) / 0.8))) + Math.sin(t * 30) * 6;
  rocketCup(W / 2, ry, 1.6, t, Math.sin(t * 7) * 0.05);
  person(W / 2, ry - 100, 0.8, assign(TEO_KID, { seated: true, eyes: 'wide', mouth: 'grin', la: 2.8, ra: 2.8, hair: 'spiky', bob: 0 }), t);
  title('rocket fuel', W / 2, 230, pop(t, w('s05', 'rocket') - 0.05), 110, { color: NEON.yellow });
});
sfx('blowout', tRocket + 0.05, 0.4); sfx('riser', tRocket, 0.5); sfx('rumble', tRocket + 0.1, 0.6); sfx('pop', w('s05', 'rocket') - 0.05, 0.4);
const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
scene(tSleep - 0.1, S('s06'), (t, lt) => {
  room({ wall: '#2b2a5c', floor: '#3b3570', stripe: '#ff4fa3', window: false });
  rr(700, 140, 300, 340, 12); fs('#0d0221', PAL.ink, 8); circle(890, 250, 50, '#fff6cf', null, 0); circle(870, 235, 46, '#0d0221', null, 0);
  // calendar flipping through the week
  const n = Math.min(6, Math.floor(clamp01(lt / Math.max(0.5, S('s06') - tSleep - 0.2)) * 7));
  withT(250, 330, 1, -0.04, () => { rr(-150, -150, 300, 300, 16); fs('#ffffff', PAL.ink, 7); rr(-150, -150, 300, 80, 16); fs(PAL.red, PAL.ink, 7); txt('DAY ' + (n + 1), 0, -110, { font: 'Lilita One', weight: 400, size: 46, color: '#fff' }); txt(DAYS[n], 0, 40, { font: 'Lilita One', weight: 400, size: 100 }); });
  // bed
  rr(380, 1300, 640, 120, 20); fs('#ff8fab', PAL.ink, 7); rr(380, 1180, 80, 260, 14); fs('#b967ff', PAL.ink, 7); ellipse(540, 1300, 80, 34, '#ffffff', PAL.ink, 5);
  const jit = Math.sin(t * 60) * 5;
  person(300 + jit, 1700, 1.25, assign(TEO_KID, { shirt: '#9be3c9', pattern: null, pants: '#9be3c9', shorts: false, eyes: 'wide', mouth: 'grin', la: 2.5 + Math.sin(t * 20) * 0.2, ra: 2.5 - Math.sin(t * 20) * 0.2, hair: 'spiky', bob: 0 }), t);
  withT(820, 820, 1, 0, () => { circle(0, 0, 110, '#ffffff', PAL.ink, 7); c.strokeStyle = PAL.ink; c.lineWidth = 8; c.lineCap = 'round'; c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.cos(t * 9) * 70, Math.sin(t * 9) * 70); c.moveTo(0, 0); c.lineTo(Math.cos(t * 0.75) * 46, Math.sin(t * 0.75) * 46); c.stroke(); });
});
for (let i = 0; i < 7; i++) sfx('tick', tSleep + i * Math.max(0.5, S('s06') - tSleep - 0.2) / 7, 0.3);
sfx('boing', tSleep, 0.3, { pitch: 1.4 });

// ================================================================ 7. AGE 16: hurricane; the family argues; Nan refuses (Andrew '92); "get in the car"
const tHur = S('s06'), tNan = ln('s06', 1), tCar = ln('s06', 2);
scene(tHur, tNan, (t, lt) => {
  room({ wall: '#cfd8e3', stripe: '#ff4fa3', floor: '#c9b9a3', window: false });
  boardedWindow(60, 300, 220, 330); boardedWindow(800, 300, 220, 330);
  // TV with the storm heading for Miami
  rr(300, 270, 480, 360, 20); fs('#2b2622', PAL.ink, 8);
  c.save(); rr(322, 292, 436, 316, 10); c.clip(); c.fillStyle = '#0d0221'; c.fillRect(322, 292, 436, 316);
  usMap({ zoom: 4.2, focus: [-82.5, 27.6], to: [540, 450], kz: 1, t, fl: 1, lw: 0.6 });
  const hk = clamp01(lt / 3.5); hurricane(lerp(760, 610, hk), lerp(380, 470, hk), 90, t, 0.95);
  c.restore();
  withT(700, 320, 1, 0, () => { rr(-62, -24, 124, 48, 10); fs(PAL.red, PAL.ink, 4); txt('CAT 4', 0, 2, { font: 'Lilita One', weight: 400, size: 34, color: '#fff' }); });
  rr(500, 630, 80, 40, 6); fs('#2b2622', PAL.ink, 6);
  person(250, 1700, 1.05, assign(MUM, { mouth: 'shout', eyes: 'angry', la: 2.6 + Math.sin(t * 9) * 0.15, ra: 0.4 }), t);
  person(830, 1700, 1.08, assign(DAD, { mouth: 'shout', eyes: 'angry', flip: true, la: 2.6 + Math.sin(t * 8) * 0.15, ra: 0.4 }), t);
  person(540, 1720, 0.98, assign(TEO_TEEN, { mouth: 'wavy', eyes: 'wide', la: 2.2, ra: 2.2 }), t);
  bubble(270, 830, "We're leaving!", pop(t, w('s06', 'argues') - 0.05), { size: 46, tail: 'down' });
  bubble(800, 900, "No we're bloody not!", pop(t, w('s06', 'leaving') - 0.05), { size: 46, tail: 'down', maxW: 460 });
  title('age 16', W / 2, 170, pop(t, tHur + 0.05), 96);
});
sfx('rain', tHur, 0.35, { dur: tNan - tHur + 3 }); sfx('pop', w('s06', 'argues') - 0.05, 0.4); sfx('pop', w('s06', 'leaving') - 0.05, 0.4); sfx('stinger', tHur + 0.1, 0.3, { soft: 1 });
function rocker(x, y, s, ang, who, t) {
  withT(x, y, s, ang, () => {
    c.strokeStyle = PAL.ink; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.arc(0, -1200, 1260, PI / 2 - 0.2, PI / 2 + 0.2); c.stroke(); c.strokeStyle = '#8b5a2b'; c.lineWidth = 8; c.stroke();
    rr(-170, -560, 34, 520, 10); fs('#8b5a2b', PAL.ink, 6); rr(136, -560, 34, 520, 10); fs('#8b5a2b', PAL.ink, 6);
    rr(-170, -600, 340, 60, 20); fs('#a0703a', PAL.ink, 6);
    who();
    rr(-180, -150, 360, 40, 12); fs('#a0703a', PAL.ink, 6); rr(-160, -110, 26, 110, 6); fs('#8b5a2b', PAL.ink, 5); rr(134, -110, 26, 110, 6); fs('#8b5a2b', PAL.ink, 5);
  });
}
scene(tNan, tCar, (t) => {
  room({ wall: '#d9e6da', stripe: '#ff901f', floor: '#c9b9a3', window: false });
  rr(640, 160, 380, 440, 12); fs('#3a4c63', PAL.ink, 8); c.save(); rr(648, 168, 364, 424, 8); c.clip(); c.fillStyle = '#4a5f7a'; c.fillRect(648, 168, 364, 424); palm(760, 760, 0.62, t, { lean: 0.5, wind: 0.6 + 0.2 * Math.sin(t * 3) }); rain(t, { n: 30, angle: 0.5 }); c.restore();
  const ang = Math.sin(t * 2.4) * 0.06;
  rocker(540, 1660, 1.0, ang, () => person(0, -110, 1.0, assign(NAN, { seated: true, mouth: 'flat', eyes: 'angry', la: 1.5, ra: 1.5, elbow: 1.7, bob: 0 }), t), t);
  card(330, 520, 520, 290, { big: 'Andrew', l1: '1992, Category 5', src: 'NOAA National Hurricane Center', bigSize: 96, accent: PAL.red }, pop(t, w('s06', 'andrew') - 0.1), -0.04);
  bubble(560, 880, 'I survived Andrew, mijo.', pop(t, w('s06', 'refuses') - 0.05), { size: 48, maxW: 600 });
});
sfx('creak', tNan, 0.4); sfx('pop', w('s06', 'refuses') - 0.05, 0.4); sfx('stamp', w('s06', 'andrew') - 0.1, 0.5);
scene(tCar, S('s07'), (t, lt) => {
  outdoor({ horizon: 1250, skyTop: '#2b3445', sky: '#55627a', ground: '#4f6b55' });
  const fl = Math.max(0, Math.sin(t * 2.3) > 0.97 ? 1 : 0); if (fl) { c.fillStyle = 'rgba(255,255,255,.35)'; c.fillRect(0, 0, W, H); }
  for (let i = 0; i < 3; i++) cloudPuff(((lt * 300 + i * 400) % 1500) - 200, 200 + i * 110, 1.1, '#3a4458');
  palm(30, 1330, 0.9, t, { lean: 0.35, wind: 0.7 + 0.25 * Math.sin(t * 4) }); palm(980, 1300, 0.7, t, { lean: 0.6, wind: 0.7 + 0.25 * Math.sin(t * 4 + 1) });
  car(800, 1560, 1.1, NEON.hot, null, t);
  const wob = Math.sin(t * 7) * 0.08;
  person(430, 1720, 1.05, assign(TEO_TEEN, { mouth: 'shout', eyes: 'angry', la: 2.85, ra: 2.85, elbow: 0.2, lean: wob * 0.5 }), t);
  rocker(440 + Math.sin(t * 7) * 10, 1150, 0.62, wob, () => person(0, -110, 1.0, assign(NAN, { seated: true, mouth: 'frown', eyes: 'angry', la: 1.5, ra: 1.5, elbow: 1.7, bob: 0 }), t), t);
  rain(t, { n: 90, angle: 0.5 });
  c.strokeStyle = 'rgba(255,255,255,.4)'; c.lineWidth = 6; c.lineCap = 'round'; for (let i = 0; i < 6; i++) { const y = 400 + i * 150, x = ((lt * 1400 + i * 300) % 1600) - 300; c.beginPath(); c.moveTo(x, y); c.quadraticCurveTo(x + 120, y - 20, x + 240, y); c.stroke(); }
  bubble(W / 2, 330, "GET IN THE BLOODY CAR, NAN, FOR #@%!'S SAKE!", pop(t, tCar + 0.05), { size: 54, maxW: 900, color: PAL.red });
});
sfx('rain', tCar, 0.5, { dur: S('s07') - tCar + 0.5 }); sfx('rumble', tCar + 0.2, 0.5); sfx('pop', tCar + 0.05, 0.5); sfx('horn', tCar + 1.0, 0.3);

// ================================================================ 8. STONE CRAB (Oct–May) and CUBAN SANDWICHES
const tCrab = S('s07'), tCubano = ln('s07', 1);
const MONTHS = 'JFMAMJJASOND';
scene(tCrab, tCubano, (t) => {
  room({ wall: '#ffe6c7', stripe: '#05a8b8', floor: '#d6b48a', window: false });
  rr(0, 1230, W, 60, 6); fs('#ffffff', PAL.ink, 6); c.fillStyle = '#f6c9d6'; c.fillRect(0, 1290, W, H - 1290);
  crabPlate(520, 1290, 1.05 * pop(t, tCrab + 0.1));
  const kcal = pop(t, w('s07', 'october') - 0.1);
  if (kcal > 0) withT(270, 600, kcal, -0.04, () => {
    rr(-200, -200, 400, 420, 18); fs('#ffffff', PAL.ink, 7); rr(-200, -200, 400, 80, 18); fs(NEON.teal, PAL.ink, 7); txt('SEASON', 0, -160, { font: 'Lilita One', weight: 400, size: 46, color: '#fff' });
    for (let i = 0; i < 12; i++) { const x = -135 + (i % 4) * 90, y = -60 + Math.floor(i / 4) * 100, on = i >= 9 || i <= 4, ki = clamp01((t - w('s07', 'october') - i * 0.05) / 0.2); rr(x - 36, y - 36, 72, 72, 12); fs(on ? (ki > 0 ? NEON.orange : '#eeeeee') : '#dddddd', PAL.ink, 4); txt(MONTHS[i], x, y + 2, { font: 'Lilita One', weight: 400, size: 44, color: on ? '#fff' : '#9a9a9a' }); if (!on && ki > 0) { c.strokeStyle = PAL.red; c.lineWidth = 7; c.beginPath(); c.moveTo(x - 24, y - 24); c.lineTo(x + 24, y + 24); c.stroke(); } }
  });
  card(760, 640, 440, 270, { big: 'Oct–May', l1: 'stone crab season', src: 'Florida Fish & Wildlife', bigSize: 88, accent: NEON.orange }, pop(t, w('s07', 'season') - 0.15), 0.04);
  title('stone crab', W / 2, 200, pop(t, w('s07', 'stone') - 0.05), 110);
  const kk = pop(t, w('s07', 'may'));
  if (kk > 0) crab(890, 1100 + Math.abs(Math.sin(t * 8)) * -10, 0.75 * kk, t);
});
sfx('pop', tCrab + 0.1, 0.4); sfx('pop', w('s07', 'stone') - 0.05, 0.4); for (let i = 0; i < 12; i++) sfx('tick', w('s07', 'october') + i * 0.05, 0.15); sfx('pop', w('s07', 'season') - 0.15, 0.4); sfx('squawk', w('s07', 'may'), 0.3, { pitch: 1.6 });
scene(tCubano, S('s08'), (t) => {
  room({ wall: '#fff1c7', stripe: NEON.hot, floor: '#d6b48a', window: false });
  for (let i = 0; i < 4; i++) { c.fillStyle = i % 2 ? '#ffe39a' : '#fff1c7'; }
  const ks = backOut(clamp01((t - tCubano - 0.15) / 0.5));
  person(250, 1700, 1.15, assign(TEO_TEEN, { mouth: 'open', eyes: 'wide', la: 0.3, ra: PI / 2 + 0.05, elbow: 0 }), t);
  if (ks > 0) cubano(lerp(1500, 730, ks), 1290, 1.0, 680, 0.02);
  // tape measure along the sandwich
  const km = pop(t, w('s07', 'size') - 0.05);
  if (km > 0) { c.save(); c.globalAlpha = Math.min(1, km); rr(390, 1352, 680 * clamp01(km), 46, 6); fs('#ffd319', PAL.ink, 5); c.fillStyle = PAL.ink; for (let x = 400; x < 390 + 680 * clamp01(km); x += 25) c.fillRect(x, 1352, 4, x % 100 < 25 ? 26 : 14); c.restore(); }
  title('Cuban sandwich', W / 2, 220, pop(t, w('s07', 'cuban') - 0.05), 104);
  hand('bigger than his arm', 690, 1080, pop(t, w('s07', 'arm') - 0.05), 64, NEON.pink, -0.04);
});
sfx('whoosh', tCubano + 0.1, 0.5); sfx('pop', w('s07', 'cuban') - 0.05, 0.4); sfx('scratch', w('s07', 'size') - 0.05, 0.3); sfx('pop', w('s07', 'arm') - 0.05, 0.4);

// ================================================================ 9. AGE 22: New York in flip-flops; "You're from Miami?" "How the f*** did you know?"
const tNY = S('s08'), tFreezeA = ln('s08', 1), tAre = ln('s08', 2), tKnow = ln('s08', 3);
scene(tNY, tFreezeA, (t, lt) => {
  outdoor({ horizon: 1250, skyTop: '#8f9db3', sky: '#d5dde6', ground: '#eef3f7' });
  nycSkyline(1250, t);
  c.fillStyle = '#eef3f7'; c.fillRect(0, 1250, W, H - 1250); c.fillStyle = '#8a8f99'; c.fillRect(0, 1330, W, 200);
  taxi(W + 300 - ((lt * 380) % (W + 700)), 1500, 0.85, t);
  person(400, 1700, 1.1, assign(TEO, { hat: shades(), mouth: 'grin', la: 0.3, ra: 2.6, wave: 'r' }), t);
  suitcase(620, 1700, 1.0, NEON.pink);
  snow(t, { n: 70 });
  title('age 22', 820, 230, pop(t, tNY + 0.05), 96);
  hand('New York', 280, 230, pop(t, w('s08', 'new') - 0.05), 80, '#ffffff');
});
sfx('whoosh', tNY, 0.4); sfx('horn', tNY + 0.6, 0.3); sfx('pop', w('s08', 'new') - 0.05, 0.4);
scene(tFreezeA, tAre, (t) => {
  outdoor({ horizon: 1250, skyTop: '#a7b4c6', sky: '#e2e8ef', ground: '#f4f7fa' });
  nycSkyline(1250, t);
  c.fillStyle = '#f4f7fa'; c.fillRect(0, 1250, W, H - 1250);
  const jit = Math.sin(t * 50) * 6;
  person(560 + jit, 1720, 1.3, assign(TEO, { skin: '#a9c4e0', mouth: 'wavy', eyes: 'wide', la: 1.3, ra: 1.3, elbow: 1.8, bob: 0 }), t);
  withT(560 + jit, 1720 - 1.3 * 1.4 * 330, 1.3, 0, () => { c.fillStyle = '#dff4ff'; c.strokeStyle = PAL.ink; c.lineWidth = 3; for (const dx of [-12, 10]) { c.beginPath(); c.moveTo(dx - 6, 30); c.lineTo(dx, 58); c.lineTo(dx + 6, 30); c.closePath(); c.fill(); c.stroke(); } });
  // flip-flop close-up inset
  const ki = pop(t, w('s08', 'flipflops') - 0.1);
  if (ki > 0) withT(270, 720, ki, 0, () => {
    circle(0, 0, 200, '#f4f7fa', PAL.ink, 8); c.save(); c.beginPath(); c.arc(0, 0, 194, 0, PI * 2); c.clip();
    ellipse(0, 60, 150, 70, '#ffffff', null, 0); ellipse(10, 30, 120, 52, NEON.pink, PAL.ink, 6); ellipse(10, 10, 100, 46, '#a9c4e0', PAL.ink, 6);
    for (let i = 0; i < 5; i++) circle(-60 + i * 30, -30 + Math.abs(i - 1) * 4, 16 - i * 1.5, '#a9c4e0', PAL.ink, 4);
    c.strokeStyle = NEON.pink; c.lineWidth = 12; c.beginPath(); c.moveTo(-40, -20); c.lineTo(20, 20); c.lineTo(80, -10); c.stroke();
    snow(t, { n: 25, seed: 9 }); c.restore();
  });
  thermometer(900, 1150, 0.8, 0.12, '20°', '#4a90d9');
  snow(t, { n: 110, speed: 180 });
  title('flip-flops?!', W / 2, 230, pop(t, w('s08', 'freezing') - 0.05), 110, { color: '#9fe2ff' });
});
sfx('shimmer', tFreezeA, 0.4); sfx('pop', w('s08', 'freezing') - 0.05, 0.4); sfx('pop', w('s08', 'flipflops') - 0.1, 0.5); sfx('trombone', w('s08', 'flipflops') + 0.3, 0.3);
const NYER = { skin: SK[0], hair: 'short', hairColor: '#5a4a3a', shirt: '#3a3a48', pants: '#22222c', ph: 1.4, hat: beanie('#e63946') };
scene(tAre, S('s09'), (t) => {
  c.fillStyle = '#1e2433'; c.fillRect(0, 0, W, H); c.fillStyle = '#7a3b2e'; for (let y = 0; y < 1180; y += 44) for (let x = (y / 44 % 2) * 50; x < W; x += 100) { c.fillRect(x + 3, y + 3, 94, 38); }
  c.fillStyle = 'rgba(20,24,36,.55)'; c.fillRect(0, 0, W, 1180); c.fillStyle = '#d8dde4'; c.fillRect(0, 1180, W, H - 1180);
  snow(t, { n: 50, seed: 12 });
  const turn = t > tKnow - 0.15;
  if (!turn) { person(540, 1680, 1.25, assign(NYER, { mouth: 'grin', la: 0.2, ra: 2.5, wave: 'r' }), t); bubble(540, 560, "You're from bloody Miami, aren't you?", pop(t, tAre + 0.05), { size: 52, maxW: 820 }); }
  else { person(540, 1680, 1.25, assign(TEO, { hat: shades(), mouth: 'open', eyes: 'wide', la: 1.3, ra: 1.3, elbow: 1.3, hold: { side: 1, draw: tt => cafecito(0, -10, 0.55, tt) } }), t); bubble(540, 560, 'How the #@%! did you bloody know?', pop(t, tKnow - 0.1), { size: 52, maxW: 820, color: PAL.red }); }
});
sfx('pop', tAre + 0.05, 0.4); sfx('pop', tKnow - 0.1, 0.5); sfx('scratch', tKnow - 0.15, 0.3);

// ================================================================ 10. AGE 30: beach wedding to Vale; salsa, DJ, 60 cousins; Mr. 305
const tWed = S('s09'), tParty = ln('s09', 1), t305 = ln('s09', 2);
function beach(t) {
  sunsetSky(1120); retroSun(W / 2, 1060, 230, { glow: 0.5 });
  sea(1100, 1260, t, { col: '#ff8a7a', dark: '#c4508a' });
  c.fillStyle = '#f6d7a7'; c.fillRect(0, 1250, W, H - 1250); c.fillStyle = 'rgba(255,255,255,.4)'; c.fillRect(0, 1250, W, 10);
}
scene(tWed, t305, (t) => {
  beach(t);
  palm(40, 1400, 0.95, t, { lean: 0.15 }); palm(1040, 1400, 0.9, t + 1, { lean: -0.15 });
  const kc = clamp01((t - w('s09', 'sixty') + 0.1) / 0.8), nC = Math.floor(kc * 22);
  for (let i = 0; i < nC; i++) { const x = 60 + (i % 11) * 96 + (Math.floor(i / 11) % 2) * 40, y = 1300 - Math.floor(i / 11) * 60; person(x, y, 0.4, { skin: SK[(i * 3) % 5], hair: ['short', 'long', 'curly', 'spiky', 'bun'][i % 5], hairColor: ['#1d1410', '#3b2a20', '#24160f', '#5a3a22'][i % 4], shirt: [NEON.pink, NEON.teal, NEON.yellow, '#ffffff', NEON.violet][i % 5], pattern: i % 3 ? null : 'floral', pants: '#3b4a6b', la: 2.6 + Math.sin(t * 6 + i) * 0.2, ra: 2.6, ph: i }, t); }
  weddingArch(540, 1500, 1.0, t);
  const kd = pop(t, w('s09', 'dj') - 0.05);
  if (kd > 0) { withT(930, 1560, kd, 0, () => { rr(-130, -170, 260, 170, 12); fs('#2a0f3d', PAL.ink, 6); neonText('DJ', 0, -90, { size: 70, col: NEON.teal, font: 'Lilita One', outline: false }); }); for (let i = 0; i < 4; i++) { const ph = (t * 0.6 + i / 4) % 1; c.globalAlpha = Math.min(1, (1 - ph) * 2); note(900 + Math.sin(ph * 6 + i) * 60, 1300 - ph * 500, 0.9, [NEON.pink, NEON.yellow, NEON.teal, '#ffffff'][i]); c.globalAlpha = 1; } }
  const salsa = t > w('s09', 'salsa') - 0.1;
  person(390, 1700, 1.08, assign(TEO, { shirt: '#ffffff', pattern: 'suit', tie: NEON.pink, pants: '#ffffff', shorts: false, shoes: '#2b2622', mouth: 'grin', la: salsa ? 2.6 + Math.sin(t * 8) * 0.3 : 2.7, ra: 0.5, wave: salsa ? null : 'l', lean: salsa ? Math.sin(t * 8) * 0.08 : 0 }), t);
  person(690, 1700, 1.03, assign(VALE, { veil: true, mouth: 'grin', la: 0.5, ra: salsa ? 2.6 + Math.sin(t * 8 + 1) * 0.3 : 2.7, wave: salsa ? null : 'r', lean: salsa ? Math.sin(t * 8 + PI) * 0.08 : 0 }), t);
  title('age 30', 830, 300, pop(t, tWed + 0.05), 96);
  const kn = pop(t, w('s09', 'valentina') - 0.05);
  if (kn > 0) withT(640, 1060, kn, 0.06, () => { rr(-150, -50, 300, 100, 20); fs('#ffd319', PAL.ink, 6); txt('Valentina', 0, 4, { font: 'Patrick Hand', weight: 400, size: 64 }); const ks = clamp01((t - w('s09', 'vale') + 0.15) / 0.25); if (ks > 0) { c.strokeStyle = PAL.red; c.lineWidth = 10; c.beginPath(); c.moveTo(-120, 6); c.lineTo(-120 + 240 * ks, -4); c.stroke(); } });
  const kv = pop(t, w('s09', 'vale'));
  if (kv > 0) withT(860, 1000, kv, 0.08, () => { rr(-110, -54, 220, 108, 22); fs(NEON.pink, PAL.ink, 7); txt('Vale', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff', stroke: PAL.ink, lw: 8 }); txt('Vale', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff' }); });
  card(W / 2, 560, 520, 220, { big: '60 cousins', bigSize: 88, src: 'roughly', accent: NEON.pink }, pop(t, w('s09', 'cousins') - 0.1));
});
sfx('cheer', tWed + 0.1, 0.5); sfx('scratch', w('s09', 'vale') - 0.15, 0.3); sfx('pop', w('s09', 'vale'), 0.5); sfx('riff', w('s09', 'dj') - 0.1, 0.4); sfx('cheer', w('s09', 'cousins'), 0.6); sfx('pop', w('s09', 'cousins') - 0.1, 0.5);
scene(t305, S('s10'), (t, lt) => {
  synthSky(1420); stars(t, 900); retroSun(W / 2, 1330, 250, { glow: 0.8 }); synthGrid(1420, t);
  palm(40, 1560, 1.0, t, { lean: 0.2, dark: true }); palm(1040, 1560, 1.0, t + 1, { lean: -0.2, dark: true });
  const kM = pop(t, w('s09', 'mister') - 0.1);
  if (kM > 0) withT(W / 2, 330, kM, -0.05, () => neonText('Mister', 0, 0, { size: 120, col: NEON.teal, alpha: flick(t, w('s09', 'mister') - 0.1, 41) }));
  const k3 = pop(t, w('s09', 'threeohfive') - 0.1, 0.5);
  if (k3 > 0) withT(W / 2, 700, k3, 0, () => neonText('305', 0, 0, { size: 330, font: 'Monoton', col: NEON.pink, alpha: flick(t, w('s09', 'threeohfive') - 0.1, 42, 0.6) }));
  const ka = pop(t, w('s09', 'miami') - 0.1);
  if (ka > 0) withT(W / 2, 1000, ka, -0.03, () => neonText("Miami's area code", 0, 0, { size: 76, col: NEON.yellow, alpha: flick(t, w('s09', 'miami') - 0.1, 43) }));
});
sfx('flicker', w('s09', 'mister') - 0.1, 0.4); sfx('flicker', w('s09', 'threeohfive') - 0.1, 0.5); sfx('boom', w('s09', 'threeohfive') - 0.05, 0.35); sfx('flicker', w('s09', 'miami') - 0.1, 0.35);

// ================================================================ 11. OLD AGE: ~78 years; still sweating, still cafecito, still dodging iguanas
const tOld = S('s10'), tGrow = ln('s10', 1), tSweat = ln('s10', 2), tCafe2 = ln('s10', 3), tDodge = ln('s10', 4);
scene(tOld, tSweat, (t) => {
  beach(t);
  palm(80, 1420, 0.9, t, { lean: 0.15 }); palm(1000, 1420, 0.85, t + 1, { lean: -0.15 });
  bench(540, 1640, 1.3);
  person(430, 1560, 1.0, assign(TEO_OLD, { seated: true, mouth: 'smile', la: 0.3, ra: 1.0 }), t);
  person(660, 1560, 1.0, assign(VALE_OLD, { seated: true, mouth: 'smile', la: 1.0, ra: 0.3 }), t);
  card(W / 2, 520, 600, 300, { big: '~78 years', l1: 'life expectancy in the US', src: 'CDC, 2023', bigSize: 104, accent: NEON.pink }, pop(t, w('s10', 'seventyeight') - 0.1));
  hand('Teo, age 78', 300, 820, pop(t, tGrow + 0.05), 70, '#ffffff');
});
sfx('pop', w('s10', 'seventyeight') - 0.1, 0.5); sfx('pop', tGrow + 0.05, 0.3);
scene(tSweat, tCafe2, (t) => {
  outdoor({ horizon: 1200, skyTop: '#ff9f43', sky: '#ffe08a', ground: '#f3d9a4' });
  withT(540, 520, 1 + 0.04 * Math.sin(t * 5), 0, () => { c.save(); c.rotate(t * 0.4); for (let i = 0; i < 14; i++) { c.rotate(PI / 7); c.fillStyle = '#ffd319'; c.beginPath(); c.moveTo(-20, -190); c.lineTo(0, -260); c.lineTo(20, -190); c.fill(); } c.restore(); circle(0, 0, 170, '#ffd319', PAL.ink, 8); shades()(-20); c.strokeStyle = PAL.ink; c.lineWidth = 8; c.beginPath(); c.arc(0, 50, 60, 0.2 * PI, 0.8 * PI); c.stroke(); });
  c.strokeStyle = 'rgba(255,255,255,.5)'; c.lineWidth = 5; for (let i = 0; i < 6; i++) { c.beginPath(); for (let y = 1000; y < 1500; y += 20) c.lineTo(120 + i * 170 + Math.sin(y / 40 + t * 6 + i) * 10, y); c.stroke(); }
  const fan = tt => { c.save(); c.rotate(Math.sin(tt * 18) * 0.5); c.beginPath(); c.moveTo(0, 0); c.arc(0, 0, 90, -PI * 0.85, -PI * 0.15); c.closePath(); fs(NEON.pink, PAL.ink, 5); c.restore(); };
  person(540, 1720, 1.25, assign(TEO_OLD, { mouth: 'wavy', eyes: 'closed', la: 0.3, ra: 2.3, elbow: 0.6, hold: { side: 1, draw: fan } }), t);
  sweat(540, 1720 - 1.25 * 1.4 * 340, 1.2, t);
  title('still sweating.', W / 2, 220, pop(t, tSweat + 0.05), 110);
});
sfx('pop', tSweat + 0.05, 0.4);
scene(tCafe2, tDodge, (t) => {
  ventanita(t, { inside: serverInside, wall: '#f9b4cf' });
  cafecito(640, 1006, 0.9, t);
  person(460, 1720, 1.25, assign(TEO_OLD, { mouth: 'grin', la: 0.3, ra: 1.4, elbow: 1.3, hold: { side: 1, draw: tt => cafecito(0, -10, 0.55, tt) } }), t);
  title('still cafecito.', W / 2, 160, pop(t, tCafe2 + 0.05), 104);
});
sfx('clink', tCafe2 + 0.1, 0.4); sfx('pop', tCafe2 + 0.05, 0.4);
scene(tDodge, S('s11'), (t, lt) => {
  outdoor({ horizon: 1250, skyTop: '#55c2f0', sky: '#bdeafc', ground: '#cfe3a4' });
  palm(760, 1420, 1.0, t, { lean: -0.12 });
  const dt = lt - 0.35, yy = fallY(dt, 780, 1440), dodge = ss(tDodge + 0.15, tDodge + 0.45, t);
  iguana(640, yy, 0.55, { frozen: true, rot: dt > 0 ? Math.min(PI, dt * 8) : 0, t });
  person(lerp(560, 300, dodge), 1720, 1.2, assign(TEO_OLD, { mouth: dodge > 0.3 ? 'open' : 'smile', eyes: dodge > 0.3 ? 'wide' : 'open', lean: -0.25 * dodge, la: 2.4 * dodge, ra: 0.3, hold: { side: 1, draw: () => { c.strokeStyle = PAL.ink; c.lineWidth = 12; c.beginPath(); c.moveTo(0, 0); c.lineTo(10, 180); c.stroke(); c.strokeStyle = '#8b5a2b'; c.lineWidth = 6; c.stroke(); } } }), t);
  title('still dodging', W / 2, 200, pop(t, tDodge + 0.05), 104);
  title('iguanas.', W / 2, 330, pop(t, w('s10', 'iguanas') - 0.05), 104, { color: '#7fd35a' });
});
sfx('whoosh', tDodge + 0.35, 0.4); sfx('thunk', tDodge + 0.35 + Math.sqrt(2 * 660 / 2600), 0.6); sfx('boing', tDodge + 0.2, 0.3, { pitch: 1.5 });

// ================================================================ 12. LOOP: "Where will you be born next time?" — the pin bounces again
const tEnd = S('s11');
const LOOP = ['Denver', 'Boston', 'Phoenix', 'Chicago', 'New Orleans', 'Seattle', 'Nashville', 'Los Angeles', 'Detroit'];
const LSTOPS = LOOP.map((n, i) => [n, tEnd + 0.55 + i * 0.62]);
scene(tEnd, DUR + 1, (t) => {
  synthBack(t, { sunY: 600 });
  const p = usMap({ t, labels: 1 });
  cityDots(p, { major: 1, show: LOOP.filter((n, i) => t > LSTOPS[i][1]) });
  hopPin(p, LSTOPS, t, 1.15);
  palm(-30, H + 30, 1.05, t, { lean: 0.32, dark: true }); palm(W + 30, H + 30, 1.05, t + 1, { lean: -0.32, dark: true });
  header(t, 1, 'next time?', tEnd - 0.2);
  c.globalAlpha = 0.9; rr(110, 1700, 860, 120, 20); fs('rgba(13,2,33,.8)', null, 0);
  ['Sources: CDC births & life expectancy 2023; UN WPP;', 'City of Miami; MDPL; NOAA NHC; Florida FWC.'].forEach((q, i) => txt(q, W / 2, 1738 + i * 42, { font: 'Patrick Hand', weight: 400, size: 32, color: '#ffffff' }));
  c.globalAlpha = 1;
}, { zoom: 0 });
LSTOPS.forEach(([, tt], i) => { if (tt < DUR) sfx('boing', tt, 0.35, { pitch: 1 + (i % 4) * 0.1 }); });
sfx('whoosh', tEnd, 0.5); sfx('flicker', tEnd, 0.3);

// cut whooshes between scenes
[tTuttle, tFlood, tCold, tCafe, tHur, tCrab, tNY, tWed, t305, tOld].forEach(t => sfx('swoosh', t - 0.05, 0.35));
music(0, 0.7); music(tPlace, 0.8); music(tNY, 0.75); music(tOld, 0.6); music(DUR - 0.6, 0.6); music(DUR, 0);
tl.set({}, {}, DUR);

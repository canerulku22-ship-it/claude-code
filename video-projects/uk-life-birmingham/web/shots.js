// "Where will you be born this time?" — UK edition: Birmingham. One scene per narration line (like the format), flat
// cartoon style, every element popping in on its word.
import { c, W, H, PI, PAL, tl, DUR, S, L, w, we, sfx, music, clamp01, lerp, ss, pop, popOut, backOut, elastic, mulberry32, scene, overlay, rr, fs, circle, ellipse, txt, withT, title, hand, card, bubble } from './core.js';
import { person, room, outdoor, cloudPuff, unionFlag, brumSkyline, londonSkyline, canal, narrowboat, gondola, trolley, car, coach, mug, balti, choc, suitcase, guitar, bolt, bench, bunting, junction } from './art.js';
import { globe, space, pin } from './globe.js';

const BRUM = [-1.89, 52.48];
const ln = (s, i) => L(s, i).start;
const next = (s, i) => { const l = L(s, i); return l.start; };
const SK = PAL.skin;
const GAZ_KID = { kid: true, skin: SK[0], hair: 'spiky', hairColor: '#c9772e', shirt: '#8e1b3a', pants: '#555b66', ph: 0.3 };
const GAZ_TEEN = { skin: SK[0], hair: 'short', hairColor: '#c9772e', shirt: '#1f2a44', pattern: 'tracksuit', shirt2: '#ffffff', pants: '#1f2a44', ph: 0.3 };
const GAZ = { skin: SK[0], hair: 'short', hairColor: '#c9772e', shirt: '#2f6fb5', pants: '#3b4a6b', ph: 0.3 };
const GAZ_OLD = { old: true, skin: SK[0], hair: 'bald', hairColor: '#e2e2e2', glasses: true, tache: '#e9e9e9', shirt: '#8a6a48', pants: '#5b5b5b', ph: 0.3 };
const SHAZ = { skin: SK[4], hair: 'long', hairColor: '#e8c35a', shirt: '#ffffff', dress: '#ffffff', pants: '#f2d5c4', ph: 1.1 };
const SHAZ_OLD = { old: true, skin: SK[4], hair: 'curly', hairColor: '#e6e6e6', glasses: true, shirt: '#c97bb2', pattern: 'dots', dress: '#a75d93', pants: '#f2d5c4', ph: 1.1 };
const MUM = { skin: SK[0], hair: 'long', hairColor: '#7a4528', shirt: '#e76f51', pants: '#3b4a6b', ph: 0.9 };
const DAD = { skin: SK[0], hair: 'short', hairColor: '#3b2a20', tache: '#3b2a20', shirt: '#2a9d8f', pattern: 'stripes', shirt2: '#1d6f66', pants: '#3b3b48', ph: 2.1 };
const NAN = { old: true, skin: SK[0], hair: 'curly', hairColor: '#dcdcdc', glasses: true, shirt: '#9b5de5', pattern: 'dots', pants: '#5e548e', ph: 1.7 };

// ================================================================ 1. GLOBE: spin, zoom to Birmingham, clouds
const tPlace = ln('s02', 0), tTicket = ln('s02', 1), tBrumWord = w('s02', 'birmingham');
const ease3 = k => 1 - Math.pow(1 - clamp01(k), 3);
function globeState(t) {
  const ks = ease3((t - 0.2) / (tPlace + 0.2));
  const lon = lerp(-160, BRUM[0], ks) , lat = lerp(8, BRUM[1], ks);
  const kz = clamp01((t - tPlace - 0.25) / (tBrumWord - tPlace + 0.15)), z = Math.pow(kz, 2.2);
  const r = 340 * Math.pow(26000 / 340, z), cy = lerp(930, 960, z);
  return { lon, lat, r, cy, kz };
}
scene(0, tTicket, (t) => {
  space(t);
  const g = globeState(t);
  globe({ cx: W / 2, cy: g.cy, r: g.r, lon: g.lon, lat: g.lat, ukGlow: ss(tPlace - 0.1, tPlace + 0.4, t) * (1 - ss(tBrumWord - 0.5, tBrumWord, t)) });
  // the pin rides the centre of the disc
  const pk = pop(t, 0.35, 0.45);
  pin(W / 2, g.cy - 8 + Math.sin(t * 5) * 4 * (1 - g.kz), 1.25 * pk);
  // labels
  const kUK = ss(tPlace, tPlace + 0.3, t) * (1 - ss(tBrumWord - 0.2, tBrumWord, t));
  if (kUK > 0) hand('United Kingdom', W / 2, g.cy - 210, kUK, 78, '#ffffff', -0.02);
  const kB = pop(t, tBrumWord - 0.05);
  if (kB > 0) { circle(W / 2, g.cy - 8, 18 * kB, PAL.orange, PAL.ink, 6); hand('Birmingham', W / 2, g.cy - 230, kB, 92, PAL.orange, -0.03); }
  // header (fades as we dive)
  const kh = 1 - ss(tPlace, tPlace + 0.4, t);
  if (kh > 0.01) { c.globalAlpha = kh; txt('Where will you be born', W / 2, 300, { font: 'Patrick Hand', weight: 400, size: 86, color: '#ffffff' }); txt('this time?', W / 2, 395, { font: 'Patrick Hand', weight: 400, size: 86, color: PAL.orange }); c.globalAlpha = 1; }
}, { zoom: 0 });
sfx('whoosh', 0.25, 0.4); sfx('tick', 0.5, 0.3);
for (let i = 0; i < 14; i++) sfx('tick', 0.5 + (tPlace - 0.6) * (1 - Math.pow(1 - i / 14, 2)), 0.22);
sfx('ding', tPlace - 0.05, 0.5); sfx('whoosh', tPlace + 0.3, 0.5); sfx('pop', tBrumWord, 0.5);
// cloud wipe into the city
const tWipe = tTicket;
overlay(t => {
  const k = clamp01(1 - Math.abs(t - tWipe) / 0.45); if (k <= 0) return;
  const R = mulberry32(2);
  for (let i = 0; i < 22; i++) { const x = R() * W, y = R() * H, s = 2.4 + R() * 1.6, side = x < W / 2 ? -1 : 1; cloudPuff(x + side * (1 - k) * 900, y, s, '#f6f3ee'); }
});
sfx('whoosh', tWipe - 0.3, 0.6);

// ================================================================ 2. TICKET TO LIFE over the Birmingham skyline
scene(tTicket, ln('s02', 2), (t, lt) => {
  outdoor({ horizon: 1150 }); cloudPuff(220, 240, 0.8); cloudPuff(860, 330, 0.65);
  brumSkyline(1150, t);
  c.fillStyle = '#c9b48f'; c.fillRect(0, 1150, W, 140); c.fillStyle = '#4f8f7f'; c.fillRect(0, 1290, W, H - 1290);
  narrowboat(560 + Math.sin(t * 0.8) * 20, 1360, 0.9);
  const k = pop(t, tTicket + 0.15);
  withT(W / 2, 600, k, -0.03, () => {
    rr(-380 + 10, -230 + 12, 760, 460, 28); fs('rgba(0,0,0,.2)', null, 0);
    rr(-380, -230, 760, 460, 28); fs('#fbf6ea', PAL.ink, 7);
    c.setLineDash([14, 12]); c.strokeStyle = 'rgba(43,38,34,.35)'; c.lineWidth = 4; rr(-356, -206, 712, 412, 20); c.stroke(); c.setLineDash([]);
    txt('TICKET TO LIFE', 0, -170, { size: 34, color: '#7d7468' });
    txt('United Kingdom • Birmingham', 0, -110, { size: 46 });
    txt('boy', 0, -62, { font: 'Patrick Hand', weight: 400, size: 44, color: PAL.red });
    txt('1 in 200', 0, 18 + 6, { font: 'Lilita One', weight: 400, size: 140, color: PAL.orangeDark, stroke: PAL.orangeDark, lw: 16 }); txt('1 in 200', 0, 18, { font: 'Lilita One', weight: 400, size: 140, color: PAL.orange, stroke: PAL.orangeDark, lw: 9 }); txt('1 in 200', 0, 18, { font: 'Lilita One', weight: 400, size: 140, color: PAL.orange });
    txt('chance of being born in the UK', 0, 116, { size: 38 });
    txt('ONS / NRS / NISRA births vs UN world births, 2023', 0, 176, { font: 'Patrick Hand', weight: 400, size: 30, color: '#7d7468' });
  });
});
sfx('pop', tTicket + 0.15, 0.6);

// ================================================================ 3. FAMILY: 15,000 babies; "Your name is Gary… Gaz"
const tBabies = ln('s02', 2), tName = ln('s02', 3), tGaz = w('s02', 'gaz');
function baby(t) { ellipse(0, -10, 48, 34, '#f3f0e8', PAL.ink, 5); circle(-26, -26, 24, SK[0], PAL.ink, 5); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.beginPath(); c.arc(-26, -22, 8, 0.2 * PI, 0.8 * PI); c.stroke(); }
scene(tBabies, ln('s03', 0), (t, lt) => {
  room({ flag: true });
  const cheer = Math.sin(t * 6) * 0.2;
  person(250, 1640, 1.05, Object.assign({}, NAN, { la: 2.4 + cheer, ra: 2.4 - cheer }), t);
  person(560, 1660, 1.1, Object.assign({}, MUM, { la: 1.35, ra: 1.35, elbow: 1.2, hold: { side: -1, draw: baby } }), t);
  person(860, 1650, 1.12, Object.assign({}, DAD, { la: 2.6 + cheer, ra: 2.5 - cheer, mouth: 'grin' }), t);
  card(W / 2, 520, 600, 300, { big: '15,000', l1: 'babies born in', l2: 'Birmingham a year', src: 'ONS (approx.)' }, pop(t, tBabies + 0.2));
  // name tag
  const kn = pop(t, tName + 0.1);
  if (kn > 0) {
    withT(460, 1000, kn, -0.06, () => {
      rr(-120, -50, 240, 100, 20); fs('#ffd23f', PAL.ink, 6);
      txt('Gary', 0, 4, { font: 'Patrick Hand', weight: 400, size: 70 });
      const ks = clamp01((t - tGaz + 0.15) / 0.25); if (ks > 0) { c.strokeStyle = PAL.red; c.lineWidth = 10; c.beginPath(); c.moveTo(-90, 6); c.lineTo(-90 + 180 * ks, -4); c.stroke(); }
    });
    const kg = pop(t, tGaz);
    if (kg > 0) withT(700, 950, kg, 0.08, () => { rr(-110, -54, 220, 108, 22); fs(PAL.orange, PAL.ink, 7); txt('Gaz', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff', stroke: PAL.ink, lw: 8 }); txt('Gaz', 0, 4, { font: 'Lilita One', weight: 400, size: 84, color: '#fff' }); });
  }
});
sfx('cheer', tBabies + 0.1, 0.5); sfx('pop', tBabies + 0.2, 0.5); sfx('pop', tName + 0.1, 0.5); sfx('scratch', tGaz - 0.15, 0.4); sfx('pop', tGaz, 0.6);

// ================================================================ 4. CANALS > VENICE; shopping trolleys; second city
const tCanal = ln('s03', 0), tTrolley = ln('s03', 1), tSecond = ln('s03', 2);
scene(tCanal, tTrolley, (t) => {
  canal(); narrowboat(420 + (t - tCanal) * 40, 1330, 1.0);
  title('more canals than Venice', W / 2, 250, pop(t, tCanal + 0.1), 84);
  card(W / 2, 560, 640, 300, { big: '35 miles', l1: 'of canal in Birmingham', l2: 'Venice: about 26', src: 'Canal & River Trust' }, pop(t, w('s03', 'venice') - 0.1));
  const kv = pop(t, w('s03', 'venice'));
  if (kv > 0) withT(850, 1080, kv, 0.05, () => { circle(0, 0, 150, '#bfe3f2', PAL.ink, 7); c.save(); c.beginPath(); c.arc(0, 0, 146, 0, PI * 2); c.clip(); c.fillStyle = '#3f8fb5'; c.fillRect(-150, 30, 300, 150); gondola(0, 50, 0.45); c.restore(); hand('Venice', 0, -100, 1, 52, PAL.orange); });
});
sfx('pop', tCanal + 0.1, 0.4); sfx('pop', w('s03', 'venice') - 0.1, 0.5);
scene(tTrolley, tSecond, (t) => {
  canal();
  const k = clamp01((t - tTrolley - 0.3) / 0.8), rise = backOut(k);
  trolley(560, 1500 - 220 * rise, 1.5, -0.25 + Math.sin(t * 2) * 0.03);
  c.fillStyle = '#4f8f7f'; c.fillRect(0, 1440, W, H - 1440);
  c.strokeStyle = 'rgba(255,255,255,.6)'; c.lineWidth = 6; for (let i = 0; i < 3; i++) { const r = ((t * 120 + i * 90) % 280); c.beginPath(); c.ellipse(560, 1440, r, r * 0.22, 0, 0, PI * 2); c.stroke(); }
  withT(260, 1470 + Math.sin(t * 2) * 6, 1, 0.3, () => { rr(-50, -30, 100, 60, 10); fs('#e63946', PAL.ink, 5); txt('CRISPS', 0, 2, { size: 22, color: '#fff' }); });
  title('gondolas?', W / 2, 300, pop(t, tTrolley + 0.1), 110);
  const kx = pop(t, w('s03', 'shopping') - 0.05); if (kx > 0) { c.strokeStyle = PAL.red; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); c.moveTo(W / 2 - 260, 330 - 40); c.lineTo(W / 2 - 260 + 520 * kx, 330 - 40 + 40 * kx); c.stroke(); }
  title('trolleys.', W / 2, 470, pop(t, w('s03', 'trolleys') - 0.05), 110, { color: '#ffd23f' });
});
sfx('splash', tTrolley + 0.4, 0.8); sfx('pop', w('s03', 'trolleys') - 0.05, 0.5);
scene(tSecond, S('s04'), (t) => {
  space(t); c.fillStyle = '#2f6db0'; c.fillRect(0, 0, W, H);
  const p = globe({ cx: W / 2, cy: 900, r: 5200, lon: -2.1, lat: 53.0 });
  const [bx, by] = p(BRUM), [mx, my] = p([-2.24, 53.48]);
  pin(bx, by, 0.9 * pop(t, tSecond + 0.1)); hand('Birmingham', bx, by + 70, pop(t, tSecond + 0.15), 60, '#ffffff');
  pin(mx, my, 0.9 * pop(t, w('s03', 'manchester') - 0.05), '#6cabdd'); hand('Manchester', mx, my - 150, pop(t, w('s03', 'manchester')), 60, '#ffffff');
  title('second city', W / 2, 250, pop(t, w('s03', 'second') - 0.05), 110);
  const ka = pop(t, w('s03', 'furious') - 0.1);
  if (ka > 0) { person(780, 1700, 0.95 * ka, { skin: SK[1], hair: 'short', hairColor: '#222', shirt: '#6cabdd', pants: '#2b2b48', eyes: 'angry', mouth: 'shout', la: 2.7, ra: 2.7 + Math.sin(t * 12) * 0.2, ph: 0.5 }, t); for (let i = 0; i < 3; i++) { const ph = (t * 1.5 + i / 3) % 1; c.globalAlpha = 1 - ph; cloudPuff(780 + (i - 1) * 60, 1260 - ph * 160, 0.4 + ph * 0.3, '#ffffff'); c.globalAlpha = 1; } }
});
sfx('pop', tSecond + 0.1, 0.4); sfx('pop', w('s03', 'manchester') - 0.05, 0.4); sfx('stamp', w('s03', 'second') - 0.05, 0.5); sfx('buzz', w('s03', 'furious') - 0.1, 0.5);

// ================================================================ 5. SPAGHETTI JUNCTION, since 1972; dad loses it
const tSpag = S('s04'), tShift = ln('s04', 1);
function dadInCar(t, shout) { person(8, 52, 0.46, Object.assign({}, DAD, { mouth: shout ? 'shout' : 'frown', eyes: shout ? 'angry' : 'open', bob: 0 }), t); }
scene(tSpag, tShift, (t) => {
  junction(t);
  car(560, 1560, 1.25, '#e63946', tt => dadInCar(tt, false), t);
  title('since 1972', W / 2, 260, pop(t, w('s04', 'nineteen') - 0.05), 110);
  hand('Spaghetti Junction', W / 2, 400, pop(t, w('s04', 'spaghetti') - 0.05), 70, '#ffffff');
});
sfx('horn', tSpag + 0.4, 0.4); sfx('pop', w('s04', 'nineteen') - 0.05, 0.4);
scene(tShift, S('s05'), (t) => {
  junction(t, true);
  const sh = Math.sin(t * 40) * 6;
  car(560 + sh, 1580, 1.7, '#e63946', tt => dadInCar(tt, true), t);
  bubble(W / 2, 640, 'SHIFT YOUR BLOODY CAR, YOU #@%!ING MUPPET!', pop(t, tShift + 0.05), { size: 54, maxW: 860, color: PAL.red });
});
sfx('horn', tShift, 0.8); sfx('horn', tShift + 0.5, 0.6); sfx('pop', tShift + 0.05, 0.5);

// ================================================================ 6. AGE 5: Cadbury World (since 1824), sick on the coach
const tCad = S('s05'), t1824 = ln('s05', 1), tCoach = ln('s05', 2), tFfs = ln('s05', 3);
scene(tCad, tCoach, (t) => {
  room({ wall: '#5b2a86', floor: '#3c1c5a', stripe: '#ffd23f', window: false });
  const R = mulberry32(5);
  for (let i = 0; i < 10; i++) { const x = 80 + R() * 920, y = ((t * 220 + R() * 1400) % 1300) - 200; choc(x, y, 0.45, R() * 6 + t); }
  title('age 5', 860, 230, pop(t, tCad + 0.05), 96);
  hand('Cadbury World', 330, 230, pop(t, w('s05', 'cadbury') - 0.05), 74, '#ffd23f');
  person(260, 1700, 1.25, Object.assign({}, GAZ_KID, { mouth: 'grin', la: 2.6, ra: 2.5, hold: { side: 1, draw: () => choc(0, 0, 0.35, 0.6) } }), t);
  person(560, 1700, 1.2, { kid: true, skin: SK[2], hair: 'curly', hairColor: '#1d1d1d', shirt: '#8e1b3a', pants: '#555b66', mouth: 'open', la: 2.4, ra: 2.4, ph: 1 }, t);
  person(840, 1700, 1.2, { kid: true, skin: SK[4], hair: 'bun', hairColor: '#7a4528', shirt: '#8e1b3a', dress: '#555b66', mouth: 'smile', la: 2.5, ra: 0.3, ph: 2 }, t);
  card(W / 2, 620, 560, 300, { big: 'since 1824', l1: 'Cadbury in Birmingham', src: 'Cadbury' , bigSize: 92 }, pop(t, t1824 + 0.1));
});
sfx('cheer', tCad + 0.2, 0.4); sfx('pop', t1824 + 0.1, 0.5);
scene(tCoach, S('s06'), (t) => {
  outdoor({ horizon: 1250, ground: '#7b8088' });
  cloudPuff(200, 260, 0.7); cloudPuff(840, 380, 0.6);
  const bump = Math.abs(Math.sin(t * 9)) * 6;
  coach(540, 1500 - bump, 1.2, t);
  withT(540, 1500 - bump, 1.2, 0, () => { c.save(); rr(-350 + 115, -270, 95, 120, 14); c.clip(); person(-188, -12, 0.42, Object.assign({}, GAZ_KID, { sick: true, mouth: 'wavy', bob: 0 }), t); c.restore(); });
  const kp = pop(t, w('s05', 'throws') - 0.05); if (kp > 0) withT(330, 1560, kp, 0, () => { c.fillStyle = '#9ccf5a'; c.beginPath(); c.ellipse(0, 0, 60, 26, 0, 0, PI * 2); c.fill(); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.stroke(); });
  if (t >= tFfs - 0.1) {
    const kt = pop(t, tFfs - 0.1);
    person(860, 1700, 1.05 * kt, { skin: SK[0], hair: 'bun', hairColor: '#4a3426', glasses: true, shirt: '#6a994e', dress: '#3d5a3a', mouth: 'shout', eyes: 'angry', la: 2.9, ra: 0.3, ph: 0.2 }, t);
    bubble(560, 760, "OH, FOR F***'S SAKE, BLOODY GARY!", pop(t, tFfs), { size: 54, maxW: 860, color: PAL.red });
  }
});
sfx('splat', w('s05', 'throws') - 0.05, 0.7); sfx('pop', tFfs, 0.5);

// ================================================================ 7. AGE 16: flat cap, "Peaky Blinders" — expectation vs reality
const tCap = S('s06'), tShelby = ln('s06', 1);
scene(tCap, tShelby, (t) => {
  room({ wall: '#dfe7ee', stripe: '#3d5a80', window: true });
  rr(620, 380, 300, 640, 150); fs('#cfe3ef', PAL.ink, 9); c.save(); rr(630, 390, 280, 620, 140); c.clip(); person(770, 1180, 0.85, Object.assign({}, GAZ_TEEN, { flatcap: '#5a4a3a', flip: true, mouth: 'smile', eyes: 'angry', la: 0.2, ra: 2.2, bob: 0 }), t); c.restore();
  person(330, 1680, 1.15, Object.assign({}, GAZ_TEEN, { flatcap: t > w('s06', 'flat') - 0.1 ? '#5a4a3a' : null, mouth: 'smile', la: 0.2, ra: 2.3, wave: 'r' }), t);
  title('age 16', 260, 230, pop(t, tCap + 0.05), 96);
  hand('Peaky Blinders?', 330, 400, pop(t, w('s06', 'peaky') - 0.05), 72, PAL.orange);
});
sfx('pop', w('s06', 'flat') - 0.1, 0.5);
scene(tShelby, S('s07'), (t) => {
  c.fillStyle = '#3b3b40'; c.fillRect(0, 0, W / 2, H); c.fillStyle = PAL.wall; c.fillRect(W / 2, 0, W / 2, H);
  for (let i = 0; i < 4; i++) { c.globalAlpha = 0.25; cloudPuff(120 + i * 120, 1200 - ((t * 60 + i * 100) % 500), 0.8, '#9a9aa0'); c.globalAlpha = 1; }
  c.fillStyle = PAL.ink; c.fillRect(W / 2 - 4, 0, 8, H);
  person(270, 1640, 1.1, { skin: SK[0], hair: 'short', hairColor: '#1d1d1d', flatcap: '#2b2b2b', shirt: '#2b2b2b', pattern: 'suit', tie: '#2b2b2b', pants: '#1d1d1d', mouth: 'flat', eyes: 'angry', la: 0.15, ra: 0.15, bob: 0.4 }, t);
  person(810, 1640, 1.1, Object.assign({}, GAZ_TEEN, { flatcap: '#5a4a3a', mouth: 'grin', la: 0.3, ra: 2.6, wave: 'r' }), t);
  hand('expectation', 270, 340, pop(t, tShelby + 0.05), 72, '#ffffff');
  hand('reality', 810, 340, pop(t, w('s06', 'just') - 0.1), 72, PAL.orange);
});
sfx('whoosh', tShelby, 0.4); sfx('pop', w('s06', 'just') - 0.1, 0.5);

// ================================================================ 8. TEA (100 million cups a day) and BALTI
const tTea = S('s07'), tBalti = ln('s07', 1);
scene(tTea, tBalti, (t) => {
  room({ wall: '#f4ecd8', stripe: '#c1666b' });
  const n = Math.floor(clamp01((t - tTea - 0.2) / 2.2) * 24);
  for (let i = 0; i < n; i++) { const col = i % 6, row = Math.floor(i / 6); mug(170 + col * 150, 1480 - row * 135, 0.9, ['#ffffff', '#ffd23f', '#e63946', '#2f6fb5'][i % 4], row === Math.floor((n - 1) / 6), t + i); }
  card(W / 2, 520, 640, 320, { big: '100 million', l1: 'cups of tea drunk in the', l2: 'UK every day', src: 'UK Tea & Infusions Association', bigSize: 96 }, pop(t, w('s07', 'hundred') - 0.05));
});
for (let i = 0; i < 8; i++) sfx('clink', tTea + 0.25 + i * 0.27, 0.3, { pitch: 1 + (i % 4) * 0.08 });
sfx('pop', w('s07', 'hundred') - 0.05, 0.5);
scene(tBalti, S('s08'), (t) => {
  room({ wall: '#f6e3c5', stripe: '#b5523b' });
  rr(80, 1330, 920, 40, 10); fs('#8b5a2b', PAL.ink, 6); rr(120, 1370, 30, 330, 6); fs('#6b4423', PAL.ink, 5); rr(930, 1370, 30, 330, 6); fs('#6b4423', PAL.ink, 5);
  person(250, 1700, 1.0, Object.assign({}, DAD, { mouth: 'grin', la: 0.4, ra: 2.2 }), t);
  person(820, 1700, 1.0, Object.assign({}, GAZ_TEEN, { mouth: 'open', la: 2.4, ra: 0.4 }), t);
  balti(540, 1300, 1.0, t);
  withT(330, 1335, 1, -0.15, () => { ellipse(0, 0, 90, 34, '#e9c27a', PAL.ink, 5); });
  title('balti', W / 2, 260, pop(t, w('s07', 'balti') - 0.05), 120);
  card(W / 2, 560, 640, 260, { big: 'made in Brum', l1: '(supposedly)', src: 'the Balti Triangle', bigSize: 88 }, pop(t, w('s07', 'invented') - 0.05));
});
sfx('sizzle', tBalti, 0.5); sfx('pop', w('s07', 'invented') - 0.05, 0.5);

// ================================================================ 9. AGE 22: London. "A cob?" "Londoners." Accent. "How did you know?"
const tLondon = S('s08'), tCob = ln('s08', 1), tLondoners = ln('s08', 2), tAccent = ln('s08', 3), tAre = ln('s08', 4), tKnow = ln('s08', 5);
scene(tLondon, tCob, (t) => {
  outdoor({ horizon: 1150, skyTop: '#9fb8c8', sky: '#cdd8de', ground: '#8a8f99' });
  cloudPuff(250, 250, 0.8, '#e8ecef'); cloudPuff(800, 330, 0.7, '#e8ecef');
  londonSkyline(1150);
  // red bus
  withT(1300 - ((t - tLondon) * 260) % 1700, 1300, 0.9, 0, () => { rr(-260, -300, 520, 300, 30); fs('#d62828', PAL.ink, 7); for (let r = 0; r < 2; r++) for (let i = 0; i < 4; i++) { rr(-230 + i * 120, -275 + r * 130, 95, 85, 12); fs('#cfe8f1', PAL.ink, 5); } circle(-160, 0, 40, '#2b2622', PAL.ink, 6); circle(160, 0, 40, '#2b2622', PAL.ink, 6); });
  person(430, 1700, 1.1, Object.assign({}, GAZ, { mouth: 'smile', la: 0.3, ra: 2.6, wave: 'r' }), t);
  suitcase(620, 1700, 1.0);
  title('age 22', 820, 230, pop(t, tLondon + 0.05), 96);
});
sfx('whoosh', tLondon, 0.4);
const SERVER = { skin: SK[1], hair: 'bun', hairColor: '#2b1d14', shirt: '#ffffff', pattern: 'apron', shirt2: '#2a9d8f', pants: '#2b2b2b', ph: 0.7 };
scene(tCob, tAccent, (t) => {
  room({ wall: '#e8f1ec', stripe: '#2a9d8f', window: false });
  // menu board
  rr(200, 160, 680, 360, 16); fs('#2d3a33', PAL.ink, 8); txt('SANDWICHES', 540, 230, { font: 'Patrick Hand', weight: 400, size: 64, color: '#ffffff' }); for (let i = 0; i < 4; i++) { c.fillStyle = 'rgba(255,255,255,.5)'; c.fillRect(260, 300 + i * 52, 380 - i * 40, 12); c.fillRect(760, 300 + i * 52, 60, 12); }
  person(760, 1520, 1.0, Object.assign({}, SERVER, { mouth: t > w('s08', 'nobody') ? 'flat' : 'smile', eyes: t > w('s08', 'nobody') ? 'wide' : 'open', la: 0.2, ra: 0.2 }), t);
  rr(560, 1420, 520, 300, 10); fs('#c9b48f', PAL.ink, 7);
  person(300, 1700, 1.1, Object.assign({}, GAZ, { mouth: t > tLondoners ? 'frown' : 'smile', eyes: t > tLondoners ? 'angry' : 'open', la: 0.2, ra: 1.4 }), t);
  bubble(330, 700, 'A cob, please.', pop(t, w('s08', 'cob') - 0.05) * (1 - ss(tLondoners - 0.1, tLondoners, t)), { tail: 'down', size: 54 });
  bubble(760, 920, 'A... what?', pop(t, w('s08', 'nobody') - 0.05) * (1 - ss(tLondoners - 0.1, tLondoners, t)), { tail: 'down', size: 54 });
  bubble(360, 760, 'Bloody #@%!ing Londoners.', pop(t, tLondoners), { tail: 'down', size: 54, color: PAL.red });
});
sfx('pop', w('s08', 'cob') - 0.05, 0.4); sfx('pop', w('s08', 'nobody') - 0.05, 0.4); sfx('pop', tLondoners, 0.5);
scene(tAccent, tAre, (t) => {
  room({ wall: '#eef0f4', stripe: '#3d5a80', window: false });
  title('accent poll', W / 2, 220, pop(t, tAccent + 0.05), 100);
  const vals = [0.95, 0.85, 0.74, 0.62, 0.5, 0.06], cols = ['#2f6fb5', '#2a9d8f', '#e9c46a', '#f4a261', '#9b5de5', '#e63946'];
  vals.forEach((v, i) => {
    const k = clamp01((t - tAccent - 0.3 - i * 0.12) / 0.4), y = 400 + i * 120;
    rr(300, y, 640 * v * backOut(k), 80, 14); fs(cols[i], PAL.ink, 6);
    txt(i === 5 ? 'Brummie' : '•••', 270, y + 40, { size: 40, align: 'right', color: i === 5 ? PAL.red : '#8a8f99' });
  });
  person(540, 1720, 1.1, Object.assign({}, GAZ, { mouth: 'frown', eyes: 'open', la: 0.1, ra: 0.1 }), t);
  hand('bloody rude.', 700, 1160, pop(t, w('s08', 'attractive') - 0.05), 70, PAL.orange);
});
sfx('pop', tAccent + 0.05, 0.4); sfx('trombone', tAccent + 1.0, 0.4);
const LONDONER = { skin: SK[0], hair: 'short', hairColor: '#d9b65c', shirt: '#2b2d42', pattern: 'suit', tie: '#c0392b', pants: '#2b2d42', ph: 1.4 };
scene(tAre, S('s09'), (t) => {
  c.fillStyle = '#5a1f2e'; c.fillRect(0, 0, W, H); c.fillStyle = '#7a2a3a'; c.fillRect(0, 1180, W, H - 1180);
  const gazTurn = t > tKnow - 0.15;
  if (!gazTurn) { person(540, 1680, 1.25, Object.assign({}, LONDONER, { mouth: 'grin', la: 0.2, ra: 2.5, wave: 'r' }), t); bubble(540, 560, "You're from bloody Birmingham, aren't you?", pop(t, tAre + 0.05), { size: 52, maxW: 820 }); }
  else { person(540, 1680, 1.25, Object.assign({}, GAZ, { mouth: 'open', eyes: 'wide', la: 1.3, ra: 1.3 }), t); bubble(540, 560, 'How the #@%! did you bloody know?', pop(t, tKnow - 0.1), { size: 52, maxW: 820, color: PAL.red }); }
});
sfx('pop', tAre + 0.05, 0.4); sfx('pop', tKnow - 0.1, 0.5);

// ================================================================ 10. AGE 30: married to Shaz; balti, Black Sabbath, 40 cousins; heavy metal
const tWed = S('s09'), tParty = ln('s09', 1), tMetal = ln('s09', 2);
scene(tWed, tMetal, (t) => {
  outdoor({ horizon: 1150, skyTop: '#ffd9a8', sky: '#ffeccf', ground: '#d8c39a' });
  // the pub
  rr(90, 420, 900, 730, 6); fs(PAL.brick, PAL.ink, 7); c.beginPath(); c.moveTo(60, 430); c.lineTo(540, 250); c.lineTo(1020, 430); c.closePath(); fs('#4a3b36', PAL.ink, 7);
  rr(330, 470, 420, 110, 14); fs('#1f3b2d', PAL.ink, 6); txt('THE BRUM ARMS', 540, 527, { font: 'Lilita One', weight: 400, size: 56, color: '#ffd23f' });
  for (const x of [170, 770]) { rr(x, 640, 140, 170, 10); fs('#ffe9a8', PAL.ink, 6); } rr(470, 820, 140, 330, 10); fs('#5a3a22', PAL.ink, 6);
  bunting(180, t);
  // cousins crowd
  const kc = clamp01((t - w('s09', 'forty') + 0.1) / 0.8), nC = Math.floor(kc * 22), R = mulberry32(12);
  for (let i = 0; i < nC; i++) { const x = 60 + (i % 11) * 96 + (Math.floor(i / 11) % 2) * 40, y = 1260 - Math.floor(i / 11) * 70; person(x, y, 0.42, { skin: SK[i % 5], hair: ['short', 'long', 'curly', 'spiky', 'bun'][i % 5], hairColor: ['#3b2a20', '#c9772e', '#1d1d1d', '#e8c35a'][i % 4], shirt: ['#e63946', '#2f6fb5', '#2a9d8f', '#ffd23f', '#9b5de5'][i % 5], pants: '#3b4a6b', la: 2.6, ra: 2.6, ph: i }, t); }
  const kd = pop(t, w('s09', 'dj') - 0.05);
  if (kd > 0) { withT(900, 1520, kd, 0, () => { rr(-130, -160, 260, 160, 12); fs('#2b2b2b', PAL.ink, 6); circle(-60, -150, 34, '#555', PAL.ink, 5); circle(60, -150, 34, '#555', PAL.ink, 5); }); guitar(900, 1250, 0.8 * kd, -0.5 + Math.sin(t * 6) * 0.08); bolt(1000, 1160, 0.6 * kd); }
  const kb = pop(t, w('s09', 'balti') - 0.05); if (kb > 0) balti(170, 1560, 0.55 * kb, t);
  person(380, 1700, 1.1, Object.assign({}, GAZ, { shirt: '#2b2d42', pattern: 'suit', tie: '#e63946', pants: '#2b2d42', mouth: 'grin', la: 2.7, ra: 0.5, wave: 'l' }), t);
  person(700, 1700, 1.05, Object.assign({}, SHAZ, { veil: true, mouth: 'grin', la: 0.5, ra: 2.7, wave: 'r' }), t);
  title('age 30', 830, 340, pop(t, tWed + 0.05), 96);
  const kt = pop(t, w('s09', 'shaz') - 0.05); if (kt > 0) withT(640, 1090, kt, 0.06, () => { rr(-100, -50, 200, 100, 20); fs('#ffd23f', PAL.ink, 6); txt('Shaz', 0, 4, { font: 'Patrick Hand', weight: 400, size: 66 }); });
  card(W / 2, 600, 500, 220, { big: '40 cousins', bigSize: 88, src: 'roughly' }, pop(t, w('s09', 'cousins') - 0.1));
});
sfx('cheer', tWed + 0.1, 0.5); sfx('riff', w('s09', 'sabbath') - 0.1, 0.6); sfx('cheer', w('s09', 'cousins'), 0.6); sfx('pop', w('s09', 'cousins') - 0.1, 0.5);
scene(tMetal, S('s10'), (t) => {
  c.fillStyle = '#1b1426'; c.fillRect(0, 0, W, H);
  for (let i = 0; i < 6; i++) { c.fillStyle = `rgba(255,${120 + i * 20},40,${0.08 + 0.05 * Math.sin(t * 5 + i)})`; c.beginPath(); c.moveTo(540, -50); c.lineTo(80 + i * 190, 1300); c.lineTo(180 + i * 190, 1300); c.closePath(); c.fill(); }
  c.fillStyle = '#2b2233'; c.fillRect(0, 1300, W, H - 1300);
  for (const x of [170, 910]) { rr(x - 120, 980, 240, 320, 14); fs('#1d1d1f', PAL.ink, 7); for (const y of [1060, 1220]) { circle(x, y, 62, '#3a3a3e', PAL.ink, 6); circle(x, y, 20, '#1d1d1f', null, 0); } }
  guitar(540, 1180, 1.7 + Math.sin(t * 8) * 0.02, -0.45 + Math.sin(t * 4) * 0.05);
  bolt(250, 760, 1.0 * pop(t, tMetal + 0.15)); bolt(850, 820, 0.9 * pop(t, tMetal + 0.3));
  title('heavy metal', W / 2, 250, pop(t, w('s09', 'heavy') - 0.05), 110, { color: '#e63946' });
  card(W / 2, 560, 600, 250, { big: '1968', l1: 'Black Sabbath form in Brum', src: 'Aston, Birmingham', bigSize: 110 }, pop(t, w('s09', 'birmingham') - 0.1));
});
sfx('riff', tMetal, 0.8); sfx('boom', tMetal + 0.15, 0.4);

// ================================================================ 11. OLD AGE: 80 years; still stuck, still tara-a-bit, still balti
const tOld = S('s10'), tGrow = ln('s10', 1), tStuck = ln('s10', 2), tTara = ln('s10', 3), tStillB = ln('s10', 4);
scene(tOld, tStuck, (t) => {
  outdoor({ horizon: 1150, skyTop: '#f7b267', sky: '#fde4c3', ground: '#c9b48f' });
  circle(780, 900, 120, '#ffd23f', null, 0);
  c.fillStyle = '#4f8f7f'; c.fillRect(0, 1150, W, 120); c.fillStyle = 'rgba(255,255,255,.25)'; for (let i = 0; i < 6; i++) c.fillRect(80 + i * 170, 1190 + (i % 2) * 30, 80, 6);
  bench(540, 1640, 1.3);
  person(430, 1560, 1.0, Object.assign({}, GAZ_OLD, { seated: true, mouth: 'smile', la: 0.3, ra: 1.0 }), t);
  person(660, 1560, 1.0, Object.assign({}, SHAZ_OLD, { seated: true, mouth: 'smile', la: 1.0, ra: 0.3 }), t);
  card(W / 2, 520, 600, 300, { big: '~80 years', l1: 'life expectancy in the UK', src: 'ONS, 2021–23', bigSize: 104 }, pop(t, w('s10', 'eighty') - 0.1));
  hand('Gaz, age 80', 300, 800, pop(t, tGrow + 0.05), 70, '#ffffff');
});
sfx('pop', w('s10', 'eighty') - 0.1, 0.5);
scene(tStuck, tTara, (t) => {
  junction(t);
  car(560, 1560, 1.25, '#e63946', tt => person(8, 52, 0.46, Object.assign({}, GAZ_OLD, { mouth: 'frown', bob: 0 }), tt), t);
  title('still stuck.', W / 2, 260, pop(t, tStuck + 0.05), 120);
});
sfx('horn', tStuck + 0.2, 0.4);
scene(tTara, tStillB, (t) => {
  outdoor({ horizon: 1150 }); brumSkyline(1150, t); c.fillStyle = '#c9b48f'; c.fillRect(0, 1150, W, H - 1150);
  person(540, 1700, 1.25, Object.assign({}, GAZ_OLD, { mouth: 'grin', la: 0.2, ra: 2.7, wave: 'r' }), t);
  title('tara-a-bit!', W / 2, 260, pop(t, w('s10', 'taraabit') - 0.1), 120);
});
sfx('pop', w('s10', 'taraabit') - 0.1, 0.5);
scene(tStillB, S('s11'), (t) => {
  room({ wall: '#f6e3c5', stripe: '#b5523b' });
  person(540, 1730, 1.15, Object.assign({}, GAZ_OLD, { mouth: 'grin', la: 2.3, ra: 2.3 }), t);
  rr(80, 1470, 920, 40, 10); fs('#8b5a2b', PAL.ink, 6);
  balti(540, 1450, 0.85, t);
  title('still balti.', W / 2, 260, pop(t, tStillB + 0.05), 120);
});
sfx('sizzle', tStillB, 0.4);

// ================================================================ 12. LOOP: "Where will you be born next time?"
const tEnd = S('s11');
scene(tEnd, DUR + 1, (t) => {
  space(t);
  globe({ cx: W / 2, cy: 960, r: 340, lon: BRUM[0] - (t - tEnd) * 70, lat: lerp(BRUM[1], 10, ss(tEnd, tEnd + 1.5, t)) });
  pin(W / 2, 950 + Math.sin(t * 5) * 4, 1.25);
  txt('Where will you be born', W / 2, 300, { font: 'Patrick Hand', weight: 400, size: 86, color: '#ffffff' }); txt('next time?', W / 2, 395, { font: 'Patrick Hand', weight: 400, size: 86, color: PAL.orange });
  c.globalAlpha = 0.8;
  ['Sources: ONS, NRS, NISRA, UN; Canal & River Trust;', 'UK Tea & Infusions Association; ONS life tables.'].forEach((s, i) => txt(s, W / 2, 1640 + i * 40, { font: 'Patrick Hand', weight: 400, size: 32, color: '#c9d3ea' }));
  c.globalAlpha = 1;
}, { zoom: 0 });
sfx('whoosh', tEnd, 0.5);

// cut whooshes between scenes
[tCanal, tSpag, tCad, tCap, tTea, tLondon, tWed, tOld].forEach(t => sfx('swoosh', t - 0.05, 0.35));
music(0, 0.7); music(tPlace, 0.8); music(tLondon, 0.75); music(tOld, 0.6); music(DUR - 0.6, 0.6); music(DUR, 0);
tl.set({}, {}, DUR);

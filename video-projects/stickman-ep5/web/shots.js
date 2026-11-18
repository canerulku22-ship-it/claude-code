// Episode 5 — "If your elevator ever stops on a floor you didn't press". A steel elevator car (with a real mirror on
// the back wall) opening onto a long apartment hallway. Characters are translucent glowing ghosts (?style=solid: matte).
import { THREE, tl, C, scene, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, particles, text, rrect, floor } from './engine.js';
import { Reflector } from 'three/addons/objects/Reflector.js';
import { DUR, S, L, w, sfx, music, clamp01, lerp } from './lib.js';
import { stickFigure, setPose, POSES } from './stick.js';
import { panelMesh, propMat, darkMat, box } from './props.js';

const PI = Math.PI;
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const ss = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const hash = (n) => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };
function flicker(t, n = 3, amt = 0.75) { for (let i = 0; i < n; i++) tl.fromTo(post, { flicker: amt }, { flicker: 0, duration: 0.06, immediateRender: false }, t + i * 0.09 + (i % 2) * 0.03); sfx('flicker', t, 0.45); }

// ---------------------------------------------------------------- timeline anchors
const tDidnt = w('s01', 'didnt'), tDont = L('s01', 1).start;
const tHall = S('s02'), tCarpet = L('s02', 1).start, tLight = w('s02', 'same', 1);
const tEnd = S('s03'), tSomeone = w('s03', 'someone');
const tSpeak = S('s04'), tHold = w('s04', 'hold'), tPress = L('s04', 1).start, tClose1 = w('s04', 'close'), tOnce = w('s04', 'once');
const tSlow = S('s05');
const tStop = S('s06'), tHalf = w('s06', 'halfway'), tDontLook = L('s06', 1).start, tGap = L('s06', 1).end + 0.2, tIsnt = L('s06', 2).start, tAnymore = w('s06', 'anymore');
const tBreath = S('s07'), tAgain = w('s07', 'again');
const tMirror = S('s08'), tLookM = w('s08', 'look');
const tCorner = S('s09'), tSomeone2 = w('s09', 'someone'), tGot = L('s09', 1).start;
const tCta = S('s10');
const tSlam = tAgain + 0.3;

// ---------------------------------------------------------------- materials
floor.visible = false;   // no global mirror floor here: carpet + car floor instead
const steel = new THREE.MeshStandardMaterial({ color: 0x9aa1aa, roughness: 0.32, metalness: 0.75 });
const steelDark = new THREE.MeshStandardMaterial({ color: 0x5d636c, roughness: 0.4, metalness: 0.7 });
const wallMat = new THREE.MeshStandardMaterial({ color: 0x6a6e77, roughness: 0.88 });
const wainMat = new THREE.MeshStandardMaterial({ color: 0x33363d, roughness: 0.7 });
const doorMat = new THREE.MeshStandardMaterial({ color: 0x2a2d33, roughness: 0.55 });
const ceilMat = new THREE.MeshStandardMaterial({ color: 0x4b4f57, roughness: 0.9 });
function carpetTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#1b1c21'; g.fillRect(0, 0, 256, 256);
  g.strokeStyle = '#7d1f28'; g.lineWidth = 7;
  for (const [x, y] of [[128, 128], [0, 0], [256, 0], [0, 256], [256, 256]]) { g.beginPath(); g.moveTo(x, y - 70); g.lineTo(x + 70, y); g.lineTo(x, y + 70); g.lineTo(x - 70, y); g.closePath(); g.stroke(); }
  g.fillStyle = '#5c616b'; for (const [x, y] of [[128, 128], [0, 0], [256, 0], [0, 256], [256, 256]]) { g.beginPath(); g.arc(x, y, 9, 0, PI * 2); g.fill(); }
  g.strokeStyle = '#2c2e35'; g.lineWidth = 3; g.strokeRect(1, 1, 254, 254);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}

// ---------------------------------------------------------------- the elevator car (x ±0.8, z ±0.75, y 0..2.3; doors at z=+0.75)
const car = new THREE.Group(); scene.add(car);
const CX = 0.8, CZ = 0.75, CH = 2.3, DW = 0.5, DH = 2.1;
const slab = (g, w, h, d, x, y, z, m) => g.add(at(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m), x, y, z));
slab(car, 0.05, CH, CZ * 2, -CX, CH / 2, 0, steel); slab(car, 0.05, CH, CZ * 2, CX, CH / 2, 0, steel);   // side walls
slab(car, CX * 2, CH, 0.05, 0, CH / 2, -CZ, steelDark);                                                    // back wall
slab(car, CX - DW, CH, 0.05, -(CX + DW) / 2, CH / 2, CZ, steel); slab(car, CX - DW, CH, 0.05, (CX + DW) / 2, CH / 2, CZ, steel);
slab(car, DW * 2, CH - DH, 0.05, 0, (DH + CH) / 2, CZ, steel);
slab(car, CX * 2, 0.04, CZ * 2, 0, -0.02, 0, new THREE.MeshStandardMaterial({ color: 0x22242a, roughness: 0.35, metalness: 0.4 }));
slab(car, CX * 2, 0.04, CZ * 2, 0, CH + 0.02, 0, ceilMat);
// panel seams + handrails
for (const x of [-0.27, 0.27]) slab(car, 0.008, CH - 0.1, 0.01, x, CH / 2, -CZ + 0.03, steel);
for (const sx of [-1, 1]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, CZ * 2 - 0.3, 10), steel); r.rotation.x = PI / 2; r.position.set(sx * (CX - 0.07), 0.95, -0.05); car.add(r); }
// ceiling light panel
const carLightMat = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
slab(car, 0.9, 0.02, 0.7, 0, CH - 0.005, -0.05, carLightMat);
const carLight = new THREE.PointLight(0xe8eeff, 0, 4.5, 1.3); carLight.position.set(0, CH - 0.15, 0); car.add(carLight);
// mirror on the back wall (real reflection: the twist lives in it)
const mirror = new Reflector(new THREE.PlaneGeometry(1.3, 1.5), { textureWidth: 640, textureHeight: 740, color: 0xb4bac4, clipBias: 0.003 });
mirror.position.set(0, 1.32, -CZ + 0.035); car.add(mirror);
for (const [w_, h_, x, y] of [[1.38, 0.04, 0, 2.09], [1.38, 0.04, 0, 0.55], [0.04, 1.58, -0.67, 1.32], [0.04, 1.58, 0.67, 1.32]]) slab(car, w_, h_, 0.03, x, y, -CZ + 0.04, steel);
// door leaves (outside the front wall; slide apart)
const leaves = [-1, 1].map(s => { const g = new THREE.Group(); g.add(at(new THREE.Mesh(new THREE.BoxGeometry(DW + 0.02, DH, 0.03), steel), 0, DH / 2, 0)); g.add(at(new THREE.Mesh(new THREE.BoxGeometry(0.006, DH - 0.2, 0.034), steelDark), -s * (DW / 2 - 0.02), DH / 2, 0)); g.userData.s = s; car.add(g); return g; });
const door = { open: 0, jolt: 0 };
every(() => leaves.forEach(g => { const s = g.userData.s; g.position.set(s * (DW / 2 + door.open * DW * 0.98) + s * door.jolt * 0.01, 0, CZ + 0.05); }));
// LED floor displays (inside above the door, outside above the landing) + button panel
const DISP = { f: '4', up: 1, red: 0, glitch: 0 };
function led(c, s, P, color, size) {
  c.fillStyle = '#050608'; rrect(c, 0, 0, P.cw, P.ch, 14); c.fill();
  c.font = `900 ${size}px "Inter Display"`; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.shadowColor = color; c.shadowBlur = 16; c.fillStyle = color; c.fillText(s, P.cw / 2, P.ch / 2 + 4);
  c.shadowBlur = 0; c.fillStyle = 'rgba(5,6,8,.55)'; for (let y = 0; y < P.ch; y += 7) c.fillRect(0, y, P.cw, 2); for (let x = 0; x < P.cw; x += 7) c.fillRect(x, 0, 2, P.ch);
}
const dispText = t => (DISP.glitch > 0 ? ['6', '--', '?', '6̶', '--'][Math.floor(t * 14) % 5] : (DISP.up ? '▲ ' : '') + DISP.f);
const dispKey = t => `${dispText(t)}|${DISP.red > 0.5}`;
const dispDraw = (c, t, P) => led(c, dispText(t), P, DISP.red > 0.5 ? '#ff3846' : '#f4f7ff', 150);
panelMesh(car, { w: 0.44, h: 0.17, x: 0, y: 2.2, z: CZ - 0.03, ry: PI, ppu: 900, boost: 1.9, key: dispKey, draw: dispDraw });
panelMesh(car, { w: 0.2, h: 0.085, x: (CX + DW) / 2, y: 1.52, z: CZ - 0.03, ry: PI, ppu: 1400, boost: 1.9, key: dispKey, draw: (c, t, P) => led(c, dispText(t), P, DISP.red > 0.5 ? '#ff3846' : '#f4f7ff', 92) });
const PANEL = { lit: '8', close: 0 };
panelMesh(car, { w: 0.2, h: 0.52, x: (CX + DW) / 2, y: 1.18, z: CZ - 0.03, ry: PI, ppu: 1000, boost: 1.5, key: () => `${PANEL.lit}|${PANEL.close > 0.5}`, draw: (c, t, P) => {
  c.fillStyle = '#16181d'; rrect(c, 0, 0, P.cw, P.ch, 18); c.fill(); c.strokeStyle = '#6b717b'; c.lineWidth = 6; c.stroke();
  const col = [P.cw * 0.32, P.cw * 0.68], r = P.cw * 0.12;
  for (let i = 0; i < 8; i++) {
    const x = col[i % 2], y = P.ch * (0.68 - Math.floor(i / 2) * 0.15), lit = PANEL.lit.includes(String(i + 1));
    c.beginPath(); c.arc(x, y, r, 0, PI * 2); c.fillStyle = lit ? '#ffffff' : '#2a2d34'; c.shadowColor = '#fff'; c.shadowBlur = lit ? 20 : 0; c.fill(); c.shadowBlur = 0;
    c.font = `800 ${r * 1.1}px Inter`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = lit ? '#0b0c10' : '#aeb4be'; c.fillText(String(i + 1), x, y + 2);
  }
  const yb = P.ch * 0.86, on = PANEL.close > 0.5;
  for (const [x, s, act] of [[col[0], '◀▶', false], [col[1], '▶◀', on]]) { c.beginPath(); c.arc(x, yb, r, 0, PI * 2); c.fillStyle = act ? '#ff3846' : '#2a2d34'; c.shadowColor = '#ff3846'; c.shadowBlur = act ? 24 : 0; c.fill(); c.shadowBlur = 0; c.font = `800 ${r * 0.7}px Inter`; c.fillStyle = act ? '#fff' : '#aeb4be'; c.fillText(s, x, yb + 1); }
} });

// ---------------------------------------------------------------- the hallway (z 0.86 → 13, x ±0.95, ceiling 2.5)
const hall = new THREE.Group(); scene.add(hall);
const HX = 0.95, HZ0 = 0.86, HZ1 = 13, HH = 2.5, HL = HZ1 - HZ0, HZM = (HZ0 + HZ1) / 2;
const ctex = carpetTexture(); ctex.repeat.set(2.2, HL / 0.85);
const carpet = new THREE.Mesh(new THREE.PlaneGeometry(HX * 2, HL), new THREE.MeshStandardMaterial({ map: ctex, roughness: 0.95 })); carpet.rotation.x = -PI / 2; carpet.position.set(0, 0.002, HZM); hall.add(carpet);
for (const sx of [-1, 1]) { slab(hall, 0.05, HH, HL, sx * HX, HH / 2, HZM, wallMat); slab(hall, 0.06, 0.9, HL, sx * (HX - 0.01), 0.45, HZM, wainMat); slab(hall, 0.07, 0.04, HL, sx * (HX - 0.02), 0.92, HZM, steel); }
slab(hall, HX * 2, 0.05, HL, 0, HH, HZM, ceilMat);
slab(hall, HX * 2, HH, 0.05, 0, HH / 2, HZ1, wallMat); slab(hall, HX * 2, 0.9, 0.06, 0, 0.45, HZ1 - 0.01, wainMat);
// landing wall around the elevator opening + its frame
slab(hall, HX - 0.55, HH, 0.05, -(HX + 0.55) / 2, HH / 2, HZ0, wallMat); slab(hall, HX - 0.55, HH, 0.05, (HX + 0.55) / 2, HH / 2, HZ0, wallMat);
slab(hall, 1.1, HH - 2.15, 0.05, 0, (2.15 + HH) / 2, HZ0, wallMat);
for (const [w_, h_, x, y] of [[0.06, 2.18, -0.58, 1.09], [0.06, 2.18, 0.58, 1.09], [1.22, 0.06, 0, 2.18]]) slab(hall, w_, h_, 0.1, x, y, HZ0 + 0.03, steel);
panelMesh(hall, { w: 0.36, h: 0.14, x: 0, y: 2.33, z: HZ0 + 0.04, ppu: 900, boost: 1.9, key: dispKey, draw: dispDraw });
// apartment doors with number plates
for (const [sx, z, n] of [[-1, 3.0, '601'], [1, 5.4, '602'], [-1, 7.9, '603'], [1, 10.3, '604']]) {
  const g = new THREE.Group(); g.position.set(sx * (HX - 0.03), 0, z); g.rotation.y = -sx * PI / 2; hall.add(g);
  g.add(at(box(0.88, 2.04, 0.05, 0.015, doorMat), 0, 1.02, 0));
  for (const [w_, h_, x, y] of [[0.06, 2.1, -0.47, 1.05], [0.06, 2.1, 0.47, 1.05], [1.0, 0.06, 0, 2.1]]) g.add(at(box(w_, h_, 0.08, 0.01, steelDark), x, y, 0.01));
  g.add(at(new THREE.Mesh(new THREE.SphereGeometry(0.03, 12, 10), steel), 0.34, 1.0, 0.05));
  panelMesh(g, { w: 0.16, h: 0.07, x: 0, y: 1.62, z: 0.03, ppu: 1200, boost: 1.2, draw: (c, t, P) => { c.fillStyle = '#c9ced6'; rrect(c, 0, 0, P.cw, P.ch, 10); c.fill(); text(c, n, P.cw / 2, P.ch / 2 + 2, { size: 60, weight: 800, color: '#14161a' }); } });
}
// ceiling lamps (one always flickers) + the lamp at the far end (off until the reveal)
const LAMPS = [2.4, 4.8, 7.2, 9.6, 12.1].map((z, i) => {
  const m = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.03, 28), m); disc.position.set(0, HH - 0.02, z); hall.add(disc);
  const l = new THREE.PointLight(0xfff0dc, 0, 4.2, 1.5); l.position.set(0, HH - 0.2, z); hall.add(l);
  return { m, l, z, i };
});
const LT = { car: 1, hall: 0, end: 0, env: 1 };
const flick = t => { const a = hash(Math.floor(t * 9)), b = hash(Math.floor(t * 23) + 7); return a < 0.18 ? 0.05 : b < 0.12 ? 0.35 : 1; };
every(t => {
  carLightMat.color.setScalar(2.1 * LT.car + 0.02); carLight.intensity = 2.4 * LT.car;
  for (const L_ of LAMPS) {
    let k = LT.hall * (L_.i === 2 ? flick(t) : 1) * (L_.i === 4 ? LT.end : 1);
    L_.m.color.setRGB(2.3 * k + 0.02, 2.15 * k + 0.02, 1.9 * k + 0.02); L_.l.intensity = 1.7 * k;
  }
  lights.ambient.intensity = (0.03 + 0.04 * Math.max(LT.car, LT.hall)) * LT.env; scene.environmentIntensity = 0.45 * LT.env;
});
tl.set(key, { intensity: 0 }, 0); tl.set(lights.moon, { intensity: 0 }, 0); tl.set(lights.rim, { intensity: 0.08 }, 0);

// dust in the air
{
  const R = mulberry32(51), P = Array.from({ length: 110 }, () => [(R() - 0.5) * 1.8, 0.3 + R() * 2.1, -0.6 + R() * 13, R() * 6.28, 0.4 + R()]);
  scene.add(particles({ count: P.length, texture: TEX.soft, size: 0.011, color: '#dfe6ff', boost: 1.4, fn: (t, p, a) => P.forEach((d, i) => { p.set([d[0] + Math.sin(t * 0.3 * d[4] + d[3]) * 0.08, d[1] + Math.sin(t * 0.2 + d[3]) * 0.06, d[2] + Math.cos(t * 0.25 * d[4] + d[3]) * 0.08], i * 3); a[i] = 0.3 + 0.3 * Math.sin(t * d[4] + d[3]); }) }));
}

// ---------------------------------------------------------------- people
const STAND_Y = 0.83 * 0.85;
function person() { const f = stickFigure(); f.userData.root.scale.setScalar(0.85); f.userData.pool.visible = false; scene.add(f); return f; }
const YOU = person(), yp = YOU.userData.pose;
setPose(YOU, 'stand', { x: 0.1, y: STAND_Y, z: -0.15, ry: 0, cold: 0 });
const IT = person(), ip = IT.userData.pose;
setPose(IT, 'stand', { x: 0, y: STAND_Y, z: HZ1 - 0.45, ry: 0, alpha: 0, neckX: 0.18 });
every(() => { IT.visible = ip.alpha > 0.003; });
const itRun = { k: 0 };   // 0..1 sprint from z 4.2 to the doors
every(t => { if (itRun.k > 0 && itRun.k < 1) { ip.z = lerp(4.2, 1.2, itRun.k); ip.walk = itRun.k * 4.5; } });

// ================================================================ BEATS
music(0, 0.45);
sfx('engine', 0, 0.45, { dur: tDont - 0.2 });     // the car humming upward
// 1 HOOK — alone in the elevator; the display climbs; it stops on six; you pressed eight
tl.set(DISP, { f: '5' }, 1.1); tl.set(DISP, { f: '6' }, tDidnt - 0.25); tl.set(DISP, { up: 0 }, tDont - 0.2);
camSet(0, { x: -0.2, y: 1.22, z: 0.62, tx: 0.08, ty: 1.42, tz: -0.5, roll: -3, fov: 60 });
camTo(0, { x: -0.1, y: 1.3, z: 0.55, roll: 0 }, tDidnt - 0.05, 'none');
camSet(tDidnt - 0.05, { x: 0.28, y: 1.42, z: 0.18, tx: 0.65, ty: 1.3, tz: CZ, roll: 0, fov: 42 });
camTo(tDidnt - 0.05, { x: 0.32, z: 0.3 }, tDont - tDidnt - 0.05, 'none');
sfx('tick', tDidnt - 0.25, 0.5); shake(tDidnt - 0.25, 0.3, 0.3);
// 2 DON'T STEP OUT — ding; the doors open on a dark hallway
sfx('ding', tDont - 0.15, 0.7); sfx('hiss', tDont, 0.25);
tl.to(door, { open: 1, duration: 1.3, ease: 'power2.inOut' }, tDont - 0.05); tl.set(LT, { hall: 1 }, tDont);
camSet(tDont - 0.1, { x: 0.22, y: 1.6, z: -0.66, tx: -0.05, ty: 1.28, tz: 8, roll: 0, fov: 50 });
camTo(tDont - 0.1, { z: -0.5 }, tHall - tDont + 0.1, 'none');
flash(tDont, 0.2, 0.25, '#ff2030'); sfx('hit', tDont, 0.35);
// 3 THE HALLWAY — exactly like yours: push to the threshold; the carpet; the flickering light
camTo(tHall, { x: 0.15, y: 1.5, z: 0.35, tz: 8 }, tCarpet - tHall, 'power1.inOut');
camSet(tCarpet, { x: 0.25, y: 0.34, z: 1.25, tx: 0.0, ty: 0.0, tz: 5.0, roll: 3, fov: 50 });
camTo(tCarpet, { z: 1.7 }, tLight - tCarpet, 'none');
camSet(tLight, { x: 0.32, y: 1.28, z: 5.3, tx: 0.0, ty: 2.45, tz: 7.2, roll: -4, fov: 50 });
camTo(tLight, { z: 5.55 }, tEnd - tLight, 'none');
sfx('buzz', tLight, 0.5); sfx('buzz', tLight + 0.7, 0.35);
music(tHall, 0.55);
// 4 SOMEONE AT THE END — the end lamp sputters on: a figure, face to the wall
camSet(tEnd, { x: 0.0, y: 1.5, z: 0.3, tx: 0.0, ty: 1.15, tz: 12.5, roll: 0, fov: 22 });
camTo(tEnd, { fov: 13, y: 1.42 }, tSpeak - tEnd, 'power1.in');
[0, 0.12, 0.3].forEach((d, i) => tl.set(LT, { end: i % 2 ? 0.2 : 1 }, tSomeone - 0.15 + d));
tl.to(ip, { alpha: 1, duration: 0.25 }, tSomeone - 0.1);
sfx('flicker', tSomeone - 0.15, 0.5); sfx('stinger', tSomeone, 0.45, { soft: 1 }); music(tEnd, 0.65, { heart: 0.35 });
// 5 DON'T SPEAK / DON'T HOLD THE DOOR — you, seen from the hallway; a hand drifts to the door, then back
camSet(tSpeak, { x: 0.3, y: 1.45, z: 1.75, tx: 0.12, ty: 1.35, tz: -0.15, roll: 2, fov: 38 });
camTo(tSpeak, { z: 1.55 }, tPress - tSpeak, 'none');
tl.to(yp, { lShX: -1.0, lShZ: 0.35, lElX: -0.2, duration: 0.45 }, tHold - 0.1);
tl.to(yp, { lShX: 0, lShZ: 0.08, lElX: 0, duration: 0.3 }, tPress - 0.35);
// 6 PRESS CLOSE. ONCE.
tl.to(yp, { x: 0.36, z: 0.24, duration: 0.5, ease: 'power2.inOut' }, tPress - 0.1);
tl.fromTo(yp, { walk: 0 }, { walk: 1, duration: 0.5, immediateRender: false }, tPress - 0.1);
camSet(tPress, { x: -0.22, y: 1.48, z: 0.42, tx: 0.66, ty: 1.15, tz: CZ, roll: 0, fov: 40 });
camTo(tPress, { x: -0.15 }, tSlow - tPress, 'none');
tl.to(yp, { lShX: -1.4, lShZ: 0.3, lElX: -0.15, duration: 0.35, ease: 'power2.out' }, tClose1 - 0.3);
tl.set(PANEL, { close: 1 }, tClose1 + 0.05); sfx('click', tClose1 + 0.05, 0.8);
tl.to(yp, { lShX: 0, lShZ: 0.08, lElX: 0, duration: 0.4 }, tOnce + 0.35); tl.set(PANEL, { close: 0 }, tOnce + 0.5);
// 7 CLOSING SLOWLY — from behind you: the doors creep shut; the figure hasn't moved
camSet(tSlow, { x: 0.12, y: 1.6, z: -0.62, tx: 0.0, ty: 1.25, tz: 10, roll: 0, fov: 34 });
camTo(tSlow, { z: -0.5 }, tStop - tSlow, 'none');
tl.to(door, { open: 0.46, duration: tHalf - tSlow - 0.1, ease: 'none' }, tSlow);
sfx('engine', tSlow, 0.25, { dur: tHalf - tSlow });
// 8 THEY STOP HALFWAY — a clunk; the display glitches; don't look
tl.fromTo(door, { jolt: 1 }, { jolt: 0, duration: 0.3, ease: 'elastic.out(1, 0.3)', immediateRender: false }, tHalf - 0.1);
sfx('thunk', tHalf - 0.1, 0.9); shake(tHalf - 0.1, 0.6, 0.4); flicker(tHalf, 2, 0.6);
tl.set(DISP, { glitch: 1, red: 1 }, tHalf); tl.set(DISP, { glitch: 0, f: '7', up: 1, red: 0 }, tSlam + 0.9);
camSet(tStop, { x: 0.1, y: 1.38, z: 3.3, tx: 0.12, ty: 1.22, tz: 0.4, roll: -2, fov: 40 });
camTo(tStop, { z: 3.0 }, tDontLook - tStop, 'none');
camSet(tDontLook, { x: 0.18, y: 1.42, z: 1.5, tx: 0.34, ty: 1.3, tz: 0.2, roll: 3, fov: 34 });
camTo(tDontLook, { z: 1.35 }, tGap - tDontLook, 'none');
tl.to(yp, { neckX: 0.6, tremble: 0.6, duration: 0.4 }, tDontLook + 0.2);
music(tStop, 0.75, { heart: 0.8 });
// 9 IT ISN'T FACING THE WALL ANYMORE — through the gap: the end is empty… then it's closer… closer
camSet(tGap, { x: 0.04, y: 1.5, z: -0.35, tx: 0.0, ty: 1.3, tz: 10, roll: 0, fov: 36 });
camTo(tGap, { z: -0.2 }, tBreath - tGap, 'none');
tl.set(LT, { hall: 0 }, tGap + 0.15); tl.set(LT, { hall: 1 }, tGap + 0.45); sfx('flicker', tGap + 0.15, 0.6);
tl.set(ip, { alpha: 0 }, tGap + 0.2);
tl.set(LT, { hall: 0 }, tIsnt - 0.05); tl.set(LT, { hall: 1 }, tIsnt + 0.12);
tl.set(ip, { alpha: 1, z: 7.6, ry: PI, neckX: 0.05, eyeWhite: 1 }, tIsnt + 0.05); tl.set(IT.userData.face, { visible: true }, tIsnt + 0.05);
sfx('flicker', tIsnt - 0.05, 0.6); sfx('hit', tIsnt + 0.12, 0.7);
tl.set(LT, { hall: 0 }, tAnymore - 0.05); tl.set(LT, { hall: 1 }, tAnymore + 0.1);
tl.set(ip, { z: 4.2 }, tAnymore); sfx('hit', tAnymore + 0.1, 0.9); shake(tAnymore + 0.1, 0.4, 0.3);
tl.to(ip, { smile: 1, duration: 0.5 }, tAnymore + 0.2);
// 10 HOLD YOUR BREATH, PRESS CLOSE AGAIN — jab the button; it sprints; the doors slam on it
camSet(tBreath, { x: -0.22, y: 1.48, z: 0.42, tx: 0.66, ty: 1.15, tz: CZ, roll: 2, fov: 40 });
camTo(tBreath, { x: -0.16 }, tAgain - 0.85 - tBreath, 'none');
tl.to(yp, { neckX: 0.25, lShX: -1.4, lShZ: 0.3, lElX: -0.15, tremble: 0.9, duration: 0.3 }, tBreath + 0.2);
for (let i = 0; i < 3; i++) { const tt = tBreath + 0.45 + i * 0.28; tl.fromTo(yp, { lElX: -0.45 }, { lElX: -0.1, duration: 0.12, immediateRender: false }, tt); tl.set(PANEL, { close: 1 }, tt + 0.1); tl.set(PANEL, { close: 0 }, tt + 0.25); sfx('click', tt + 0.1, 0.7); }
camSet(tAgain - 0.85, { x: 0.04, y: 1.5, z: -0.3, tx: 0.0, ty: 1.3, tz: 10, roll: 0, fov: 38 });
camTo(tAgain - 0.85, { z: -0.1 }, tSlam - tAgain + 1.6, 'none');
tl.set(ip, Object.assign({}, POSES.creep, { torsoX: 0.35, lShX: -1.3, rShX: -1.3, neckX: -0.1 }), tAgain - 0.75);
tl.to(itRun, { k: 0.999, duration: tSlam - tAgain + 0.8, ease: 'power1.in' }, tAgain - 0.75);
for (let i = 0; i < 7; i++) sfx('step', tAgain - 0.7 + i * 0.15, 0.6 + i * 0.05);
tl.to(door, { open: 0, duration: 0.22, ease: 'power3.in' }, tSlam - 0.22); sfx('slam', tSlam, 1.0);
tl.set(ip, { alpha: 0 }, tSlam + 0.25); tl.set(LT, { hall: 0 }, tSlam + 0.05);
tl.fromTo(door, { jolt: 2 }, { jolt: 0, duration: 0.5, ease: 'elastic.out(1, 0.25)', immediateRender: false }, tSlam + 0.25);
sfx('knock', tSlam + 0.25, 1.0); shake(tSlam + 0.25, 1.0, 0.6); flash(tSlam + 0.25, 0.3, 0.2);
music(tSlam, 0.0); music(tSlam + 1.2, 0.5, { heart: 0.5 });
tl.to(yp, { lShX: 0, lShZ: 0.08, lElX: 0, torsoX: -0.12, neckX: 0.1, duration: 0.25 }, tSlam);
// …silence. inside, the car starts moving again
camSet(tSlam + 0.75, { x: -0.52, y: 1.5, z: -0.58, tx: 0.32, ty: 1.25, tz: 0.6, roll: 0, fov: 54 });
camTo(tSlam + 0.75, { x: -0.45, z: -0.5 }, tMirror - tSlam - 0.75, 'none');
sfx('engine', tSlam + 0.9, 0.45, { dur: tCta - tSlam - 0.6 });
// 11 LOOK IN THE MIRROR — you turn around; the reflection: just you
tl.to(yp, { torsoX: 0, tremble: 0.45, duration: 0.3 }, tMirror);
tl.to(yp, { x: 0.42, z: 0.05, ry: PI, duration: 0.8, ease: 'power2.inOut' }, tLookM - 0.45);
tl.fromTo(yp, { walk: 1 }, { walk: 2, duration: 0.8, immediateRender: false }, tLookM - 0.45);
camSet(tMirror, { x: 0.2, y: 1.55, z: 0.62, tx: 0.05, ty: 1.3, tz: -CZ, roll: 0, fov: 64 });
camTo(tMirror, { x: 0.16, z: 0.56 }, tCorner - tMirror, 'none');
tl.set(DISP, { f: '8' }, tCorner - 0.3);
// 12 SOMEONE IN THE CORNER BEHIND YOU — only in the mirror; then it turns its head
tl.set(ip, Object.assign({}, POSES.stand, { x: -0.62, y: STAND_Y, z: 0.55, ry: -PI / 4, walk: 0, smile: 0, eyeWhite: 0, neckX: 0.2, neckY: 0, alpha: 0 }), tCorner);
tl.set(IT.userData.face, { visible: false }, tCorner);
tl.set(itRun, { k: 1 }, tCorner);
tl.to(ip, { alpha: 1, duration: 0.2 }, tSomeone2 + 0.05); flicker(tSomeone2, 2, 0.5);
camTo(tCorner, { x: 0.1, y: 1.5, z: 0.4, tx: 0.02 }, tGot - tCorner, 'power1.in');
sfx('stinger', tSomeone2 + 0.1, 0.5, { soft: 1 }); music(tCorner, 0.7, { heart: 0.9 });
tl.set(IT.userData.face, { visible: true }, tGot + 0.1);
tl.to(ip, { neckY: PI, duration: 0.6, ease: 'power2.inOut' }, tGot);
tl.to(ip, { eyeWhite: 1, duration: 0.1 }, tGot + 0.45); tl.to(ip, { smile: 1, duration: 0.4 }, tGot + 0.55);
sfx('creak', tGot, 0.5, { dur: 0.7 }); sfx('stinger', tGot + 0.5, 1.0); flash(tGot + 0.5, 0.3, 0.25, '#ff2030'); shake(tGot + 0.5, 0.6, 0.4);
tl.to(LT, { car: 0.0, env: 0.12, duration: 0.08 }, tGot + 1.15); flicker(tGot + 1.0, 2, 0.8);
tl.set(DISP, { red: 1, f: '?', up: 0 }, tGot + 0.5);
music(tGot + 0.5, 0.6, { heart: 0.4 });
// 13 CTA — from the hallway of your floor: ding, the doors open… and the mirror shows who's riding with you
tl.set(LT, { car: 1, hall: 1, end: 1, env: 1 }, tCta); tl.set(DISP, { f: '8', up: 0, red: 0, glitch: 0 }, tCta);
tl.set(yp, Object.assign({}, POSES.stand, { x: 0.12, y: STAND_Y, z: -0.12, ry: 0, tremble: 0.35, neckX: 0.05, walk: 0 }), tCta);
tl.set(ip, { neckY: 0, eyeWhite: 0, smile: 0 }, tCta); tl.set(IT.userData.face, { visible: false }, tCta);
tl.set(door, { open: 0, jolt: 0 }, tCta);
tl.to(door, { open: 1, duration: 1.2, ease: 'power2.inOut' }, tCta + 0.35); sfx('ding', tCta + 0.2, 0.7); sfx('hiss', tCta + 0.35, 0.25);
tl.to(door, { open: 0, duration: 1.4, ease: 'power2.inOut' }, DUR - 1.7);
camSet(tCta, { x: 0.0, y: 1.4, z: 5.2, tx: 0.0, ty: 1.55, tz: 0.8, roll: 0, fov: 40 });
camTo(tCta, { z: 4.95 }, DUR - tCta, 'power1.out');
{
  const tF = w('s10', 'follow');
  const q1 = panelMesh(scene, { w: 0.95, h: 0.1, x: 0, y: 2.15, z: 2.6, ppu: 1700, draw: (c, t, P) => text(c, 'WOULD YOU HAVE STEPPED OUT?', P.cw / 2, P.ch / 2, { size: 84, weight: 900, color: '#fff', font: 'Inter Display', spacing: 3, glow: 12 }) });
  const q2 = panelMesh(scene, { w: 0.66, h: 0.06, x: 0, y: 2.05, z: 2.6, ppu: 1700, draw: (c, t, P) => text(c, 'COMMENT  YES  OR  NO', P.cw / 2, P.ch / 2, { size: 58, weight: 800, color: C.red, spacing: 12, glow: 12 }) });
  const fb = panelMesh(scene, { w: 0.5, h: 0.09, x: 0, y: 0.86, z: 2.9, ppu: 1700, key: t => (t > tF + 0.4 ? 'on' : 'off'), draw: (c, t, P) => {
    const on = t > tF + 0.4; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? 'rgba(255,255,255,.06)' : '#ffffff'; c.fill(); if (on) { c.strokeStyle = '#fff'; c.lineWidth = 5; c.stroke(); } c.restore();
    text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR MORE RULES', P.cw / 2, P.ch / 2 + 3, { size: on ? 70 : 56, weight: 900, color: on ? '#fff' : '#08080a', spacing: 3 });
  } });
  [q1, q2, fb].forEach((p, i) => { p.mesh.visible = false; tl.set(p.mesh, { visible: true }, tCta); p.mesh.scale.setScalar(0.0001); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.4, ease: 'back.out(2)', immediateRender: false }, [w('s10', 'would') - 0.05, w('s10', 'comments') - 0.1, tF - 0.1][i]); });
  sfx('pop', w('s10', 'would'), 0.4); sfx('pop', tF, 0.4); sfx('click', tF + 0.4, 0.7);
  music(tCta, 0.5); music(DUR - 0.8, 0.5); music(DUR, 0);
}
tl.set({}, {}, DUR);

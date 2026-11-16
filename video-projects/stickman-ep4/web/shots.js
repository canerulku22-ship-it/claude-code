// Episode 4 — "If you ever fall asleep on the last bus home". The bus is one model (interior + shell) that stays at the
// origin while the world (road, streetlights, reflector posts, bus stops) scrolls past by a distance integral, so both
// interior and exterior shots share one set of geometry. Characters are translucent glowing ghosts (?style=solid: matte).
import { THREE, tl, C, scene, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, particles, text, rrect, floorU, dashedLine, zoomBlur } from './engine.js';
import { T, DUR, S, E, L, w, we, sfx, music, clamp01, lerp } from './lib.js';
import { stickFigure, setPose, POSES, STYLE } from './stick.js';
import { panelMesh, propMat, darkMat, box } from './props.js';

const PI = Math.PI;
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const ss = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
function flicker(t, n = 3, amt = 0.75) { for (let i = 0; i < n; i++) tl.fromTo(post, { flicker: amt }, { flicker: 0, duration: 0.06, immediateRender: false }, t + i * 0.09 + (i % 2) * 0.03); sfx('flicker', t, 0.45); }

// ---------------------------------------------------------------- timeline anchors
const tWake = w('s01', 'wake'), tSilent = w('s01', 'silent'), tInside = L('s01', 1).start - 0.05;
const tDont = w('s02', 'dont'), tFacing = L('s02', 1).start, tStill = L('s02', 2).start;
const tDriver = S('s03'), tTurns = L('s03', 1).start;
const tCount = S('s04'), tOne = L('s04', 1).start, tTwo = L('s04', 2).start, tThree = L('s04', 3).start;
const tFourth = S('s05'), tSame = w('s05', 'same'), tStay = L('s05', 1).start;
const tWalk = S('s06'), tStep = L('s06', 1).start;
const tWhisper = S('s07'), tWStop = w('s07', 'stops'), tWName = w('s07', 'whispers'), tLookUp = L('s07', 1).start;
const tClose = S('s08'), tHands = w('s08', 'look');
const tGlow = S('s09'), tNever = L('s09', 1).start, tHome = w('s09', 'home');
const tCta = S('s10');

// ---------------------------------------------------------------- driving: speed profile + time-skip jumps → distance
const V = 11;
const STOP = { s4: w('s05', 'stand') + 0.1, go4: w('s08', 'close') + 0.55 };
function speedK(t) {
  if (t >= tCta) return 0;                                       // CTA: world holds still, the bus itself drives off
  let k = 1;
  k *= 1 - ss(tCount + 0.2, tOne, t) * (1 - ss(tThree + 0.75, tThree + 1.7, t));   // stops 1-3 (cuts hide the jumps)
  k *= 1 - ss(tFourth - 0.2, STOP.s4, t) * (1 - ss(STOP.go4, STOP.go4 + 1.6, t));
  return k;
}
const JUMPS = [[tTwo - 0.06, 70], [tThree - 0.06, 70]];
const DT = 1 / 240, NS = Math.ceil((DUR + 2) / DT), CUM = new Float32Array(NS + 1);
for (let i = 0; i < NS; i++) CUM[i + 1] = CUM[i] + V * speedK(i * DT) * DT;
function dist(t) {
  const f = Math.max(0, Math.min(NS - 1e-6, t / DT)), i = Math.floor(f);
  let d = CUM[i] + (CUM[i + 1] - CUM[i]) * (f - i);
  for (const [tj, dj] of JUMPS) if (t >= tj) d += dj;
  return d;
}
const D_STOP = [tOne, tTwo, tThree].map(t => dist(t + 0.01));   // where shelters 1..3 sit (door lines up at those times)

// ---------------------------------------------------------------- materials
const wallMat = new THREE.MeshStandardMaterial({ color: 0x4a4e57, roughness: 0.8, metalness: 0.05 });
const shellMat = new THREE.MeshStandardMaterial({ color: 0xa9afb9, roughness: 0.32, metalness: 0.35 });
const seatMat = new THREE.MeshStandardMaterial({ color: 0x1d2027, roughness: 0.9 });
const railMat = new THREE.MeshStandardMaterial({ color: 0xdfe3ea, roughness: 0.25, metalness: 0.7 });
const glassMat = new THREE.MeshBasicMaterial({ color: 0x8fa3c0, transparent: true, opacity: 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
const stripMat = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
const blackMat = new THREE.MeshBasicMaterial({ color: 0x000000 });

// ---------------------------------------------------------------- the bus (local: x ±1.31, z -6.1 front … 3.25 rear, floor y 0)
const bus = new THREE.Group(); scene.add(bus);
const BX = 1.28, ZF = -6.1, ZR = 3.25, YW0 = 0.95, YW1 = 1.85, YR = 2.42, DOOR0 = 1.9, DOOR1 = 2.95, ZDOOR = (DOOR0 + DOOR1) / 2;
const slab = (w, h, d, x, y, z, m = wallMat) => bus.add(at(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m), x, y, z));
// side walls: lower panel, upper band, window pillars (outer shell skin slightly outside)
for (const sx of [-1, 1]) {
  const segs = sx < 0 ? [[ZF, ZR]] : [[ZF, DOOR0], [DOOR1, ZR]];
  for (const [a, b] of segs) { slab(0.05, YW0, b - a, sx * BX, YW0 / 2, (a + b) / 2); slab(0.02, YW0, b - a, sx * (BX + 0.035), YW0 / 2, (a + b) / 2, shellMat); }
  slab(0.05, YR - YW1, ZR - ZF, sx * BX, (YW1 + YR) / 2, (ZF + ZR) / 2); slab(0.02, YR - YW1, ZR - ZF, sx * (BX + 0.035), (YW1 + YR) / 2, (ZF + ZR) / 2, shellMat);
  for (let z = ZF + 0.02; z <= ZR; z += 1.17) slab(0.1, YW1 - YW0, 0.1, sx * (BX + 0.01), (YW0 + YW1) / 2, Math.min(z, ZR - 0.05), shellMat);
  const gl = new THREE.Mesh(new THREE.PlaneGeometry(ZR - ZF, YW1 - YW0), glassMat); gl.rotation.y = PI / 2; gl.position.set(sx * (BX + 0.02), (YW0 + YW1) / 2, (ZF + ZR) / 2); bus.add(gl);
  // window sill rail
  const sill = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, ZR - ZF, 8), railMat); sill.rotation.x = PI / 2; sill.position.set(sx * (BX - 0.06), YW0 + 0.02, (ZF + ZR) / 2); bus.add(sill);
}
slab(BX * 2 + 0.1, 0.1, ZR - ZF + 0.1, 0, YR + 0.05, (ZF + ZR) / 2, shellMat);           // roof
const liveryMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(0.9), toneMapped: false });
for (const sx of [-1, 1]) { slab(0.01, 0.07, ZR - ZF, sx * (BX + 0.05), 0.72, (ZF + ZR) / 2, liveryMat); slab(0.01, 0.16, ZR - ZF, sx * (BX + 0.05), 0.08, (ZF + ZR) / 2, darkMat); }
{ const ws = new THREE.Mesh(new THREE.PlaneGeometry(BX * 2, 2.05 - YW0), glassMat); ws.position.set(0, (YW0 + 2.05) / 2, ZF - 0.01); bus.add(ws); }
slab(BX * 2, 0.02, ZR - ZF, 0, YR - 0.01, (ZF + ZR) / 2, wallMat);                       // ceiling
// front: dash panel, windshield frame, sign band; rear: wall with a window
slab(BX * 2 + 0.08, YW0, 0.08, 0, YW0 / 2, ZF, shellMat);
slab(BX * 2 + 0.08, YR - 2.05, 0.08, 0, (2.05 + YR) / 2, ZF, shellMat);
for (const sx of [-1, 0, 1]) slab(sx ? 0.1 : 0.05, 2.05 - YW0, 0.1, sx * (BX - 0.02), (YW0 + 2.05) / 2, ZF, shellMat);
slab(BX * 2 + 0.08, 1.2, 0.08, 0, 0.6, ZR, shellMat); slab(BX * 2 + 0.08, YR - 1.95, 0.08, 0, (1.95 + YR) / 2, ZR, shellMat);
for (const sx of [-1, 1]) slab(0.55, 0.75, 0.08, sx * (BX - 0.24), 1.575, ZR, shellMat);
// ceiling light strips + interior lights
const strips = [-0.62, 0.62].map(x => { const m = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.03, ZR - ZF - 0.6), stripMat); m.position.set(x, YR - 0.03, (ZF + ZR) / 2 + 0.2); bus.add(m); return m; });
const inLights = [-4.2, -1.3, 1.6].map(z => { const l = new THREE.PointLight(0xe6edff, 0, 6.5, 1.25); l.position.set(0, 2.2, z); bus.add(l); return l; });
const light = { strip: 1, outside: 1, head: 1 };
// grab rails along the ceiling + poles at the aisle
for (const sx of [-1, 1]) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.016, ZR - ZF - 1.2, 8), railMat); r.rotation.x = PI / 2; r.position.set(sx * 0.42, 2.02, (ZF + ZR) / 2 + 0.3); bus.add(r); }
// seats (double benches, facing -z); passenger rows
const ROWS = [-4.3, -3.45, -2.6, -1.75, -0.9, -0.05, 0.8, 1.65];
function bench(sx, z) {
  const g = new THREE.Group(); g.position.set(sx * 0.76, 0, z); bus.add(g);
  g.add(at(box(0.86, 0.1, 0.46, 0.03, seatMat), 0, 0.43, -0.02));
  const back = at(box(0.86, 0.52, 0.07, 0.03, seatMat), 0, 0.76, 0.24); back.rotation.x = -0.1; g.add(back);
  const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.84, 10), railMat); rail.rotation.z = PI / 2; rail.position.set(0, 1.04, 0.27); g.add(rail);
  g.add(at(box(0.1, 0.38, 0.3, 0.02, darkMat), -sx * 0.25, 0.19, 0));
  return g;
}
for (const z of ROWS) { bench(-1, z); if (z < 1.2) bench(1, z); }
// driver area: dash, wheel, seat, partition
slab(BX * 2 - 0.1, 0.25, 0.5, 0, YW0 - 0.1, ZF + 0.3, darkMat);
const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.21, 0.022, 10, 40), darkMat); wheel.position.set(-0.75, 1.1, -5.55); wheel.rotation.x = -1.05; bus.add(wheel);
const dseat = bench(-1, -5.0); dseat.scale.x = 0.55; dseat.position.x = -0.75;
const part = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), glassMat); part.position.set(-0.75, 1.35, -4.66); bus.add(part);
slab(0.9, 0.05, 0.05, -0.75, 1.8, -4.66, railMat); slab(0.04, 1.8, 0.04, -0.29, 0.9, -4.66, railMat);
// floor: aisle LED edge strips + door step well
const aisleMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.55, 0.6, 0.7), toneMapped: false });
for (const sx of [-1, 1]) slab(0.025, 0.012, ZR - ZF - 1.0, sx * 0.31, 0.006, (ZF + ZR) / 2 + 0.3, aisleMat);
slab(0.4, 0.02, DOOR1 - DOOR0, BX - 0.2, 0.01, ZDOOR, new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(0.35), toneMapped: false }));
// rear door: two leaves that slide apart along the outside of the shell
const leafW = (DOOR1 - DOOR0) / 2;
const leaves = [-1, 1].map(s => {
  const g = new THREE.Group(); bus.add(g);
  g.add(at(box(0.05, YW0, leafW - 0.02, 0.01, shellMat), 0, YW0 / 2, 0));
  g.add(at(box(0.05, 0.08, leafW - 0.02, 0.01, shellMat), 0, YW1 - 0.04, 0));
  for (const e of [-1, 1]) g.add(at(box(0.05, YW1 - YW0, 0.05, 0.01, shellMat), 0, (YW0 + YW1) / 2, e * (leafW / 2 - 0.035)));
  const gl = new THREE.Mesh(new THREE.PlaneGeometry(leafW, YW1 - YW0), glassMat); gl.rotation.y = PI / 2; gl.position.y = (YW0 + YW1) / 2; g.add(gl);
  g.userData.s = s; return g;
});
const door = { open: 0 };
every(() => leaves.forEach(g => { const s = g.userData.s; g.position.set(BX + 0.04 + 0.08 * clamp01(door.open * 3), 0, ZDOOR + s * leafW / 2 + s * door.open * (leafW - 0.02)); }));
// darkness beyond the open door at stop 4 (blocks the road view)
const voidPlane = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 2.6), blackMat); voidPlane.rotation.y = -PI / 2; voidPlane.position.set(BX + 1.6, 1.2, ZDOOR); bus.add(voidPlane); voidPlane.visible = false;
// wheels
const wheels = [];
for (const sx of [-1, 1]) for (const z of [-4.4, 1.6]) {
  const g = new THREE.Group(); g.position.set(sx * (BX + 0.17), 0.44, z); bus.add(g);
  const tire = new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.44, 0.3, 32), darkMat); tire.rotation.z = PI / 2; g.add(tire);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.31, 6), railMat); hub.rotation.z = PI / 2; g.add(hub);
  wheels.push(g);
}
// head/tail lights
const headMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 3.1, 2.9), toneMapped: false });
const tailMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(2.6), toneMapped: false });
const glowSprite = (color, s, opacity = 0.7) => { const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: TEX.glow, color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false })); m.scale.setScalar(s); return m; };
const heads = [], tails = [];
for (const sx of [-1, 1]) {
  bus.add(at(new THREE.Mesh(new THREE.CircleGeometry(0.11, 24), headMat), sx * 0.95, 0.55, ZF - 0.05)).children;
  const hg = glowSprite(new THREE.Color('#fff4dc'), 1.6, 0.8); hg.position.set(sx * 0.95, 0.55, ZF - 0.15); bus.add(hg); heads.push(hg);
  const tm = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 0.36), tailMat); tm.position.set(sx * 1.05, 0.75, ZR + 0.05); bus.add(tm);
  const tg = glowSprite(new THREE.Color(C.red), 1.1, 0.7); tg.position.set(sx * 1.05, 0.75, ZR + 0.15); bus.add(tg); tails.push(tg);
}
// headlight beam on the road ahead
const beam = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 16), new THREE.MeshBasicMaterial({ map: TEX.glow, color: new THREE.Color('#e9edf5').multiplyScalar(0.55), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
beam.rotation.x = -PI / 2; beam.position.set(0, 0.01, ZF - 8.5); bus.add(beam);
const headLight = new THREE.SpotLight(0xf2f4ff, 0, 30, 0.5, 0.6, 1.2); headLight.position.set(0, 0.8, ZF - 0.2); headLight.target.position.set(0, 0, ZF - 12); bus.add(headLight, headLight.target);

// LED signs: interior "next stop" display + exterior destination signs
const SIGN = { stop: 0, red: 0, dest: 'HOME', glitch: 0 };
function led(c, s, P, color, size) {
  c.fillStyle = '#050608'; rrect(c, 0, 0, P.cw, P.ch, 18); c.fill();
  c.font = `900 ${size}px "Inter Display"`; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.shadowColor = color; c.shadowBlur = 18; c.fillStyle = color; c.fillText(s, P.cw / 2, P.ch / 2 + 4);
  c.shadowBlur = 0; c.fillStyle = 'rgba(5,6,8,.55)';
  for (let y = 0; y < P.ch; y += 7) c.fillRect(0, y, P.cw, 2);
  for (let x = 0; x < P.cw; x += 7) c.fillRect(x, 0, 2, P.ch);
}
const display = panelMesh(bus, { w: 1.3, h: 0.3, x: 0, y: 2.17, z: ZF + 0.07, ppu: 640, boost: 1.9, key: t => `${SIGN.stop}|${SIGN.red > 0.5}|${Math.floor(t * 3) % 2}|${SIGN.glitch > 0 ? Math.floor(t * 20) : 0}`, draw: (c, t, P) => {
  const blink = Math.floor(t * 3) % 2 === 0;
  const s = SIGN.stop === 0 ? (blink ? 'NEXT STOP' : 'NEXT STOP  ▸') : `STOP  ${SIGN.stop}`;
  led(c, SIGN.glitch > 0 && Math.floor(t * 20) % 3 === 0 ? 'ST0P  ?' : s, P, SIGN.red > 0.5 ? '#ff3846' : '#f4f7ff', 120);
} });
const destF = panelMesh(bus, { w: 1.6, h: 0.3, x: 0, y: 2.24, z: ZF - 0.05, ry: PI, ppu: 600, boost: 1.9, key: t => SIGN.dest, draw: (c, t, P) => led(c, SIGN.dest, P, SIGN.dest === 'HOME' ? '#f4f7ff' : '#ff3846', SIGN.dest === 'HOME' ? 130 : 92) });
const destR = panelMesh(bus, { w: 1.4, h: 0.26, x: 0, y: 2.18, z: ZR + 0.05, ppu: 600, boost: 1.9, key: t => SIGN.dest, draw: (c, t, P) => led(c, SIGN.dest, P, SIGN.dest === 'HOME' ? '#f4f7ff' : '#ff3846', SIGN.dest === 'HOME' ? 120 : 80) });

// ---------------------------------------------------------------- the world outside (scrolls by dist(t))
const world = new THREE.Group(); scene.add(world);
const wrap = (z, lo, len) => ((z - lo) % len + len) % len + lo;
floorU.strength.value = 0.32;
const curb = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.14, 400), new THREE.MeshStandardMaterial({ color: 0x3a3e46, roughness: 0.9 })); curb.position.set(3.35, 0.07, 0); world.add(curb);
const centerLine = dashedLine(400, 0, PI / 2, 0.5); centerLine.position.x = -2.05; world.add(centerLine);
const edgeLine = new THREE.Mesh(new THREE.PlaneGeometry(0.06, 400), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.28, depthWrite: false })); edgeLine.rotation.x = -PI / 2; edgeLine.position.set(2.42, 0.004, 0); world.add(edgeLine);
// streetlights: right curb + far left, staggered
const LAMP_SP = 15, LAMP_N = 6, LAMP_LO = -60;
const poleMat = new THREE.MeshStandardMaterial({ color: 0x4a4f58, roughness: 0.6, metalness: 0.4 });
const bulbMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 2.5, 2.3), toneMapped: false });
const lamps = [];
for (const [sx, off] of [[1, 0], [-1, LAMP_SP / 2]]) for (let i = 0; i < LAMP_N; i++) {
  const g = new THREE.Group(); world.add(g);
  const px = sx > 0 ? 3.9 : -5.6;
  g.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 4.6, 10), poleMat), px, 2.3, 0));
  const arm = at(new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.06, 0.08), poleMat), px - sx * 0.5, 4.55, 0); g.add(arm);
  const bulb = at(new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.06, 0.18), bulbMat), px - sx * 1.0, 4.48, 0); g.add(bulb);
  const halo = glowSprite(new THREE.Color('#f4efe4'), 2.4, 0.55); halo.position.set(px - sx * 1.0, 4.4, 0); g.add(halo);
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), new THREE.MeshBasicMaterial({ map: TEX.glow, color: new THREE.Color('#d9d4c8').multiplyScalar(0.35), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
  pool.rotation.x = -PI / 2; pool.position.set(px - sx * 1.2, 0.02, 0); g.add(pool);
  g.userData = { z0: i * LAMP_SP + off, halo, pool, sx, px };
  lamps.push(g);
}
const lampLights = [1, -1].map(sx => { const l = new THREE.PointLight(0xf1ece2, 0, 11, 1.3); l.position.set(sx > 0 ? 3.0 : -4.6, 4.2, 0); scene.add(l); l.userData.sx = sx; return l; });
// reflector posts on the curb: fast streaks that sell the speed
const POST_SP = 6, POST_N = 16;
const postMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.2, 2.2), toneMapped: false });
const posts = Array.from({ length: POST_N }, (_, i) => { const g = new THREE.Group(); g.add(at(new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.9, 0.06), poleMat), 0, 0.45, 0)); g.add(at(new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.12, 0.02), postMat), 0, 0.8, -0.04)); g.position.x = 2.75; g.userData.z0 = i * POST_SP; world.add(g); return g; });
// bus stop shelters 1..3 (each a little darker than the last)
const shelters = D_STOP.map((D, i) => {
  const g = new THREE.Group(); world.add(g);
  g.add(at(box(0.08, 2.3, 2.6, 0.02, poleMat), 3.95, 1.15, 0));
  g.add(at(box(1.2, 0.06, 2.8, 0.02, poleMat), 3.5, 2.33, 0));
  g.add(at(box(0.45, 0.06, 1.8, 0.02, poleMat), 3.65, 0.5, 0));
  const adMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.3, 1.35, 1.45), toneMapped: false });
  g.add(at(new THREE.Mesh(new THREE.BoxGeometry(0.04, 1.4, 0.9), adMat), 3.9, 1.25, -0.7));
  const sign = at(new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.03, 24), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 1.6, 1.6), toneMapped: false })), 2.9, 2.6, 1.6); sign.rotation.z = PI / 2; g.add(sign);
  g.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 2.6, 8), poleMat), 2.9, 1.3, 1.6));
  const sl = new THREE.PointLight(0xe8eeff, 0, 6, 1.4); sl.position.set(3.4, 2.1, -0.3); g.add(sl);
  g.userData = { D, adMat, sl, k: [0.85, 0.45, 0.25][i] };
  return g;
});
every(t => {
  const d = dist(t), lk = light.outside;
  centerLine.material.map.offset.x = -d / 2;
  for (const g of lamps) { g.position.z = wrap(g.userData.z0 + d, LAMP_LO, LAMP_SP * LAMP_N); g.visible = lk > 0.01; g.userData.halo.material.opacity = 0.55 * lk; g.userData.pool.material.opacity = lk; }
  bulbMat.color.setRGB(2.6 * lk + 0.02, 2.5 * lk + 0.02, 2.3 * lk + 0.02);
  for (const l of lampLights) {   // follow the streetlight nearest the bus on that side
    let best = 1e9; for (const g of lamps) if (g.userData.sx === l.userData.sx && Math.abs(g.position.z + 1.4) < Math.abs(best + 1.4)) best = g.position.z;
    l.position.z = best; l.intensity = 9 * lk * (1 - ss(9, 16, Math.abs(best + 1.4)));
  }
  for (const p of posts) { p.position.z = wrap(p.userData.z0 + d, -60, POST_SP * POST_N); p.visible = lk > 0.01; }
  for (const g of shelters) {
    const z = ZDOOR + d - g.userData.D; g.position.z = z; g.visible = z > -70 && z < 40;
    const k = g.userData.k * (g === shelters[2] ? (0.55 + 0.45 * Math.sign(Math.sin(t * 37) + 0.6)) : 1);
    g.userData.adMat.color.setRGB(1.3 * k, 1.35 * k, 1.45 * k); g.userData.sl.intensity = 3.2 * k;
  }
  for (const wh of wheels) wh.rotation.x = -(d + (-bus.position.z)) / 0.44;
  // interior + bus lights
  stripMat.color.setScalar(1.9 * light.strip + 0.03);
  inLights.forEach(l => { l.intensity = 1.1 * light.strip; });
  lights.ambient.intensity = 0.05 + 0.05 * light.strip;
  headMat.color.setRGB(3.2 * light.head, 3.1 * light.head, 2.9 * light.head); heads.forEach(h => { h.material.opacity = 0.8 * light.head; }); beam.material.opacity = light.head; headLight.intensity = 14 * light.head;
});
tl.set(key, { intensity: 0 }, 0); tl.set(lights.moon, { intensity: 0 }, 0); tl.set(lights.rim, { intensity: 0.12 }, 0);
scene.environmentIntensity = 0.35;

// dust in the cabin air (catches the light)
{
  const R = mulberry32(44), P = Array.from({ length: 90 }, () => [(R() - 0.5) * 2.3, 0.4 + R() * 1.9, ZF + R() * (ZR - ZF), R() * 6.28, 0.4 + R()]);
  bus.add(particles({ count: P.length, texture: TEX.soft, size: 0.012, color: '#dfe6ff', boost: 1.4, fn: (t, p, a) => P.forEach((d, i) => { p.set([d[0] + Math.sin(t * 0.3 * d[4] + d[3]) * 0.1, d[1] + Math.sin(t * 0.2 + d[3]) * 0.08, d[2] + Math.cos(t * 0.25 * d[4] + d[3]) * 0.1], i * 3); a[i] = 0.35 + 0.35 * Math.sin(t * d[4] + d[3]); }) }));
}

// ---------------------------------------------------------------- people
const SEATED_Y = 0.52, STAND_Y = 0.83 * 0.85;
function person(opts = {}) { const f = stickFigure(opts); f.userData.root.scale.setScalar(0.85); f.userData.pool.visible = false; bus.add(f); return f; }
const YOU = person(); const yp = YOU.userData.pose;
const YOU_X = -0.98, YOU_Z = 0.8;
setPose(YOU, 'seat', { x: YOU_X, y: SEATED_Y, z: YOU_Z, ry: PI, neckZ: -0.42, neckX: 0.25, cold: 0 });
const PAX = [[0.98, -4.3], [-0.54, -3.45], [0.54, -2.6], [-0.98, -1.75], [0.98, -0.9], [0.54, -0.05]].map(([x, z], i) => {
  const f = person(); setPose(f, 'seat', { x, y: SEATED_Y, z, ry: PI, neckX: 0.02, lShX: -0.3, lElX: -1.0, rShX: -0.3, rElX: -1.0 });
  return { f, p: f.userData.pose, x, z, i };
});
const WH = PAX[0];   // the whisperer: the front-most passenger, last in the line
// driver (cap + hands on the wheel)
const DRV = person(); const dp = DRV.userData.pose;
setPose(DRV, 'seat', { x: -0.75, y: SEATED_Y, z: -5.02, ry: PI, lShX: -1.05, lElX: -0.55, rShX: -1.05, rElX: -0.55, neckX: 0.05 });
{
  const capM = new THREE.MeshStandardMaterial({ color: 0x1a1c22, roughness: 0.6 });
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.135, 0.143, 0.1, 28), capM); cap.position.y = 0.098; DRV.userData.head.add(cap);
  const brim = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.015, 24, 1, false, -PI / 2, PI), capM); brim.position.set(0, 0.052, 0.1); DRV.userData.head.add(brim);
}

// passengers: seated → stand together → single-file, perfectly in step, down the aisle and out the rear door
const tStand = tSame + 0.02, tW0 = tWalk + 0.15, LAT = 0.6;
const WALK_LEN = (YOU_Z - WH.z);                      // whisperer walks this far up the aisle, then stops by you
const VW = 1.15;                                      // one shared, unhurried pace
const tWStart = (tWStop + 0.25) - WALK_LEN / VW;     // the whisperer waits, then comes last
const tWGo = tLookUp + 0.85, VW2 = VW * 1.6;         // …and leaves after the long pause
const tWExit = tWGo + (ZDOOR - (YOU_Z + 0.06) + BX + 0.4) / VW2;
const wpose = { lean: 0 };
const AISLE_X = 0.02;
function walker(m, t) {
  const p = m.p, side = m.x > 0 ? 1.5 * PI : 0.5 * PI, fwd = m.x > 0 ? 2 * PI : 0, right = m.x > 0 ? 2.5 * PI : 0.5 * PI;
  if (t < tStand) { p.x = m.x; p.z = m.z; p.y = SEATED_Y; p.ry = PI; p.walk = 0; p.alpha = 1; return; }
  const ky = ss(tStand, tStand + 0.22, t);
  p.y = lerp(SEATED_Y, STAND_Y, ky); p.z = m.z + 0.06 * ky;
  if (t < tW0) { p.x = m.x; p.ry = PI; p.walk = 0; p.alpha = 1; return; }
  // lateral into the aisle
  const kl = ss(tW0, tW0 + LAT, t);
  p.x = lerp(m.x, AISLE_X, kl); p.ry = lerp(PI, side, ss(tW0, tW0 + 0.3, t));
  let walked = Math.abs(m.x - AISLE_X) * kl;
  if (t < tW0 + LAT) { p.walk = walked / 0.7; p.alpha = 1; return; }
  // up the aisle (toward the rear)
  let s = VW * (t - tW0 - LAT), paused = 0;
  if (m === WH) {   // waits its turn, stops by you, leans in, then goes on (faster)
    s = VW * Math.max(0, t - tWStart); paused = t < tWStart ? 1 : 0;
    if (s >= WALK_LEN) { s = WALK_LEN + Math.max(0, t - tWGo) * VW2; paused = t < tWGo ? 1 : 0; }
  }
  const zA = m.z + 0.06, aisleLen = ZDOOR - zA;
  p.ry = lerp(side, fwd, ss(tW0 + LAT - 0.25, tW0 + LAT + 0.15, t));
  if (s < aisleLen) { p.z = zA + s; p.x = AISLE_X - (m === WH ? 0.14 * ss(tWStop, tWStop + 0.6, t) * (1 - ss(tWGo - 0.3, tWGo, t)) : 0); }
  else {
    const s2 = s - aisleLen; p.z = ZDOOR; p.x = AISLE_X + s2;
    p.ry = lerp(fwd, right, ss(0, 0.35, s2));
    p.y = STAND_Y - 0.32 * ss(BX - 0.1, BX + 0.35, p.x);
    p.alpha = 1 - ss(BX - 0.1, BX + 0.55, p.x);
    p.ghost = p.x > BX - 0.25 ? 1 : 0;   // solid style: they turn to light as they step out
  }
  if (m === WH && paused && t > tWStop) p.ry = lerp(fwd, fwd - 0.5 * PI, ss(tWStop + 0.2, tWStop + 0.6, t)) + lerp(0, 0.5 * PI, ss(tWGo - 0.4, tWGo, t));
  walked += s; p.walk = paused ? Math.round(walked / 0.7 * 2) / 2 : walked / 0.7;
  f_visible(m, p.alpha > 0.002);
}
function f_visible(m, v) { m.f.visible = v; }
every(t => { for (const m of PAX) walker(m, t); });
// joint poses (GSAP): stand together, swing arms while walking, the whisperer leans in
PAX.forEach(m => {
  tl.to(m.p, Object.assign({}, POSES.stand, { neckX: 0, duration: 0.22, ease: 'power3.out' }), tStand);
});
tl.to(WH.p, Object.assign({}, POSES.lean, { torsoX: 0.95, neckX: 0.3, neckZ: 0, lShX: -0.2, rShX: -0.2, lElX: -0.2, rElX: -0.2, duration: 0.5, ease: 'power2.inOut' }), tWStop + 0.35);
tl.to(WH.p, Object.assign({}, POSES.stand, { duration: 0.4 }), tWGo - 0.45);
tl.fromTo(WH.p, { eyeWhite: 0 }, { eyeWhite: 1, duration: 0.15, immediateRender: false }, tLookUp + 0.25);
tl.to(WH.p, { smile: 1, duration: 0.5 }, tLookUp + 0.45);
tl.set(WH.f.userData.face, { visible: true }, tLookUp + 0.2);
tl.to(WH.p, { eyeWhite: 0, smile: 0, duration: 0.2 }, tWGo - 0.3);
tl.set(WH.f.userData.face, { visible: false }, tWGo);
// footsteps: everyone in step (one shared stride)
{
  const stepT = 0.7 / 2 / VW;
  for (let t = tW0 + LAT; t < tW0 + LAT + (ZDOOR - PAX[1].z + BX) / VW; t += stepT) sfx('step', t, 0.42);
  for (let t = tWGo + 0.1; t < tWExit; t += 0.7 / 2 / VW2) sfx('step', t, 0.5);
}

// ---------------------------------------------------------------- cuts, lights, signs, sound
music(0, 0.45);
sfx('engine', 0, 0.8, { dur: tSilent + 0.05 });
// 1 HOOK — the bus at night, coming at us; its windows full of glowing passengers
camSet(0, { x: -2.9, y: 0.75, z: -15.0, tx: -0.35, ty: 1.55, tz: -4.2, roll: 3, fov: 38 });
camTo(0, { x: -2.75, y: 1.0, z: -11.6, tx: -0.55, ty: 1.5, tz: -3.4, roll: 0 }, tInside, 'power1.inOut');
sfx('swoosh', 0.4, 0.3);
// 2 WAKE — you asleep against the window; streetlights sweep; you jolt awake; the engine dies
camSet(tInside, { x: -0.05, y: 1.36, z: -0.85, tx: -1.0, ty: 1.08, tz: 0.8, roll: 2, fov: 42 });
camTo(tInside, { x: -0.2, z: -0.55, ty: 1.1 }, S('s02') - tInside, 'none');
sfx('whoosh', tInside, 0.25);
tl.to(yp, { neckZ: 0, neckX: 0.05, duration: 0.18, ease: 'power3.out' }, tWake - 0.05);
tl.to(yp, { neckY: 0.35, duration: 0.25 }, tWake + 0.35); tl.to(yp, { neckY: -0.2, duration: 0.3 }, tWake + 0.75); tl.to(yp, { neckY: 0, duration: 0.3 }, tSilent + 0.3);
sfx('hit', tWake - 0.05, 0.35);
tl.to(light, { strip: 0.55, duration: 0.15 }, tSilent + 0.1); flicker(tSilent + 0.1, 3, 0.6);
music(tSilent, 0.3, { heart: 0.25 }); music(tSilent + 1.5, 0.55, { heart: 0.25 });
// 3 PASSENGERS — over your shoulder down the aisle; dolly between the still rows; then from the front: faceless, frozen
camSet(S('s02'), { x: -0.32, y: 1.5, z: 1.8, tx: 0.25, ty: 1.05, tz: -3.8, roll: 0, fov: 44 });
camTo(S('s02'), { z: 1.55, y: 1.45 }, tFacing - S('s02'), 'none');
tl.to(yp, { neckY: -0.55, duration: 0.3 }, tDont - 0.1); tl.to(yp, { neckY: 0, duration: 0.2, ease: 'power3.out' }, tDont + 0.35);
flash(tDont, 0.2, 0.25, '#ff2030'); sfx('hit', tDont, 0.35);
camSet(tFacing, { x: 0.02, y: 1.38, z: 1.2, tx: 0.0, ty: 1.12, tz: -6, roll: 0, fov: 50 });
camTo(tFacing, { z: -1.4, y: 1.32 }, tStill - tFacing, 'power1.inOut');
camSet(tStill, { x: 0.0, y: 2.22, z: -5.75, tx: 0.0, ty: 0.85, tz: -0.4, roll: 0, fov: 60 });
camTo(tStill, { z: -5.45, y: 2.15 }, tDriver - tStill, 'none');
sfx('stinger', tStill, 0.4, { soft: 1 });
// 4 DRIVER — his back, the wheel, the road rushing in the headlights; the head ticks, just once
camSet(tDriver, { x: 0.3, y: 1.55, z: -3.3, tx: -0.72, ty: 1.08, tz: -5.4, roll: -2, fov: 44 });
camTo(tDriver, { x: 0.18, z: -3.6 }, tTurns - tDriver, 'none');
camSet(tTurns, { x: -0.4, y: 1.5, z: -3.55, tx: -0.75, ty: 1.2, tz: -5.1, roll: 0, fov: 40 });
camTo(tTurns, { z: -3.8 }, tCount - tTurns, 'none');
tl.to(dp, { neckY: 0.12, duration: 0.08 }, w('s03', 'turns') + 0.15); tl.to(dp, { neckY: 0, duration: 0.5, ease: 'power2.inOut' }, w('s03', 'turns') + 0.6);
sfx('tick', w('s03', 'turns') + 0.15, 0.9);
// 5 COUNT — the display; three stops, each colder and darker outside
camSet(tCount, { x: 0.2, y: 1.85, z: -2.5, tx: 0.0, ty: 2.12, tz: ZF, roll: -2, fov: 40 });
camTo(tCount, { z: -2.85 }, tOne - tCount, 'none');
sfx('ding', tCount + 0.3, 0.5); sfx('brake', tOne - 0.55, 0.5);
tl.set(SIGN, { stop: 1 }, tOne - 0.02);
camSet(tOne, { x: 2.3, y: 1.5, z: 11.0, tx: 1.85, ty: 1.4, tz: -1.0, roll: 0, fov: 40 });
camTo(tOne, { z: 10.4 }, tTwo - tOne, 'none');
tl.set(light, { outside: 0.8 }, tOne); sfx('hiss', tOne + 0.05, 0.4);
tl.set(SIGN, { stop: 2 }, tTwo - 0.02);
camSet(tTwo, { x: -0.55, y: 1.35, z: 0.2, tx: 3.6, ty: 1.3, tz: 1.9, roll: 0, fov: 48 });
camTo(tTwo, { x: -0.45 }, tThree - tTwo, 'none');
tl.set(light, { outside: 0.5 }, tTwo - 0.06); sfx('hiss', tTwo + 0.05, 0.4); flicker(tTwo - 0.06, 1, 0.5);
tl.set(SIGN, { stop: 3 }, tThree - 0.02);
camSet(tThree, { x: -0.2, y: 1.9, z: -3.0, tx: 0.0, ty: 2.15, tz: ZF, roll: 3, fov: 36 });
camTo(tThree, { z: -3.3 }, tFourth - tThree, 'none');
tl.set(light, { outside: 0.25 }, tThree - 0.06); sfx('hiss', tThree + 0.05, 0.4); flicker(tThree - 0.06, 2, 0.6);
tl.to(light, { outside: 0.0, duration: 0.6 }, tThree + 0.6);
music(tCount, 0.6, { heart: 0.45 });
// 6 FOURTH STOP — red 4, hard brake, outside goes black; they all stand at once
tl.set(SIGN, { stop: 4, red: 1 }, tFourth + 0.05);
camSet(tFourth, { x: 0.25, y: 1.85, z: -2.6, tx: 0.0, ty: 2.12, tz: ZF, roll: 2, fov: 40 });
camTo(tFourth, { z: -3.0 }, w('s05', 'theyll') - tFourth, 'power1.in');
camSet(w('s05', 'theyll'), { x: 0.0, y: 2.2, z: -5.7, tx: 0.0, ty: 0.95, tz: -0.4, roll: 0, fov: 58 });
camTo(w('s05', 'theyll'), { z: -5.2, y: 2.05 }, tStay - w('s05', 'theyll'), 'power1.in');
sfx('brake', tFourth, 0.8); shake(STOP.s4 - 0.3, 0.5, 0.6); sfx('hiss', STOP.s4, 0.6);
tl.to(light, { strip: 0.4, duration: 0.2 }, tFourth + 0.2);
sfx('slam', tStand, 0.6); shake(tStand, 0.8, 0.4); flash(tStand, 0.25, 0.2); flicker(tStand + 0.05, 2, 0.7);
music(tFourth, 0.75, { heart: 0.7 });
// STAY IN YOUR SEAT — you grip the seat in front; a red ring locks you in
camSet(tStay, { x: 0.3, y: 1.62, z: 2.25, tx: -0.9, ty: 0.92, tz: 0.6, roll: -3, fov: 46 });
camTo(tStay, { x: 0.2, z: 2.0 }, tWalk - tStay, 'none');
tl.to(yp, { lShX: -1.25, lElX: -0.35, rShX: -1.25, rElX: -0.35, neckX: 0.15, tremble: 0.7, duration: 0.25 }, tStay - 0.1);
const ring = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.455, 56), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(3), transparent: true, opacity: 0, toneMapped: false, side: THREE.DoubleSide }));
ring.rotation.x = -PI / 2; ring.position.set(YOU_X + 0.05, 0.012, YOU_Z - 0.05); bus.add(ring);
tl.to(ring.material, { opacity: 0.95, duration: 0.25 }, tStay); tl.to(ring.material, { opacity: 0, duration: 0.4 }, tWalk + 1.0);
sfx('hit', tStay, 0.45);
// 7 WALK PAST — door opens to nothing; they come down the aisle in step
tl.to(door, { open: 1, duration: 0.7, ease: 'power2.inOut' }, tWalk - 0.25); tl.set(voidPlane, { visible: true }, tWalk - 0.3); sfx('hiss', tWalk - 0.25, 0.6);
camSet(tWalk, { x: -0.72, y: 1.22, z: 1.3, tx: 0.1, ty: 1.15, tz: -2.6, roll: 2, fov: 46 });
camTo(tWalk, { x: -0.6, tx: 0.35, tz: -1.5 }, tStep - tWalk, 'power1.inOut');
camSet(tStep, { x: -1.05, y: 2.12, z: 3.0, tx: 1.35, ty: 0.85, tz: 2.1, roll: 0, fov: 56 });
camTo(tStep, { x: -0.9, y: 2.05 }, tWhisper - tStep, 'none');
sfx('whoosh', tStep + 0.6, 0.2);
// 8 WHISPER — one of them stops right next to you and leans in
camSet(tWhisper, { x: -0.35, y: 1.42, z: 1.9, tx: 0.05, ty: 1.15, tz: -1.5, roll: 2, fov: 46 });
camTo(tWhisper, { z: 1.75 }, tWName - 0.1 - tWhisper, 'none');
camSet(tWName - 0.1, { x: -2.45, y: 1.3, z: 0.66, tx: -0.55, ty: 1.15, tz: 0.76, roll: 0, fov: 42 });
camTo(tWName - 0.1, { x: -2.2 }, tLookUp - tWName + 0.1, 'none');
tl.to(yp, { neckX: 0.62, neckY: 0, tremble: 1, lShX: -0.85, lElX: -0.8, rShX: -0.85, rElX: -0.8, duration: 0.4 }, tWName - 0.1);
const hush = panelMesh(bus, { w: 0.5, h: 0.2, x: -0.5, y: 1.46, z: 0.8, ry: -PI / 2, ppu: 700, boost: 1.0, key: t => (t > tWName && t < tLookUp + 0.6 ? Math.floor(t * 24) : 'x'), draw: (c, t, P) => {
  if (!(t > tWName && t < tLookUp + 0.6)) return;
  const k = Math.min(1, (t - tWName) * 4) * (1 - clamp01((t - tLookUp - 0.3) / 0.3));
  c.save(); c.globalAlpha = k; c.font = '900 92px "Inter Display"'; c.textAlign = 'center'; c.textBaseline = 'middle';
  const msg = 'psst…', n = Math.min(msg.length, Math.floor((t - tWName) * 9) + 1);
  for (let i = 0; i < 3; i++) { c.filter = `blur(${2 + i * 3}px)`; c.fillStyle = `rgba(220,232,255,${0.5 - i * 0.12})`; c.fillText(msg.slice(0, n), P.cw / 2 + Math.sin(t * 40 + i) * 4, P.ch / 2 + Math.cos(t * 33 + i) * 3); }
  c.filter = 'none'; c.fillStyle = '#eef3ff'; c.fillText(msg.slice(0, n), P.cw / 2, P.ch / 2); c.restore();
} });
hush.mesh.visible = false; tl.set(hush.mesh, { visible: true }, tWName); tl.set(hush.mesh, { visible: false }, tLookUp + 0.65);
sfx('whisper', tWName, 0.9); sfx('whisper', tWName + 0.6, 0.6);
camSet(tLookUp, { x: -2.15, y: 1.24, z: 0.68, tx: -0.62, ty: 1.12, tz: 0.74, roll: 3, fov: 40 });
camTo(tLookUp, { x: -2.0 }, tClose - tLookUp, 'none');
sfx('stinger', tLookUp + 0.25, 0.6, { soft: 1 }); music(tLookUp, 0.75, { heart: 1.0 });
// 9 DOORS CLOSE → look at your hands
camSet(tClose, { x: -1.05, y: 2.12, z: 3.0, tx: 1.35, ty: 0.85, tz: 2.1, roll: 0, fov: 56 });
camTo(tClose, { x: -0.9, y: 2.05 }, tHands - tClose, 'none');
const tShut = Math.max(w('s08', 'close') - 0.2, tWExit + 0.1);
tl.to(door, { open: 0, duration: 0.6, ease: 'power2.in' }, tShut); tl.set(voidPlane, { visible: false }, tShut + 0.65);
sfx('hiss', tShut, 0.6); sfx('thunk', tShut + 0.6, 0.8); shake(tShut + 0.6, 0.35, 0.3);
sfx('engine', STOP.go4, 0.7, { dur: tCta - STOP.go4 + 0.5 });
tl.to(yp, Object.assign({}, POSES.hold, { lKnX: 1.57, rKnX: 1.57, lShX: -0.5, rShX: -0.5, lElX: -1.35, rElX: -1.35, neckX: 0.7, tremble: 0.25, duration: 0.5 }), tHands - 0.3);
camSet(tHands, { x: -0.62, y: 1.62, z: 0.95, tx: -0.98, ty: 0.68, tz: 0.35, roll: 0, fov: 44 });
camTo(tHands, { y: 1.5, z: 0.85 }, tGlow - tHands, 'none');
music(tClose, 0.5, { heart: 0.6 });
// 10 TWIST — your hands start to glow like theirs; then all of you; the driver finally turns around
tl.set(yp, { hGhost: 1 }, tGlow + 0.05);
tl.fromTo(yp, { hCold: 0, hGlow: 0 }, { hCold: 1, hGlow: 2.6, duration: 1.3, ease: 'power2.in', immediateRender: false }, w('s09', 'glowing') - 0.2);
sfx('shimmer', w('s09', 'glowing') - 0.2, 0.7); sfx('riser', tGlow, 0.5, { dur: tNever - tGlow + 0.2 });
camSet(tNever, { x: 0.3, y: 1.32, z: -0.15, tx: -0.98, ty: 1.02, tz: 0.8, roll: 0, fov: 44 });
camTo(tNever, { x: 0.15, z: 0.05 }, tHome - 0.35 - tNever, 'none');
camSet(tHome - 0.35, { x: -0.92, y: 1.6, z: 1.7, tx: -0.45, ty: 1.2, tz: -5.0, roll: 0, fov: 40 });
camTo(tHome - 0.35, { x: -0.62, y: 1.5, z: -1.4, tx: -0.72, ty: 1.28, tz: -5.0 }, tCta - tHome + 0.35, 'power2.inOut');
tl.set(yp, { ghost: 1 }, tNever);
tl.fromTo(yp, { cold: 0, glow: 1 }, { cold: 1, glow: 1.35, duration: 0.6, immediateRender: false }, tNever);
tl.to(yp, { hGlow: 1.35, tremble: 0, neckX: 0.15, duration: 0.6 }, tNever);
flash(tNever, 0.35, 0.4, '#cfe4ff'); sfx('stinger', tNever, 0.8);
tl.set(DRV.userData.face, { visible: true }, tHome + 0.3);
tl.to(dp, { neckY: PI, duration: 0.8, ease: 'power2.inOut' }, tHome); tl.to(dp, { eyeGlow: 1, duration: 0.2 }, tHome + 0.6); tl.to(dp, { smile: 1, duration: 0.6 }, tHome + 0.9);
sfx('creak', tHome, 0.55, { dur: 0.9 }); sfx('hit', tHome + 0.65, 0.8); flash(tHome + 0.65, 0.2, 0.25, '#ff2030'); music(tHome + 0.3, 0.55, { heart: 0.3 });
tl.set(SIGN, { dest: 'NOT IN SERVICE' }, tNever);
// 11 CTA — the bus pulls away into the dark
tl.set(light, { outside: 0.35, strip: 0.8 }, tCta);
tl.set(SIGN, { stop: 0, red: 0 }, tCta);
camSet(tCta, { x: 0.0, y: 1.8, z: 12.5, tx: 0, ty: 1.55, tz: 0, roll: 0, fov: 40 });
camTo(tCta, { z: 11.9 }, DUR - tCta, 'none');
tl.fromTo(bus.position, { z: 0 }, { z: -42, duration: DUR - tCta, ease: 'power2.in', immediateRender: false }, tCta + 0.3);
sfx('engine', tCta, 0.9, { dur: DUR - tCta });
{
  const tF = w('s10', 'follow');
  const q1 = panelMesh(scene, { w: 2.4, h: 0.24, x: 0, y: 3.05, z: 5.9, ppu: 700, draw: (c, t, P) => text(c, 'WOULD YOU HAVE STAYED?', P.cw / 2, P.ch / 2, { size: 84, weight: 900, color: '#fff', font: 'Inter Display', spacing: 3, glow: 12 }) });
  const q2 = panelMesh(scene, { w: 1.6, h: 0.14, x: 0, y: 2.8, z: 5.9, ppu: 700, draw: (c, t, P) => text(c, 'COMMENT  YES  OR  NO', P.cw / 2, P.ch / 2, { size: 58, weight: 800, color: C.red, spacing: 12, glow: 12 }) });
  const fb = panelMesh(scene, { w: 1.25, h: 0.22, x: 0, y: 0.35, z: 6.6, ppu: 700, key: t => (t > tF + 0.4 ? 'on' : 'off'), draw: (c, t, P) => {
    const on = t > tF + 0.4; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? 'rgba(255,255,255,.06)' : '#ffffff'; c.fill(); if (on) { c.strokeStyle = '#fff'; c.lineWidth = 5; c.stroke(); } c.restore();
    text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR MORE RULES', P.cw / 2, P.ch / 2 + 3, { size: on ? 70 : 56, weight: 900, color: on ? '#fff' : '#08080a', spacing: 3 });
  } });
  [q1, q2, fb].forEach((p, i) => { p.mesh.visible = false; tl.set(p.mesh, { visible: true }, tCta); p.mesh.scale.setScalar(0.0001); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.4, ease: 'back.out(2)', immediateRender: false }, [w('s10', 'would') - 0.05, w('s10', 'comments') - 0.1, tF - 0.1][i]); });
  sfx('pop', w('s10', 'would'), 0.4); sfx('pop', tF, 0.4); sfx('click', tF + 0.4, 0.7);
  music(tCta, 0.5); music(DUR - 0.8, 0.5); music(DUR, 0);
}
tl.set({}, {}, DUR);

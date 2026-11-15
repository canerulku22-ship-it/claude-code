// Episode 3 — "If your shadow ever stops copying you at dinner". Candlelit table; every wall shadow is its own
// flattened, independently animated figure, so YOUR shadow can lag, stop, stare and open white eyes.
import { THREE, tl, C, scene, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, particles, text, floorU } from './engine.js';
import { T, DUR, S, L, w, we, sfx, music, clamp01, lerp, q } from './lib.js';
import { stickFigure, setPose, POSES } from './stick.js';
import { panelMesh, propMat, darkMat, box } from './props.js';

const PI = Math.PI;
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const POSE_KEYS = ['torsoX', 'torsoZ', 'neckX', 'neckY', 'neckZ', 'lShX', 'lShZ', 'lElX', 'rShX', 'rShZ', 'rElX', 'lHipX', 'lKnX', 'rHipX', 'rKnX', 'ry', 'walk', 'tremble'];
function flicker(t, n = 3, amt = 0.75) { for (let i = 0; i < n; i++) tl.fromTo(post, { flicker: amt }, { flicker: 0, duration: 0.06, immediateRender: false }, t + i * 0.09 + (i % 2) * 0.03); sfx('flicker', t, 0.45); }

// ---------------------------------------------------------------- the dining room
const room = new THREE.Group(); scene.add(room);
const WALL_Z = -1.55, DOOR_X0 = 1.3, DOOR_X1 = 1.86, DOOR_H = 2.15;
const wallMat = new THREE.MeshStandardMaterial({ color: 0x60646d, roughness: 0.95 });
const wallPiece = (x0, x1, y0, y1) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), wallMat); m.position.set((x0 + x1) / 2, (y0 + y1) / 2, WALL_Z); room.add(m); return m; };
wallPiece(-4, DOOR_X0, 0, 3.4); wallPiece(DOOR_X1, 4, 0, 3.4); wallPiece(DOOR_X0, DOOR_X1, DOOR_H, 3.4);
// doorway frame + dark kitchen beyond
[[DOOR_X0 - 0.035, DOOR_H / 2, 0.07, DOOR_H + 0.07], [DOOR_X1 + 0.035, DOOR_H / 2, 0.07, DOOR_H + 0.07], [(DOOR_X0 + DOOR_X1) / 2, DOOR_H + 0.035, DOOR_X1 - DOOR_X0 + 0.14, 0.07]].forEach(([x, y, ww, hh]) => room.add(at(box(ww, hh, 0.12), x, y, WALL_Z + 0.02)));
const kitchenDark = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 2.4), new THREE.MeshBasicMaterial({ color: 0x050506 })); kitchenDark.position.set((DOOR_X0 + DOOR_X1) / 2, 1.2, WALL_Z - 0.9); room.add(kitchenDark);
// table, chairs, plates, cups
const TABLE_Y = 0.78;
room.add(at(box(2.2, 0.06, 1.0, 0.025), 0, TABLE_Y, 0));
for (const [x, z] of [[-1.0, -0.42], [1.0, -0.42], [-1.0, 0.42], [1.0, 0.42]]) room.add(at(box(0.06, TABLE_Y, 0.06, 0.02), x, TABLE_Y / 2, z));
function chair(x, z, ry) {
  const g = new THREE.Group(); g.add(at(box(0.44, 0.05, 0.42, 0.02), 0, 0.46, 0), at(box(0.44, 0.55, 0.05, 0.02), 0, 0.74, -0.2));
  for (const [cx, cz] of [[-0.19, -0.18], [0.19, -0.18], [-0.19, 0.18], [0.19, 0.18]]) g.add(at(box(0.04, 0.46, 0.04, 0.012), cx, 0.23, cz));
  g.position.set(x, 0, z); g.rotation.y = ry; room.add(g); return g;
}
const SEATS = { you: { x: -0.45, z: -0.68, ry: 0 }, sib: { x: 0.45, z: -0.68, ry: 0 }, dad: { x: -1.32, z: 0, ry: PI / 2 }, mom: { x: 1.32, z: 0, ry: -PI / 2 } };
const CH = {}; for (const [k, s] of Object.entries(SEATS)) CH[k] = chair(s.x, s.z, s.ry);
const plateMat = new THREE.MeshStandardMaterial({ color: 0xf2f4f8, roughness: 0.4 });
const foodMat = new THREE.MeshStandardMaterial({ color: 0x9aa0aa, roughness: 0.8 });
for (const [k, s] of Object.entries(SEATS)) {
  const px = s.x + Math.sin(s.ry) * 0.42, pz = s.z + Math.cos(s.ry) * 0.42;
  const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.13, 0.02, 32), plateMat); plate.position.set(px, TABLE_Y + 0.04, pz); room.add(plate);
  const food = new THREE.Mesh(new THREE.SphereGeometry(0.07, 20, 12, 0, PI * 2, 0, PI / 2), foodMat); food.position.set(px, TABLE_Y + 0.05, pz); food.scale.set(1.2, 0.6, 1); room.add(food);
  const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.035, 0.11, 20), propMat); cup.position.set(px + 0.2 * Math.cos(s.ry), TABLE_Y + 0.085, pz - 0.2 * Math.sin(s.ry)); room.add(cup);
}
// candles (the light that throws the big shadows) + pendant lamp
const flames = [], candleXs = [-0.18, 0, 0.18];
const flameMat = new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffcf6e').multiplyScalar(3), toneMapped: false });
candleXs.forEach((x, i) => {
  const h = 0.16 + (i === 1 ? 0.06 : 0);
  room.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, h, 16), propMat), x, TABLE_Y + 0.03 + h / 2, 0.05));
  const f = new THREE.Mesh(new THREE.SphereGeometry(0.018, 12, 10), flameMat); f.scale.set(1, 2.1, 1); f.position.set(x, TABLE_Y + 0.03 + h + 0.03, 0.05); room.add(f); flames.push(f);
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(0.35, 0.35), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, color: new THREE.Color('#ffb54a') })); halo.position.copy(f.position); room.add(halo); f.userData.halo = halo;
});
const candleLight = new THREE.PointLight(0xffb866, 0, 7, 1.2); candleLight.position.set(0, TABLE_Y + 0.35, 0.15); scene.add(candleLight);
const lampG = new THREE.Group(); lampG.position.set(0, 2.25, 0); room.add(lampG);
lampG.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.005, 1.2, 6), darkMat), 0, 0.6, 0));
const shade = new THREE.Mesh(new THREE.ConeGeometry(0.26, 0.2, 32, 1, true), new THREE.MeshStandardMaterial({ color: 0xe9ecf2, side: THREE.DoubleSide, roughness: 0.6 })); lampG.add(shade);
const bulbMat = new THREE.MeshBasicMaterial({ color: new THREE.Color('#fff0d0').multiplyScalar(2.4), toneMapped: false });
const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 12), bulbMat); bulb.position.y = -0.08; lampG.add(bulb);
const lampLight = new THREE.PointLight(0xfff0d8, 0, 6, 1.3); lampLight.position.set(0, 2.05, 0.1); scene.add(lampLight);
const light = { lamp: 1, candle: 1, amb: 0.035, env: 1 };
every(t => {
  const fl = 0.9 + 0.1 * Math.sin(t * 23) * Math.sin(t * 7.3 + 1);
  candleLight.intensity = 2.1 * light.candle * fl; lampLight.intensity = 1.1 * light.lamp;
  bulbMat.color.setRGB(2.4 * light.lamp + 0.03, 2.25 * light.lamp + 0.03, 1.9 * light.lamp + 0.03);
  flames.forEach((f, i) => { const s = light.candle * (0.9 + 0.12 * Math.sin(t * 19 + i * 2)); f.scale.set(s, 2.1 * s, s); f.userData.halo.material.opacity = 0.55 * light.candle; });
  lights.ambient.intensity = light.amb; scene.environmentIntensity = 0.5 * light.env; key.intensity = 3 * light.env; lights.rim.intensity = 0.25 * light.env;
});
tl.set(lights.moon, { intensity: 0 }, 0);
floorU.strength.value = 0.3;

// ---------------------------------------------------------------- the family (+ their shadows on the wall)
const shadowMat = new THREE.MeshBasicMaterial({ color: 0x0b0c0f, transparent: true, opacity: 0.86, depthWrite: false });
function person(seat, opts = {}) {
  const f = stickFigure(opts); f.userData.root.scale.setScalar(opts.scale ?? 0.85); room.add(f); f.userData.pool.visible = false;
  setPose(f, 'seat', { x: seat.x, y: 0.52, z: seat.z, ry: seat.ry });
  // wall shadow: same rig, flattened against the wall
  const sh = stickFigure({ hair: opts.hair }); sh.userData.pool.visible = false; sh.scale.set(1, 1, 0.02); sh.position.z = WALL_Z + 0.03; room.add(sh);
  sh.userData.root.scale.setScalar((opts.scale ?? 0.85) * 1.45);
  sh.traverse(o => { if (o.isMesh && !sh.userData.face.children.includes(o)) o.material = shadowMat; });
  sh.userData.face.visible = false;
  return { f, sh, p: f.userData.pose, sp: sh.userData.pose, follow: true };
}
const YOU = person(SEATS.you), SIB = person(SEATS.sib, { scale: 0.72 }), DAD = person(SEATS.dad, { scale: 0.95 }), MOM = person(SEATS.mom, { hair: true, scale: 0.9 });
SIB.p.y = 0.48; DAD.p.y = 0.53;
const FAM = [YOU, SIB, DAD, MOM];
const shadowXY = (x, y) => [Math.sign(x) * Math.min(Math.abs(x) * 2.0, 2.0), 1.2 + (y - 0.52) * 1.6];
// eating: arm cycles as pure functions of time (so the shadow can run the same motion with a delay)
function eatK(t, period, phase) { const u = ((t + phase) / period) % 1; return u < 0.45 ? Math.sin(u / 0.45 * PI) ** 1.2 : 0; }
function applyEat(p, k) { p.rShX = lerp(-0.85, -1.55, k); p.rElX = lerp(-0.8, -2.15, k); p.neckX = lerp(0.12, 0.0, k); }
const EAT = { you: 1, sib: 1, dad: 1, mom: 1 }, twin = { lag: 0.15, stop: 0, watch: 0, eyes: 0, gone: 0 };
const params = { you: [2.3, 0.4], sib: [2.0, 1.1], dad: [2.6, 0.2], mom: [2.4, 1.7] };
// fork in every right hand
const forkMat = new THREE.MeshStandardMaterial({ color: 0xd0d4dc, metalness: 0.6, roughness: 0.3 });
FAM.forEach(m => { const fk = new THREE.Mesh(new THREE.CapsuleGeometry(0.008, 0.12, 4, 8), forkMat); fk.position.set(0, -0.3, 0.05); fk.rotation.x = 1.2; m.f.userData.J.rEl.add(fk); });

// ---------------------------------------------------------------- timeline anchors
const tHook = 0, tLook = w('s02', 'dont'), tLate = S('s03'), tLift = w('s03', 'lift'), tLater = w('s03', 'later');
const tStop = S('s04'), tWatch = w('s04', 'watches'), tChair = S('s05'), tMomUp = w('s06', 'gets'), tOut = w('s06', 'out');
const tHold = S('s07'), tBack = w('s08', 'back'), tSmile = w('s08', 'smiling'), tWall = S('s09'), tKitchen = w('s09', 'kitchen'), tGetOut = w('s09', 'get');
const tCake = S('s10'), tCta = S('s11');
// your eating is aligned so a forkful peaks just after "You lift your fork"
params.you[1] = params.you[0] - ((tLift + 0.35) % params.you[0]) + params.you[0] * 0.225;

every(t => {
  for (const [name, m] of Object.entries({ you: YOU, sib: SIB, dad: DAD, mom: MOM })) {
    const [per, ph] = params[name];
    if (EAT[name] > 0.01 && m.f.visible) { const p0 = Object.assign({}, m.p); applyEat(m.p, eatK(t, per, ph) * EAT[name]); }
  }
  for (const m of FAM) {
    const [sx, sy] = shadowXY(m.p.x, m.p.y);
    if (m.follow) { for (const k of POSE_KEYS) m.sp[k] = m.p[k]; m.sp.x = sx; m.sp.y = sy; m.sp.z = 0; }
  }
  // your shadow: same arm cycle, but late; later it stops and stares
  const sp = YOU.sp, [per, ph] = params.you;
  const lagK = eatK(t - twin.lag, per, ph) * (1 - twin.stop);
  applyEat(sp, lagK * EAT.you);
  sp.neckZ = lerp(sp.neckZ, 0.55, twin.watch); sp.neckY = lerp(0, 0.5, twin.watch); sp.neckX = lerp(sp.neckX, -0.05, twin.watch);
  sp.eyeWhite = twin.eyes; sp.smile = twin.eyes > 0.5 ? Math.min(1, (twin.eyes - 0.5) * 2) : 0;
  YOU.sh.userData.face.visible = twin.eyes > 0.01;
  YOU.sh.visible = twin.gone < 0.5;
});
YOU.follow = true;  // pose copied, then the eating/stare overrides above apply on top

// ================================================================ BEATS
music(0, 0.55);
// 1 HOOK — wide candlelit dinner, shadows loom on the wall; your shadow is a hair late
tl.set(light, { lamp: 1, candle: 1, amb: 0.035 }, 0);
camSet(0, { x: 0.0, y: 1.55, z: 6.6, tx: 0.0, ty: 1.15, tz: -0.6, roll: 0, fov: 40 });
camTo(0.05, { z: 5.4, y: 1.45 }, L('s01', 1).start - 0.05, 'power1.inOut');
tl.fromTo(twin, { lag: 0 }, { lag: 0.3, duration: 1.5, immediateRender: false }, L('s01', 1).start);
camSet(L('s01', 1).start, { x: -0.55, y: 1.6, z: 2.9, tx: -0.7, ty: 1.6, tz: -1.3, roll: -2, fov: 38 });
camTo(L('s01', 1).start, { z: 2.6 }, L('s01', 2).start - L('s01', 1).start, 'none');
sfx('swoosh', L('s01', 1).start - 0.05, 0.25);
camSet(L('s01', 2).start, { x: -0.3, y: 1.5, z: 2.1, tx: -0.55, ty: 1.3, tz: -0.8, roll: 2, fov: 36 });
camTo(L('s01', 2).start, { z: 1.85 }, S('s02') - L('s01', 2).start, 'none');
// 2 DON'T LOOK — you glance at the wall; the shadow's eyes flick open and shut
camSet(S('s02'), { x: 0.15, y: 1.65, z: 3.2, tx: -0.65, ty: 1.55, tz: -1.0, roll: -2, fov: 38 });
camTo(S('s02'), { z: 2.6 }, S('s03') - S('s02'), 'none');
tl.to(YOU.p, { neckY: 0.9, neckX: -0.15, duration: 0.25, ease: 'power2.out' }, tLook);
tl.to(YOU.p, { neckY: 0, neckX: 0.12, duration: 0.35, ease: 'power2.inOut' }, tLook + 0.7);
tl.fromTo(twin, { eyes: 0 }, { eyes: 0.45, duration: 0.08, immediateRender: false }, tLook + 0.12);
tl.to(twin, { eyes: 0, duration: 0.08 }, tLook + 0.75);
sfx('hit', tLook + 0.12, 0.45); flicker(tLook + 0.15, 2, 0.5);
// 3 LATE — split view: you below, your shadow above; lag grows to one second
camSet(tLate, { x: -0.6, y: 1.65, z: 2.6, tx: -0.72, ty: 1.62, tz: -1.3, roll: 0, fov: 38 });
camTo(tLate, { z: 2.3 }, tStop - tLate, 'none');
tl.to(twin, { lag: 1.0, duration: Math.max(0.5, tLater - tLate), ease: 'power1.inOut' }, tLate);
const lagHud = panelMesh(room, { w: 0.55, h: 0.18, x: -0.85, y: 2.72, z: WALL_Z + 0.05, ppu: 700, boost: 1.9, key: t => Math.round(twin.lag * 10), draw: (c, t, P) => {
  c.font = '900 92px "Inter Display"'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineWidth = 10; c.strokeStyle = 'rgba(0,0,0,.8)';
  const s = `+${twin.lag.toFixed(1)}s`; c.strokeText(s, P.cw / 2, P.ch / 2); c.shadowColor = C.red; c.shadowBlur = 16; c.fillStyle = '#FF3B47'; c.fillText(s, P.cw / 2, P.ch / 2);
} });
lagHud.mesh.visible = false; tl.set(lagHud.mesh, { visible: true }, tLate + 0.2); tl.set(lagHud.mesh, { visible: false }, tStop);
sfx('tick', tLift + 0.35, 0.6); sfx('tick', tLift + 1.35, 0.8);
// 4 STOP + WATCH — the shadow stops eating, turns, opens white eyes and smiles
camSet(tStop, { x: -0.6, y: 1.95, z: 2.5, tx: -0.85, ty: 1.95, tz: -1.5, roll: -2, fov: 34 });
camTo(tStop, { z: 1.9, y: 2.0 }, tChair - tStop, 'power1.in');
tl.to(twin, { stop: 1, duration: 0.5 }, tStop);
tl.to(twin, { watch: 1, duration: 1.1, ease: 'power2.inOut' }, tWatch - 0.3);
tl.to(twin, { eyes: 1, duration: 0.25 }, tWatch + 0.3);
sfx('stinger', tWatch + 0.3, 0.55, { soft: 1 }); music(tStop, 0.7, { heart: 0.6 });
// 5 NEVER LEAVE THE TABLE — family keeps eating; red ring around your chair; the eyes slide toward the empty-chair idea
camSet(tChair, { x: 0.0, y: 1.85, z: 5.0, tx: 0.0, ty: 1.0, tz: -0.4, roll: 0, fov: 38 });
camTo(tChair, { z: 4.4 }, S('s06') - tChair, 'none');
const ring = new THREE.Mesh(new THREE.RingGeometry(0.34, 0.37, 48), new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(3), transparent: true, opacity: 0, toneMapped: false, side: THREE.DoubleSide }));
ring.rotation.x = -PI / 2; ring.position.set(SEATS.you.x, 0.01, SEATS.you.z - 0.05); room.add(ring);
tl.to(ring.material, { opacity: 0.9, duration: 0.3 }, w('s05', 'never'));
tl.to(ring.material, { opacity: 0, duration: 0.3 }, S('s06'));
sfx('hit', w('s05', 'never'), 0.4);
tl.to(twin, { eyes: 0.6, duration: 0.3 }, tChair);
// 6 MOM GETS UP FOR DESSERT → walks into the kitchen; the lights die
camSet(S('s06'), { x: 0.65, y: 1.55, z: 3.9, tx: 0.95, ty: 1.05, tz: -0.6, roll: -2, fov: 38 });
camTo(S('s06'), { x: 0.75, z: 3.5 }, S('s07') - S('s06'), 'none');
tl.to(EAT, { mom: 0, duration: 0.2 }, tMomUp - 0.2);
tl.to(MOM.p, Object.assign({}, POSES.stand, { x: SEATS.mom.x + 0.25, y: 0.83 * 0.9, z: 0.15, ry: -PI / 2 + 0.6, duration: 0.6, ease: 'power2.inOut' }), tMomUp);
sfx('cloth', tMomUp, 0.4);
{
  const p = MOM.p, t0 = tMomUp + 0.65, dur = 1.6, cyc = 2;
  tl.to(p, { ry: PI + 0.25, duration: 0.3 }, t0 - 0.05);
  tl.to(p, { x: (DOOR_X0 + DOOR_X1) / 2, z: WALL_Z - 0.55, duration: dur, ease: 'none' }, t0);
  tl.fromTo(p, { walk: 0 }, { walk: cyc, duration: dur, ease: 'none', immediateRender: false }, t0);
  for (let i = 0; i < cyc * 2; i++) sfx('step', t0 + (i + 0.5) * dur / (cyc * 2), 0.3);
  tl.set(MOM.f, { visible: false }, t0 + dur); tl.set(MOM.sh, { visible: false }, t0 + dur - 0.3);
}
tl.to(light, { lamp: 0, candle: 0, amb: 0.0, env: 0.04, duration: 0.25 }, tOut + 0.1);
flicker(tOut, 3, 0.85);
const smoke = (() => { const R = mulberry32(12), P = Array.from({ length: 40 }, (_, i) => [candleXs[i % 3] + (R() - 0.5) * 0.03, R(), (R() - 0.5) * 0.05, 0.15 + R() * 0.2]); room.add(particles({ count: P.length, texture: TEX.soft, size: 0.03, color: '#9aa0aa', boost: 0.6, additive: true, fn: (t, p, a) => P.forEach((d, i) => { const f = t - tOut - 0.15 - d[1] * 0.4; p.set([d[0] + Math.sin(f * 3 + i) * 0.02 * f * 3, TABLE_Y + 0.25 + f * d[3] * 1.5, 0.05 + d[2]], i * 3); a[i] = f > 0 && f < 1.6 ? (1 - f / 1.6) * 0.5 : 0; }) })); })();
sfx('blowout', tOut + 0.05, 0.7); music(tOut + 0.1, 0.0);
// 7 HOLD ON TO YOUR CHAIR — darkness; only the shadow's eyes; the chair rattles
camSet(S('s07'), { x: -0.1, y: 1.7, z: 3.0, tx: -0.45, ty: 1.7, tz: -1.3, roll: 3, fov: 40 });
camTo(S('s07'), { z: 2.7 }, S('s08') - S('s07'), 'none');
tl.to(EAT, { you: 0, sib: 0, dad: 0, duration: 0.2 }, tOut);
tl.to(YOU.p, Object.assign({}, POSES.grip, { tremble: 0.9, duration: 0.3 }), S('s07') - 0.1);
tl.to(twin, { eyes: 1.0, duration: 0.2 }, S('s07'));
tl.to(YOU.sp, {}, 0); // (shadow keeps copying your grip via follow)
tl.fromTo(twin, { watch: 1 }, { watch: 0.2, duration: 1.5, ease: 'power1.inOut', immediateRender: false }, S('s07'));
const eyesX = { dx: 0 };
every(t => { YOU.sh.position.x = eyesX.dx; });
tl.to(eyesX, { dx: 2.2, duration: 2.0, ease: 'power2.in' }, w('s07', 'let'));
tl.set(twin, { gone: 1 }, S('s08') - 0.02);
[0, 0.3, 0.55, 0.85].forEach(d => { tl.fromTo(CH.you.position, { x: SEATS.you.x + 0.04 }, { x: SEATS.you.x, duration: 0.12, immediateRender: false }, w('s07', 'dont') + d); sfx('knock', w('s07', 'dont') + d, 0.35); shake(w('s07', 'dont') + d, 0.25, 0.15); });
sfx('whisper', S('s07') + 0.2, 0.7); sfx('whisper', w('s07', 'let'), 0.6); music(S('s07'), 0.6, { heart: 1.0 });
// 8 LIGHTS BACK — mom is in her seat, smiling (and she casts no shadow)
tl.set(light, { lamp: 1, candle: 1, amb: 0.035, env: 1 }, tBack); flash(tBack, 0.25, 0.25);
tl.set(MOM.f, { visible: true }, tBack - 0.01); tl.set(MOM, { follow: false }, tBack - 0.01);
tl.set(MOM.p, Object.assign({}, POSES.seat, { x: SEATS.mom.x, y: 0.52, z: SEATS.mom.z, ry: -PI / 2, walk: 0, neckY: 0.95, tremble: 0 }), tBack - 0.01);
tl.set(MOM.f.userData.face, { visible: true }, tBack); tl.set(MOM.p, { smile: 0 }, tBack);
tl.set(YOU.p, Object.assign({}, POSES.seat, { x: SEATS.you.x, y: 0.52, z: SEATS.you.z, ry: 0, tremble: 0.3 }), tBack);
tl.set(eyesX, { dx: 0 }, tBack); tl.set(twin, { gone: 0, eyes: 0, watch: 0, stop: 0, lag: 0 }, tBack);
camSet(tBack, { x: 0.45, y: 1.35, z: 1.9, tx: 1.3, ty: 1.2, tz: 0.0, roll: -2, fov: 34 });
camTo(tBack, { x: 0.6, z: 1.55 }, tWall - tBack, 'none');
tl.fromTo(MOM.p, { smile: 0 }, { smile: 1, duration: 0.8, immediateRender: false }, tSmile - 0.2);
sfx('stinger', tSmile, 0.5, { soft: 1 }); music(tBack, 0.5, { heart: 0.5 });
// 9 LOOK AT THE WALL — her shadow stands in the kitchen doorway, pounding to get out
camSet(tWall, { x: 1.0, y: 1.75, z: 3.8, tx: 1.65, ty: 1.65, tz: WALL_Z, roll: 0, fov: 38 });
camTo(tWall, { x: 1.5, z: 3.0, tx: 2.0 }, tCake - tWall, 'power1.inOut');
{
  const s = MOM.sh; tl.set(s, { visible: true }, tWall);
  const sx = DOOR_X1 + 0.42, sy = 1.2 + (0.83 * 0.9 - 0.52) * 1.6;
  tl.set(s.userData.pose, Object.assign({}, POSES.carry, { x: sx, y: sy, z: 0, ry: 0, walk: 0, neckY: 0, tremble: 0 }), tWall);
  tl.to(s.userData.pose, Object.assign({}, POSES.bang, { duration: 0.4 }), tGetOut - 0.15);
  [0, 0.28, 0.56, 0.84, 1.12].forEach(d => { tl.fromTo(s.userData.pose, { lElX: -0.35, rElX: -0.35 }, { lElX: -0.9, rElX: -0.9, duration: 0.1, yoyo: true, repeat: 1, immediateRender: false }, tGetOut + d); sfx('knock', tGetOut + d + 0.08, 0.6); shake(tGetOut + d + 0.08, 0.15, 0.15); });
  // trapped cake silhouette in her shadow's hands
  const cakeSh = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.12, 24), shadowMat); cakeSh.scale.z = 0.02; cakeSh.position.set(sx + 0.03, sy + 0.38, WALL_Z + 0.03); room.add(cakeSh); cakeSh.visible = false;
  tl.set(cakeSh, { visible: true }, tWall); tl.set(cakeSh, { visible: false }, tGetOut - 0.15);
}
// 10 DON'T EAT THE CAKE — the thing in mom's seat slides a cake to you; her eyes go red
const cake = new THREE.Group(); cake.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.12, 32), propMat), 0, 0.06, 0));
cake.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.155, 0.155, 0.02, 32), new THREE.MeshStandardMaterial({ color: 0xc23a4a, roughness: 0.6 })), 0, 0.12, 0));
const cflame = new THREE.Mesh(new THREE.SphereGeometry(0.014, 10, 8), flameMat); cflame.scale.set(1, 2, 1); cflame.position.set(0, 0.22, 0); cake.add(cflame, at(new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.08, 8), propMat), 0, 0.17, 0));
cake.position.set(0.85, TABLE_Y + 0.03, 0.05); cake.visible = false; room.add(cake);
tl.set(cake, { visible: true }, tCake - 0.01);
tl.fromTo(cake.position, { x: 0.85, z: 0.05 }, { x: -0.25, z: -0.2, duration: 1.0, ease: 'power2.inOut', immediateRender: false }, tCake + 0.15);
tl.to(MOM.p, { rShX: -1.4, rElX: -0.3, duration: 0.5 }, tCake);
sfx('swoosh', tCake + 0.15, 0.3);
camSet(tCake, { x: 0.25, y: 1.55, z: 2.0, tx: 0.3, ty: 0.9, tz: -0.1, roll: -3, fov: 36 });
camTo(tCake, { x: 0.65, y: 1.45, z: 1.7, tx: 1.1, ty: 1.15, tz: 0 }, 1.6, 'power2.inOut');
tl.to(MOM.p, { eyeGlow: 1, duration: 0.15 }, tCake + 1.4);
tl.to(light, { lamp: 0.15, candle: 0.4, duration: 0.3 }, tCake + 1.4);
sfx('stinger', tCake + 1.4, 1.0); flash(tCake + 1.4, 0.2, 0.25, '#ff2030'); shake(tCake + 1.4, 0.7, 0.4);
music(tCake + 1.4, 0.55, { heart: 0.4 });
// 11 CTA — the table from afar, every shadow on the wall; one of them has white eyes again
tl.set(light, { lamp: 0.9, candle: 1, amb: 0.035, env: 1 }, tCta);
tl.set(cake, { visible: false }, tCta);
tl.set(twin, { eyes: 1, watch: 1, stop: 1 }, tCta);
camSet(tCta, { x: 0, y: 1.8, z: 6.8, tx: 0, ty: 1.55, tz: -0.6, roll: 0, fov: 40 });
camTo(tCta, { z: 6.0 }, DUR - tCta, 'power1.out');
{
  const tF = w('s11', 'follow');
  const q1 = panelMesh(room, { w: 2.4, h: 0.24, x: 0, y: 3.05, z: 0.2, ppu: 700, draw: (c, t, P) => text(c, 'WOULD YOU HAVE STAYED?', P.cw / 2, P.ch / 2, { size: 84, weight: 900, color: '#fff', font: 'Inter Display', spacing: 3, glow: 12 }) });
  const q2 = panelMesh(room, { w: 1.6, h: 0.14, x: 0, y: 2.8, z: 0.2, ppu: 700, draw: (c, t, P) => text(c, 'COMMENT  YES  OR  NO', P.cw / 2, P.ch / 2, { size: 58, weight: 800, color: C.red, spacing: 12, glow: 12 }) });
  const fb = panelMesh(room, { w: 1.25, h: 0.22, x: 0, y: 0.35, z: 0.9, ppu: 700, key: t => (t > tF + 0.4 ? 'on' : 'off'), draw: (c, t, P) => {
    const on = t > tF + 0.4; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? 'rgba(255,255,255,.06)' : '#ffffff'; c.fill(); if (on) { c.strokeStyle = '#fff'; c.lineWidth = 5; c.stroke(); } c.restore();
    text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR MORE RULES', P.cw / 2, P.ch / 2 + 3, { size: on ? 70 : 56, weight: 900, color: on ? '#fff' : '#08080a', spacing: 3 });
  } });
  [q1, q2, fb].forEach((p, i) => { p.mesh.scale.setScalar(0.0001); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.4, ease: 'back.out(2)' }, [w('s11', 'would') - 0.05, w('s11', 'comments') - 0.1, tF - 0.1][i]); });
  sfx('pop', w('s11', 'would'), 0.4); sfx('pop', tF, 0.4); sfx('click', tF + 0.4, 0.7);
  music(tCta, 0.5); music(DUR - 0.8, 0.5); music(DUR, 0);
}
tl.set(EAT, { you: 1, sib: 1, dad: 1, mom: 0 }, tBack);
// cutlery clinks: one per forkful, while each person is eating
{
  const windows = { you: [[0.3, tOut], [tBack + 0.3, tCta]], sib: [[0.3, tOut], [tBack + 0.3, tCta]], dad: [[0.3, tOut], [tBack + 0.3, tCta]], mom: [[0.3, tMomUp - 0.3]] };
  for (const [name, wins] of Object.entries(windows)) {
    const [per, ph] = params[name];
    for (const [a, b] of wins) for (let k = Math.ceil((a + ph) / per); k * per - ph < b; k++) { const tt = k * per - ph + 0.02; if (tt > a && tt < b) sfx('clink', tt, name === 'you' ? 0.3 : 0.18, { pitch: 1 + (name.length % 3) * 0.08 }); }
  }
}
tl.set({}, {}, DUR);

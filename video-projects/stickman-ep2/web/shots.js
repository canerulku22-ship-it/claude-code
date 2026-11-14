// Episode 2 — "If your room ever has two doors". Five sets, heavy character animation (walk cycles, poses, door mechanics).
import { THREE, tl, C, scene, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, particles, text } from './engine.js';
import { T, DUR, S, L, w, we, sfx, music, clamp01, lerp, q } from './lib.js';
import { stickFigure, setPose, POSES } from './stick.js';
import { bed, nightstand, windowFrame, door, clock, eyesInDark, panelMesh, bathroomSet, kitchenSet, bubble, propMat, box } from './props.js';

const PI = Math.PI;
const greyMat = new THREE.MeshStandardMaterial({ color: 0xa9adb6, emissive: 0xa9adb6, emissiveIntensity: 0.02, roughness: 0.7 });
// ---------------------------------------------------------------- helpers
const SETS = [];
function set(ranges) { const g = new THREE.Group(); scene.add(g); SETS.push([g, ranges]); return g; }
every(t => { for (const [g, r] of SETS) g.visible = r.some(([a, b]) => t >= a && t < b); });
function look(t, L0, dur = 0.01) {
  tl.to(lights.ambient, { intensity: L0.amb, duration: dur }, t); tl.to(lights.moon, { intensity: L0.moon ?? 0, duration: dur }, t);
  tl.to(key, { intensity: L0.key, duration: dur }, t); tl.to(lights.rim, { intensity: L0.rim ?? 0.4, duration: dur }, t);
  tl.to(lights.hallLight, { intensity: L0.hall ?? 0, duration: dur }, t); tl.to(lights.phoneLight, { intensity: L0.phone ?? 0, duration: dur }, t);
}
const NIGHT = { amb: 0.1, moon: 0.45, key: 5, rim: 0.5 }, MORNING = { amb: 0.55, moon: 0, key: 22, rim: 0.9 };
function flicker(t, n = 3, amt = 0.75) { for (let i = 0; i < n; i++) tl.fromTo(post, { flicker: amt }, { flicker: 0, duration: 0.06, immediateRender: false }, t + i * 0.09 + (i % 2) * 0.03); sfx('flicker', t, 0.45); }
function kid() { const f = stickFigure(); f.userData.root.scale.setScalar(0.85); return f; }
const STAND_Y = 0.705;
// walk: tween position + gait phase; footsteps on every half-cycle
function walk(fig, t0, dur, to, { cycles = null, stride = 1.0, ease = 'none', steps = true, gain = 0.35 } = {}) {
  const p = fig.userData.pose;
  tl.to(p, Object.assign({ duration: dur, ease }, to), t0);
  const n = cycles ?? Math.max(1, Math.round(dur / 1.1));
  tl.fromTo(p, { walk: 0 }, { walk: n, duration: dur, ease: 'none', immediateRender: false }, t0);
  if (steps) for (let i = 0; i < n * 2; i++) sfx('step', t0 + (i + 0.5) * dur / (n * 2), gain);
}
function knockJolt(d, t, amp = 0.025) { tl.fromTo(d.userData.leafG.position, { z: amp }, { z: 0, duration: 0.14, ease: 'power2.out', immediateRender: false }, t); sfx('knock', t, 0.85); shake(t, 0.18, 0.18); }
function dustBurst(parent, t0, { x, y = 0.05, z, n = 60, spread = 0.9, seed = 3 }) {
  const R = mulberry32(seed), P = Array.from({ length: n }, () => [(R() - 0.5) * spread, R() * 0.3, (R() - 0.5) * 0.3, (R() - 0.5) * 0.8, 0.3 + R() * 0.9, (R() - 0.5) * 0.5]);
  parent.add(particles({ count: n, texture: TEX.soft, size: 0.05, color: '#d8dce6', boost: 1.2, additive: true, fn: (t, p, a) => P.forEach((d, i) => { const f = t - t0; p.set([x + d[0] + d[3] * f, y + d[1] + d[4] * f * 0.6, z + d[2] + d[5] * f], i * 3); a[i] = f > 0 && f < 1.6 ? (1 - f / 1.6) * 0.6 : 0; }) }));
}

// ================================================================ SET 1: BEDROOM (night: s01–s06 line 2; morning: s08)
const tHall = L('s06', 2).start;               // hallway starts on "Don't run."
const bedroom = set([[0, L('s05', 1).start], [S('s06'), tHall], [S('s08'), S('s09')]]);
const BED = { x: -0.35 }, B = bed(); B.g.position.set(BED.x, 0, 0); bedroom.add(B.g);
const NS = nightstand(); NS.position.set(-1.58, 0, 0.05); bedroom.add(NS);
const WIN = windowFrame(0.9); WIN.position.set(-0.6, 1.85, -1.2); bedroom.add(WIN);
const CLK = clock(bedroom, { x: -1.55, y: 2.2, z: -1.2, size: 0.42 }); CLK.state.min = 0;
const TALL = door({ W: 0.9, H: 2.5, mat: greyMat, frameMat: greyMat, inside: 'dark' }); TALL.position.set(0.55, 0, -1.3); TALL.rotation.z = 0.012; bedroom.add(TALL);
const REAL = door(); REAL.position.set(1.62, 0, -0.42); REAL.rotation.y = -0.5; bedroom.add(REAL);
const K = kid(); bedroom.add(K);
setPose(K, 'lie', { x: BED.x + 0.08, y: 0.6, z: 0, ry: PI / 2, torsoX: -1.47, neckX: -0.1 });
K.userData.pool.visible = false;
// the thing behind the tall door: stretched, grey, faceless but for black eyes
const IT = stickFigure({ color: 0xd2d6de, emissive: 0.0 }); IT.userData.root.scale.set(0.85, 1.22, 0.85); bedroom.add(IT);
setPose(IT, 'creep', { x: 0.9, y: 0.705 * 1.22, z: -1.46, ry: 0, neckZ: 0.55, torsoZ: -0.12 }); IT.userData.face.visible = true; IT.userData.smile.visible = false;
IT.userData.eyes.forEach(e => e.scale.setScalar(1.6)); IT.visible = false; IT.userData.pool.visible = false;
look(0, NIGHT);

// ---------------------------------------------------------------- 1  HOOK: a second door grows out of the floor
{
  const tW = w('s01', 'wake'), tTwo = w('s01', 'two'), tN = w('s01', 'never');
  music(0, 0.55);
  camSet(0, { x: 0.15, y: 1.6, z: 8.2, tx: 0.1, ty: 1.05, tz: -0.4, roll: 0, fov: 40 });
  camTo(0.05, { z: 6.6, y: 1.5 }, tN - 0.05, 'power1.inOut');
  tl.to(K.userData.pose, Object.assign({}, POSES.sit, { x: BED.x - 0.2, y: 0.6, ry: PI / 2 + 0.55, neckX: 0.05, duration: 0.6, ease: 'power3.out' }), tW - 0.05);
  sfx('cloth', tW, 0.5);
  TALL.scale.y = 0.0001;
  tl.fromTo(TALL.scale, { y: 0.0001 }, { y: 1, duration: 1.1, ease: 'power2.out', immediateRender: false }, tTwo - 0.1);
  dustBurst(bedroom, tTwo, { x: 0.55, z: -1.15, seed: 4 });
  sfx('rumble', tTwo - 0.1, 0.8, { dur: 1.3 }); shake(tTwo, 0.45, 1.1); flicker(tTwo + 0.9, 2, 0.6);
  tl.to(K.userData.pose, { tremble: 0.35, duration: 0.4 }, tTwo + 0.3);
  // "never open the one that wasn't there before": push toward the tall door, red NEVER OPEN tag
  camTo(tN, { x: 0.5, y: 1.45, z: 3.6, tx: 0.55, ty: 1.25, tz: -1.3 }, S('s02') - tN, 'power2.inOut');
  const tag = panelMesh(bedroom, { w: 0.9, h: 0.16, x: 0.55, y: 2.72, z: -1.2, ppu: 800, boost: 1.9, draw: (c, t, P) => {
    c.font = '900 64px "Inter Display"'; c.letterSpacing = '10px'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.lineWidth = 12; c.strokeStyle = 'rgba(0,0,0,.85)'; c.strokeText('NEVER OPEN', P.cw / 2, P.ch / 2); c.shadowColor = C.red; c.shadowBlur = 18; c.fillStyle = '#FF3B47'; c.fillText('NEVER OPEN', P.cw / 2, P.ch / 2);
  } });
  tag.mesh.scale.setScalar(0.0001);
  tl.fromTo(tag.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.35, ease: 'back.out(2.5)' }, w('s01', 'open') - 0.05);
  tl.to(tag.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001, duration: 0.15 }, S('s03'));
  sfx('hit', w('s01', 'open'), 0.5);
}
// ---------------------------------------------------------------- 2  IT'S ALWAYS A LITTLE TOO TALL (measure lines)
{
  const t0 = S('s02'), tT = w('s02', 'too');
  camSet(t0 - 0.02, { x: 1.05, y: 1.45, z: 5.6, tx: 1.05, ty: 1.2, tz: -0.8, roll: 0, fov: 38 });
  camTo(t0, { z: 5.0 }, S('s03') - t0, 'none');
  const meas = (x, z, ry, h, col, t, label) => {
    const p = panelMesh(bedroom, { w: 0.35, h: h + 0.2, x, y: (h + 0.2) / 2, z, ry, ppu: 500, boost: col === C.red ? 1.9 : 1.0, key: tt => (tt < t + 0.8 ? q(tt) : 'd'), draw: (c, tt, P) => {
      const k = clamp01((tt - t) / 0.6), y1 = P.ch - 40, y0 = y1 - (P.ch - 120) * k;
      c.strokeStyle = col; c.lineWidth = 7; c.shadowColor = col; c.shadowBlur = 12; c.beginPath(); c.moveTo(P.cw / 2, y1); c.lineTo(P.cw / 2, y0); c.moveTo(P.cw / 2 - 30, y1); c.lineTo(P.cw / 2 + 30, y1); if (k > 0.98) { c.moveTo(P.cw / 2 - 30, y0); c.lineTo(P.cw / 2 + 30, y0); } c.stroke();
      if (k > 0.98) text(c, label, P.cw / 2, y0 - 34, { size: 44, weight: 900, color: col, font: 'Inter Display' });
    } });
    tl.set(p.mesh, { visible: false }, S('s03'));
    return p;
  };
  meas(2.12, -0.15, -0.5, 2.0, C.white, t0 + 0.1, 'NORMAL');
  meas(0.0, -1.2, 0, 2.5, C.red, tT - 0.15, 'TOO TALL');
  sfx('swoosh', t0 + 0.1, 0.3); sfx('stinger', tT + 0.1, 0.45, { soft: 1 });
}
// ---------------------------------------------------------------- 3  3 AM: KNOCKING
{
  const t0 = S('s03'), tK = w('s03', 'knocking'), t3 = L('s03', 1).start, tM = L('s03', 2).start;
  camSet(t0 - 0.02, { x: -1.45, y: 2.15, z: -0.35, tx: -1.55, ty: 2.2, tz: -1.2, roll: -2, fov: 32 });
  tl.fromTo(CLK.state, { min: 59 - 60 }, { min: 0, duration: 0.6, ease: 'power2.out', immediateRender: false }, t0 + 0.05);
  sfx('clock', w('s03', 'three') + 0.05, 0.9);
  camSet(tK - 0.25, { x: -0.15, y: 1.55, z: 4.4, tx: 0.3, ty: 1.15, tz: -0.9, roll: -3, fov: 36 });
  camTo(tK - 0.2, { z: 3.9 }, S('s04') - tK, 'none');
  const ks = [tK + 0.15, tK + 0.45, tK + 0.75];
  const ks1 = [t3 + 0.95, t3 + 1.22, t3 + 1.49], ks2 = [tM + 0.95, tM + 1.22, tM + 1.49];
  [...ks1, ...ks2].forEach(t => knockJolt(TALL, t, 0.035));
  tl.to(K.userData.pose, { tremble: 0.8, duration: 0.3 }, ks1[0]);
  music(t3, 0.7, { heart: 0.5 });
  // brief reaction shot from behind the kid during the second set
  camSet(tM - 0.03, { x: -1.7, y: 1.85, z: 2.4, tx: 0.45, ty: 1.15, tz: -1.2, roll: 2, fov: 36 });
  camTo(tM, { x: -1.5, z: 2.1 }, S('s04') - tM, 'none');
  sfx('whoosh', tM - 0.1, 0.2);
}
// ---------------------------------------------------------------- 4  IT CALLS YOUR NAME IN YOUR MOM'S VOICE
{
  const t0 = S('s04'), tC = w('s04', 'calls'), tM = w('s04', 'moms');
  camSet(t0 - 0.02, { x: 0.15, y: 1.55, z: 3.9, tx: 0.35, ty: 1.45, tz: -1.2, roll: -4, fov: 34 });
  camTo(t0, { z: 3.4, x: 0.2 }, S('s05') - t0, 'none');
  bubble(bedroom, { msg: 'SWEETIE? IT\'S MOM.', t0: tC + 0.1, t1: S('s06') + 0.8, x: 0.05, y: 1.95, z: -1.0, w: 1.0, h: 0.32, color: '#ffffff', tail: 'right' });
  bubble(bedroom, { msg: 'OPEN THE DOOR.', t0: tM + 0.25, t1: S('s06') + 0.8, x: 0.25, y: 1.58, z: -0.95, w: 0.85, h: 0.3, color: '#FF3B47', tail: 'right' });
  sfx('whisper', tC + 0.05, 0.7); sfx('whisper', tM + 0.2, 0.6);
  flicker(tM + 0.6, 2, 0.5);
  music(t0, 0.75, { heart: 0.7 });
}
// ---------------------------------------------------------------- 5  DON'T ANSWER / YOUR MOM NEVER KNOCKS (cut to mom asleep)
const momRoom = set([[L('s05', 1).start, S('s06')]]);
{
  const t0 = S('s05'), tN = L('s05', 1).start;
  camSet(t0 - 0.02, { x: 0.25, y: 1.45, z: 2.9, tx: -0.45, ty: 0.95, tz: 0, roll: -2, fov: 34 });
  camTo(t0, { z: 2.6 }, tN - t0, 'none');
  tl.to(K.userData.pose, Object.assign({}, POSES.mouth, { x: BED.x - 0.2, y: 0.6, ry: PI / 2 + 0.55, tremble: 0.5, duration: 0.35, ease: 'power3.out' }), t0 - 0.05);
  sfx('cloth', t0, 0.4);
  // mom asleep down the hall (separate little set)
  const mb = bed(); mb.g.position.set(0, 0, 0); momRoom.add(mb.g);
  const mom = stickFigure({ hair: true }); mom.userData.root.scale.setScalar(0.85); momRoom.add(mom); mom.userData.pool.visible = false;
  setPose(mom, 'lie', { x: 0.08, y: 0.6, z: 0, ry: PI / 2, torsoX: -1.47, neckX: -0.1 });
  const mw = windowFrame(0.8); mw.position.set(-0.2, 1.8, -1.2); momRoom.add(mw);
  const zz = panelMesh(momRoom, { w: 0.5, h: 0.4, x: -0.55, y: 1.15, z: 0.1, ppu: 600, key: t => q(t, 12), draw: (c, t, P) => {
    for (let i = 0; i < 3; i++) { const ph = ((t * 0.8 + i / 3) % 1); c.globalAlpha = Math.sin(ph * PI); text(c, 'Z', 80 + i * 90 + ph * 40, P.ch - 60 - ph * 160, { size: 60 + i * 18, weight: 900, color: '#cfd6e6', font: 'Inter Display' }); }
  } });
  camSet(tN - 0.02, { x: 0.35, y: 1.55, z: 3.4, tx: -0.35, ty: 0.65, tz: 0, roll: -2, fov: 34 });
  camTo(tN, { z: 3.0 }, S('s06') - tN, 'none');
  sfx('swoosh', tN - 0.05, 0.25);
  tl.to(lights.ambient, { intensity: 0.08, duration: 0.01 }, tN);
}
// ---------------------------------------------------------------- 6  THE HANDLE TURNS → GET UP → WALK SLOWLY (it peeks out)
{
  const t0 = S('s06'), tH = w('s06', 'handle'), tG = w('s06', 'get'), tWk = L('s06', 1).start;
  look(t0, NIGHT);
  camSet(t0 - 0.02, { x: 0.9, y: 1.12, z: -0.25, tx: TALL.position.x + 0.36, ty: 1.0, tz: -1.28, roll: -3, fov: 30 });
  camTo(t0, { z: -0.45 }, tG - t0, 'none');
  const lv = TALL.userData.lever;
  tl.to(lv.rotation, { z: 0.75, duration: 0.9, ease: 'power2.inOut' }, tH);
  sfx('creak', tH, 0.5, { dur: 0.9 });
  tl.set(IT, { visible: true }, tG - 0.3);
  tl.to(TALL.userData.hinge.rotation, { y: 0.55, duration: 1.4, ease: 'power2.inOut' }, w('s06', 'turn') + 0.2);
  sfx('creak', w('s06', 'turn') + 0.2, 0.75, { dur: 1.5 });
  // get out of bed
  tl.to(K.userData.pose, Object.assign({}, POSES.sit, { x: BED.x + 0.05, y: 0.6, z: 0.35, ry: 0.15, tremble: 0.15, duration: 0.5, ease: 'power2.inOut' }), tG - 0.05);
  tl.to(K.userData.pose, Object.assign({}, POSES.stand, { x: BED.x + 0.05, y: STAND_Y, z: 0.78, ry: 0.15, tremble: 0, duration: 0.55, ease: 'power2.inOut' }), tG + 0.5);
  sfx('cloth', tG, 0.45); sfx('step', tG + 0.9, 0.35);
  camSet(tG - 0.02, { x: -0.4, y: 1.6, z: 4.4, tx: 0.55, ty: 1.0, tz: -0.6, roll: -2, fov: 38 });
  camTo(tG, { x: -0.2, z: 4.1 }, tWk - tG, 'none');
  // walk to the real door, slowly; it leans out to watch
  const door = REAL.position, stop = { x: door.x - 0.3, z: door.z + 0.5 };
  const dx = stop.x - (BED.x + 0.05), dz = stop.z - 0.78;
  tl.to(K.userData.pose, { ry: Math.atan2(dx, dz), duration: 0.45, ease: 'power2.inOut' }, tWk - 0.15);
  walk(K, tWk + 0.3, 3.0, { x: stop.x, z: stop.z }, { cycles: 3, gain: 0.3 });
  tl.to(IT.userData.pose, { x: 0.97, torsoZ: -0.3, neckZ: 0.75, ry: 0.35, duration: 2.2, ease: 'power1.inOut' }, tWk);
  tl.to(IT.userData.pose, { ry: 0.85, duration: 2.0, ease: 'power1.inOut' }, tWk + 1.6);
  camTo(tWk, { x: 0.6, y: 1.45, z: 3.6, tx: 0.95, ty: 1.0, tz: -0.4 }, tHall - tWk, 'power1.inOut');
  // open the real door as the kid arrives
  tl.to(REAL.userData.hinge.rotation, { y: 1.2, duration: 0.8, ease: 'power2.inOut' }, tWk + 3.0);
  tl.to([REAL.userData.hallMat], { opacity: 0.12, duration: 0.6 }, tWk + 3.1);
  sfx('creak', tWk + 3.0, 0.35, { dur: 0.8 });
  music(tWk, 0.8, { heart: 0.9 });
}
// ================================================================ SET 2: HALLWAY (walk to bathroom; it steps out behind you) + flashback
const tBath = L('s07', 1).start, tFb = L('s09', 1).start;
const hall = set([[tHall, tBath], [tFb, S('s10')]]);
const HD = [];
{
  const sides = [[1.0, 1.0, -PI / 2], [-1.0, -0.4, PI / 2], [1.0, -2.0, -PI / 2], [-1.0, -3.0, PI / 2]];
  sides.forEach(([x, z, ry]) => { const d = door(); d.position.set(x, 0, z); d.rotation.y = ry; hall.add(d); HD.push(d); });
  const BD = door({ inside: 'dark' }); BD.position.set(0, 0, -4.4); hall.add(BD); HD.push(BD);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.09, 20, 14), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffe7c4').multiplyScalar(2.2), toneMapped: false })); lamp.position.set(0, 2.55, -1.6); hall.add(lamp);
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(3, 3), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, color: new THREE.Color('#ffe2b0') }));
  pool.rotation.x = -PI / 2; pool.position.set(0, 0.006, -1.6); hall.add(pool);
  const k2 = kid(); hall.add(k2); setPose(k2, 'stand', { x: 0, y: STAND_Y, z: 0.2, ry: PI });
  const it2 = stickFigure({ color: 0xd2d6de, emissive: 0 }); it2.userData.root.scale.set(0.85, 1.22, 0.85); hall.add(it2);
  setPose(it2, 'creep', { x: 1.25, y: 0.705 * 1.22, z: 1.0, ry: -PI / 2, neckZ: 0.4 }); it2.userData.face.visible = true; it2.userData.smile.visible = false; it2.userData.eyes.forEach(e => e.scale.setScalar(1.6));
  look(tHall, { amb: 0.07, key: 2, rim: 0.3, hall: 0 });
  tl.set(lights.hallLight.position, { x: 0, y: 2.4, z: -1.6 }, tHall);
  tl.to(lights.hallLight, { intensity: 1.3, duration: 0.01 }, tHall);
  camSet(tHall, { x: -0.15, y: 1.5, z: 3.9, tx: 0.05, ty: 1.05, tz: -3.5, roll: -2, fov: 36 });
  camTo(tHall, { z: 3.2 }, tBath - tHall, 'none');
  walk(k2, tHall + 0.05, tBath - tHall - 0.5, { z: -3.75 }, { cycles: 4, gain: 0.3 });
  // it steps out of your bedroom door into the hallway behind you
  tl.to(HD[0].userData.hinge.rotation, { y: -1.1, duration: 0.7, ease: 'power2.inOut' }, w('s06', 'hear') - 0.3);
  walk(it2, w('s06', 'hear'), 1.6, { x: 0.6, z: 0.85 }, { cycles: 2, steps: false });
  tl.to(it2.userData.pose, { ry: PI, duration: 0.8, ease: 'power2.inOut' }, w('s06', 'hear') + 1.2);
  sfx('creak', w('s06', 'hear') - 0.3, 0.4, { dur: 0.7 });
  // bathroom door opens, kid slips in, door closes
  const tIn = tBath - 1.0;
  tl.to(HD[4].userData.hinge.rotation, { y: 1.25, duration: 0.45, ease: 'power2.out' }, tIn - 0.4);
  walk(k2, tIn, 0.5, { z: -4.7 }, { cycles: 1, gain: 0.25 });
  tl.to(HD[4].userData.hinge.rotation, { y: 0, duration: 0.3, ease: 'power3.in' }, tIn + 0.45);
  sfx('slam', tIn + 0.75, 0.55); shake(tIn + 0.76, 0.35, 0.3);
  // ---- flashback (s09 line 2): it knocks on mom's door, in your voice
  const tf = tFb;
  look(tf, { amb: 0.05, key: 1.5, rim: 0.25 });
  tl.to(lights.hallLight, { intensity: 0.9, duration: 0.01 }, tf);
  tl.set(k2, { visible: false }, tf); tl.set(it2.userData.pose, Object.assign({}, POSES.knock, { x: -0.5, y: 0.705 * 1.22, z: -0.4, ry: -PI / 2, neckZ: 0.3, walk: 0 }), tf);
  tl.set(HD[0].userData.hinge.rotation, { y: 0 }, tf);
  camSet(tf, { x: 1.1, y: 1.65, z: 2.6, tx: -0.75, ty: 1.3, tz: -0.4, roll: 3, fov: 36 });
  camTo(tf, { x: 0.9, z: 2.2 }, S('s10') - tf, 'none');
  [0.15, 0.45, 0.75].forEach(d => { tl.fromTo(it2.userData.pose, { rElX: -1.1 }, { rElX: -1.6, duration: 0.12, yoyo: true, repeat: 1, immediateRender: false }, tf + d); knockJolt(HD[1], tf + d + 0.1, 0.02); });
  bubble(hall, { msg: 'MOM? IT\'S ME. OPEN UP.', t0: w('s09', 'calling') + 0.1, x: -0.25, y: 1.95, z: -0.2, ry: -0.6, w: 0.95, h: 0.3, color: '#FF3B47', tail: 'left' });
  flicker(tf + 0.05, 2, 0.6); sfx('whisper', w('s09', 'calling'), 0.6);
}
// ================================================================ SET 3: BATHROOM (lock, huddle, feet in the light)
const bath = set([[tBath, S('s08')]]);
{
  const t0 = tBath;
  bath.add(bathroomSet());
  const BD = door({ inside: 'dark' }); BD.position.set(0, 0, -1.3); bath.add(BD);
  const k3 = kid(); bath.add(k3); setPose(k3, 'stand', { x: 0.05, y: STAND_Y, z: -0.95, ry: PI });
  look(t0, { amb: 0.05, key: 2.5, rim: 0.25 });
  tl.to(lights.hallLight, { intensity: 0, duration: 0.01 }, t0);
  tl.to(BD.userData.stripMat, { opacity: 1, duration: 0.01 }, t0); tl.to(BD.userData.stripGlow.material, { opacity: 0.55, duration: 0.01 }, t0);
  camSet(t0, { x: 0.35, y: 1.25, z: 2.2, tx: 0.0, ty: 0.75, tz: -1.1, roll: -2, fov: 36 });
  camTo(t0, { z: 1.8 }, S('s08') - t0, 'none');
  // lock: the lever snaps + click
  tl.to(k3.userData.pose, Object.assign({}, POSES.knock, { ry: PI, duration: 0.3 }), t0 + 0.05);
  tl.to(BD.userData.lever.rotation, { z: 0.5, duration: 0.15 }, t0 + 0.35); sfx('click', t0 + 0.4, 0.9);
  // turn, slide down the door, hug knees
  tl.to(k3.userData.pose, Object.assign({}, POSES.stand, { ry: 0, x: -0.3, duration: 0.45, ease: 'power2.inOut' }), t0 + 0.7);
  tl.to(k3.userData.pose, Object.assign({}, POSES.huddle, { x: -0.34, y: 0.2, z: -0.98, ry: 0, tremble: 0.5, duration: 0.8, ease: 'power2.inOut' }), t0 + 1.2);
  sfx('cloth', t0 + 1.25, 0.4);
  // in the silence: two feet step into the light under the door, then knocks
  const tF = we('s07', 'up') + 0.1;
  BD.userData.feet.forEach((f, i) => { tl.set(f, { visible: true }, tF + i * 0.25); tl.fromTo(f.position, { x: (i ? 1 : -1) * 0.6 }, { x: (i ? 1 : -1) * 0.12, duration: 0.25, ease: 'power2.out', immediateRender: false }, tF + i * 0.25); sfx('step', tF + i * 0.25, 0.4); });
  [0.65, 0.9, 1.15].forEach(d => knockJolt(BD, tF + d, 0.02));
  tl.to(k3.userData.pose, { tremble: 1.0, duration: 0.2 }, tF + 0.6);
  camTo(tF, { x: 0.3, y: 0.5, z: 1.1, tx: 0.08, ty: 0.12, tz: -1.25 }, 1.2, 'power2.inOut');
  music(t0, 0.85, { heart: 1.0 });
}
// ================================================================ BEDROOM MORNING (s08): the extra door dissolves
{
  const t0 = S('s08'), tG = w('s08', 'gone');
  look(t0, MORNING);
  tl.set(WIN.userData.moon, { visible: false }, t0); tl.set(WIN.userData.sun, { visible: true }, t0);
  tl.set(CLK.state, { min: 7 * 60 - 3 * 60 + 15 }, t0);
  tl.set(IT, { visible: false }, t0); tl.set(TALL.userData.hinge.rotation, { y: 0 }, t0); tl.set(TALL.userData.lever.rotation, { z: 0 }, t0);
  tl.set(REAL.userData.hinge.rotation, { y: 0 }, t0); tl.set(REAL.userData.hallMat, { opacity: 0 }, t0);
  tl.set(K.userData.pose, Object.assign({}, POSES.stand, { x: 0.4, y: STAND_Y, z: 0.55, ry: PI + 0.15, tremble: 0, walk: 0 }), t0);
  camSet(t0, { x: 0.3, y: 1.55, z: 6.0, tx: 0.3, ty: 1.15, tz: -0.6, roll: 0, fov: 38 });
  camTo(t0, { z: 5.2 }, S('s09') - t0, 'none');
  tl.to(TALL.scale, { y: 0.0001, duration: 0.9, ease: 'power2.in' }, tG - 0.2);
  dustBurst(bedroom, tG, { x: 0.55, y: 0.3, z: -1.15, seed: 9, n: 80, spread: 1.0 });
  sfx('rumble', tG - 0.2, 0.5, { dur: 1.0 }); sfx('birds', t0 + 0.1, 0.35);
  music(t0, 0.35);
}
// ================================================================ SET 4: KITCHEN (mom asks) + her turn
const kitchen = set([[S('s09'), tFb], [S('s10'), S('s11')]]);
{
  const t0 = S('s09');
  kitchen.add(kitchenSet());
  const kw = windowFrame(0.75); kw.position.set(-0.55, 1.85, -1.3); kitchen.add(kw); kw.userData.moon.visible = false; kw.userData.sun.visible = true;
  const mom = stickFigure({ hair: true }); mom.userData.root.scale.setScalar(0.92); kitchen.add(mom);
  setPose(mom, 'stand', { x: -0.45, y: 0.83 * 0.92, z: -0.25, ry: 0.7 });
  const k4 = kid(); kitchen.add(k4); setPose(k4, 'stand', { x: 0.55, y: STAND_Y, z: 0.25, ry: -1.9 });
  look(t0, MORNING);
  camSet(t0, { x: 0.1, y: 1.45, z: 4.5, tx: 0.0, ty: 1.25, tz: -0.4, roll: 0, fov: 36 });
  camTo(t0, { z: 4.0 }, tFb - t0, 'none');
  bubble(kitchen, { msg: 'WHY DID YOU KNOCK ON MY DOOR LAST NIGHT?', t0: w('s09', 'ask') - 0.1, x: -0.1, y: 1.85, z: -0.1, w: 1.45, h: 0.34, color: '#ffffff', tail: 'left', cps: 30 });
  tl.to(mom.userData.pose, { neckX: 0.15, lShX: -0.4, lElX: -1.6, duration: 0.6 }, w('s09', 'ask'));
  sfx('pop', w('s09', 'ask'), 0.3);
  // s10: back in the kitchen — mom turns, the double's face appears on her, eyes ignite
  const tB = S('s10'), tO = w('s10', 'open');
  look(tB, MORNING);
  tl.set(mom.userData.face, { visible: true }, tB);
  tl.set(mom.userData.pose, { smile: 0, eyeGlow: 0 }, tB);
  camSet(tB, { x: -0.1, y: 1.45, z: 1.9, tx: -0.42, ty: 1.4, tz: -0.25, roll: -2, fov: 32 });
  camTo(tB, { x: -0.25, z: 1.35, ty: 1.42 }, S('s11') - tB, 'power1.inOut');
  tl.to(mom.userData.pose, { ry: 0.1, neckZ: 0.55, lShX: 0, lElX: 0, duration: 1.4, ease: 'power2.inOut' }, tB + 0.1);
  tl.fromTo(mom.userData.pose, { smile: 0 }, { smile: 1, duration: 0.8, immediateRender: false }, tO - 0.3);
  tl.to(mom.userData.pose, { eyeGlow: 1, duration: 0.15 }, tO + 0.35);
  look(tO + 0.3, { amb: 0.02, key: 1.2, rim: 0.1 }, 0.25);
  sfx('stinger', tO + 0.35, 1.0); flash(tO + 0.35, 0.22, 0.25, '#ff2030'); shake(tO + 0.35, 0.8, 0.45);
  music(tB, 0.3); music(tO + 0.35, 0.6, { heart: 0.4 });
}
// ================================================================ SET 5: END CARD — the two doors, comment prompt
const cta = set([[S('s11'), DUR + 1]]);
{
  const t0 = S('s11'), tF = w('s11', 'follow');
  const d1 = door(); d1.position.set(-0.7, 0, 0); cta.add(d1);
  const d2 = door({ W: 0.9, H: 2.5, mat: greyMat, frameMat: greyMat, inside: 'dark' }); d2.position.set(0.7, 0, 0); d2.rotation.z = 0.012; cta.add(d2);
  const eyes = eyesInDark(); eyes.position.set(0.95, 1.75, -0.12); eyes.scale.set(0.8, 0.0001, 0.8); cta.add(eyes);
  look(t0, { amb: 0.08, key: 12, rim: 0.35 });
  camSet(t0, { x: 0, y: 1.5, z: 6.4, tx: 0, ty: 1.45, tz: 0, roll: 0, fov: 36 });
  camTo(t0, { z: 5.6 }, DUR - t0, 'power1.out');
  const q1 = panelMesh(cta, { w: 2.2, h: 0.24, x: 0, y: 3.0, z: 0.2, ppu: 700, draw: (c, t, P) => text(c, 'WOULD YOU HAVE ANSWERED?', P.cw / 2, P.ch / 2, { size: 80, weight: 900, color: '#fff', font: 'Inter Display', spacing: 3, glow: 12 }) });
  const q2 = panelMesh(cta, { w: 1.6, h: 0.14, x: 0, y: 2.75, z: 0.2, ppu: 700, draw: (c, t, P) => text(c, 'COMMENT  YES  OR  NO', P.cw / 2, P.ch / 2, { size: 58, weight: 800, color: C.red, spacing: 12, glow: 12 }) });
  const fb = panelMesh(cta, { w: 1.2, h: 0.22, x: 0, y: 0.3, z: 0.5, ppu: 700, key: t => (t > tF + 0.4 ? 'on' : 'off'), draw: (c, t, P) => {
    const on = t > tF + 0.4; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? 'rgba(255,255,255,.06)' : '#ffffff'; c.fill(); if (on) { c.strokeStyle = '#fff'; c.lineWidth = 5; c.stroke(); } c.restore();
    text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR MORE RULES', P.cw / 2, P.ch / 2 + 3, { size: on ? 70 : 56, weight: 900, color: on ? '#fff' : '#08080a', spacing: 3 });
  } });
  [q1, q2, fb].forEach((p, i) => { p.mesh.scale.setScalar(0.0001); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.4, ease: 'back.out(2)' }, [w('s11', 'would') - 0.05, w('s11', 'comments') - 0.1, tF - 0.1][i]); });
  sfx('pop', w('s11', 'would'), 0.4); sfx('pop', tF, 0.4); sfx('click', tF + 0.4, 0.7);
  // the tall door creaks open a crack, eyes blink in the dark
  tl.to(d2.userData.hinge.rotation, { y: 0.35, duration: 1.4, ease: 'power2.inOut' }, t0 + 0.6);
  sfx('creak', t0 + 0.6, 0.4, { dur: 1.4 });
  tl.to(eyes.scale, { y: 0.8, duration: 0.15 }, t0 + 1.9);
  tl.to(eyes.scale, { y: 0.0001, duration: 0.06, yoyo: true, repeat: 1 }, t0 + 3.2);
  music(t0, 0.5); music(DUR - 0.8, 0.5); music(DUR, 0);
}
tl.set({}, {}, DUR);

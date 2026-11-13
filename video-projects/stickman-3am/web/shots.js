// "If your phone ever lights up at 3:07 AM" — one continuous 3D bedroom; shots are camera + lighting states.
import { THREE, tl, C, scene, camState, camTo, camSet, shake, flash, zoomBlur, post, key, lights, floorU, TEX, every, mulberry32, shot, text } from './engine.js';
import { T, DUR, S, L, w, we, sfx, music, clamp01, lerp, prog, q, E_OUT, E_INOUT } from './lib.js';
import { stickFigure, setPose, POSES } from './stick.js';
import { bed, nightstand, phone, windowFrame, door, clock, redX, eyesInDark, panelMesh, propMat } from './props.js';

const PI = Math.PI;
// ---------------------------------------------------------------- the room (always present)
const room = new THREE.Group(); scene.add(room);
const BED = { x: -0.35, z: 0 }, NS = { x: -1.58, z: 0.05 }, DOOR = { x: 1.32, z: -0.6, ry: -0.32 };
const B = bed(); B.g.position.set(BED.x, 0, BED.z); room.add(B.g);
const NSg = nightstand(); NSg.position.set(NS.x, 0, NS.z); room.add(NSg);
const PH = phone(); PH.position.set(NS.x, 0.507, NS.z + 0.02); PH.rotation.y = PI / 2 + 0.25; room.add(PH);
const PHS = PH.userData.state;
const WIN = windowFrame(0.95); WIN.position.set(-0.45, 1.78, -1.15); room.add(WIN);
const DR = door(); DR.position.set(DOOR.x, 0, DOOR.z); DR.rotation.y = DOOR.ry; room.add(DR);
const CLK = clock(room, { x: 0.62, y: 2.05, z: -1.15, size: 0.48 });
const LAMP = new THREE.Group(); LAMP.position.set(NS.x + 0.12, 0.5, NS.z - 0.1); room.add(LAMP);
// "you": lying in bed, head on the pillow (-x)
const YOU = stickFigure(); YOU.userData.root.scale.setScalar(0.85); room.add(YOU);
setPose(YOU, 'lie', { x: BED.x + 0.08, y: 0.6, z: 0.0, ry: PI / 2, torsoX: -1.47, neckX: -0.1 });
YOU.userData.pool.visible = false;
// "it": the double in the doorway
const IT = stickFigure({ emissive: 0.05 }); IT.userData.root.scale.setScalar(0.85); room.add(IT);
const itBase = { x: DOOR.x + 0.03, y: 0.705, z: DOOR.z - 0.05, ry: -0.55 };
setPose(IT, 'creep', Object.assign({}, itBase)); IT.visible = false;
const EYES = eyesInDark(); EYES.position.set(BED.x + 0.15, 0.1, 0.1); EYES.scale.set(1, 0.0001, 1); EYES.visible = false; room.add(EYES);
// threshold line on the floor
const thrMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.red).multiplyScalar(3.5), transparent: true, opacity: 0, toneMapped: false });
const thr = new THREE.Mesh(new THREE.PlaneGeometry(0.95, 0.025), thrMat); thr.rotation.set(-PI / 2, 0, DOOR.ry); thr.position.set(DOOR.x + 0.06, 0.006, DOOR.z + 0.16); room.add(thr);

// ---------------------------------------------------------------- lighting looks
const NIGHT = { amb: 0.1, moon: 0.45, key: 5, rim: 0.5 }, MORNING = { amb: 0.55, moon: 0.0, key: 22, rim: 0.9 };
function look(t, L0, dur = 0.01) {
  tl.to(lights.ambient, { intensity: L0.amb, duration: dur }, t); tl.to(lights.moon, { intensity: L0.moon, duration: dur }, t);
  tl.to(key, { intensity: L0.key, duration: dur }, t); tl.to(lights.rim, { intensity: L0.rim, duration: dur }, t);
}
look(0, NIGHT);
lights.phoneLight.position.set(NS.x + 0.05, 0.98, NS.z + 0.15);
lights.hallLight.position.set(DOOR.x + 0.25, 1.5, DOOR.z - 1.5);
function flicker(t, n = 3, amt = 0.75) { for (let i = 0; i < n; i++) { const tt = t + i * 0.09 + (i % 2) * 0.03; tl.fromTo(post, { flicker: amt }, { flicker: 0, duration: 0.06, immediateRender: false }, tt); } sfx('flicker', t, 0.5); }
function cut(t, s = 'swoosh', g = 0.25) { if (s) sfx(s, t - 0.05, g); }
// breathing under the blanket
every(t => { B.blanket.scale.y = 1 + Math.sin(t * 2.2) * 0.04 * (YOU.userData.pose.lieBreath ?? 1); });

// ---------------------------------------------------------------- camera presets
const PHONE_P = new THREE.Vector3(NS.x, 0.51, NS.z + 0.02);
const CAM = {
  wide: { x: 0.0, y: 1.55, z: 7.9, tx: -0.08, ty: 1.0, tz: -0.2, roll: 0, fov: 38 },
  phone: { x: NS.x + 0.22, y: 0.98, z: NS.z + 0.5, tx: PHONE_P.x, ty: PHONE_P.y, tz: PHONE_P.z, roll: -4, fov: 30 },
  phoneTight: { x: NS.x + 0.12, y: 0.82, z: NS.z + 0.3, tx: PHONE_P.x, ty: PHONE_P.y, tz: PHONE_P.z, roll: -6, fov: 30 },
  bed: { x: 1.05, y: 1.7, z: 2.7, tx: -0.55, ty: 0.55, tz: 0, roll: -3, fov: 34 },
  toDoor: { x: -1.3, y: 1.5, z: 3.6, tx: 1.05, ty: 1.0, tz: -0.6, roll: -2, fov: 34 },
  door: { x: 0.35, y: 1.15, z: 2.4, tx: DOOR.x, ty: 1.05, tz: DOOR.z, roll: -3, fov: 34 },
  side: { x: -1.9, y: 1.35, z: 3.4, tx: 0.55, ty: 0.75, tz: -0.4, roll: -3, fov: 36 },
  clock: { x: 0.7, y: 2.0, z: 0.55, tx: 0.62, ty: 2.02, tz: -1.15, roll: -3, fov: 32 },
  under: { x: BED.x + 0.3, y: 0.16, z: 1.9, tx: BED.x + 0.15, ty: 0.12, tz: 0.2, roll: -4, fov: 32 },
};
const headCam = (dist, dy = 0.02) => { const hx = itBase.x - 0.02, hz = itBase.z + 0.04, hy = 1.4, d = [Math.sin(itBase.ry), Math.cos(itBase.ry)]; return { x: hx + d[0] * dist, y: hy + dy, z: hz + d[1] * dist, tx: hx, ty: hy, tz: hz, roll: -2, fov: 30 }; };

// ---------------------------------------------------------------- 1  HOOK
{
  const t1 = w('s01', 'lights'), tL2 = L('s01', 1).start;
  music(0, 0.6);
  camSet(0, CAM.wide);
  camTo(0.05, { x: -0.6, y: 1.25, z: 5.0, tx: -0.9, ty: 0.8, tz: 0 }, tL2 - 0.15, 'power1.inOut');
  tl.set(PHS, { mode: 'notif' }, 0);
  tl.fromTo(PHS, { lit: 0 }, { lit: 1, duration: 0.15 }, t1);
  tl.fromTo(lights.phoneLight, { intensity: 0 }, { intensity: 0.45, duration: 0.15 }, t1);
  tl.to(PH.userData.flip.position, { x: 0.006, duration: 0.03, yoyo: true, repeat: 15, ease: 'none' }, t1 + 0.02);
  sfx('buzz', t1 + 0.02, 0.8); sfx('buzz', t1 + 0.75, 0.6);
  camSet(tL2 - 0.04, CAM.phone);
  camTo(tL2, { x: CAM.phoneTight.x, y: CAM.phoneTight.y + 0.06, z: CAM.phoneTight.z + 0.06 }, S('s02') - tL2, 'none');
  cut(tL2, 'swoosh', 0.2);
  sfx('hit', w('s01', 'own'), 0.35);
}
// ---------------------------------------------------------------- 2  DO NOT READ IT
{
  const t0 = S('s02'), td = w('s02', 'do');
  const X = redX(room, { x: PHONE_P.x + 0.05, y: PHONE_P.y + 0.16, z: PHONE_P.z + 0.02, ry: 0.25, w: 0.2, h: 0.2, boost: 1.5 });
  X.mesh.scale.setScalar(0.0001);
  tl.fromTo(X.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.35, ease: 'back.out(2.5)' }, td - 0.05);
  tl.to(X.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001, duration: 0.2 }, S('s03') + 0.25);
  X.mesh.lookAt(NS.x + 0.42, 1.02, NS.z + 0.62);
  sfx('stinger', td, 0.9); shake(td, 0.8, 0.45); flicker(td + 0.05, 2, 0.6);
  camSet(t0 - 0.02, { x: NS.x + 0.42, y: 1.02, z: NS.z + 0.62, tx: PHONE_P.x, ty: PHONE_P.y + 0.12, tz: PHONE_P.z, roll: 3, fov: 32 });
  camTo(t0, { x: NS.x + 0.36, z: NS.z + 0.52 }, S('s03') - t0, 'none');
}
// ---------------------------------------------------------------- 3  FACE DOWN / CLOSE YOUR EYES
{
  const t0 = S('s03'), tf = w('s03', 'turn') + 0.05, tC = L('s03', 1).start;
  camSet(t0 - 0.02, CAM.phone);
  tl.to(PH.userData.flip.position, { y: 0.07, duration: 0.25, ease: 'power2.out' }, tf);
  tl.to(PH.userData.flip.rotation, { x: PI, duration: 0.45, ease: 'power2.inOut' }, tf + 0.05);
  tl.to(PH.userData.flip.position, { y: 0.0, duration: 0.2, ease: 'power2.in' }, tf + 0.3);
  tl.to(lights.phoneLight, { intensity: 0, duration: 0.25 }, tf + 0.35);
  sfx('swoosh', tf, 0.3); sfx('thunk', tf + 0.5, 0.5);
  cut(tC, 'swoosh', 0.2);
  camSet(tC - 0.03, CAM.bed);
  camTo(tC, { z: 2.95, y: 1.8, x: 1.2 }, S('s04') - tC, 'none');
  tl.to(B.blanketPivot.scale, { x: 1.45, duration: 0.7, ease: 'power2.inOut' }, w('s03', 'close') - 0.05);
  tl.to(B.blanketPivot.position, { y: 0.69, duration: 0.7, ease: 'power2.inOut' }, w('s03', 'close') - 0.05);
  sfx('cloth', w('s03', 'close'), 0.55);
  tl.to(YOU.userData.pose, { tremble: 0.35, duration: 0.5 }, w('s03', 'eyes'));
}
// ---------------------------------------------------------------- 4  LOOK AT THE DOOR
{
  const t0 = S('s04'), tLk = w('s04', 'look');
  camSet(t0 - 0.02, CAM.toDoor);
  camTo(t0, { x: -0.9, z: 3.0, tx: DOOR.x - 0.1 }, S('s05') - t0, 'power1.inOut');
  const msg = 'LOOK AT THE DOOR';
  const gt = panelMesh(room, { w: 0.78, h: 0.14, x: DOOR.x - 0.17, y: 1.55, z: DOOR.z + 0.6, ry: -0.3, ppu: 900, boost: 2.0, key: t => q(Math.min(t, tLk + 1.2)) + (t > tLk ? Math.floor(t * 9) % 4 : 0),
    draw: (c, t, P) => {
      const n = Math.floor(clamp01((t - tLk + 0.05) * 18 / msg.length) * msg.length), fl = Math.floor(t * 9) % 4 === 0 ? 0.55 : 1;
      c.font = '900 100px "Inter Display"'; c.letterSpacing = '10px';
      const size = Math.floor(100 * Math.min(1, P.cw * 0.94 / c.measureText(msg).width));
      c.font = `900 ${size}px "Inter Display"`; c.letterSpacing = `${size * 0.1}px`; c.textAlign = 'center'; c.textBaseline = 'middle';
      const full = c.measureText(msg).width, x0 = (P.cw - full) / 2, s0 = msg.slice(0, n);
      c.globalAlpha = fl; c.textAlign = 'left';
      c.lineJoin = 'round'; c.lineWidth = size * 0.16; c.strokeStyle = 'rgba(0,0,0,.85)'; c.strokeText(s0, x0, P.ch / 2);
      c.shadowColor = C.red; c.shadowBlur = size * 0.25; c.fillStyle = '#FF3B47'; c.fillText(s0, x0, P.ch / 2);
    } });
  gt.mesh.visible = false; tl.set(gt.mesh, { visible: true }, tLk - 0.05); tl.set(gt.mesh, { visible: false }, S('s05') + 0.2);
  for (let k = 0; k < 7; k++) sfx('type', tLk + k * 0.07, 0.3);
  sfx('whisper', tLk, 0.5); flicker(tLk + 0.6, 2, 0.5);
  tl.to(YOU.userData.pose, { tremble: 0.15, duration: 0.5 }, t0);
}
// ---------------------------------------------------------------- 5  SOMEONE STANDING THERE
{
  const t0 = S('s05'), tLook = w('s05', 'look'), tSt = w('s05', 'standing'), tL2 = L('s05', 1).start;
  tl.set(IT, { visible: true }, t0);
  camSet(t0 - 0.02, CAM.door);
  camTo(t0, { x: 0.55, z: 2.0 }, tL2 - t0, 'power1.inOut');
  tl.to(DR.userData.hinge.rotation, { y: 1.3, duration: 2.4, ease: 'power2.inOut' }, tLook - 0.1);
  tl.to(DR.userData.hallMat, { opacity: 0.16, duration: 1.6 }, tLook + 0.2);
  tl.to(DR.userData.spill.material, { opacity: 0.35, duration: 1.6 }, tLook + 0.2);
  tl.to(lights.hallLight, { intensity: 1.6, duration: 1.6 }, tLook + 0.2);
  sfx('creak', tLook - 0.05, 0.75, { dur: 2.2 });
  flicker(tSt, 3, 0.8);
  music(tSt, 0.75, { heart: 0.5 });
  // "exactly like you": push to the double's face, head tilts
  cut(tL2, 'whoosh', 0.3);
  camSet(tL2 - 0.03, headCam(2.4, -0.25));
  camTo(tL2, headCam(1.6, -0.1), S('s06') - tL2, 'power1.inOut');
  tl.to(IT.userData.pose, { neckZ: 0.6, duration: 1.6, ease: 'power2.inOut' }, w('s05', 'exactly'));
  sfx('boom', w('s05', 'you', 1), 0.45);
}
// ---------------------------------------------------------------- 6  IT WILL SMILE / WAIT
{
  const t0 = S('s06'), tS = w('s06', 'smile'), tW = w('s06', 'wait');
  tl.set(IT.userData.face, { visible: true }, t0 - 0.05);
  camSet(t0 - 0.02, headCam(1.0, -0.02));
  camTo(t0, headCam(0.82, -0.02), tW - t0, 'none');
  tl.fromTo(IT.userData.pose, { smile: 0 }, { smile: 1, duration: 0.8, ease: 'power2.inOut', immediateRender: false }, tS - 0.05);
  sfx('stinger', tS + 0.1, 0.45, { soft: 1 });
  camTo(tW - 0.1, headCam(1.5, -0.05), S('s07') - tW + 0.1, 'power2.inOut');
  flicker(tW + 0.3, 1, 0.9);
  music(t0, 0.8, { heart: 0.8 });
}
// ---------------------------------------------------------------- 7  THRESHOLD / EYES SHUT / NO MATTER WHAT YOU HEAR
{
  const t0 = S('s07'), tC = w('s07', 'come'), tN = w('s07', 'notice'), tSh = L('s07', 1).start, tH = w('s07', 'hear');
  camSet(t0 - 0.02, CAM.side);
  camTo(t0, { x: -1.6, z: 3.0 }, tSh - t0, 'none');
  tl.to(thrMat, { opacity: 0.9, duration: 0.4 }, tC);
  sfx('swoosh', tC, 0.3);
  tl.to(IT.userData.pose, Object.assign({}, POSES.lean, { neckZ: 0.6, duration: 1.2, ease: 'power2.inOut' }), tN - 0.2);
  sfx('creak', tN, 0.3, { dur: 0.6 });
  cut(tSh, 'swoosh', 0.2);
  camSet(tSh - 0.03, { x: -1.75, y: 1.15, z: 1.75, tx: 0.9, ty: 0.95, tz: -0.5, roll: 3, fov: 36 });
  camTo(tSh, { x: -1.55, z: 1.5, y: 1.1 }, S('s08') - tSh, 'none');
  tl.to(YOU.userData.pose, { tremble: 0.9, duration: 0.3 }, tSh);
  [0, 0.42, 0.84].forEach(d => { sfx('knock', tH + d, 0.75); shake(tH + d, 0.25, 0.2); });
  sfx('whisper', tH + 0.3, 0.45);
  music(tSh, 0.9, { heart: 1.0 });
}
// ---------------------------------------------------------------- 8  3:33 / GONE
{
  const t0 = S('s08'), tT = w('s08', 'tick'), tG = L('s08', 1).start;
  camSet(t0 - 0.02, CAM.clock);
  camTo(t0, { z: 0.15 }, tG - t0, 'none');
  tl.fromTo(CLK.state, { min: 7 }, { min: 33, duration: tT - t0 - 0.1, ease: 'power1.in', immediateRender: false }, t0 + 0.05);
  for (let tt = t0 + 0.1; tt < tT - 0.05; tt += 0.14) sfx('tick', tt, 0.4);
  sfx('clock', tT, 1.0);
  music(tT, 0.0);
  cut(tG, 'whoosh', 0.25);
  camSet(tG - 0.03, CAM.wide);
  tl.to(DR.userData.hinge.rotation, { y: 0, duration: 0.22, ease: 'power3.in' }, tG + 0.15);
  tl.to([DR.userData.hallMat, DR.userData.spill.material], { opacity: 0, duration: 0.1 }, tG + 0.36);
  tl.to(lights.hallLight, { intensity: 0, duration: 0.1 }, tG + 0.36);
  tl.set(IT, { visible: false }, tG + 0.33);
  tl.to(thrMat, { opacity: 0, duration: 0.1 }, tG + 0.36);
  sfx('slam', tG + 0.36, 1.0); shake(tG + 0.37, 1.0, 0.45);
  tl.to(YOU.userData.pose, { tremble: 0, duration: 0.6 }, tG + 0.6);
}
// ---------------------------------------------------------------- 9  MORNING
{
  const t0 = S('s09');
  look(t0, MORNING, 0.01);
  tl.set(WIN.userData.moon, { visible: false }, t0); tl.set(WIN.userData.sun, { visible: true }, t0);
  tl.set(WIN.userData.halo.material.color, { r: 1, g: 0.85, b: 0.4 }, t0);
  tl.set(B.blanketPivot.scale, { x: 1 }, t0); tl.set(B.blanketPivot.position, { y: 0.62 }, t0);
  tl.set(CLK.state, { min: 7 + 4 * 60 }, t0);
  camSet(t0, { x: 0.1, y: 1.45, z: 6.2, tx: -0.2, ty: 0.95, tz: -0.2, roll: 0, fov: 36 });
  camTo(t0, { z: 5.4 }, S('s10') - t0, 'none');
  tl.to(YOU.userData.pose, Object.assign({}, POSES.sit, { ry: PI / 2, x: BED.x - 0.15, y: 0.6, torsoX: 0.05, lShX: -2.6, rShX: -2.6, lShZ: 0.4, rShZ: -0.4, lElX: -0.3, rElX: -0.3, duration: 1.0, ease: 'power2.inOut' }), t0 + 0.15);
  tl.to(YOU.userData.pose, { lShX: -0.35, rShX: -0.35, lShZ: 0.12, rShZ: -0.12, lElX: -0.6, rElX: -0.6, duration: 0.6, ease: 'power2.inOut' }, t0 + 1.25);
  sfx('birds', t0, 0.35); music(t0, 0.35);
  sfx('riser', w('s09', 'nobody'), 0.35, { dur: 1.4 });
}
// ---------------------------------------------------------------- 10  CHECK THE MESSAGE / READ
{
  const t0 = S('s10'), tCh = w('s10', 'check'), tR = w('s10', 'read');
  camSet(t0 - 0.02, CAM.phone);
  camTo(t0, CAM.phoneTight, S('s11') - t0, 'power1.inOut');
  tl.set(PHS, { mode: 'thread', read: 0 }, t0);
  tl.to(PH.userData.flip.position, { y: 0.07, duration: 0.2 }, tCh - 0.1);
  tl.to(PH.userData.flip.rotation, { x: 0, duration: 0.4, ease: 'power2.inOut' }, tCh - 0.05);
  tl.to(PH.userData.flip.position, { y: 0, duration: 0.2 }, tCh + 0.25);
  tl.to(lights.phoneLight, { intensity: 0.3, duration: 0.2 }, tCh + 0.2);
  sfx('swoosh', tCh, 0.3);
  tl.fromTo(PHS, { read: 0 }, { read: 1, duration: 0.5, immediateRender: false }, tR - 0.1);
  sfx('hit', tR, 0.5); music(tR, 0.55, { heart: 0.6 });
}
// ---------------------------------------------------------------- 11  SOMETHING ELSE DID. AND IT NEVER LEFT.
{
  const t0 = S('s11'), tSo = w('s11', 'something'), tNe = w('s11', 'never'), tLe = w('s11', 'left');
  camSet(t0 - 0.02, { x: -0.55, y: 1.2, z: 2.0, tx: -0.6, ty: 0.95, tz: 0, roll: -2, fov: 34 });
  camTo(t0, { z: 2.6, y: 1.1 }, tSo - t0, 'none');
  tl.to(YOU.userData.pose, { neckX: 0.5, lShX: -0.6, rShX: -0.6, lElX: -1.4, rElX: -1.4, duration: 0.5 }, t0);
  look(tSo, { amb: 0.06, moon: 0, key: 1.5, rim: 0.2 }, 1.4);
  tl.to(WIN.userData.sun.material, { opacity: 0.15, duration: 1.4 }, tSo);
  tl.to(WIN.userData.halo.material, { opacity: 0.0, duration: 1.4 }, tSo);
  sfx('down', tSo, 0.45, { dur: 1.6 }); music(tSo, 0.25);
  camSet(tNe - 0.05, CAM.under);
  camTo(tNe, { x: BED.x + 0.25, z: 1.25, y: 0.16 }, DUR - tNe, 'power1.in');
  tl.set(EYES, { visible: true }, tLe); tl.to(EYES.scale, { y: 1, duration: 0.18, ease: 'power3.out' }, tLe + 0.05);
  tl.to(EYES.scale, { y: 0.0001, duration: 0.06, yoyo: true, repeat: 1 }, tLe + 1.0);
  sfx('stinger', tLe + 0.05, 1.0); flash(tLe + 0.05, 0.25, 0.25, '#ff2030'); shake(tLe + 0.05, 0.8, 0.5);
  look(tLe, { amb: 0.0, moon: 0, key: 0, rim: 0 }, 0.3);
}
// ---------------------------------------------------------------- 12  CTA
{
  const t0 = S('s12'), tF = w('s12', 'follow');
  tl.set(room, { visible: false }, t0);
  const cta = shot(t0, DUR + 1, (g, h) => {
    const you = stickFigure(); you.userData.root.scale.setScalar(0.85); g.add(you); setPose(you, 'stand', { y: 0.705 });
    const it = stickFigure({ emissive: 0.02 }); it.userData.root.scale.setScalar(0.85); g.add(it); setPose(it, 'creep', { x: 0.55, y: 0.705, z: -1.6, ry: -0.35, smile: 1 }); it.userData.face.visible = true;
    it.userData.pose.eyeGlow = 1;
    const q1 = panelMesh(g, { w: 2.2, h: 0.3, x: 0, y: 2.25, z: 0, ppu: 700, draw: (c, t, P) => text(c, 'WOULD YOU HAVE LOOKED?', P.cw / 2, P.ch / 2, { size: 80, weight: 900, color: '#fff', font: 'Inter Display', spacing: 4, glow: 14 }) });
    const q2 = panelMesh(g, { w: 1.6, h: 0.16, x: 0, y: 1.95, z: 0, ppu: 700, draw: (c, t, P) => text(c, 'COMMENT  YES  OR  NO', P.cw / 2, P.ch / 2, { size: 64, weight: 800, color: C.red, spacing: 14, glow: 12 }) });
    const fb = panelMesh(g, { w: 1.3, h: 0.24, x: 0, y: 1.62, z: 0.1, ppu: 700, key: t => (t > tF + 0.4 ? 'on' : 'off'), draw: (c, t, P) => {
      const on = t > tF + 0.4; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? 'rgba(255,255,255,.06)' : '#ffffff'; c.fill(); if (on) { c.strokeStyle = '#fff'; c.lineWidth = 5; c.stroke(); } c.restore();
      text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR MORE RULES', P.cw / 2, P.ch / 2 + 3, { size: on ? 72 : 60, weight: 900, color: on ? '#fff' : '#08080a', spacing: 3 });
    } });
    [q1, q2, fb].forEach((p, i) => { p.mesh.scale.setScalar(0.0001); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.4, ease: 'back.out(2)' }, [w('s12', 'would') - 0.05, w('s12', 'comments') - 0.1, tF - 0.1][i]); });
    sfx('pop', w('s12', 'would'), 0.4); sfx('pop', tF, 0.4); sfx('click', tF + 0.4, 0.7);
    flicker(t0 + 1.4, 2, 0.6);
  });
  look(t0, { amb: 0.08, moon: 0, key: 14, rim: 0.4 }, 0.01);
  camSet(t0, { x: 0, y: 1.45, z: 6.6, tx: 0, ty: 1.5, tz: 0, roll: 0, fov: 34 });
  camTo(t0, { z: 5.9 }, DUR - t0, 'power1.out');
  music(t0, 0.5); music(DUR - 1.0, 0.5); music(DUR, 0);
}
tl.set({}, {}, DUR);

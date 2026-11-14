// Poseable 3D pictogram stick figure. Joints are groups; a pose is a plain object of joint angles that GSAP can tween.
import { THREE, TEX } from './engine.js';

const D = THREE.MathUtils.degToRad;
const LIMB_R = 0.07, TORSO_R = 0.11;
const capsule = (len, r) => { const g = new THREE.CapsuleGeometry(r, len, 8, 20); g.translate(0, -len / 2, 0); return g; }; // hangs down from its pivot
const GEO = { upper: capsule(0.28, LIMB_R), lower: capsule(0.27, LIMB_R * 0.95), thigh: capsule(0.38, LIMB_R * 1.08), shin: capsule(0.38, LIMB_R), torso: (() => { const g = new THREE.CapsuleGeometry(TORSO_R, 0.42, 8, 24); g.translate(0, 0.21 + 0.02, 0); return g; })(), head: new THREE.SphereGeometry(0.135, 40, 28) };

export const POSES = {
  stand:  { torsoX: 0, torsoZ: 0, neckX: 0, neckZ: 0, lShX: 0, lShZ: 0.08, lElX: 0, rShX: 0, rShZ: -0.08, rElX: 0, lHipX: 0, lKnX: 0, rHipX: 0, rKnX: 0 },
  sit:    { torsoX: 0.05, torsoZ: 0, neckX: 0.1, neckZ: 0, lShX: -0.35, lShZ: 0.1, lElX: -0.6, rShX: -0.35, rShZ: -0.1, rElX: -0.6, lHipX: -1.57, lKnX: 0, rHipX: -1.57, rKnX: 0 },
  lie:    { torsoX: -1.57, torsoZ: 0, neckX: -0.05, neckZ: 0, lShX: 0, lShZ: 0.12, lElX: 0, rShX: 0, rShZ: -0.12, rElX: 0, lHipX: -1.57, lKnX: 0, rHipX: -1.57, rKnX: 0 },
  creep:  { torsoX: 0.12, torsoZ: 0, neckX: 0.25, neckZ: 0.35, lShX: 0.05, lShZ: 0.05, lElX: -0.1, rShX: 0.05, rShZ: -0.05, rElX: -0.1, lHipX: 0, lKnX: 0, rHipX: 0, rKnX: 0 },
  lean:   { torsoX: 0.45, torsoZ: 0, neckX: 0.15, neckZ: 0.3, lShX: -0.5, lShZ: 0.05, lElX: -0.5, rShX: -0.7, rShZ: -0.05, rElX: -0.4, lHipX: -0.15, lKnX: 0.25, rHipX: 0.1, rKnX: 0.1 },
  huddle: { torsoX: 0.3, torsoZ: 0, neckX: 0.35, neckZ: 0, lShX: -1.15, lShZ: 0.25, lElX: -1.2, rShX: -1.15, rShZ: -0.25, rElX: -1.2, lHipX: -2.2, lKnX: 2.45, rHipX: -2.2, rKnX: 2.45 },
  mouth:  { torsoX: 0.08, torsoZ: 0, neckX: 0.05, neckZ: 0, lShX: -1.2, lShZ: 0.5, lElX: -2.2, rShX: -1.2, rShZ: -0.5, rElX: -2.2, lHipX: -1.57, lKnX: 0, rHipX: -1.57, rKnX: 0 },
  knock:  { torsoX: 0.05, torsoZ: 0, neckX: 0.1, neckZ: 0, lShX: 0, lShZ: 0.08, lElX: 0, rShX: -1.35, rShZ: -0.15, rElX: -1.1, lHipX: 0, lKnX: 0, rHipX: 0, rKnX: 0 },
  hold:   { torsoX: 0.12, torsoZ: 0, neckX: 0.45, neckZ: 0, lShX: -0.55, lShZ: 0.15, lElX: -1.5, rShX: -0.55, rShZ: -0.15, rElX: -1.5, lHipX: -1.57, lKnX: 0, rHipX: -1.57, rKnX: 0 },
};

export function stickFigure({ color = 0xf2f4f8, emissive = 0.08, hair = false, hairColor = 0x4a4e57 } = {}) {
  const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: emissive, roughness: 0.55, metalness: 0 });
  const mesh = (geo) => { const m = new THREE.Mesh(geo, mat); m.castShadow = false; return m; };
  const root = new THREE.Group();            // pelvis
  const torso = new THREE.Group(); root.add(torso); torso.add(mesh(GEO.torso));
  const neck = new THREE.Group(); neck.position.y = 0.62; torso.add(neck);
  const head = mesh(GEO.head); head.position.y = 0.16; neck.add(head);
  const limb = (parent, x, y, g1, g2, len1) => {
    const a = new THREE.Group(); a.position.set(x, y, 0); parent.add(a); a.add(mesh(g1));
    const b = new THREE.Group(); b.position.y = -len1; a.add(b); b.add(mesh(g2));
    return [a, b];
  };
  const [lSh, lEl] = limb(torso, 0.17, 0.5, GEO.upper, GEO.lower, 0.28);
  const [rSh, rEl] = limb(torso, -0.17, 0.5, GEO.upper, GEO.lower, 0.28);
  const [lHip, lKn] = limb(root, 0.085, 0, GEO.thigh, GEO.shin, 0.38);
  const [rHip, rKn] = limb(root, -0.085, 0, GEO.thigh, GEO.shin, 0.38);
  if (hair) {   // long hair: a cap over the skull + a fall down the back
    const hm = new THREE.MeshStandardMaterial({ color: hairColor, roughness: 0.7 });
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.15, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.62), hm); cap.rotation.x = 0.55; head.add(cap);
    const fall = new THREE.Mesh(new THREE.CapsuleGeometry(0.13, 0.42, 8, 16), hm); fall.position.set(0, -0.2, -0.075); fall.scale.set(1.1, 1, 0.5); head.add(fall);
    for (const sx of [-1, 1]) { const side = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.3, 6, 12), hm); side.position.set(sx * 0.12, -0.12, 0.0); side.rotation.z = sx * 0.12; head.add(side); }
  }
  // face (hidden until needed): two eye dots + a smile arc on the front of the head
  const face = new THREE.Group(); head.add(face);
  const featMat = new THREE.MeshBasicMaterial({ color: 0x050506 });
  const eyeGeo = new THREE.SphereGeometry(0.018, 12, 10);
  const HR = 0.135, onSurf = (x, y) => Math.sqrt(Math.max(0, HR * HR - x * x - y * y)) + 0.001;
  const eyes = [-0.045, 0.045].map(x => { const e = new THREE.Mesh(eyeGeo, featMat.clone()); e.position.set(x, 0.035, onSurf(x, 0.035) - 0.006); face.add(e); return e; });
  const arc = new THREE.CatmullRomCurve3(Array.from({ length: 11 }, (_, i) => { const u = i / 10 * 2 - 1, x = u * 0.075, y = -0.05 + 0.032 * u * u; return new THREE.Vector3(x, y, onSurf(x, y)); }));
  const smileGeo = new THREE.TubeGeometry(arc, 40, 0.0075, 6, false);
  const smile = new THREE.Mesh(smileGeo, featMat.clone()); face.add(smile);
  smileGeo.setDrawRange(0, 0);
  face.visible = false;
  // contact shadow / glow pool
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.1), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0.22, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
  pool.rotation.x = -Math.PI / 2; pool.scale.set(1, 0.55, 1);
  const wrap = new THREE.Group(); wrap.add(root); wrap.add(pool);
  const pose = Object.assign({}, POSES.stand, { x: 0, y: 0.83, z: 0, ry: 0, rx: 0, rz: 0, tremble: 0, walk: 0, smile: 0, eyeGlow: 0 });
  const J = { torso, neck, lSh, lEl, rSh, rEl, lHip, lKn, rHip, rKn };
  wrap.userData = {
    pose, mat, eyes, smile, face, head, pool, root,
    update: t => {
      const p = pose, tr = p.tremble ? Math.sin(t * 61) * 0.025 * p.tremble : 0;
      const wk = p.walk ? Math.sin(p.walk * Math.PI * 2) : 0;
      root.position.set(p.x, p.y + Math.abs(wk) * 0.02, p.z);
      root.rotation.set(p.rx, p.ry, p.rz + tr);
      torso.rotation.set(p.torsoX, 0, p.torsoZ + tr * 0.5);
      neck.rotation.set(p.neckX, 0, p.neckZ);
      lSh.rotation.set(p.lShX - wk * 0.45, 0, p.lShZ); lEl.rotation.x = p.lElX;
      rSh.rotation.set(p.rShX + wk * 0.45, 0, p.rShZ); rEl.rotation.x = p.rElX;
      lHip.rotation.x = p.lHipX + wk * 0.5; lKn.rotation.x = p.lKnX + Math.max(0, -wk) * 0.6;
      rHip.rotation.x = p.rHipX - wk * 0.5; rKn.rotation.x = p.rKnX + Math.max(0, wk) * 0.6;
      pool.position.set(p.x, 0.003, p.z);
      smileGeo.setDrawRange(0, Math.floor(smileGeo.index.count * p.smile / 6) * 6);
      for (const e of eyes) { e.material.color.setRGB(0.02 + p.eyeGlow * 2.4, 0.02 + p.eyeGlow * 0.15, 0.02 + p.eyeGlow * 0.15); }
    },
  };
  return wrap;
}
export function setPose(fig, name, extra = {}) { Object.assign(fig.userData.pose, POSES[name], extra); }
export { D };

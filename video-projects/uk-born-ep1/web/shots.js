// UK "Where will you be born?" part 1 — a 3D extruded map of the UK (Natural Earth outlines), a red map pin that
// bounces between near-miss towns and lands on Scunthorpe, then four banter fact cards drawn as camera-space HUD panels.
import { THREE, tl, C, scene, camera, camState, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, text, rrect, floor, dust, film, bloom, zoomBlur } from './engine.js';
import { DUR, S, L, w, we, sfx, music, clamp01, lerp } from './lib.js';
import { stickFigure, setPose } from './stick.js';
import { panelMesh } from './props.js';

const PI = Math.PI;
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const ss = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const easeBack = k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };

// ---------------------------------------------------------------- daylight look
floor.visible = false; dust.visible = false;
scene.background = new THREE.Color(0x0d3f86);
scene.fog = new THREE.Fog(0x0d3f86, 40, 90);
scene.environmentIntensity = 0.7;
film.uniforms.vig.value = 0.28; film.uniforms.grain.value = 0.018; film.uniforms.ca.value = 0.0015;
post.bloom = 0.35;
tl.set(key, { intensity: 0 }, 0); tl.set(lights.moon, { intensity: 0 }, 0); tl.set(lights.rim, { intensity: 0.35 }, 0); tl.set(lights.ambient, { intensity: 0.35 }, 0);
const sun = new THREE.DirectionalLight(0xfff4e0, 2.6); sun.position.set(-6, 14, 8); scene.add(sun);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x2b5e2b, 0.9));

// ---------------------------------------------------------------- map projection (1 unit = 1° of latitude)
const LON0 = -2.6, LAT0 = 54.4, KX = Math.cos(54.5 * PI / 180);
const P = (lon, lat) => [(lon - LON0) * KX, -(lat - LAT0)];   // → world [x, z]
const LAND_H = 0.14;

// sea: cartoon waves drawn on a canvas, slowly drifting
function seaTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 512); gr.addColorStop(0, '#1f78d1'); gr.addColorStop(1, '#2186e0'); g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(255,255,255,.16)'; g.lineWidth = 5; g.lineCap = 'round';
  const R = mulberry32(3);
  for (let i = 0; i < 26; i++) { const x = R() * 512, y = R() * 512; g.beginPath(); g.arc(x, y, 16, PI * 1.1, PI * 1.9); g.stroke(); g.beginPath(); g.arc(x + 30, y, 16, PI * 1.1, PI * 1.9); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(14, 14); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const seaTex = seaTexture();
const sea = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshStandardMaterial({ map: seaTex, roughness: 0.45, metalness: 0.05 }));
sea.rotation.x = -PI / 2; sea.position.y = -0.01; scene.add(sea);
every(t => { seaTex.offset.set(t * 0.012, t * 0.02); });

// land: extruded polygons + a sandy rim (a slightly fatter, lower extrusion)
function shapesOf(polys) {
  return polys.map(rings => {
    const toV = r => r.map(([lon, lat]) => { const [x, z] = P(lon, lat); return new THREE.Vector2(x, -z); });
    const sh = new THREE.Shape(toV(rings[0])); for (const h of rings.slice(1)) sh.holes.push(new THREE.Path(toV(h))); return sh;
  });
}
function landMesh(polys, top, side, h, { rim = true } = {}) {
  const g = new THREE.Group(), shapes = shapesOf(polys);
  const geo = new THREE.ExtrudeGeometry(shapes, { depth: h, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 1, curveSegments: 1 });
  const m = new THREE.Mesh(geo, [new THREE.MeshStandardMaterial({ color: top, roughness: 0.85 }), new THREE.MeshStandardMaterial({ color: side, roughness: 0.8 })]);
  m.rotation.x = -PI / 2; g.add(m);
  if (rim) {
    const rg = new THREE.ExtrudeGeometry(shapes, { depth: h * 0.35, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.035, bevelSegments: 1, curveSegments: 1 });
    const r = new THREE.Mesh(rg, new THREE.MeshStandardMaterial({ color: 0xf6e7b8, roughness: 0.9 })); r.rotation.x = -PI / 2; r.position.y = -0.005; g.add(r);
  }
  scene.add(g); return g;
}
const MAPD = window.MAP;
landMesh(MAPD.uk, 0x47b552, 0x2c7a35, LAND_H);
landMesh(MAPD.iom, 0x47b552, 0x2c7a35, LAND_H);
landMesh(MAPD.ie, 0x9aa79d, 0x6f7a72, LAND_H * 0.6);
landMesh(MAPD.fr, 0x9aa79d, 0x6f7a72, LAND_H * 0.6);

// nation borders (approximate, dashed) + nation labels lying on the land
const BORDERS = [
  [[-3.07, 54.98], [-2.93, 55.03], [-2.75, 55.12], [-2.62, 55.2], [-2.47, 55.3], [-2.33, 55.36], [-2.2, 55.44], [-2.2, 55.55], [-2.28, 55.64], [-2.12, 55.72], [-2.03, 55.81]],
  [[-3.08, 53.26], [-2.95, 53.16], [-2.78, 53.0], [-2.98, 52.9], [-3.09, 52.75], [-3.12, 52.6], [-3.03, 52.45], [-3.02, 52.33], [-3.1, 52.2], [-3.04, 52.07], [-2.94, 51.97], [-2.84, 51.85], [-2.7, 51.74], [-2.65, 51.62]],
];
const dashMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 });
for (const line of BORDERS) {
  const pts = line.map(([lo, la]) => { const [x, z] = P(lo, la); return new THREE.Vector3(x, LAND_H + 0.016, z); });
  const curve = new THREE.CatmullRomCurve3(pts), len = curve.getLength(), n = Math.floor(len / 0.07);
  for (let i = 0; i < n; i += 2) {
    const a = curve.getPointAt(i / n), b = curve.getPointAt(Math.min(1, (i + 1) / n));
    const d = new THREE.Mesh(new THREE.PlaneGeometry(a.distanceTo(b), 0.022), dashMat);
    d.position.copy(a).lerp(b, 0.5); d.rotation.set(-PI / 2, 0, -Math.atan2(b.z - a.z, b.x - a.x)); scene.add(d);
  }
}
function flatLabel(s, lon, lat, size = 0.32, color = 'rgba(255,255,255,.55)', spacing = 14) {
  const [x, z] = P(lon, lat), wpx = s.length * size * 260 + 60;
  const p = panelMesh(scene, { w: wpx / 520, h: size * 1.1, x, y: LAND_H + 0.02, z, rx: -PI / 2, ppu: 520, boost: 1.0, draw: (c, t, Pn) => text(c, s, Pn.cw / 2, Pn.ch / 2, { size: size * 400, weight: 900, color, font: 'Inter Display', spacing }) });
  return p;
}
flatLabel('SCOTLAND', -4.3, 56.85, 0.3); flatLabel('ENGLAND', -1.2, 52.75, 0.3); flatLabel('WALES', -3.75, 52.35, 0.22); flatLabel('N. IRELAND', -6.75, 54.85, 0.16, 'rgba(255,255,255,.55)', 6);
flatLabel('IRELAND', -8.0, 53.2, 0.24, 'rgba(255,255,255,.28)');

// ---------------------------------------------------------------- towns: dots + camera-facing labels (screen-constant size)
const TOWNS = {
  London: [51.507, -0.128, 1], Birmingham: [52.486, -1.89, 1], Manchester: [53.481, -2.243, 1], Liverpool: [53.408, -2.991, 0], Leeds: [53.8, -1.549, 1],
  Newcastle: [54.978, -1.618, 1], Sheffield: [53.383, -1.465, 0], Bristol: [51.455, -2.588, 0], Glasgow: [55.864, -4.252, 1], Edinburgh: [55.953, -3.189, 1],
  Cardiff: [51.481, -3.179, 1], Belfast: [54.597, -5.93, 1], Aberdeen: [57.15, -2.094, 1], Inverness: [57.478, -4.225, 1], Plymouth: [50.376, -4.143, 0],
  Truro: [50.263, -5.051, 0], Norwich: [52.63, 1.297, 1], Hull: [53.767, -0.327, 0], Scunthorpe: [53.588, -0.654, 0], Grimsby: [53.567, -0.081, 0],
  Nottingham: [52.954, -1.158, 0], Southampton: [50.909, -1.404, 0], Brighton: [50.823, -0.137, 0], Swansea: [51.621, -3.944, 0], Carlisle: [54.892, -2.934, 0],
  Dundee: [56.462, -2.971, 0], York: [53.959, -1.082, 0], Blackpool: [53.817, -3.036, 0], Lincoln: [53.234, -0.538, 0], Derry: [54.997, -7.309, 0], Exeter: [50.718, -3.534, 0],
  Oxford: [51.752, -1.258, 0], Cambridge: [52.205, 0.119, 0], Leicester: [52.637, -1.135, 0], Stoke: [53.003, -2.18, 0], Ipswich: [52.056, 1.148, 0],
};
const TW = {};
const dotGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.02, 20), dotRing = new THREE.CylinderGeometry(0.062, 0.062, 0.016, 20);
const dotMat = new THREE.MeshBasicMaterial({ color: 0xffffff }), ringMat = new THREE.MeshBasicMaterial({ color: 0x14361a });
function labelSprite(s) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 128; const g = c.getContext('2d');
  g.font = '900 64px "Inter Display"'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
  g.lineWidth = 14; g.strokeStyle = 'rgba(10,25,45,.9)'; g.strokeText(s, 256, 66); g.fillStyle = '#ffffff'; g.fillText(s, 256, 66);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; tx.anisotropy = 8;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false, toneMapped: false })); sp.center.set(0.5, 0); return sp;
}
for (const [name, [lat, lon, major]] of Object.entries(TOWNS)) {
  const [x, z] = P(lon, lat);
  const g = new THREE.Group(); g.position.set(x, LAND_H + 0.012, z); scene.add(g);
  g.add(at(new THREE.Mesh(dotRing, ringMat), 0, 0, 0), at(new THREE.Mesh(dotGeo, dotMat), 0, 0.006, 0));
  const sp = labelSprite(name); sp.position.y = 0.08; g.add(sp);
  const anchor = { Glasgow: 0.92, Edinburgh: 0.08, Cardiff: 0.92, Bristol: 0.08, Leeds: 0.15, Manchester: 0.85, Hull: 0.1, Grimsby: 0.1, Scunthorpe: 0.85, Lincoln: 0.5 }[name];
  if (anchor !== undefined) sp.center.set(anchor, 0);
  TW[name] = { x, z, g, sp, major, pop: { k: major ? 1 : 0 } };
}
const camPos = new THREE.Vector3();
every(() => {
  camPos.set(camState.x, camState.y, camState.z);
  for (const T of Object.values(TW)) {
    const d = camPos.distanceTo(T.g.position), k = T.pop.k;
    const s = Math.min(d, 15) * 0.026 * (0.75 + 0.25 * k);
    T.sp.scale.set(s * 4 * Math.max(k, 0.001), s * Math.max(k, 0.001), 1);
    T.sp.material.opacity = Math.min(1, k * 1.5);
    T.sp.visible = k > 0.01;
    T.g.children[0].scale.setScalar(Math.min(1, Math.max(0.28, d / 14))); T.g.children[1].scale.setScalar(Math.min(1, Math.max(0.28, d / 14)));
  }
});

// ---------------------------------------------------------------- the pin
const pin = new THREE.Group(); scene.add(pin);
const pinBody = new THREE.Group(); pin.add(pinBody);
const pinMat = new THREE.MeshStandardMaterial({ color: 0xe8202c, roughness: 0.28, metalness: 0.15, emissive: 0x3a0005 });
const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 40, 28), pinMat); head.position.y = 0.56; pinBody.add(head);
const cone = new THREE.Mesh(new THREE.ConeGeometry(0.168, 0.46, 40, 1, true), pinMat); cone.rotation.x = PI; cone.position.y = 0.3; pinBody.add(cone);
const dotW = new THREE.Mesh(new THREE.SphereGeometry(0.075, 24, 16), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4 })); dotW.position.set(0, 0.58, 0.15); pinBody.add(dotW);
const shine = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 12), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.2, 2.2), toneMapped: false })); shine.position.set(-0.08, 0.67, 0.13); pinBody.add(shine);
// top hat (Edinburgh gag)
const hat = new THREE.Group(); hat.position.y = 0.72; pinBody.add(hat);
const hatMat = new THREE.MeshStandardMaterial({ color: 0x111216, roughness: 0.5 });
hat.add(at(new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.2, 28), hatMat), 0, 0.12, 0), at(new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.02, 28), hatMat), 0, 0.02, 0), at(new THREE.Mesh(new THREE.CylinderGeometry(0.123, 0.123, 0.045, 28), new THREE.MeshStandardMaterial({ color: 0xc8102e })), 0, 0.06, 0));
hat.visible = false;
const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.22, 32), new THREE.MeshBasicMaterial({ map: TEX.soft, color: 0x000000, transparent: true, opacity: 0.45, depthWrite: false }));
shadow.rotation.x = -PI / 2; scene.add(shadow);
const ringFx = new THREE.Mesh(new THREE.RingGeometry(0.2, 0.25, 48), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
ringFx.rotation.x = -PI / 2; scene.add(ringFx);

// ---------------------------------------------------------------- timeline anchors
const tLets = L('s01', 1).start, tLondon = L('s02', 0).start, tCorn = L('s02', 2).start, tEdin = L('s02', 4).start, tRoll = L('s02', 6).start;
const tScun = L('s03', 0).start, tFfs = L('s03', 1).start;
const tF1 = S('s04'), tAol = L('s04', 1).start, tProb = L('s04', 2).start;
const tF2 = S('s05'), tBin = L('s05', 1).start;
const tF3 = S('s06'), tWest = L('s06', 1).start;
const tF4 = S('s07'), tLeft = L('s07', 1).start;
const tCta = S('s08'), tYours = L('s08', 1).start, tFollow = L('s08', 2).start;

// path: [town, land time, leave time, hop height]
const BHAM = 'Birmingham';
const STOPS = [
  [BHAM, tLets + 0.75, tLondon - 0.62, 0],
  ['London', tLondon, L('s02', 1).end + 0.12, 1.2],
  ['Truro', tCorn, L('s02', 3).end + 0.12, 1.6],
  ['Edinburgh', tEdin, L('s02', 5).end + 0.05, 2.4],
  ['Manchester', tRoll + 0.55, tRoll + 0.62, 1.6],
  ['Leeds', tRoll + 1.12, tRoll + 1.17, 0.7],
  ['Hull', tRoll + 1.62, tRoll + 1.67, 0.55],
  ['Lincoln', tRoll + 2.1, tRoll + 2.15, 0.4],
  ['Scunthorpe', tScun, 1e9, 0.35],
];
const DROP_H = 9;
function pinState(t) {
  // before the drop: hidden in the sky above Birmingham
  const b = TW[BHAM];
  if (t < STOPS[0][1]) { const k = clamp01((t - (tLets + 0.05)) / 0.7); return { x: b.x, z: b.z, y: DROP_H * (1 - k * k), air: 1, spin: 0, land: -1 }; }
  for (let i = 0; i < STOPS.length; i++) {
    const [name, t1, t2] = STOPS[i], T = TW[name];
    if (t >= t1 && t < t2) return { x: T.x, z: T.z, y: 0, air: 0, land: t - t1, i };
    const nx = STOPS[i + 1];
    if (nx && t >= t2 && t < nx[1]) {
      const N = TW[nx[0]], k = (t - t2) / (nx[1] - t2);
      return { x: lerp(T.x, N.x, k), z: lerp(T.z, N.z, k), y: 4 * nx[3] * k * (1 - k), air: 1, k, spin: k * PI * 2 * (nx[3] > 1 ? 2 : 1), dir: Math.atan2(N.x - T.x, N.z - T.z), land: -1 };
    }
  }
  const T = TW.Scunthorpe; return { x: T.x, z: T.z, y: 0, air: 0, land: t - tScun, i: STOPS.length - 1 };
}
const PIN = { wilt: 0, scale: 1, hat: 0 };
every(t => {
  const s = pinState(t);
  const cd = Math.hypot(camState.x - s.x, camState.y - s.y, camState.z - s.z);
  const sc = Math.min(1.7, Math.max(0.5, cd / 8.5)) * PIN.scale;
  const elev = Math.atan2(camState.y - s.y, Math.hypot(camState.x - s.x, camState.z - s.z));
  pin.position.set(s.x, LAND_H + s.y, s.z); pin.scale.setScalar(sc);
  // squash on landing (elastic), stretch in the air, spin while flying
  let sy = 1, sxz = 1;
  if (s.land >= 0) { const q = s.land; const e = Math.exp(-q * 7) * Math.cos(q * 26); sy = 1 - 0.35 * e; sxz = 1 + 0.22 * e; }
  else if (s.air) { sy = 1.08; sxz = 0.94; }
  pinBody.scale.set(sxz, sy, sxz);
  pinBody.rotation.set(0, s.air ? (s.spin || 0) : 0, 0);
  pin.rotation.set(0, 0, 0);
  pin.rotateOnWorldAxis(new THREE.Vector3(1, 0, 0), -0.85 * elev); // lean away so it stands up on screen
  if (PIN.wilt > 0) pin.rotateOnWorldAxis(new THREE.Vector3(0, 0, 1), -0.55 * PIN.wilt);
  shadow.position.set(s.x, LAND_H + 0.012, s.z); const hk = clamp01(s.y / 3);
  shadow.scale.setScalar(sc * (1 - 0.5 * hk)); shadow.material.opacity = 0.45 * (1 - 0.7 * hk) * (t > tLets ? 1 : 0);
  pin.visible = t > tLets;
  // landing ring
  if (s.land >= 0 && s.land < 0.5) { ringFx.position.set(s.x, LAND_H + 0.02, s.z); const k = s.land / 0.5; ringFx.scale.setScalar(sc * (1 + k * 3)); ringFx.material.opacity = 0.9 * (1 - k); } else ringFx.material.opacity = 0;
  hat.visible = PIN.hat > 0.01; hat.scale.setScalar(Math.max(0.001, PIN.hat));
  // town labels pop when the pin touches them
  for (let i = 0; i < STOPS.length; i++) { const T = TW[STOPS[i][0]]; if (!T.major) T.pop.k = t >= STOPS[i][1] ? ss(STOPS[i][1], STOPS[i][1] + 0.2, t) : 0; }
});
STOPS.forEach(([, t1], i) => { if (i < STOPS.length - 1) sfx('boing', t1, i === 0 ? 0.8 : 0.55, { pitch: 1 + (i % 3) * 0.12 }); });

// ---------------------------------------------------------------- spin gags
// London: a price tag. Cornwall: tourists everywhere. Edinburgh: the pin gets a top hat.
const gag = (txt, color, name, t0, t1, dy = 0.9) => {
  const T = TW[name];
  const p = panelMesh(scene, { w: 2.6, h: 0.72, x: T.x, y: LAND_H + dy, z: T.z - 0.9, rx: -1.2, ppu: 600, boost: 1.0, draw: (c, t, Pn) => {
    c.fillStyle = color; rrect(c, 8, 8, Pn.cw - 16, Pn.ch - 16, 40); c.fill(); c.lineWidth = 10; c.strokeStyle = '#ffffff'; c.stroke();
    text(c, txt, Pn.cw / 2, Pn.ch / 2 + 10, { size: 270, weight: 900, color: '#ffffff', font: 'Inter Display', spacing: 4 });
  } });
  p.mesh.scale.setScalar(0.0001);
  tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.35, ease: 'back.out(2.2)', immediateRender: false }, t0);
  tl.to(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001, duration: 0.15 }, t1);
  return p;
};
gag('£££££', '#1f9d55', 'London', tLondon + 0.3, STOPS[1][2] - 0.05); sfx('cash', tLondon + 0.3, 0.6);
gag('TOURISTS', '#ff7a00', 'Truro', tCorn + 0.35, STOPS[2][2] - 0.05, 1.0);
gag('TOO POSH', '#6a1b9a', 'Edinburgh', w('s02', 'posh') - 0.1, STOPS[3][2], 1.15);
tl.fromTo(PIN, { hat: 0 }, { hat: 1, duration: 0.3, ease: 'back.out(3)', immediateRender: false }, tEdin + 0.3); tl.to(PIN, { hat: 0, duration: 0.2 }, STOPS[3][2] + 0.1);
sfx('pop', tEdin + 0.3, 0.6); sfx('pop', w('s02', 'posh') - 0.1, 0.4);
{
  const T = TW.Truro, R = mulberry32(9), cols = [0xff6f61, 0xffd166, 0x4cc9f0, 0xf72585, 0xffffff, 0x90e0ef, 0xffb703, 0xb5e48c];
  const tour = Array.from({ length: 16 }, (_, i) => {
    const f = stickFigure({ color: cols[i % cols.length], emissive: 0.15 }); f.userData.pool.visible = false; scene.add(f);
    const a = R() * PI * 2, r = 0.25 + R() * 0.45;
    setPose(f, 'stand', { x: T.x + Math.cos(a) * r * 1.3, y: LAND_H + 0.2, z: T.z + Math.sin(a) * r * 0.9, ry: R() * PI * 2, rx: -0.9 }); f.userData.root.scale.setScalar(0.24);
    return { f, t0: tCorn + 0.3 + i * 0.05, ph: R() * 6 };
  });
  every(t => { for (const m of tour) { const k = ss(m.t0, m.t0 + 0.2, t) * (1 - ss(STOPS[2][2], STOPS[2][2] + 0.2, t)); m.f.visible = k > 0.01; m.f.userData.root.scale.setScalar(0.24 * Math.max(0.001, k)); m.f.userData.pose.walk = t * 1.6 + m.ph; } });
  for (let i = 0; i < 16; i += 3) sfx('pop', tCorn + 0.3 + i * 0.05, 0.25, { pitch: 1 + i * 0.03 });
}

// ---------------------------------------------------------------- HUD (camera space: x ±0.432, y ±0.768 at z = -2, fov 42)
const hud = new THREE.Group(); hud.position.z = -2; camera.add(hud);
const HPX = 1250;   // canvas px per HUD unit (1080 px = 0.864)
function hp(o) { const p = panelMesh(hud, Object.assign({ ppu: HPX, boost: 0.98 }, o)); p.mesh.renderOrder = 10; p.mat.depthTest = false; return p; }
function popIn(p, t0, t1 = 1e9, ease = 'back.out(2)') {
  p.mesh.visible = false; p.mesh.scale.setScalar(0.0001);
  tl.set(p.mesh, { visible: true }, t0); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.35, ease, immediateRender: false }, t0);
  if (t1 < 1e8) { tl.to(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001, duration: 0.18, ease: 'power2.in' }, t1 - 0.18); tl.set(p.mesh, { visible: false }, t1); }
  return p;
}
const card = (c, P, fill = '#ffffff', stroke = '#0b1d36', r = 44, lw = 12) => { c.fillStyle = fill; rrect(c, lw, lw, P.cw - lw * 2, P.ch - lw * 2, r); c.fill(); c.lineWidth = lw; c.strokeStyle = stroke; c.stroke(); };
// Union flag (simplified, symmetric)
function unionFlag(c, x, y, w, h) {
  c.save(); c.beginPath(); c.rect(x, y, w, h); c.clip();
  c.fillStyle = '#012169'; c.fillRect(x, y, w, h);
  c.lineCap = 'butt'; const diag = (lw, col) => { c.strokeStyle = col; c.lineWidth = lw; c.beginPath(); c.moveTo(x, y); c.lineTo(x + w, y + h); c.moveTo(x + w, y); c.lineTo(x, y + h); c.stroke(); };
  diag(h * 0.2, '#ffffff'); diag(h * 0.07, '#C8102E');
  c.fillStyle = '#ffffff'; c.fillRect(x + w / 2 - h * 0.17, y, h * 0.34, h); c.fillRect(x, y + h * 0.33, w, h * 0.34);
  c.fillStyle = '#C8102E'; c.fillRect(x + w / 2 - h * 0.1, y, h * 0.2, h); c.fillRect(x, y + h * 0.4, w, h * 0.2);
  c.restore();
}

// title (hook) — on screen from frame one
const title = hp({ w: 0.8, h: 0.26, x: 0, y: 0.56, draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36');
  unionFlag(c, 46, 54, 150, 100);
  text(c, 'WHERE WILL', P.cw / 2 + 70, 92, { size: 74, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 1 });
  text(c, 'YOU BE BORN?', P.cw / 2 + 70, 172, { size: 92, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 1 });
  text(c, 'UK EDITION  •  PART 1', P.cw / 2, P.ch - 58, { size: 34, weight: 800, color: '#5b6b80', spacing: 8 });
} });
popIn(title, 0.0, tScun - 0.1);
title.mesh.scale.setScalar(1); tl.set(title.mesh, { visible: true }, 0);
every(t => { if (t < 0.25) title.mesh.scale.setScalar(0.85 + 0.15 * easeBack(clamp01(t / 0.25))); });

// "SCUNTHORPE" landing banner
const banner = hp({ w: 0.82, h: 0.24, x: 0, y: 0.52, draw: (c, _t, P) => {
  card(c, P, '#C8102E', '#ffffff', 40, 14);
  text(c, 'SCUNTHORPE', P.cw / 2, P.ch / 2 - 18, { size: 130, weight: 900, color: '#ffffff', font: 'Inter Display', spacing: 2 });
  text(c, 'NORTH LINCOLNSHIRE', P.cw / 2, P.ch / 2 + 78, { size: 36, weight: 800, color: 'rgba(255,255,255,.85)', spacing: 10 });
} });
popIn(banner, tScun + 0.02, tF1 + 0.05, 'back.out(3)');
// fact chip
function chip(n, t0, t1) { return popIn(hp({ w: 0.3, h: 0.09, x: -0.25, y: 0.68, draw: (c, _t, P) => { card(c, P, '#FFE14D', '#0b1d36', 50, 10); text(c, `FACT ${n}`, P.cw / 2, P.ch / 2 + 4, { size: 66, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 3 }); } }), t0, t1); }

// ---- FACT 1: the name / AOL 1996 / the Scunthorpe problem
chip(1, tF1, tF2);
const tSwear = w('s04', 'swear');
const nameBoard = hp({ w: 0.82, h: 0.2, x: 0, y: 0.47, key: t => Math.floor(clamp01((t - tSwear) / 0.3) * 12), draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36', 36, 10);
  const letters = 'SCUNTHORPE'.split(''), lw = (P.cw - 120) / letters.length;
  letters.forEach((ch, i) => text(c, ch, 60 + lw * (i + 0.5), P.ch / 2 + 6, { size: 150, weight: 900, color: '#0b1d36', font: 'Inter Display' }));
  const k = clamp01((window.__t - tSwear) / 0.3);
  if (k > 0) { const x0 = 60 + lw * 1 - 8, wBar = (lw * 4 + 16) * k; c.fillStyle = '#0b0b0d'; rrect(c, x0, 34, wBar, P.ch - 68, 14); c.fill(); if (k > 0.6) text(c, 'BEEP', x0 + (lw * 4 + 16) / 2, P.ch / 2 + 4, { size: 70, weight: 900, color: '#FF3B47', font: 'Inter Display', spacing: 10 }); }
} });
popIn(nameBoard, tF1 + 0.15, tAol);
sfx('bleep', tSwear + 0.05, 0.35, { dur: 0.25 });
const aol = hp({ w: 0.8, h: 0.5, x: 0, y: 0.36, key: t => Math.floor(t * 20), draw: (c, _t, P) => {
  const t = window.__t;
  c.fillStyle = '#c0c0c0'; c.fillRect(0, 0, P.cw, P.ch); c.lineWidth = 8; c.strokeStyle = '#ffffff'; c.beginPath(); c.moveTo(4, P.ch - 4); c.lineTo(4, 4); c.lineTo(P.cw - 4, 4); c.stroke();
  c.strokeStyle = '#404040'; c.beginPath(); c.moveTo(P.cw - 4, 4); c.lineTo(P.cw - 4, P.ch - 4); c.lineTo(4, P.ch - 4); c.stroke();
  const tb = c.createLinearGradient(0, 0, P.cw, 0); tb.addColorStop(0, '#000080'); tb.addColorStop(1, '#1084d0'); c.fillStyle = tb; c.fillRect(16, 16, P.cw - 32, 76);
  text(c, 'Sign Up  —  1996', 40, 56, { size: 44, weight: 800, color: '#ffffff', align: 'left' });
  c.fillStyle = '#c0c0c0'; c.fillRect(P.cw - 84, 26, 56, 52); text(c, '✕', P.cw - 56, 54, { size: 40, weight: 900, color: '#000' });
  const field = (lab, val, y) => { text(c, lab, 50, y, { size: 44, weight: 700, color: '#000', align: 'left' }); c.fillStyle = '#ffffff'; c.fillRect(270, y - 34, P.cw - 320, 68); c.strokeStyle = '#404040'; c.lineWidth = 4; c.strokeRect(270, y - 34, P.cw - 320, 68); text(c, val, 290, y + 2, { size: 44, weight: 700, color: '#000', align: 'left', font: 'Inter' }); };
  const typed = 'Scunthorpe', n = Math.floor(clamp01((t - tAol - 0.6) / 1.0) * typed.length);
  field('Name:', 'Dave', 170); field('Town:', typed.slice(0, n) + (Math.floor(t * 3) % 2 && n < typed.length ? '|' : ''), 270);
  const tErr = w('s04', 'filter') - 0.1;
  if (t > tErr) {
    const sh = t < tErr + 0.4 ? Math.sin(t * 90) * 10 : 0;
    c.save(); c.translate(sh, 0); c.fillStyle = '#ffffff'; c.fillRect(40, 340, P.cw - 80, 230); c.strokeStyle = '#C8102E'; c.lineWidth = 8; c.strokeRect(40, 340, P.cw - 80, 230);
    c.fillStyle = '#C8102E'; c.beginPath(); c.arc(120, 455, 46, 0, PI * 2); c.fill(); text(c, '!', 120, 458, { size: 70, weight: 900, color: '#fff' });
    text(c, 'ERROR', 190, 410, { size: 58, weight: 900, color: '#C8102E', align: 'left' });
    text(c, 'Offensive language detected.', 190, 475, { size: 38, weight: 700, color: '#000', align: 'left' });
    text(c, 'Account blocked.', 190, 528, { size: 38, weight: 700, color: '#000', align: 'left' });
    c.restore();
  } else { c.fillStyle = '#c0c0c0'; c.fillRect(P.cw / 2 - 130, 380, 260, 80); c.strokeStyle = '#404040'; c.lineWidth = 4; c.strokeRect(P.cw / 2 - 130, 380, 260, 80); text(c, 'JOIN', P.cw / 2, 421, { size: 46, weight: 800, color: '#000' }); }
} });
popIn(aol, tAol, tProb + 0.1);
for (let i = 0; i < 10; i++) sfx('type', tAol + 0.6 + i * 0.1, 0.4);
sfx('buzz', w('s04', 'filter') - 0.1, 0.6); shake(w('s04', 'filter') - 0.1, 0.25, 0.3);
const stamp = hp({ w: 0.84, h: 0.24, x: 0, y: 0.4, rz: 0.08, draw: (c, _t, P) => {
  c.strokeStyle = '#C8102E'; c.lineWidth = 18; rrect(c, 20, 20, P.cw - 40, P.ch - 40, 30); c.stroke();
  text(c, 'THE SCUNTHORPE', P.cw / 2, P.ch / 2 - 34, { size: 92, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 4 });
  text(c, 'PROBLEM', P.cw / 2, P.ch / 2 + 62, { size: 92, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 14 });
} });
popIn(stamp, w('s04', 'scunthorpe', 1) - 0.05, tF2, 'back.out(4)');
const lookUp = popIn(hp({ w: 0.36, h: 0.07, x: 0.2, y: 0.24, draw: (c, _t, P) => { card(c, P, '#0b1d36', '#ffffff', 40, 6); text(c, '(LOOK IT UP)', P.cw / 2, P.ch / 2 + 3, { size: 44, weight: 900, color: '#ffffff', spacing: 4 }); } }), we('s04', 'problem') + 0.15, tF2);
sfx('stamp', w('s04', 'scunthorpe', 1) - 0.05, 0.9); shake(w('s04', 'scunthorpe', 1), 0.3, 0.25);

// ---- FACT 2: Industrial Garden Town / wheelie bin water feature
chip(2, tF2, tF3);
const sign = hp({ w: 0.82, h: 0.34, x: 0, y: 0.42, draw: (c, _t, P) => {
  card(c, P, '#00703c', '#ffffff', 40, 14);
  text(c, 'WELCOME TO', P.cw / 2, 92, { size: 52, weight: 800, color: '#ffffff', spacing: 10 });
  text(c, 'SCUNTHORPE', P.cw / 2, 196, { size: 118, weight: 900, color: '#ffffff', font: 'Inter Display', spacing: 2 });
  c.fillStyle = '#FFE14D'; rrect(c, 70, 270, P.cw - 140, 96, 22); c.fill();
  text(c, 'Industrial Garden Town', P.cw / 2, 320, { size: 64, weight: 900, color: '#00381e', font: 'Inter Display' });
} });
popIn(sign, tF2 + 0.2, tBin + 0.1);
const bin = hp({ w: 0.6, h: 0.56, x: 0, y: 0.36, key: t => Math.floor(t * 24), draw: (c, _t, P) => {
  const t = window.__t, cx = P.cw / 2, by = P.ch - 60, fk = clamp01((t - (w('s05', 'water') - 0.15)) / 0.3);
  card(c, P, '#ffffff', '#0b1d36', 40, 12);
  // fountain arcs
  if (fk > 0) for (let j = 0; j < 7; j++) { const a = -PI / 2 + (j - 3) * 0.28, ph = (t * 2.2 + j * 0.13) % 1; c.strokeStyle = `rgba(20,120,230,${0.9 * fk})`; c.lineWidth = 16; c.lineCap = 'round'; c.beginPath(); for (let s = 0; s <= 1.0001; s += 0.05) { const vx = Math.cos(a) * 260, vy = Math.sin(a) * 420; const x = cx + vx * s, y = 250 + vy * s + 520 * s * s; s === 0 ? c.moveTo(x, y) : c.lineTo(x, y); } c.stroke(); c.fillStyle = `rgba(20,120,230,${fk})`; const s = ph; c.beginPath(); c.arc(cx + Math.cos(a) * 260 * s, 250 + Math.sin(a) * 420 * s + 520 * s * s, 10, 0, PI * 2); c.fill(); }
  // bin body
  c.fillStyle = '#2b2f36'; c.beginPath(); c.moveTo(cx - 150, 270); c.lineTo(cx + 150, 270); c.lineTo(cx + 120, by - 20); c.lineTo(cx - 120, by - 20); c.closePath(); c.fill();
  c.fillStyle = '#3a3f48'; rrect(c, cx - 170, 238, 340, 46, 14); c.fill();
  c.fillStyle = '#16181c'; c.beginPath(); c.arc(cx - 105, by - 6, 30, 0, PI * 2); c.arc(cx + 105, by - 6, 30, 0, PI * 2); c.fill();
  c.strokeStyle = '#4a505a'; c.lineWidth = 8; for (const x of [-60, 0, 60]) { c.beginPath(); c.moveTo(cx + x, 320); c.lineTo(cx + x * 0.85, by - 60); c.stroke(); }
  if (fk > 0.5) { c.fillStyle = '#FFE14D'; rrect(c, cx - 200, 80, 400, 70, 20); c.fill(); text(c, 'WATER FEATURE', cx, 116, { size: 50, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 2 }); }
} });
popIn(bin, w('s05', 'wheelie') - 0.1, tF3);
sfx('pop', w('s05', 'wheelie') - 0.1, 0.5); sfx('shimmer', w('s05', 'water') - 0.15, 0.6);

// ---- FACT 3: steelworks / Saturday recall / the most love you'll ever get
chip(3, tF3, tF4);
const steel = hp({ w: 0.82, h: 0.36, x: 0, y: 0.43, key: t => Math.floor(t * 20), draw: (c, _t, P) => {
  const t = window.__t;
  const sky = c.createLinearGradient(0, 0, 0, P.ch); sky.addColorStop(0, '#ffb35c'); sky.addColorStop(1, '#ff7a3d'); card(c, P, '#ff9a4d', '#0b1d36', 36, 12); c.fillStyle = sky; rrect(c, 12, 12, P.cw - 24, P.ch - 24, 32); c.fill();
  // smoke
  for (let i = 0; i < 10; i++) { const ph = (t * 0.35 + i * 0.1) % 1, sx = [210, 330, 610][i % 3], r = 30 + ph * 60; c.fillStyle = `rgba(90,90,100,${0.55 * (1 - ph)})`; c.beginPath(); c.arc(sx + ph * 120, 150 - ph * 160, r, 0, PI * 2); c.fill(); }
  c.fillStyle = '#1d1f26';
  for (const [x, w_, h_] of [[190, 44, 230], [310, 44, 260], [590, 44, 200]]) c.fillRect(x, P.ch - 40 - h_, w_, h_);
  c.fillRect(80, P.ch - 190, 760, 150); c.fillRect(420, P.ch - 260, 120, 220);
  c.fillStyle = '#ffcc33'; for (let i = 0; i < 6; i++) c.fillRect(110 + i * 120, P.ch - 150, 50, 30);
  text(c, 'STEELWORKS', P.cw / 2, P.ch - 90, { size: 54, weight: 900, color: '#ffffff', spacing: 10 });
  if (t > w('s06', 'shut') - 0.05) { c.save(); c.translate(P.cw - 190, 90); c.rotate(0.12); c.fillStyle = '#C8102E'; rrect(c, -150, -46, 300, 92, 18); c.fill(); text(c, 'CLOSING?', 0, 3, { size: 52, weight: 900, color: '#fff', font: 'Inter Display' }); c.restore(); }
} });
popIn(steel, tF3 + 0.2, w('s06', 'parliament') - 0.05);
sfx('thunk', w('s06', 'shut') - 0.05, 0.6);
const cal = hp({ w: 0.5, h: 0.46, x: 0, y: 0.38, draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36', 36, 12);
  c.fillStyle = '#C8102E'; rrect(c, 12, 12, P.cw - 24, 150, 30); c.fill(); c.fillRect(12, 110, P.cw - 24, 52);
  text(c, 'SATURDAY', P.cw / 2, 92, { size: 80, weight: 900, color: '#ffffff', font: 'Inter Display', spacing: 4 });
  text(c, '12', P.cw / 2, 300, { size: 200, weight: 900, color: '#0b1d36', font: 'Inter Display' });
  text(c, 'APRIL 2025', P.cw / 2, 440, { size: 54, weight: 800, color: '#5b6b80', spacing: 8 });
  text(c, 'PARLIAMENT RECALLED', P.cw / 2, 520, { size: 40, weight: 900, color: '#C8102E', spacing: 4 });
} });
popIn(cal, w('s06', 'parliament') - 0.05, tWest);
sfx('pop', w('s06', 'parliament') - 0.05, 0.6); sfx('ding', w('s06', 'saturday'), 0.5);
const love = hp({ w: 0.7, h: 0.46, x: 0, y: 0.38, key: t => Math.floor(t * 24), draw: (c, _t, P) => {
  const t = window.__t, b = 1 + 0.08 * Math.max(0, Math.sin(t * 9)) ** 4;
  card(c, P, '#ffffff', '#0b1d36', 36, 12);
  c.save(); c.translate(P.cw / 2, 210); c.scale(b, b); c.fillStyle = '#e8202c';
  c.beginPath(); c.moveTo(0, 90); c.bezierCurveTo(-190, -20, -110, -150, 0, -60); c.bezierCurveTo(110, -150, 190, -20, 0, 90); c.fill(); c.restore();
  text(c, 'WESTMINSTER', P.cw / 2, 380, { size: 62, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 4 });
  text(c, '+ SCUNTHORPE', P.cw / 2, 460, { size: 62, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 4 });
} });
popIn(love, tWest, tF4);
sfx('pop', tWest, 0.5);

// ---- FACT 4: Keegan and Botham played for Scunthorpe United… then left
chip(4, tF4, tCta);
const pitch = hp({ w: 0.82, h: 0.5, x: 0, y: 0.36, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t, run = clamp01((t - (tLeft + 0.25)) / 1.1), runE = run * run;
  card(c, P, '#2e9e48', '#0b1d36', 36, 12);
  c.save(); rrect(c, 12, 12, P.cw - 24, P.ch - 24, 32); c.clip();
  for (let i = 0; i < 8; i++) { c.fillStyle = i % 2 ? '#34ad50' : '#2e9e48'; c.fillRect(12 + i * 130, 12, 130, P.ch); }
  c.strokeStyle = 'rgba(255,255,255,.7)'; c.lineWidth = 8; c.strokeRect(60, 150, P.cw - 120, P.ch - 120);
  c.fillStyle = '#7b1e3a'; rrect(c, 120, 40, P.cw - 240, 90, 18); c.fill(); text(c, 'SCUNTHORPE UNITED', P.cw / 2, 87, { size: 52, weight: 900, color: '#9bd3ff', font: 'Inter Display', spacing: 4 });
  const fig = (x, name, ph) => {
    const y = 340, bob = run > 0 ? Math.abs(Math.sin((t * 14) + ph)) * 14 : 0, lg = run > 0 ? Math.sin(t * 14 + ph) * 0.6 : 0.15;
    c.save(); c.translate(x, y - bob); c.lineCap = 'round';
    c.strokeStyle = '#ffffff'; c.lineWidth = 22;
    c.beginPath(); c.moveTo(0, 30); c.lineTo(Math.sin(lg) * 70, 30 + Math.cos(lg) * 80); c.moveTo(0, 30); c.lineTo(-Math.sin(lg) * 70, 30 + Math.cos(lg) * 80); c.stroke();
    c.fillStyle = '#7b1e3a'; rrect(c, -40, -110, 80, 150, 24); c.fill(); c.fillStyle = '#9bd3ff'; c.fillRect(-40, -110, 80, 26);
    c.strokeStyle = '#ffffff'; c.beginPath(); c.moveTo(-34, -90); c.lineTo(-34 - Math.cos(lg) * 30, -20 + Math.sin(lg) * 40); c.moveTo(34, -90); c.lineTo(34 + Math.cos(lg) * 30, -20 - Math.sin(lg) * 40); c.stroke();
    c.fillStyle = '#ffffff'; c.beginPath(); c.arc(0, -160, 46, 0, PI * 2); c.fill();
    c.restore();
    c.fillStyle = 'rgba(11,29,54,.85)'; rrect(c, x - 130, y + 128, 260, 66, 20); c.fill(); text(c, name, x, y + 162, { size: 46, weight: 900, color: '#ffffff', spacing: 4 });
  };
  fig(320 + runE * 900, 'KEEGAN', 0); fig(700 + runE * 700, 'BOTHAM', 1.6);
  if (run > 0.05 && run < 0.9) for (let i = 0; i < 5; i++) { c.fillStyle = `rgba(255,255,255,${0.4 - i * 0.07})`; c.beginPath(); c.arc(300 + runE * 900 - 60 - i * 40, 470, 26 - i * 3, 0, PI * 2); c.fill(); }
  c.restore();
  if (t > w('s07', 'smart') - 0.1) { c.save(); c.translate(P.cw / 2, P.ch / 2 + 30); c.rotate(-0.08); c.fillStyle = '#FFE14D'; rrect(c, -300, -70, 600, 140, 30); c.fill(); c.lineWidth = 10; c.strokeStyle = '#0b1d36'; c.stroke(); text(c, 'SMART LADS', 0, 6, { size: 92, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 3 }); c.restore(); }
} });
popIn(pitch, tF4 + 0.2, tCta);
sfx('whoosh', tLeft + 0.25, 0.6); sfx('stamp', w('s07', 'smart') - 0.1, 0.6);

// ---- CTA: certificate, comment prompt, follow
const cert = hp({ w: 0.8, h: 0.42, x: 0, y: 0.42, draw: (c, _t, P) => {
  card(c, P, '#fbf6e8', '#8a6d3b', 30, 12);
  c.strokeStyle = '#c9b27c'; c.lineWidth = 4; rrect(c, 36, 36, P.cw - 72, P.ch - 72, 18); c.stroke();
  text(c, 'CERTIFICATE OF BIRTH', P.cw / 2, 100, { size: 50, weight: 900, color: '#5a4520', spacing: 6 });
  text(c, 'Place of birth:', 90, 210, { size: 44, weight: 700, color: '#5a4520', align: 'left' });
  text(c, 'SCUNTHORPE', P.cw / 2, 300, { size: 110, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 3 });
  text(c, 'Condolences:', 90, 420, { size: 44, weight: 700, color: '#5a4520', align: 'left' });
  c.strokeStyle = '#C8102E'; c.lineWidth = 12; c.lineCap = 'round'; c.beginPath(); c.moveTo(420, 418); c.lineTo(450, 448); c.lineTo(510, 380); c.stroke();
} });
popIn(cert, tCta + 0.1, tYours);
const q1 = popIn(hp({ w: 0.82, h: 0.2, x: 0, y: 0.5, draw: (c, _t, P) => { card(c, P, '#ffffff', '#0b1d36'); text(c, 'WHERE DID YOURS LAND?', P.cw / 2, P.ch / 2 + 5, { size: 70, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 1 }); } }), tYours - 0.05);
const q2 = popIn(hp({ w: 0.74, h: 0.11, x: 0, y: 0.32, draw: (c, _t, P) => { card(c, P, '#C8102E', '#ffffff', 40, 8); text(c, 'COMMENT YOUR TOWN  •  I\'LL ROAST IT', P.cw / 2, P.ch / 2 + 3, { size: 37, weight: 900, color: '#ffffff', spacing: 2 }); } }), w('s08', 'town') - 0.05);
const fb = popIn(hp({ w: 0.6, h: 0.1, x: 0, y: -0.52, key: t => (t > tFollow + 0.5 ? 'on' : 'off'), draw: (c, _t, P) => {
  const on = window.__t > tFollow + 0.5; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? '#0b1d36' : '#FFE14D'; c.fill(); c.lineWidth = 8; c.strokeStyle = '#0b1d36'; c.stroke(); c.restore();
  text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR PART 2', P.cw / 2, P.ch / 2 + 3, { size: 56, weight: 900, color: on ? '#ffffff' : '#0b1d36', spacing: 3 });
} }), tFollow - 0.1);
sfx('pop', tYours, 0.5); sfx('pop', w('s08', 'town'), 0.4); sfx('pop', tFollow, 0.4); sfx('click', tFollow + 0.5, 0.7);
every(t => { window.__t = t; });   // panel draw functions read the current time

// ---------------------------------------------------------------- landing: drumroll, sad trombone, the pin wilts, a rain cloud
sfx('drumroll', tRoll, 0.7, { dur: tScun - tRoll });
sfx('trombone', tScun + 0.25, 0.8);
zoomBlur(tScun, 0.8, 0.4); shake(tScun, 0.5, 0.4); sfx('thunk', tScun, 0.7);
tl.to(PIN, { wilt: 1, duration: 0.8, ease: 'power2.inOut' }, tFfs);
tl.to(PIN, { wilt: 0, duration: 0.4 }, tF1);
{
  const T = TW.Scunthorpe, cloud = new THREE.Group(); cloud.position.set(T.x, LAND_H + 1.0, T.z); scene.add(cloud);
  const cm = new THREE.MeshStandardMaterial({ color: 0x8d96a3, roughness: 0.9 });
  for (const [x, y, r] of [[0, 0, 0.24], [0.24, -0.04, 0.19], [-0.24, -0.05, 0.18], [0.1, 0.12, 0.17], [-0.12, 0.1, 0.15]]) cloud.add(at(new THREE.Mesh(new THREE.SphereGeometry(r, 24, 16), cm), x, y, 0));
  const drops = Array.from({ length: 14 }, (_, i) => { const d = new THREE.Mesh(new THREE.CapsuleGeometry(0.012, 0.07, 3, 6), new THREE.MeshBasicMaterial({ color: 0x9fd2ff })); cloud.add(d); return { d, x: ((i * 37) % 11) / 11 * 0.5 - 0.25, ph: (i * 0.137) % 1 }; });
  const CL = { k: 0 };
  every(t => { const k = CL.k; cloud.visible = k > 0.01; cloud.scale.setScalar(Math.max(0.001, k)); cloud.position.y = LAND_H + 1.0 + Math.sin(t * 2) * 0.03; for (const r of drops) { const ph = (t * 1.6 + r.ph) % 1; r.d.position.set(r.x, -0.2 - ph * 1.0, 0.02); r.d.visible = ph < 0.92; } });
  tl.to(CL, { k: 1, duration: 0.4, ease: 'back.out(2)' }, tFfs + 0.2); tl.to(CL, { k: 0, duration: 0.3 }, tCta + 0.1);
}

// ---------------------------------------------------------------- camera
const FOV = 42, sx = TW.Scunthorpe.x, sz = TW.Scunthorpe.z;
camSet(0, { x: -0.25, y: 15.2, z: 4.6, tx: -0.25, ty: 0, tz: -0.95, roll: 0, fov: FOV });
camTo(0, { y: 14.6, z: 4.3 }, tScun - 0.25, 'none');
camTo(tScun - 0.2, { x: sx + 0.15, y: 3.3, z: sz + 2.7, tx: sx, ty: 0.25, tz: sz - 0.1 }, 0.75, 'power3.inOut');
sfx('whoosh', tScun - 0.25, 0.5);
// slow drift around the town during the facts
camTo(tF1, { x: sx - 0.6, y: 3.6, z: sz + 2.8 }, tF3 - tF1, 'sine.inOut');
camTo(tF3, { x: sx + 0.7, y: 3.4, z: sz + 2.6 }, tCta - tF3, 'sine.inOut');
camTo(tCta, { x: -0.25, y: 15.2, z: 4.6, tx: -0.25, ty: 0, tz: -0.95 }, 1.2, 'power3.inOut');
sfx('whoosh', tCta, 0.4);

// ---------------------------------------------------------------- music
music(0, 0.85); music(tRoll, 0.5); music(tScun, 0.0); music(tF1 + 0.2, 0.75); music(DUR - 1.0, 0.75); music(DUR, 0);
tl.set({}, {}, DUR);

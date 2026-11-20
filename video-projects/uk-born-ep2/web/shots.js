// UK "Where will you be born?" part 2 (Slough). Same 3D map as part 1, with more motion: a follow camera that punches
// in on every landing, a dotted flight trail + route drawn on the map, confetti bursts, drifting clouds, animated spin
// gags (rain, seagulls, midges, a crown), a slot-machine town reel, letter-by-letter town reveal, spring/whip fact cards
// and emoji stickers.
import { THREE, tl, C, scene, camera, camState, camSet, camTo, shake, flash, post, key, lights, TEX, every, mulberry32, text, rrect, floor, dust, film, zoomBlur } from './engine.js';
import { DUR, S, L, w, we, sfx, music, clamp01, lerp } from './lib.js';
import { stickFigure, setPose } from './stick.js';
import { panelMesh } from './props.js';

const PI = Math.PI;
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };
const ss = (a, b, x) => { const k = clamp01((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const backOut = (k, s = 1.70158) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2);
const elastic = k => k <= 0 ? 0 : k >= 1 ? 1 : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * (2 * PI / 3)) + 1;
const EMOJI = '"Noto Color Emoji"';

// ---------------------------------------------------------------- daylight look
floor.visible = false; dust.visible = false;
scene.background = new THREE.Color(0x0d3f86);
scene.fog = new THREE.Fog(0x0d3f86, 40, 90);
scene.environmentIntensity = 0.7;
film.uniforms.vig.value = 0.26; film.uniforms.grain.value = 0.016; film.uniforms.ca.value = 0.0015;
post.bloom = 0.35;
tl.set(key, { intensity: 0 }, 0); tl.set(lights.moon, { intensity: 0 }, 0); tl.set(lights.rim, { intensity: 0.35 }, 0); tl.set(lights.ambient, { intensity: 0.35 }, 0);
const sun = new THREE.DirectionalLight(0xfff4e0, 2.6); sun.position.set(-6, 14, 8); scene.add(sun);
scene.add(new THREE.HemisphereLight(0xcfe8ff, 0x2b5e2b, 0.9));

// ---------------------------------------------------------------- map
const LON0 = -2.6, LAT0 = 54.4, KX = Math.cos(54.5 * PI / 180);
const P = (lon, lat) => [(lon - LON0) * KX, -(lat - LAT0)];
const LAND_H = 0.14;
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
landMesh(MAPD.uk, 0x47b552, 0x2c7a35, LAND_H); landMesh(MAPD.iom, 0x47b552, 0x2c7a35, LAND_H);
landMesh(MAPD.ie, 0x9aa79d, 0x6f7a72, LAND_H * 0.6); landMesh(MAPD.fr, 0x9aa79d, 0x6f7a72, LAND_H * 0.6);
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
  return panelMesh(scene, { w: wpx / 520, h: size * 1.1, x, y: LAND_H + 0.02, z, rx: -PI / 2, ppu: 520, boost: 1.0, draw: (c, t, Pn) => text(c, s, Pn.cw / 2, Pn.ch / 2, { size: size * 400, weight: 900, color, font: 'Inter Display', spacing }) });
}
flatLabel('SCOTLAND', -4.3, 56.85, 0.3); flatLabel('ENGLAND', -1.2, 52.75, 0.3); flatLabel('WALES', -3.75, 52.35, 0.22); flatLabel('N. IRELAND', -6.75, 54.85, 0.16, 'rgba(255,255,255,.55)', 6);
flatLabel('IRELAND', -8.0, 53.2, 0.24, 'rgba(255,255,255,.28)');

// drifting clouds (with soft shadows on the map) for depth
function cloudTexture(dark) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  const blobs = [[150, 160, 70], [235, 120, 90], [330, 140, 78], [400, 170, 55], [100, 185, 45], [260, 185, 70]];
  g.fillStyle = dark ? 'rgba(0,25,50,1)' : '#ffffff';
  if (dark) g.filter = 'blur(10px)';
  for (const [x, y, r] of blobs) { g.beginPath(); g.arc(x, y, r, 0, PI * 2); g.fill(); }
  g.fillRect(100, 170, 300, 60);
  if (!dark) { g.fillStyle = 'rgba(160,190,225,.45)'; g.fillRect(100, 212, 300, 18); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
const cloudTex = cloudTexture(false), cloudShadowTex = cloudTexture(true);
// over the sea, round the edges of the frame, so they never cover the action
const CLOUDS = [[-3.9, 2.6, -3.6, 1.3], [3.0, 2.4, -4.8, 1.1], [3.2, 2.2, 0.6, 1.2], [-4.0, 2.4, 1.6, 1.0], [2.6, 2.6, 3.6, 1.0], [-2.6, 2.3, -6.6, 1.0]].map(([x, y, z, s], i) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(s * 2, s), new THREE.MeshBasicMaterial({ map: cloudTex, transparent: true, depthWrite: false, opacity: 0.92 }));
  m.rotation.x = -PI / 2; scene.add(m);
  const sh = new THREE.Mesh(new THREE.PlaneGeometry(s * 2, s), new THREE.MeshBasicMaterial({ map: cloudShadowTex, transparent: true, depthWrite: false, opacity: 0.18 }));
  sh.rotation.x = -PI / 2; scene.add(sh);
  return { m, sh, x, y, z, v: 0.05 + 0.02 * (i % 3) };
});
every(t => { for (const c of CLOUDS) { const x = c.x + Math.sin(t * c.v * 2 + c.z) * 0.35; c.m.position.set(x, c.y, c.z); c.sh.position.set(x + 0.45, 0.005, c.z + 0.6); } });

// ---------------------------------------------------------------- towns
const TOWNS = {
  London: [51.507, -0.128, 1], Birmingham: [52.486, -1.89, 1], Manchester: [53.481, -2.243, 1], Liverpool: [53.408, -2.991, 0], Leeds: [53.8, -1.549, 1],
  Newcastle: [54.978, -1.618, 1], Sheffield: [53.383, -1.465, 0], Bristol: [51.455, -2.588, 0], Glasgow: [55.864, -4.252, 1], Edinburgh: [55.953, -3.189, 1],
  Cardiff: [51.481, -3.179, 1], Belfast: [54.597, -5.93, 1], Aberdeen: [57.15, -2.094, 1], Inverness: [57.478, -4.225, 0], Plymouth: [50.376, -4.143, 0],
  Norwich: [52.63, 1.297, 1], Hull: [53.767, -0.327, 0], Brighton: [50.823, -0.137, 0], Southampton: [50.909, -1.404, 0], Swansea: [51.621, -3.944, 0],
  Carlisle: [54.892, -2.934, 0], Dundee: [56.462, -2.971, 0], York: [53.959, -1.082, 0], Nottingham: [52.954, -1.158, 0], Exeter: [50.718, -3.534, 0],
  Oxford: [51.752, -1.258, 0], Cambridge: [52.205, 0.119, 0], Reading: [51.454, -0.978, 0], Windsor: [51.4839, -0.6044, 0], Slough: [51.511, -0.595, 0],
  Highlands: [57.15, -4.9, 0], Truro: [50.263, -5.051, 0], Leicester: [52.637, -1.135, 0],
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
const ANCHOR = { Glasgow: [0.92, 0], Edinburgh: [0.08, 0], Cardiff: [0.92, 0], Leeds: [0.15, 0], Manchester: [0.85, 0], Windsor: [0.5, 1.05], Slough: [0.5, -0.1], Reading: [0.9, 0] };
for (const [name, [lat, lon, major]] of Object.entries(TOWNS)) {
  const [x, z] = P(lon, lat);
  const g = new THREE.Group(); g.position.set(x, LAND_H + 0.012, z); scene.add(g);
  g.add(at(new THREE.Mesh(dotRing, ringMat), 0, 0, 0), at(new THREE.Mesh(dotGeo, dotMat), 0, 0.006, 0));
  const sp = labelSprite(name); sp.position.y = 0.08; g.add(sp);
  if (ANCHOR[name]) sp.center.set(...ANCHOR[name]);
  if (name === 'Highlands') g.children[0].visible = g.children[1].visible = false;
  TW[name] = { x, z, g, sp, major, pop: { k: major ? 1 : 0 } };
}
const camPos = new THREE.Vector3();
every(() => {
  camPos.set(camState.x, camState.y, camState.z);
  for (const T of Object.values(TW)) {
    const d = camPos.distanceTo(T.g.position), k = T.pop.k;
    const s = Math.min(d, 15) * 0.026 * (0.75 + 0.25 * k);
    T.sp.scale.set(s * 4 * Math.max(k, 0.001), s * Math.max(k, 0.001), 1);
    T.sp.material.opacity = Math.min(1, k * 1.5); T.sp.visible = k > 0.01;
    const ds = Math.min(1, Math.max(0.28, d / 14)); T.g.children[0].scale.setScalar(ds); T.g.children[1].scale.setScalar(ds);
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
const shadow = new THREE.Mesh(new THREE.CircleGeometry(0.22, 32), new THREE.MeshBasicMaterial({ map: TEX.soft, color: 0x000000, transparent: true, opacity: 0.45, depthWrite: false }));
shadow.rotation.x = -PI / 2; scene.add(shadow);
const ringFx = new THREE.Mesh(new THREE.RingGeometry(0.2, 0.25, 48), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
ringFx.rotation.x = -PI / 2; scene.add(ringFx);
// emoji sprites (3D, camera-facing)
function emojiSprite(ch, size = 0.5) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  g.font = `200px ${EMOJI}`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(ch, 128, 140);
  const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tx, transparent: true, depthWrite: false })); sp.scale.setScalar(size); return sp;
}
const crown = emojiSprite('👑', 0.62); crown.position.y = 0.92; pinBody.add(crown); crown.visible = false;

// ---------------------------------------------------------------- timeline anchors
const tSpin = L('s01', 1).start;
const tMan = L('s02', 0).start, tBri = L('s02', 1).start, tHig = L('s02', 2).start, tWin = L('s02', 3).start, tNah = L('s02', 4).start, tTwo = w('s02', 'two');
const tSlough = L('s03', 0).start, tBastard = L('s03', 1).start;
const tF1 = S('s04'), tQuote = L('s04', 1).start, tFair = L('s04', 2).start;
const tF2 = S('s05'), tSet = L('s05', 1).start;
const tF3 = S('s06'), tSweet = L('s06', 1).start;
const tF4 = S('s07'), tUranus = L('s07', 1).start;
const tCta = S('s08'), tComment = L('s08', 1).start, tFollow = w('s08', 'follow');
const tCrash = tTwo - 0.2;

const STOPS = [
  ['Birmingham', tSpin + 0.7, tMan - 0.6, 0],
  ['Manchester', tMan, L('s02', 0).end + 0.08, 1.0],
  ['Brighton', tBri, L('s02', 1).end + 0.08, 1.8],
  ['Highlands', tHig, L('s02', 2).end + 0.08, 2.6],
  ['Windsor', tWin, tTwo - 0.05, 2.4],
  ['Slough', tSlough, 1e9, 0.32],
];
const DROP_H = 9;
function pinState(t) {
  const b = TW.Birmingham;
  if (t < STOPS[0][1]) { const k = clamp01((t - (tSpin - 0.05)) / 0.75); return { x: b.x, z: b.z, y: DROP_H * (1 - k * k), air: 1, spin: 0, land: -1, hop: -1 }; }
  for (let i = 0; i < STOPS.length; i++) {
    const [name, t1, t2] = STOPS[i], T = TW[name];
    if (t >= t1 && t < t2) return { x: T.x, z: T.z, y: 0, air: 0, land: t - t1, i };
    const nx = STOPS[i + 1];
    if (nx && t >= t2 && t < nx[1]) {
      const N = TW[nx[0]], k = (t - t2) / (nx[1] - t2);
      return { x: lerp(T.x, N.x, k), z: lerp(T.z, N.z, k), y: 4 * nx[3] * k * (1 - k), air: 1, k, spin: k * PI * 2 * (nx[3] > 1 ? 2 : 1), land: -1, hop: i };
    }
  }
  const T = TW.Slough; return { x: T.x, z: T.z, y: 0, air: 0, land: t - tSlough, i: STOPS.length - 1 };
}
const PIN = { wilt: 0, crown: 0 };
every(t => {
  const s = pinState(t);
  const cd = Math.hypot(camState.x - s.x, camState.y - s.y, camState.z - s.z);
  const sc = Math.min(1.7, Math.max(0.5, cd / 8.5));
  const elev = Math.atan2(camState.y - s.y, Math.hypot(camState.x - s.x, camState.z - s.z));
  pin.position.set(s.x, LAND_H + s.y, s.z); pin.scale.setScalar(sc);
  let sy = 1, sxz = 1;
  if (s.land >= 0) { const q = s.land; const e = Math.exp(-q * 7) * Math.cos(q * 26); sy = 1 - 0.38 * e; sxz = 1 + 0.24 * e; }
  else if (s.air) { const v = Math.abs(1 - 2 * (s.k ?? 0.5)); sy = 1 + 0.18 * v; sxz = 1 - 0.1 * v; }
  pinBody.scale.set(sxz, sy, sxz);
  pinBody.rotation.set(0, s.air ? (s.spin || 0) : 0, 0);
  pin.rotation.set(0, 0, 0);
  pin.rotateOnWorldAxis(new THREE.Vector3(1, 0, 0), -0.85 * elev);
  if (PIN.wilt > 0) pin.rotateOnWorldAxis(new THREE.Vector3(0, 0, 1), -0.55 * PIN.wilt);
  shadow.position.set(s.x, LAND_H + 0.012, s.z); const hk = clamp01(s.y / 3);
  shadow.scale.setScalar(sc * (1 - 0.5 * hk)); shadow.material.opacity = 0.45 * (1 - 0.7 * hk) * (t > tSpin ? 1 : 0);
  pin.visible = t > tSpin - 0.05;
  if (s.land >= 0 && s.land < 0.55) { ringFx.position.set(s.x, LAND_H + 0.02, s.z); const k = s.land / 0.55; ringFx.scale.setScalar(sc * (1 + k * 3.4)); ringFx.material.opacity = 0.9 * (1 - k); } else ringFx.material.opacity = 0;
  crown.visible = PIN.crown > 0.01; crown.material.opacity = Math.min(1, PIN.crown * 2);
  crown.position.set(0, 0.92, 0); crown.scale.setScalar(0.62 * Math.max(0.001, PIN.crown));
  for (let i = 0; i < STOPS.length; i++) { const T = TW[STOPS[i][0]]; if (!T.major) T.pop.k = t >= STOPS[i][1] ? ss(STOPS[i][1], STOPS[i][1] + 0.2, t) : 0; }
});
STOPS.forEach(([, t1], i) => { if (i < STOPS.length - 1) sfx('boing', t1, i === 0 ? 0.8 : 0.55, { pitch: 1 + (i % 3) * 0.12 }); });

// flight trail: dotted arc behind the pin, plus the route drawn on the map as the pin's shadow passes
const TRAIL_N = 26, trailMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, depthWrite: false });
const trail = new THREE.InstancedMesh(new THREE.SphereGeometry(0.03, 10, 8), trailMat, TRAIL_N); trail.frustumCulled = false; scene.add(trail);
const ROUTE_N = 36, routeMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.85 });
const routes = STOPS.slice(0, -1).map(() => { const m = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.022, 0.022, 0.01, 10), routeMat, ROUTE_N); m.frustumCulled = false; scene.add(m); return m; });
const MM = new THREE.Matrix4(), QQ = new THREE.Quaternion(), V1 = new THREE.Vector3(), V2 = new THREE.Vector3();
const ROUTE = { show: 1 };
every(t => {
  const s = pinState(t), sc = Math.min(1.7, Math.max(0.5, Math.hypot(camState.x - s.x, camState.y - s.y, camState.z - s.z) / 8.5));
  // arc trail of the current (or just-finished) hop
  let hop = -1, kNow = 0;
  for (let i = 0; i < STOPS.length - 1; i++) { const t2 = STOPS[i][2], t3 = STOPS[i + 1][1]; if (t >= t2 && t < t3 + 0.5) { hop = i; kNow = clamp01((t - t2) / (t3 - t2)); } }
  for (let j = 0; j < TRAIL_N; j++) {
    let scl = 0;
    if (hop >= 0) {
      const A = TW[STOPS[hop][0]], B = TW[STOPS[hop + 1][0]], h = STOPS[hop + 1][3], kj = kNow * j / (TRAIL_N - 1);
      const fade = clamp01(1 - (t - STOPS[hop + 1][1]) / 0.5);
      V1.set(lerp(A.x, B.x, kj), LAND_H + 4 * h * kj * (1 - kj) + 0.4 * sc, lerp(A.z, B.z, kj));
      scl = sc * (0.5 + 0.5 * j / TRAIL_N) * Math.min(1, fade) * (kNow - kj < 0.6 ? 1 : 0.6);
    }
    MM.compose(V1, QQ, V2.setScalar(Math.max(scl, 0.0001))); trail.setMatrixAt(j, MM);
  }
  trail.instanceMatrix.needsUpdate = true;
  // dotted route on the map, revealed as the pin travels
  routes.forEach((m, i) => {
    const A = TW[STOPS[i][0]], B = TW[STOPS[i + 1][0]], t2 = STOPS[i][2], t3 = STOPS[i + 1][1], k = clamp01((t - t2) / (t3 - t2));
    for (let j = 0; j < ROUTE_N; j++) {
      const kj = (j + 0.5) / ROUTE_N, on = kj <= k ? 1 : 0;
      V1.set(lerp(A.x, B.x, kj), LAND_H + 0.02, lerp(A.z, B.z, kj));
      MM.compose(V1, QQ, V2.setScalar(Math.max(0.0001, on * ROUTE.show * Math.min(1.4, sc * 0.9)))); m.setMatrixAt(j, MM);
    }
    m.instanceMatrix.needsUpdate = true;
  });
});

// confetti bursts on every landing (red / white / blue)
const CONF_N = 48, conf = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.07, 0.035), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, toneMapped: false }), CONF_N);
conf.frustumCulled = false; scene.add(conf);
{ const cols = [0xe8202c, 0xffffff, 0x1d4ed8, 0xffe14d]; const cc = new THREE.Color(); for (let i = 0; i < CONF_N; i++) conf.setColorAt(i, cc.set(cols[i % 4])); }
const CR = mulberry32(17), CONF = Array.from({ length: CONF_N }, () => [(CR() - 0.5) * 2, 1.2 + CR() * 1.6, (CR() - 0.5) * 2, CR() * 6.28, 4 + CR() * 8]);
const E3 = new THREE.Euler();
every(t => {
  let L_ = -1; for (let i = 1; i < STOPS.length; i++) if (t >= STOPS[i][1] && t < STOPS[i][1] + 1.3) L_ = i;
  const T = L_ >= 0 ? TW[STOPS[L_][0]] : null, dt = L_ >= 0 ? t - STOPS[L_][1] : 0;
  const sc = Math.min(1.7, Math.max(0.5, Math.hypot(camState.x - (T ? T.x : 0), camState.y, camState.z - (T ? T.z : 0)) / 8.5));
  for (let i = 0; i < CONF_N; i++) {
    const c = CONF[i]; let s = 0;
    if (T && dt < 1.3) { s = sc * (1 - dt / 1.3); V1.set(T.x + c[0] * dt * 0.9 * sc, LAND_H + 0.3 * sc + (c[1] * dt - 2.6 * dt * dt) * sc, T.z + c[2] * dt * 0.9 * sc); E3.set(c[3] + dt * c[4], dt * c[4] * 0.7, 0); QQ.setFromEuler(E3); }
    MM.compose(V1, QQ, V2.setScalar(Math.max(s, 0.0001))); conf.setMatrixAt(i, MM);
  }
  conf.instanceMatrix.needsUpdate = true;
});

// ---------------------------------------------------------------- spin gags
// Manchester: a rain cloud (+ umbrella). Brighton: seagulls nicking chips. Highlands: a midge swarm. Windsor: a crown.
function rainCloud(T, s = 1) {
  const cloud = new THREE.Group(); cloud.position.set(T.x, LAND_H + 1.0 * s, T.z); scene.add(cloud);
  const cm = new THREE.MeshStandardMaterial({ color: 0x8d96a3, roughness: 0.9 });
  for (const [x, y, r] of [[0, 0, 0.24], [0.24, -0.04, 0.19], [-0.24, -0.05, 0.18], [0.1, 0.12, 0.17], [-0.12, 0.1, 0.15]]) cloud.add(at(new THREE.Mesh(new THREE.SphereGeometry(r, 24, 16), cm), x, y, 0));
  const drops = Array.from({ length: 14 }, (_, i) => { const d = new THREE.Mesh(new THREE.CapsuleGeometry(0.012, 0.07, 3, 6), new THREE.MeshBasicMaterial({ color: 0x9fd2ff })); cloud.add(d); return { d, x: ((i * 37) % 11) / 11 * 0.5 - 0.25, ph: (i * 0.137) % 1 }; });
  const CL = { k: 0, s };
  every(t => { const k = CL.k; cloud.visible = k > 0.01; cloud.scale.setScalar(Math.max(0.001, k) * CL.s); for (const r of drops) { const ph = (t * 1.6 + r.ph) % 1; r.d.position.set(r.x, -0.2 - ph * 1.0, 0.02); r.d.visible = ph < 0.92; } });
  return CL;
}
{ const CL = rainCloud(TW.Manchester, 1.6); tl.to(CL, { k: 1, duration: 0.35, ease: 'back.out(2)' }, tMan + 0.15); tl.to(CL, { k: 0, duration: 0.25 }, STOPS[1][2] - 0.05); }
const umbrella = emojiSprite('☔', 0.9); scene.add(umbrella); umbrella.visible = false;
every(t => { const T = TW.Manchester, k = ss(w('s02', 'brolly') - 0.1, w('s02', 'brolly') + 0.15, t) * (1 - ss(STOPS[1][2] - 0.1, STOPS[1][2] + 0.1, t)); umbrella.visible = k > 0.01; umbrella.position.set(T.x + 0.75, LAND_H + 0.9 + Math.sin(t * 6) * 0.05, T.z); umbrella.scale.setScalar(1.0 * backOut(k)); umbrella.material.rotation = Math.sin(t * 5) * 0.2; });
sfx('rain', tMan + 0.15, 0.5, { dur: STOPS[1][2] - tMan });
// seagulls
const gullMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6 }), gullDark = new THREE.MeshStandardMaterial({ color: 0x3a3f48, roughness: 0.6 });
const gulls = [0, 1, 2].map(i => {
  const g = new THREE.Group(); scene.add(g);
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.16, 4, 10), gullMat); body.rotation.z = PI / 2; g.add(body);
  const beak = new THREE.Mesh(new THREE.ConeGeometry(0.022, 0.07, 8), new THREE.MeshStandardMaterial({ color: 0xffb703 })); beak.rotation.z = -PI / 2; beak.position.x = 0.15; g.add(beak);
  const wings = [-1, 1].map(s => { const pv = new THREE.Group(); pv.position.z = s * 0.04; g.add(pv); const wg = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.012, 0.26), gullMat); wg.position.z = s * 0.13; pv.add(wg); const tip = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.014, 0.06), gullDark); tip.position.z = s * 0.25; pv.add(tip); pv.userData.s = s; return pv; });
  g.userData = { wings, ph: i * 2.1 }; g.visible = false; return g;
});
const chips = emojiSprite('🍟', 0.75); scene.add(chips); chips.visible = false;
every(t => {
  const T = TW.Brighton, on = t > tBri + 0.1 && t < STOPS[2][2] + 0.4;
  gulls.forEach((g, i) => {
    g.visible = on; if (!on) return;
    const a = t * 2.2 + g.userData.ph, r = 0.65 + 0.12 * Math.sin(t * 1.3 + i), dt = t - tBri;
    const away = clamp01((t - STOPS[2][2]) / 0.4);
    g.position.set(T.x + Math.cos(a) * r + away * 3, LAND_H + 0.9 + 0.12 * Math.sin(t * 3 + i) + away * 1.5, T.z + Math.sin(a) * r * 0.7);
    g.rotation.set(0, -a - PI / 2, 0); g.scale.setScalar(Math.min(1, dt * 4) * 2.2);
    for (const wv of g.userData.wings) wv.rotation.x = wv.userData.s * (0.2 + 0.7 * Math.sin(t * 16 + i));
  });
  // the chips get nicked by the first gull on "nick"
  const kn = clamp01((t - (w('s02', 'nick') - 0.05)) / 0.6), shown = t > tBri + 0.25 && t < STOPS[2][2] + 0.4;
  chips.visible = shown;
  if (shown) { const g0 = gulls[0]; const base = new THREE.Vector3(T.x + 0.45, LAND_H + 0.35, T.z + 0.15); chips.position.copy(base).lerp(V1.set(g0.position.x, g0.position.y - 0.12, g0.position.z), kn); chips.scale.setScalar(0.75 * backOut(clamp01((t - tBri - 0.25) / 0.3))); }
});
sfx('squawk', tBri + 0.2, 0.6); sfx('squawk', w('s02', 'nick'), 0.7, { pitch: 1.15 });
// midges
const MIDGE_N = 70, midgeGeo = new THREE.BufferGeometry(), midgePos = new Float32Array(MIDGE_N * 3);
midgeGeo.setAttribute('position', new THREE.BufferAttribute(midgePos, 3));
const midges = new THREE.Points(midgeGeo, new THREE.PointsMaterial({ color: 0x111111, size: 0.05, sizeAttenuation: true })); midges.frustumCulled = false; scene.add(midges);
const MR = mulberry32(31), MID = Array.from({ length: MIDGE_N }, () => [MR() * 6.28, MR() * 6.28, 0.15 + MR() * 0.5, 2 + MR() * 5, MR()]);
every(t => {
  const T = TW.Highlands, k = ss(tHig + 0.1, tHig + 0.4, t) * (1 - ss(STOPS[3][2] - 0.1, STOPS[3][2] + 0.1, t)); midges.visible = k > 0.01;
  if (!midges.visible) return;
  const tight = 1 - 0.55 * ss(w('s02', 'eat') - 0.1, w('s02', 'alive'), t);
  MID.forEach((m, i) => { const a = m[0] + t * m[3], b = m[1] + t * m[3] * 0.7, r = m[2] * tight * 1.6; midgePos.set([T.x + Math.cos(a) * r, LAND_H + 0.45 + Math.sin(b) * r * 0.6 + 0.2, T.z + Math.sin(a) * r * 0.8], i * 3); });
  midgeGeo.attributes.position.needsUpdate = true; midges.material.size = 0.05 * (0.6 + 0.4 * k) * Math.max(1, camState.y / 9);
});
sfx('buzz', tHig + 0.15, 0.5); sfx('buzz', tHig + 0.75, 0.5); sfx('buzz', w('s02', 'eat'), 0.6);
// Windsor: crown on, "Nah" — crown off
tl.fromTo(PIN, { crown: 0 }, { crown: 1, duration: 0.3, ease: 'back.out(3)', immediateRender: false }, tWin + 0.2);
tl.to(PIN, { crown: 0, duration: 0.25 }, tNah + 0.05);
sfx('shimmer', tWin + 0.2, 0.6); sfx('fanfare', w('s02', 'royalty') - 0.05, 0.7); sfx('scratch', tNah, 0.8);

// ---------------------------------------------------------------- HUD (camera space: x ±0.432, y ±0.768 at z = -2, fov 42)
const hud = new THREE.Group(); hud.position.z = -2; camera.add(hud);
const HPX = 1250;
function hp(o) { const p = panelMesh(hud, Object.assign({ ppu: HPX, boost: 0.98 }, o)); p.mesh.renderOrder = 10; p.mat.depthTest = false; p.base = { x: o.x || 0, y: o.y || 0 }; return p; }
function popIn(p, t0, t1 = 1e9, ease = 'back.out(2)') {
  p.mesh.visible = false; p.mesh.scale.setScalar(0.0001);
  tl.set(p.mesh, { visible: true }, t0); tl.fromTo(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001 }, { x: 1, y: 1, z: 1, duration: 0.35, ease, immediateRender: false }, t0);
  if (t1 < 1e8) { tl.to(p.mesh.scale, { x: 0.0001, y: 0.0001, z: 0.0001, duration: 0.18, ease: 'power2.in' }, t1 - 0.18); tl.set(p.mesh, { visible: false }, t1); }
  return p;
}
// spring in from the right, whip out to the left
function slideIn(p, t0, t1 = 1e9) {
  const bx = p.base.x; p.mesh.visible = false;
  tl.set(p.mesh, { visible: true }, t0);
  tl.fromTo(p.mesh.position, { x: bx + 0.95 }, { x: bx, duration: 0.55, ease: 'elastic.out(1, 0.7)', immediateRender: false }, t0);
  tl.fromTo(p.mesh.rotation, { z: -0.18 }, { z: 0, duration: 0.6, ease: 'elastic.out(1, 0.5)', immediateRender: false }, t0);
  if (t1 < 1e8) { tl.to(p.mesh.position, { x: bx - 1.0, duration: 0.22, ease: 'power3.in' }, t1 - 0.22); tl.to(p.mesh.rotation, { z: 0.15, duration: 0.22, ease: 'power3.in' }, t1 - 0.22); tl.set(p.mesh, { visible: false }, t1); }
  sfx('whoosh', t0, 0.35);
  return p;
}
function sticker(ch, x, y, size, t0, t1 = 1e9, rot = 0.15) {
  const p = hp({ w: size, h: size, x, y, draw: (c, _t, P) => { c.font = `${P.ch * 0.8}px ${EMOJI}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(ch, P.cw / 2, P.ch * 0.55); } });
  popIn(p, t0, t1, 'back.out(3)');
  every(t => { if (p.mesh.visible) p.mesh.rotation.z = rot * Math.sin((t - t0) * 5) * Math.exp(-(t - t0) * 0.6) + rot * 0.3; });
  sfx('pop', t0, 0.4, { pitch: 1.2 });
  return p;
}
const card = (c, P, fill = '#ffffff', stroke = '#0b1d36', r = 44, lw = 12) => { c.fillStyle = fill; rrect(c, lw, lw, P.cw - lw * 2, P.ch - lw * 2, r); c.fill(); c.lineWidth = lw; c.strokeStyle = stroke; c.stroke(); };
function stampDraw(c, P, txt, color = '#C8102E', size = 96) { c.strokeStyle = color; c.lineWidth = 16; rrect(c, 18, 18, P.cw - 36, P.ch - 36, 26); c.stroke(); text(c, txt, P.cw / 2, P.ch / 2 + 6, { size, weight: 900, color, font: 'Inter Display', spacing: 6 }); }
function stamp(txt, x, y, wd, hg, t0, t1, rz = -0.1, color = '#C8102E', size = 96) { const p = hp({ w: wd, h: hg, x, y, rz, draw: (c, _t, P) => stampDraw(c, P, txt, color, size) }); popIn(p, t0, t1, 'back.out(4)'); sfx('stamp', t0, 0.8); shake(t0, 0.25, 0.25); return p; }
function unionFlag(c, x, y, w_, h) {
  c.save(); c.beginPath(); c.rect(x, y, w_, h); c.clip();
  c.fillStyle = '#012169'; c.fillRect(x, y, w_, h);
  const diag = (lw, col) => { c.strokeStyle = col; c.lineWidth = lw; c.beginPath(); c.moveTo(x, y); c.lineTo(x + w_, y + h); c.moveTo(x + w_, y); c.lineTo(x, y + h); c.stroke(); };
  diag(h * 0.2, '#ffffff'); diag(h * 0.07, '#C8102E');
  c.fillStyle = '#ffffff'; c.fillRect(x + w_ / 2 - h * 0.17, y, h * 0.34, h); c.fillRect(x, y + h * 0.33, w_, h * 0.34);
  c.fillStyle = '#C8102E'; c.fillRect(x + w_ / 2 - h * 0.1, y, h * 0.2, h); c.fillRect(x, y + h * 0.4, w_, h * 0.2);
  c.restore();
}
every(t => { window.__t = t; });

// title: big for the hook, then shrinks into a top bar when the spin starts
const title = hp({ w: 0.8, h: 0.26, x: 0, y: 0.5, draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36');
  unionFlag(c, 46, 54, 150, 100);
  text(c, 'WHERE WILL', P.cw / 2 + 70, 92, { size: 74, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 1 });
  text(c, 'YOU BE BORN?', P.cw / 2 + 70, 172, { size: 92, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 1 });
  text(c, 'UK EDITION  •  PART 2', P.cw / 2, P.ch - 58, { size: 34, weight: 800, color: '#5b6b80', spacing: 8 });
} });
every(t => {
  const k0 = backOut(clamp01(t / 0.3)), k1 = ss(tSpin - 0.1, tSpin + 0.35, t), out = ss(tSlough - 0.2, tSlough, t);
  title.mesh.visible = out < 0.99;
  title.mesh.scale.setScalar(Math.max(0.0001, (0.85 + 0.15 * k0) * lerp(1, 0.62, k1) * (1 - out)));
  title.mesh.position.set(0, lerp(0.5, 0.66, k1) + Math.sin(t * 2.2) * 0.004 * (1 - k1), 0);
  title.mesh.rotation.z = (1 - k1) * Math.sin(t * 1.7) * 0.012;
});
// slot-machine reel: town names whizz past, slowing, then lock on SLOUGH
const REEL = ['LONDON', 'LEEDS', 'MANCHESTER', 'BRIGHTON', 'GLASGOW', 'CARDIFF', 'NORWICH', 'BELFAST', 'HULL', 'WINDSOR', 'DERBY', 'BATH', 'YORK', 'SWINDON', 'PLYMOUTH', 'LUTON', 'SLOUGH'];
const reel = hp({ w: 0.56, h: 0.085, x: 0, y: 0.555, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t;
  c.fillStyle = '#0b1d36'; rrect(c, 6, 6, P.cw - 12, P.ch - 12, 26); c.fill(); c.strokeStyle = '#FFE14D'; c.lineWidth = 8; c.stroke();
  c.save(); rrect(c, 14, 14, P.cw - 28, P.ch - 28, 20); c.clip();
  // position along the reel: fast during the spin, easing to a stop on SLOUGH at the landing
  const t0 = tSpin, t1 = tSlough, u = clamp01((t - t0) / (t1 - t0)), pos = (1 - Math.pow(1 - u, 3)) * (REEL.length * 3 - 1);
  const idx = Math.floor(pos), frac = pos - idx, rowH = P.ch * 0.8;
  for (let d = -1; d <= 1; d++) {
    const name = REEL[((idx + d) % REEL.length + REEL.length) % REEL.length], y = P.ch / 2 + (d - frac) * rowH;
    const locked = u >= 1, isS = locked && d === 0;
    text(c, locked && d === 0 ? 'SLOUGH' : name, P.cw / 2, y + 4, { size: 58, weight: 900, color: isS ? '#FFE14D' : '#ffffff', font: 'Inter Display', spacing: 6 });
  }
  c.restore();
  text(c, '▶', 44, P.ch / 2 + 2, { size: 40, weight: 900, color: '#FFE14D' }); text(c, '◀', P.cw - 44, P.ch / 2 + 2, { size: 40, weight: 900, color: '#FFE14D' });
} });
popIn(reel, tSpin + 0.1, tSlough + 0.9);
for (let i = 0; i < 26; i++) { const u = i / 26, tt = tSpin + (tSlough - tSpin) * (1 - Math.cbrt(1 - u)); sfx('tick', tt, 0.25); }

// SLOUGH reveal: letters drop in one by one
const banner = hp({ w: 0.82, h: 0.24, x: 0, y: 0.5, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t, t0 = tSlough + 0.02;
  card(c, P, '#C8102E', '#ffffff', 40, 14);
  const word = 'SLOUGH', lw = 128;
  for (let i = 0; i < word.length; i++) {
    const k = clamp01((t - t0 - i * 0.06) / 0.35), e = elastic(k);
    if (k <= 0) continue;
    c.save(); c.translate(P.cw / 2 + (i - (word.length - 1) / 2) * lw, P.ch / 2 - 16 - (1 - e) * 120); c.rotate((1 - e) * 0.5 * (i % 2 ? 1 : -1));
    text(c, word[i], 0, 0, { size: 150, weight: 900, color: '#ffffff', font: 'Inter Display' }); c.restore();
  }
  const k2 = clamp01((t - t0 - 0.45) / 0.3);
  if (k2 > 0) { c.globalAlpha = k2; text(c, 'BERKSHIRE  •  ENGLAND', P.cw / 2 + (1 - k2) * 80, P.ch / 2 + 82, { size: 36, weight: 800, color: 'rgba(255,255,255,.88)', spacing: 10 }); c.globalAlpha = 1; }
} });
popIn(banner, tSlough, tF1 + 0.05, 'back.out(3)');
sticker('💀', 0.3, 0.33, 0.18, tBastard + 0.05, tF1, 0.3);

// speed lines for the crash zoom
const speed = hp({ w: 0.864, h: 1.536, x: 0, y: 0, boost: 1, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t, k = clamp01(1 - Math.abs(t - (tCrash + 0.2)) / 0.35); if (k <= 0) return;
  const R = mulberry32(Math.floor(t * 30)); c.strokeStyle = `rgba(255,255,255,${0.75 * k})`; c.lineCap = 'round';
  for (let i = 0; i < 60; i++) { const a = R() * PI * 2, r0 = 300 + R() * 250, r1 = r0 + 300 + R() * 500; c.lineWidth = 4 + R() * 8; c.beginPath(); c.moveTo(P.cw / 2 + Math.cos(a) * r0, P.ch / 2 + Math.sin(a) * r0); c.lineTo(P.cw / 2 + Math.cos(a) * r1, P.ch / 2 + Math.sin(a) * r1); c.stroke(); }
} });
speed.mesh.visible = false; tl.set(speed.mesh, { visible: true }, tCrash - 0.2); tl.set(speed.mesh, { visible: false }, tCrash + 0.6);

// fact chip
function chip(n, t0, t1) {
  const p = hp({ w: 0.3, h: 0.09, x: -0.25, y: 0.68, draw: (c, _t, P) => { card(c, P, '#FFE14D', '#0b1d36', 50, 10); text(c, `FACT ${n}`, P.cw / 2, P.ch / 2 + 4, { size: 66, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 3 }); } });
  slideIn(p, t0, t1); return p;
}

// ---- FACT 1: Betjeman, "Come, friendly bombs" (the quote types out with the narration)
chip(1, tF1, tF2);
const poet = hp({ w: 0.8, h: 0.3, x: 0, y: 0.43, draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36', 40, 12);
  c.font = `150px ${EMOJI}`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('🪶', 150, P.ch / 2 + 6);
  text(c, 'A FAMOUS POET', 300, 140, { size: 68, weight: 900, color: '#0b1d36', font: 'Inter Display', align: 'left', spacing: 2 });
  text(c, 'begged for Slough', 300, 230, { size: 62, weight: 800, color: '#5b6b80', align: 'left' });
  text(c, 'to be BOMBED', 300, 310, { size: 62, weight: 900, color: '#C8102E', align: 'left' });
} });
slideIn(poet, tF1 + 0.1, tQuote);
const QW = ['Come,', 'friendly', 'bombs,', 'and', 'fall', 'on', 'Slough!'];
const quoteWordTimes = ['come', 'friendly', 'bombs', 'and', 'fall', 'on', 'slough'].map(x => w('s04', x, x === 'slough' ? 1 : 0));
const scroll = hp({ w: 0.82, h: 0.5, x: 0, y: 0.36, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t;
  c.fillStyle = '#f3e3bf'; rrect(c, 30, 40, P.cw - 60, P.ch - 80, 20); c.fill(); c.strokeStyle = '#8a6d3b'; c.lineWidth = 8; c.stroke();
  c.fillStyle = '#e2cb98'; for (const y of [26, P.ch - 26]) { rrect(c, 10, y - 26, P.cw - 20, 52, 26); c.fill(); }
  c.font = 'italic 700 74px Georgia, serif'; c.fillStyle = '#3d2b12'; c.textBaseline = 'middle'; c.textAlign = 'left';
  const lines = [[0, 1, 2], [3, 4, 5, 6]]; let wi = 0;
  lines.forEach((ln, li) => { let x = 80; const y = 170 + li * 110; for (const i of ln) { const k = clamp01((t - quoteWordTimes[i] + 0.05) / 0.15); c.globalAlpha = k; c.fillText(QW[i], x, y + (1 - k) * 20); x += c.measureText(QW[i] + ' ').width; wi++; } });
  c.globalAlpha = 1;
  if (t > w('s04', 'john') - 0.1) { text(c, '— John Betjeman, 1937', P.cw - 80, P.ch - 110, { size: 46, weight: 700, color: '#6b5226', align: 'right', font: 'Inter' }); }
} });
slideIn(scroll, tQuote, tF2);
['💣', '💣', '💣'].forEach((ch, i) => sticker(ch, [-0.33, 0.33, 0.0][i], [0.62, 0.6, 0.66][i], 0.13, w('s04', 'bombs') + 0.05 + i * 0.12, tFair, 0.4));
stamp('FAIR.', 0.12, 0.17, 0.4, 0.14, w('s04', 'fair') - 0.03, tF2, -0.12, '#C8102E', 120);
sticker('🤷', -0.27, 0.13, 0.17, w('s04', 'fair') + 0.1, tF2);

// ---- FACT 2: The Office was set here (a CRT telly showing a grey office)
chip(2, tF2, tF3);
const tv = hp({ w: 0.78, h: 0.54, x: 0, y: 0.38, key: t => Math.floor(t * 15), draw: (c, _t, P) => {
  const t = window.__t;
  c.fillStyle = '#2b2f36'; rrect(c, 20, 20, P.cw - 40, P.ch - 90, 50); c.fill(); c.fillStyle = '#16181d'; c.fillRect(P.cw / 2 - 120, P.ch - 80, 240, 50);
  const sx = 70, sy = 70, sw = P.cw - 260, sh = P.ch - 190;
  c.save(); rrect(c, sx, sy, sw, sh, 30); c.clip();
  c.fillStyle = '#b9bfb3'; c.fillRect(sx, sy, sw, sh); c.fillStyle = '#9aa197'; c.fillRect(sx, sy + sh * 0.62, sw, sh * 0.38);
  // ceiling tiles + fluorescent strips
  c.strokeStyle = 'rgba(0,0,0,.12)'; c.lineWidth = 3; for (let x = sx; x < sx + sw; x += 70) { c.beginPath(); c.moveTo(x, sy); c.lineTo(x, sy + 90); c.stroke(); }
  c.fillStyle = '#f4f7ec'; c.fillRect(sx + 80, sy + 30, 160, 16); c.fillRect(sx + 380, sy + 30, 160, 16);
  // desks + a slumped worker
  c.fillStyle = '#6f6a60'; for (const dx of [60, 380]) c.fillRect(sx + dx, sy + sh * 0.55, 220, 26);
  c.fillStyle = '#2b2f36'; c.fillRect(sx + 120, sy + sh * 0.38, 100, 70); c.fillRect(sx + 440, sy + sh * 0.38, 100, 70);
  c.strokeStyle = '#ffffff'; c.lineWidth = 16; c.lineCap = 'round'; const bob = Math.sin(t * 2) * 4;
  c.beginPath(); c.arc(sx + 300, sy + sh * 0.3 + bob + 40, 28, 0, PI * 2); c.fillStyle = '#ffffff'; c.fill(); c.beginPath(); c.moveTo(sx + 300, sy + sh * 0.3 + 74 + bob); c.lineTo(sx + 300, sy + sh * 0.55); c.stroke();
  c.fillStyle = '#ffffff'; rrect(c, sx + sw - 250, sy + 110, 220, 64, 10); c.fill(); text(c, 'SLOUGH', sx + sw - 140, sy + 143, { size: 40, weight: 900, color: '#0b1d36', spacing: 6 });
  c.fillStyle = 'rgba(0,0,0,.08)'; for (let y = sy; y < sy + sh; y += 6) c.fillRect(sx, y + (Math.floor(t * 15) % 2) * 3, sw, 2);
  c.restore();
  for (const [kx, ky] of [[P.cw - 120, 160], [P.cw - 120, 280]]) { c.fillStyle = '#16181d'; c.beginPath(); c.arc(kx, ky, 34, 0, PI * 2); c.fill(); }
  c.fillStyle = '#FFE14D'; rrect(c, 40, P.ch - 150, 440, 64, 18); c.fill(); text(c, 'THE OFFICE  •  2001', 260, P.ch - 117, { size: 40, weight: 900, color: '#0b1d36', spacing: 3 });
} });
slideIn(tv, tF2 + 0.1, tF3);
sticker('😐', 0.3, 0.15, 0.16, w('s05', 'souldestroying') - 0.05, tF3);
stamp('NO SET NEEDED', 0, 0.62, 0.7, 0.12, w('s05', 'set', 1) - 0.03, tF3, 0.06, '#C8102E', 82);

// ---- FACT 3: the Mars bar was first made here, 1932
chip(3, tF3, tF4);
const bar = hp({ w: 0.8, h: 0.46, x: 0, y: 0.38, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t, k = clamp01((t - (tF3 + 0.5)) / 0.8), slide = 1 - Math.pow(1 - k, 3);
  card(c, P, '#ffffff', '#0b1d36', 40, 12);
  const yr = Math.round(lerp(1900, 1932, clamp01((t - w('s06', 'nineteen') + 0.1) / 0.6)));
  text(c, t > w('s06', 'nineteen') - 0.1 ? String(yr) : '', P.cw / 2, 110, { size: 120, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 4 });
  // chocolate bar sliding out of its wrapper
  const bx = 120, by = 220, bw = P.cw - 240, bh = 170;
  c.save(); c.translate(slide * 130, 0);
  c.fillStyle = '#5a3a22'; rrect(c, bx, by, bw, bh, 30); c.fill(); c.fillStyle = '#6e472a'; for (let i = 0; i < 5; i++) { rrect(c, bx + 20 + i * (bw - 40) / 5, by + 20, (bw - 40) / 5 - 16, bh - 40, 14); c.fill(); }
  c.restore();
  c.fillStyle = '#1a1a1a'; rrect(c, bx - 20, by - 16, bw * 0.62, bh + 32, 22); c.fill(); c.fillStyle = '#C8102E'; c.fillRect(bx - 20, by + bh / 2 - 26, bw * 0.62, 52);
  text(c, 'MADE IN SLOUGH', bx - 20 + bw * 0.31, by + bh / 2 + 2, { size: 40, weight: 900, color: '#ffffff', spacing: 4 });
  text(c, 'THE MARS BAR', P.cw / 2, P.ch - 80, { size: 56, weight: 900, color: '#0b1d36', font: 'Inter Display', spacing: 6 });
} });
slideIn(bar, tF3 + 0.1, tF4);
sticker('🍫', 0.31, 0.63, 0.16, w('s06', 'mars') - 0.05, tF4);
stamp('ONLY SWEET THING', 0, 0.12, 0.72, 0.11, w('s06', 'sweet') - 0.03, tF4, -0.06, '#C8102E', 74);

// ---- FACT 4: Uranus × Slough (Herschel lived here)
chip(4, tF4, tCta);
const space = hp({ w: 0.8, h: 0.52, x: 0, y: 0.37, key: t => Math.floor(t * 30), draw: (c, _t, P) => {
  const t = window.__t;
  card(c, P, '#0a1230', '#ffffff', 40, 12);
  const R = mulberry32(5); for (let i = 0; i < 70; i++) { const tw = 0.5 + 0.5 * Math.sin(t * 3 + i); c.fillStyle = `rgba(255,255,255,${0.3 + 0.6 * tw})`; c.beginPath(); c.arc(30 + R() * (P.cw - 60), 30 + R() * (P.ch - 60), 2 + R() * 3, 0, PI * 2); c.fill(); }
  // Uranus: pale blue ball with a tilted ring, wobbling
  const cx = P.cw * 0.7, cy = P.ch * 0.56, r = 125, wob = Math.sin(t * 2) * 0.05;
  c.save(); c.translate(cx, cy); c.rotate(1.2 + wob);
  c.strokeStyle = 'rgba(200,240,255,.8)'; c.lineWidth = 10; c.beginPath(); c.ellipse(0, 0, r * 1.55, r * 0.35, 0, PI, PI * 2); c.stroke();
  const g = c.createRadialGradient(-50, -50, 20, 0, 0, r); g.addColorStop(0, '#d9fbff'); g.addColorStop(1, '#5fc6d6'); c.fillStyle = g; c.beginPath(); c.arc(0, 0, r, 0, PI * 2); c.fill();
  c.beginPath(); c.ellipse(0, 0, r * 1.55, r * 0.35, 0, 0, PI); c.stroke(); c.restore();
  // telescope
  c.save(); c.translate(150, P.ch - 120); c.rotate(-0.7); c.fillStyle = '#c9b27c'; rrect(c, -20, -30, 260, 60, 20); c.fill(); c.fillStyle = '#8a6d3b'; c.fillRect(220, -36, 30, 72); c.restore();
  c.strokeStyle = '#c9b27c'; c.lineWidth = 10; c.beginPath(); c.moveTo(150, P.ch - 120); c.lineTo(110, P.ch - 40); c.moveTo(150, P.ch - 120); c.lineTo(200, P.ch - 40); c.stroke();
  text(c, 'URANUS', 60, 90, { size: 74, weight: 900, color: '#ffffff', font: 'Inter Display', align: 'left', spacing: 4 });
  text(c, 'found by a bloke', 60, 158, { size: 40, weight: 800, color: '#9bd3ff', align: 'left' });
  text(c, 'from SLOUGH', 60, 208, { size: 40, weight: 900, color: '#FFE14D', align: 'left' });
} });
slideIn(space, tF4 + 0.1, tCta);
sticker('🔭', -0.3, 0.12, 0.15, w('s07', 'discovered') - 0.05, tCta);
stamp('CHECKS OUT', 0.05, 0.12, 0.56, 0.12, w('s07', 'sense') - 0.05, tCta, 0.08, '#2ea043', 86);
sticker('🤣', 0.3, 0.64, 0.17, w('s07', 'perfect') - 0.05, tCta, 0.3);

// ---- CTA
const born = hp({ w: 0.8, h: 0.3, x: 0, y: 0.45, draw: (c, _t, P) => {
  card(c, P, '#ffffff', '#0b1d36', 40, 12);
  text(c, 'BORN IN', P.cw / 2, 100, { size: 60, weight: 800, color: '#5b6b80', spacing: 10 });
  text(c, 'SLOUGH', P.cw / 2, 220, { size: 150, weight: 900, color: '#C8102E', font: 'Inter Display', spacing: 6 });
} });
slideIn(born, tCta + 0.05, tComment);
stamp('UNLUCKY, MATE', 0, 0.24, 0.66, 0.11, w('s08', 'unlucky') - 0.03, tComment, -0.07, '#0b1d36', 74);
const q1 = hp({ w: 0.82, h: 0.18, x: 0, y: 0.5, draw: (c, _t, P) => { card(c, P, '#ffffff', '#0b1d36'); text(c, 'COMMENT YOUR TOWN', P.cw / 2, P.ch / 2 - 22, { size: 70, weight: 900, color: '#0b1d36', font: 'Inter Display' }); text(c, 'I\'LL ROAST IT NEXT', P.cw / 2, P.ch / 2 + 56, { size: 46, weight: 900, color: '#C8102E', spacing: 6 }); } });
slideIn(q1, tComment);
sticker('👇', 0.3, 0.33, 0.15, w('s08', 'town') - 0.05);
sticker('🔥', -0.3, 0.33, 0.15, w('s08', 'roast') - 0.05);
const fb = hp({ w: 0.6, h: 0.1, x: 0, y: -0.52, key: t => (t > tFollow + 0.5 ? 'on' : 'off'), draw: (c, _t, P) => {
  const on = window.__t > tFollow + 0.5; c.save(); c.beginPath(); c.roundRect(8, 8, P.cw - 16, P.ch - 16, (P.ch - 16) / 2); c.fillStyle = on ? '#0b1d36' : '#FFE14D'; c.fill(); c.lineWidth = 8; c.strokeStyle = '#0b1d36'; c.stroke(); c.restore();
  text(c, on ? '✓  FOLLOWING' : '+  FOLLOW FOR PART 3', P.cw / 2, P.ch / 2 + 3, { size: 56, weight: 900, color: on ? '#ffffff' : '#0b1d36', spacing: 3 });
} });
popIn(fb, tFollow - 0.1); sfx('click', tFollow + 0.5, 0.7);

// ---------------------------------------------------------------- landing beats
sfx('drumroll', tTwo - 0.1, 0.6, { dur: tSlough - tTwo + 0.1 });
sfx('trombone', tSlough + 0.3, 0.8);
zoomBlur(tSlough, 0.6, 0.35); shake(tSlough, 0.5, 0.4); sfx('thunk', tSlough, 0.7); flash(tSlough, 0.25, 0.2);
tl.to(PIN, { wilt: 1, duration: 0.7, ease: 'power2.inOut' }, tBastard);
tl.to(PIN, { wilt: 0, duration: 0.4 }, tF1);
{ const CL = rainCloud(TW.Slough, 1); tl.to(CL, { k: 1, duration: 0.4, ease: 'back.out(2)' }, tBastard + 0.15); tl.to(CL, { k: 0, duration: 0.3 }, tCta + 0.1); }
tl.to(ROUTE, { show: 0, duration: 0.4 }, tF1);
// fact transitions: whip
[tF2, tF3, tF4, tCta].forEach(t => { zoomBlur(t - 0.05, 0.45, 0.3); });

// ---------------------------------------------------------------- camera
const FOV = 42, OV = { x: -0.25, y: 15.2, z: 4.6, tx: -0.25, ty: 0, tz: -0.95 };
const sx = TW.Slough.x, sz = (TW.Slough.z + TW.Windsor.z) / 2;
camSet(0, Object.assign({ roll: 0, fov: FOV }, OV));
// procedural follow camera during the spin: leans 30% toward the pin, punches in on every landing, slight roll
every(t => {
  if (t < tSpin - 0.2 || t >= tCrash) return;
  const s = pinState(t), f = 0.3 * ss(tSpin - 0.2, tSpin + 0.5, t);
  const dx = (s.x - OV.tx) * f, dz = (s.z - OV.tz) * f;
  let punch = 0; for (let i = 1; i < STOPS.length - 1; i++) { const d = t - STOPS[i][1]; if (d >= 0 && d < 0.7) punch = Math.max(punch, Math.sin(PI * d / 0.7) * Math.exp(-d * 1.5)); }
  const z = 1 - 0.16 * punch;
  camState.tx = OV.tx + dx; camState.ty = 0; camState.tz = OV.tz + dz;
  camState.x = camState.tx + (OV.x - OV.tx) * z; camState.y = OV.y * z; camState.z = camState.tz + (OV.z - OV.tz) * z;
  camState.roll = Math.sin(t * 0.9) * 1.2 + (s.air ? Math.sin((s.k || 0) * PI) * 2.5 * Math.sign(Math.sin(t)) : 0); camState.fov = FOV;
});
// crash zoom onto Windsor/Slough for the "two miles up the road" hop
camSet(tCrash, { x: -0.25, y: 15.2, z: 4.6, tx: -0.25, ty: 0, tz: -0.95, roll: 0, fov: FOV });
camTo(tCrash, { x: sx + 0.12, y: 2.4, z: sz + 1.9, tx: sx, ty: 0.15, tz: sz - 0.05 }, 0.6, 'power4.inOut');
sfx('whoosh', tCrash, 0.6); flash(tCrash + 0.45, 0.2, 0.2);
camTo(tSlough - 0.05, { y: 2.9, z: sz + 2.4 }, tF1 - tSlough + 0.05, 'power2.out');
camTo(tF1, { x: sx - 0.6, y: 3.6, z: sz + 2.8, tx: sx, tz: sz - 0.1 }, tF3 - tF1, 'sine.inOut');
camTo(tF3, { x: sx + 0.7, y: 3.4, z: sz + 2.6 }, tCta - tF3, 'sine.inOut');
camTo(tCta, { x: -0.25, y: 15.2, z: 4.6, tx: -0.25, ty: 0, tz: -0.95 }, 1.2, 'power3.inOut');
sfx('whoosh', tCta, 0.4);

// ---------------------------------------------------------------- music
music(0, 0.85); music(tCrash, 0.4); music(tSlough, 0.0); music(tF1 + 0.2, 0.75); music(DUR - 1.0, 0.75); music(DUR, 0);
tl.set({}, {}, DUR);

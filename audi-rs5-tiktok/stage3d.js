// The 3D stage for a film: the cars from cars.js on turntables in a dark studio.
// film.html calls R3D.render(spec) with a shot description and composites the
// returned canvas. This file and car3d.js are shared, unchanged, between the films;
// each film's cars.js exports CARS = { id: { spec, color } }.
import * as THREE from 'three';
import { buildCar, makeStudio, placeCar } from './car3d.js';
import { CARS } from './cars.js';

const W = window.FRAME_W || 1920, H = window.FRAME_H || 1080;   // a film can set FRAME_W/H (e.g. 1080 x 1920 for vertical)
const canvas = document.createElement('canvas');
canvas.width = W; canvas.height = H;
const st = makeStudio(canvas, W, H);
const SPEC = Object.fromEntries(Object.entries(CARS).map(([id, c]) => [id, c.spec]));
const COL = Object.fromEntries(Object.entries(CARS).map(([id, c]) => [id, c.color]));

// turntable: dark glossy disc with a glowing rim in the car's colour
function turntable(r, col) {
  const g = new THREE.Group();
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.02, 96), new THREE.MeshPhysicalMaterial({ color: 0x07080b, roughness: 0.35, metalness: 0.2, clearcoat: 0.6, transparent: true, opacity: 0.85, envMapIntensity: 0.35 }));
  disc.position.y = 0.006; disc.receiveShadow = true; g.add(disc);
  const ring = new THREE.Mesh(new THREE.RingGeometry(r - 0.035, r + 0.02, 128), new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(2.2), side: THREE.DoubleSide, toneMapped: false }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.018; g.add(ring);
  const ticks = new THREE.Group();
  for (let i = 0; i < 72; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.012, i % 6 ? 0.08 : 0.18), new THREE.MeshBasicMaterial({ color: 0x8a96a8, transparent: true, opacity: 0.55 }));
    const a = i / 72 * Math.PI * 2;
    m.rotation.x = -Math.PI / 2; m.rotation.z = -a; m.position.set(Math.cos(a) * (r - 0.18), 0.019, Math.sin(a) * (r - 0.18)); ticks.add(m);
  }
  g.add(ticks);
  return { g, ring };
}

const actors = {};
for (const id of Object.keys(SPEC)) {
  const car = buildCar(SPEC[id]);
  const placed = placeCar(st, car);
  // lit decals (lights, glowing grilles), in the car and its floor reflection, so shots can switch them on
  const glowMats = [];
  for (const o of [car, placed.refl]) o.traverse(m => { if (m.isMesh) for (const mt of [].concat(m.material)) if (mt.emissiveMap) glowMats.push(mt); });
  // wheel indices, so the floor reflection's wheels can copy the real ones
  const wheelIdx = car.userData.wheels.map(w => car.children.indexOf(w));
  const tt = turntable(3.0, COL[id]);
  placed.root.add(tt.g);
  placed.shadow.position.y = 0.022;
  actors[id] = { ...placed, wheelIdx, tt, glowMats };
}
// night road for the driving shots: asphalt with markings that scroll under the cars,
// gravel verges, lamp posts and marker posts flying past
function makeRoad() {
  const g = new THREE.Group(), TILE = 16, WIDE = 60, LONG = 400;
  const c = document.createElement('canvas'); c.width = 1024; c.height = 1920;
  const x = c.getContext('2d'), py = z => (0.5 - z / WIDE) * c.height;   // canvas y for a road z (metres)
  x.fillStyle = '#0a0b0d'; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = '#101114'; x.fillRect(0, py(8), c.width, py(-8) - py(8));
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 26000; i++) { const v = 12 + rnd() * 20; x.fillStyle = `rgb(${v},${v},${v + 3})`; x.fillRect(rnd() * c.width, py(8) + rnd() * (py(-8) - py(8)), 2, 2); }
  for (const z of [-3.6, 3.6]) { const gr = x.createLinearGradient(0, py(z + 1.2), 0, py(z - 1.2)); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(0.5, 'rgba(0,0,0,0.18)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); x.fillStyle = gr; x.fillRect(0, py(z + 1.2), c.width, py(z - 1.2) - py(z + 1.2)); }
  x.fillStyle = '#c9cdd3';
  for (const z of [7.6, -7.6]) x.fillRect(0, py(z) - 5, c.width, 10);          // edge lines
  x.fillRect(0, py(0) - 4, c.width * 0.4, 8);                                     // centre dashes
  for (const z of [3.8, -3.8]) x.fillRect(c.width * 0.5, py(z) - 3, c.width * 0.25, 6);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = THREE.RepeatWrapping; tex.repeat.set(LONG / TILE, 1); tex.anisotropy = 8;
  const road = new THREE.Mesh(new THREE.PlaneGeometry(LONG, WIDE), new THREE.MeshStandardMaterial({ map: tex, color: 0x5c5f66, roughness: 0.82, metalness: 0, transparent: true, opacity: 0.9, envMapIntensity: 0.12 }));
  road.rotation.x = -Math.PI / 2; road.position.y = 0.002; road.receiveShadow = true; road.renderOrder = -1; g.add(road);
  const metal = new THREE.MeshStandardMaterial({ color: 0x23262b, roughness: 0.5, metalness: 0.6 });
  const lamp = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffe2b0).multiplyScalar(3), toneMapped: false });
  const refl = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xff3020).multiplyScalar(2), toneMapped: false });
  const poolMat = new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, map: (() => {
    const pc = document.createElement('canvas'); pc.width = pc.height = 256; const q = pc.getContext('2d');
    const r = q.createRadialGradient(128, 128, 0, 128, 128, 128); r.addColorStop(0, 'rgba(255,214,160,0.34)'); r.addColorStop(1, 'rgba(255,214,160,0)');
    q.fillStyle = r; q.fillRect(0, 0, 256, 256); const t = new THREE.CanvasTexture(pc); t.colorSpace = THREE.SRGBColorSpace; return t; })() });
  const movers = [];
  for (const side of [1, -1]) {
    for (let i = 0; i < 20; i++) {           // lamp posts every 20 m
      const p = new THREE.Group();
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 7, 10), metal); pole.position.y = 3.5; p.add(pole);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 2.2), metal); arm.position.set(0, 7, -side * 1.0); p.add(arm);
      const head = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 0.35), lamp); head.position.set(0, 6.93, -side * 2.0); p.add(head);
      const pool = new THREE.Mesh(new THREE.PlaneGeometry(14, 10), poolMat); pool.rotation.x = -Math.PI / 2; pool.position.set(0, 0.012 - p.position.y, -side * 3.2); p.add(pool);
      p.position.z = side * 10; p.userData.x0 = i * 20 + (side > 0 ? 0 : 10); g.add(p); movers.push(p);
    }
    for (let i = 0; i < 40; i++) {           // marker posts every 10 m
      const m = new THREE.Group();
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.9, 0.1), new THREE.MeshStandardMaterial({ color: 0xd8dade, roughness: 0.6 })); post.position.y = 0.45; m.add(post);
      const r = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.12, 0.11), refl); r.position.y = 0.78; m.add(r);
      m.position.z = side * 8.6; m.userData.x0 = i * 10 + 5; g.add(m); movers.push(m);
    }
  }
  g.userData.update = dist => {
    tex.offset.x = (dist / TILE) % 1;
    for (const m of movers) m.position.x = ((((m.userData.x0 - dist) % LONG) + LONG) % LONG) - LONG / 2;
  };
  return g;
}
const road = makeRoad();
road.visible = false; st.scene.add(road);
const studioFog = st.scene.fog, roadFog = new THREE.Fog(0x070a10, 22, 80);
const studioBg = st.scene.background, roadBg = (() => {   // night sky: black overhead, a faint glow at the horizon
  const c = document.createElement('canvas'); c.width = 4; c.height = 512; const q = c.getContext('2d');
  const gr = q.createLinearGradient(0, 0, 0, 512); gr.addColorStop(0, '#020305'); gr.addColorStop(0.42, '#0a1019'); gr.addColorStop(0.5, '#121a26'); gr.addColorStop(0.62, '#070a10'); gr.addColorStop(1, '#070a10');
  q.fillStyle = gr; q.fillRect(0, 0, 4, 512); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
st.camera.far = 200;

const big = turntable(4.6, 0xffffff);
st.scene.add(big.g);
big.ring.material.color.set(0xc9d4e2).multiplyScalar(1.6);

// coloured rim lights, one per car, switched per shot
const rim = Object.fromEntries(Object.keys(SPEC).map(id => [id, new THREE.SpotLight(COL[id], 0, 30, 0.5, 0.6)]));
for (const l of Object.values(rim)) { st.scene.add(l); st.scene.add(l.target); }

const v3 = new THREE.Vector3();
function project(obj, p) {
  v3.set(...p); obj.localToWorld(v3); v3.project(st.camera);
  return [(v3.x + 1) / 2 * W, (1 - v3.y) / 2 * H, v3.z < 1];
}

/* spec = {
     cars: [{ id, x, z, ry, spin, steer, pitch, roll, table: true, glow: 1 }],  // radians; spin = wheel angle; glow = lights
     bigTable: { ry } | null,
     road: { dist } | null,                                 // night road scrolled by `dist` metres
     cam: { az, el, dist, fov, target: [x, y, z], shift: [px, py], roll },  // orbit camera (degrees); shift moves the image
     scissor: [x, y, w, h] | null,                          // only draw this part of the frame (pixels, top-left origin)
     rim: { rs3: k, m2: k }, exposure,
     anchors: { name: [carId, x, y, z] },
   }  ->  { canvas, at: { name: [sx, sy] } } */
function render(spec) {
  for (const [id, a] of Object.entries(actors)) {
    const c = spec.cars.find(c => c.id === id);
    a.root.visible = !!c;
    if (!c) continue;
    a.root.parent !== (spec.bigTable ? big.g : st.scene) && (spec.bigTable ? big.g : st.scene).add(a.root);
    a.root.position.set(c.x || 0, 0, c.z || 0);
    a.root.rotation.y = c.ry || 0;
    a.car.rotation.set(c.roll || 0, 0, c.pitch || 0);      // body: nose-up on launch, lean in corners
    a.refl.rotation.set(-(c.roll || 0), 0, -(c.pitch || 0));
    a.tt.g.visible = c.table !== false && !spec.bigTable && !spec.road;
    a.tt.g.rotation.y = 0;
    a.shadow.visible = true;
    for (const m of a.glowMats) m.emissiveIntensity = 2.2 * (c.glow ?? 1);
    const wheels = a.car.userData.wheels;
    wheels.forEach((w, i) => {
      const left = i % 2 === 0, front = i < 2;
      w.rotation.set(0, (left ? 0 : Math.PI) + (front ? c.steer || 0 : 0), left ? -(c.spin || 0) : c.spin || 0);
      a.refl.children[a.wheelIdx[i]].rotation.copy(w.rotation);
    });
  }
  big.g.visible = !!spec.bigTable;
  road.visible = !!spec.road; st.floor.visible = st.pool.visible = !spec.road;
  st.scene.fog = spec.road ? roadFog : studioFog;
  st.scene.background = spec.road ? roadBg : studioBg;
  if (spec.road) road.userData.update(spec.road.dist || 0);
  if (spec.bigTable) big.g.rotation.y = spec.bigTable.ry || 0;
  const cam = spec.cam, az = cam.az * Math.PI / 180, el = cam.el * Math.PI / 180, tg = cam.target || [0, 0.6, 0];
  st.camera.fov = cam.fov || 30;
  if (cam.shift) st.camera.setViewOffset(W, H, -cam.shift[0], -(cam.shift[1] || 0), W, H); else st.camera.clearViewOffset();
  st.camera.updateProjectionMatrix();
  st.camera.position.set(tg[0] + Math.cos(az) * Math.cos(el) * cam.dist, tg[1] + Math.sin(el) * cam.dist, tg[2] + Math.sin(az) * Math.cos(el) * cam.dist);
  st.camera.lookAt(...tg);
  if (cam.roll) st.camera.rotateZ(cam.roll * Math.PI / 180);
  for (const [id, l] of Object.entries(rim)) {
    const k = (spec.rim && spec.rim[id]) || 0, a = actors[id];
    l.intensity = k * 60;
    if (k) { a.root.getWorldPosition(v3); l.position.set(v3.x - Math.cos(az) * 6, 5, v3.z - Math.sin(az) * 6); l.target.position.copy(v3); }
  }
  st.renderer.toneMappingExposure = spec.exposure ?? 1.05;
  st.scene.updateMatrixWorld(true);
  if (spec.scissor) { const [x, y, w, h] = spec.scissor; st.renderer.setScissorTest(true); st.renderer.setScissor(x, H - y - h, w, h); }
  st.renderer.render(st.scene, st.camera);
  st.renderer.setScissorTest(false);
  const at = {};
  for (const [name, [id, ...p]] of Object.entries(spec.anchors || {})) at[name] = project(actors[id].root, p);
  return { canvas, at };
}

const dims = id => SPEC[id];
window.R3D = { render, dims };
window.dispatchEvent(new Event('r3d-ready'));

// The 3D stage for the film: both cars on turntables in a dark studio. film.html calls
// R3D.render(spec) with a shot description and composites the returned canvas.
import * as THREE from 'three';
import { buildCar, makeStudio, placeCar } from './car3d.js';
import { RS3, M2 } from './cars.js';

const W = 1920, H = 1080;
const canvas = document.createElement('canvas');
canvas.width = W; canvas.height = H;
const st = makeStudio(canvas, W, H);
const SPEC = { rs3: RS3, m2: M2 };
const COL = { rs3: 0x7ddc2f, m2: 0x3fa9f5 };

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
for (const id of ['rs3', 'm2']) {
  const car = buildCar(SPEC[id]);
  const placed = placeCar(st, car);
  // wheel indices, so the floor reflection's wheels can copy the real ones
  const wheelIdx = car.userData.wheels.map(w => car.children.indexOf(w));
  const tt = turntable(3.0, COL[id]);
  placed.root.add(tt.g);
  placed.shadow.position.y = 0.022;
  actors[id] = { ...placed, wheelIdx, tt };
}
const big = turntable(4.6, 0xffffff);
st.scene.add(big.g);
big.ring.material.color.set(0xc9d4e2).multiplyScalar(1.6);

// coloured rim lights, one per car, switched per shot
const rim = { rs3: new THREE.SpotLight(COL.rs3, 0, 30, 0.5, 0.6), m2: new THREE.SpotLight(COL.m2, 0, 30, 0.5, 0.6) };
for (const l of Object.values(rim)) { st.scene.add(l); st.scene.add(l.target); }

const v3 = new THREE.Vector3();
function project(obj, p) {
  v3.set(...p); obj.localToWorld(v3); v3.project(st.camera);
  return [(v3.x + 1) / 2 * W, (1 - v3.y) / 2 * H, v3.z < 1];
}

/* spec = {
     cars: [{ id, x, z, ry, spin, steer, table: true }],  // ry in radians; spin = wheel angle
     bigTable: { ry } | null,
     cam: { az, el, dist, fov, target: [x, y, z] },        // orbit camera (degrees)
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
    a.tt.g.visible = c.table !== false && !spec.bigTable;
    a.tt.g.rotation.y = 0;
    a.shadow.visible = true;
    const wheels = a.car.userData.wheels;
    wheels.forEach((w, i) => {
      const left = i % 2 === 0, front = i < 2;
      w.rotation.set(0, (left ? 0 : Math.PI) + (front ? c.steer || 0 : 0), left ? -(c.spin || 0) : c.spin || 0);
      a.refl.children[a.wheelIdx[i]].rotation.copy(w.rotation);
    });
  }
  big.g.visible = !!spec.bigTable;
  if (spec.bigTable) big.g.rotation.y = spec.bigTable.ry || 0;
  const cam = spec.cam, az = cam.az * Math.PI / 180, el = cam.el * Math.PI / 180, tg = cam.target || [0, 0.6, 0];
  st.camera.fov = cam.fov || 30; st.camera.updateProjectionMatrix();
  st.camera.position.set(tg[0] + Math.cos(az) * Math.cos(el) * cam.dist, tg[1] + Math.sin(el) * cam.dist, tg[2] + Math.sin(az) * Math.cos(el) * cam.dist);
  st.camera.lookAt(...tg);
  for (const [id, l] of Object.entries(rim)) {
    const k = (spec.rim && spec.rim[id]) || 0, a = actors[id];
    l.intensity = k * 60;
    if (k) { a.root.getWorldPosition(v3); l.position.set(v3.x - Math.cos(az) * 6, 5, v3.z - Math.sin(az) * 6); l.target.position.copy(v3); }
  }
  st.renderer.toneMappingExposure = spec.exposure ?? 1.05;
  st.scene.updateMatrixWorld(true);
  st.renderer.render(st.scene, st.camera);
  const at = {};
  for (const [name, [id, ...p]] of Object.entries(spec.anchors || {})) at[name] = project(actors[id].root, p);
  return { canvas, at };
}

const dims = id => SPEC[id];
window.R3D = { render, dims };
window.dispatchEvent(new Event('r3d-ready'));

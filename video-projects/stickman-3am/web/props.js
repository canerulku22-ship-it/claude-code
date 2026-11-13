// Bedroom props in the pictogram style: soft white matte shapes on black, with a few colored accents.
import { THREE, Panel, TEX, text, rrect, C } from './engine.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const propMat = new THREE.MeshStandardMaterial({ color: 0xe6e9ef, emissive: 0xe6e9ef, emissiveIntensity: 0.04, roughness: 0.62 });
export const darkMat = new THREE.MeshStandardMaterial({ color: 0x15171c, roughness: 0.4, metalness: 0.2 });
export const box = (w, h, d, r = 0.03, mat = propMat) => new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2.1, h / 2.1, d / 2.1)), mat);
const at = (o, x, y, z) => { o.position.set(x, y, z); return o; };

export function panelMesh(parent, { w, h, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, ppu = 700, draw, key = null, boost = 0.95, additive = false, opacity = 1 }) {
  const p = new Panel({ w, h, ppu, draw, key, boost, additive, opacity });
  p.mesh.position.set(x, y, z); p.mesh.rotation.set(rx, ry, rz); parent.add(p.mesh); return p;
}

// ---------------------------------------------------------------- bed (head to -x)
export function bed() {
  const g = new THREE.Group();
  for (const [x, z] of [[-0.76, -0.42], [0.76, -0.42], [-0.76, 0.42], [0.76, 0.42]]) g.add(at(box(0.07, 0.22, 0.07, 0.02), x, 0.11, z));
  g.add(at(box(1.62, 0.16, 0.95, 0.04), 0, 0.28, 0));
  g.add(at(box(1.56, 0.14, 0.9, 0.05), 0, 0.43, 0));
  g.add(at(box(0.07, 1.02, 0.95, 0.03), -0.82, 0.56, 0));
  g.add(at(box(0.06, 0.56, 0.95, 0.03), 0.82, 0.33, 0));
  const pillow = at(box(0.3, 0.1, 0.56, 0.05), -0.6, 0.55, 0); g.add(pillow);
  const blanketPivot = new THREE.Group(); blanketPivot.position.set(0.8, 0.62, 0); g.add(blanketPivot);
  const blanket = at(box(1.12, 0.16, 0.98, 0.06), -0.56, 0.0, 0); blanketPivot.add(blanket);
  return { g, blanket, blanketPivot, pillow };
}

export function nightstand() {
  const g = new THREE.Group();
  g.add(at(box(0.42, 0.5, 0.42, 0.03), 0, 0.25, 0));
  g.add(at(box(0.32, 0.012, 0.01, 0.004, darkMat), 0, 0.3, 0.212));
  g.add(at(box(0.07, 0.025, 0.02, 0.008, darkMat), 0, 0.37, 0.215));
  return g;
}

// ---------------------------------------------------------------- phone with a live screen
export function phone() {
  const g = new THREE.Group();            // lies flat, screen up, long axis along x
  const flip = new THREE.Group(); g.add(flip);
  flip.add(box(0.16, 0.012, 0.08, 0.008, darkMat));
  const state = { mode: 'off', read: 0, lit: 0 };
  const screen = panelMesh(flip, {
    w: 0.148, h: 0.07, y: 0.0068, rx: -Math.PI / 2, rz: -Math.PI / 2 * 0, ppu: 5200, boost: 1.0,
    key: () => state.mode + state.read.toFixed(2) + state.lit.toFixed(2),
    draw: (c, t, P) => {
      const W = P.cw, H = P.ch;   // landscape canvas mapped on the phone (long side = x)
      c.save(); c.translate(W / 2, H / 2); c.rotate(Math.PI / 2); c.translate(-H / 2, -W / 2); // draw in portrait coords (H wide, W tall)
      const w = H, h = W;
      c.fillStyle = '#020203'; c.fillRect(0, 0, w, h);
      if (state.mode !== 'off' && state.lit > 0.01) {
        c.globalAlpha = state.lit;
        const gr = c.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#1d2333'); gr.addColorStop(1, '#0b0d14'); c.fillStyle = gr; c.fillRect(0, 0, w, h);
        if (state.mode === 'notif') {
          text(c, '3:07', w / 2, h * 0.17, { size: w * 0.26, weight: 300, color: '#fff', font: 'Inter Display' });
          text(c, 'Thursday', w / 2, h * 0.255, { size: w * 0.065, weight: 600, color: '#cfd6e6' });
          c.fillStyle = 'rgba(255,255,255,.16)'; rrect(c, w * 0.06, h * 0.36, w * 0.88, h * 0.13, w * 0.05); c.fill();
          c.fillStyle = '#4DD07A'; rrect(c, w * 0.1, h * 0.38, w * 0.12, w * 0.12, w * 0.03); c.fill();
          text(c, 'ME', w * 0.27, h * 0.398, { size: w * 0.07, weight: 800, color: '#fff', align: 'left' });
          text(c, 'now', w * 0.88, h * 0.398, { size: w * 0.05, weight: 500, color: '#cfd6e6', align: 'right' });
          text(c, '1 new message', w * 0.27, h * 0.45, { size: w * 0.06, weight: 500, color: '#e9edf7', align: 'left' });
        } else if (state.mode === 'thread') {
          text(c, 'ME', w / 2, h * 0.08, { size: w * 0.08, weight: 800, color: '#fff' });
          c.fillStyle = 'rgba(255,255,255,.1)'; c.fillRect(0, h * 0.12, w, 2);
          c.fillStyle = '#2b2f3b'; rrect(c, w * 0.08, h * 0.3, w * 0.7, h * 0.11, w * 0.06); c.fill();
          text(c, 'Look at the door.', w * 0.13, h * 0.355, { size: w * 0.068, weight: 600, color: '#fff', align: 'left' });
          const r = state.read; c.globalAlpha = state.lit * Math.min(1, r * 2);
          text(c, 'Read 3:08 AM', w * 0.1, h * 0.45, { size: w * 0.055, weight: 700, color: r > 0.6 ? C.red : '#9aa3b5', align: 'left' });
        }
      }
      c.restore();
    },
  });
  g.userData = { state, flip, screen };
  return g;
}

// ---------------------------------------------------------------- window with moon / sun
function moonTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  const gr = g.createRadialGradient(230, 220, 20, 256, 256, 200); gr.addColorStop(0, '#FFE9A8'); gr.addColorStop(1, '#F2B64A');
  g.fillStyle = gr; g.beginPath(); g.arc(256, 256, 190, 0, 7); g.fill();
  g.fillStyle = 'rgba(160,100,30,.25)'; for (const [x, y, r] of [[200, 200, 40], [310, 280, 30], [230, 330, 22], [320, 180, 18]]) { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function sunTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  g.strokeStyle = '#FFC93D'; g.lineWidth = 22; g.lineCap = 'round';
  for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; g.beginPath(); g.moveTo(256 + Math.cos(a) * 165, 256 + Math.sin(a) * 165); g.lineTo(256 + Math.cos(a) * 230, 256 + Math.sin(a) * 230); g.stroke(); }
  g.fillStyle = '#FFC93D'; g.beginPath(); g.arc(256, 256, 130, 0, 7); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export function windowFrame(size = 0.95) {
  const g = new THREE.Group(), b = 0.06, s = size;
  g.add(at(box(s, b, 0.08), 0, s / 2, 0), at(box(s, b, 0.08), 0, -s / 2, 0), at(box(b, s, 0.08), -s / 2, 0, 0), at(box(b, s, 0.08), s / 2, 0, 0));
  g.add(at(box(s, b * 0.6, 0.06), 0, 0, 0), at(box(b * 0.6, s, 0.06), 0, 0, 0));
  g.add(at(box(s + 0.16, 0.05, 0.16), 0, -s / 2 - 0.05, 0.03));
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(s, s), new THREE.MeshBasicMaterial({ color: 0x0a0e1a, transparent: true, opacity: 0.85 }));
  glass.position.z = -0.06; g.add(glass);
  const mk = tex => { const m = new THREE.Mesh(new THREE.PlaneGeometry(s * 0.46, s * 0.46), new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false, depthWrite: false })); m.position.set(0.07, 0.08, -0.04); m.material.color.setScalar(2.6); g.add(m); return m; };
  const moon = mk(moonTexture()), sun = mk(sunTexture()); sun.visible = false; sun.scale.setScalar(1.15);
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(s * 1.4, s * 1.4), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, color: new THREE.Color('#ffcf73') }));
  halo.position.set(0.07, 0.08, -0.05); g.add(halo);
  g.userData = { moon, sun, halo };
  return g;
}

// ---------------------------------------------------------------- door with hinge + backlit hallway
export function door() {
  const g = new THREE.Group(), W = 0.88, Hh = 2.0;
  g.add(at(box(0.07, Hh + 0.07, 0.14), -W / 2 - 0.035, Hh / 2, 0), at(box(0.07, Hh + 0.07, 0.14), W / 2 + 0.035, Hh / 2, 0), at(box(W + 0.14, 0.07, 0.14), 0, Hh + 0.035, 0));
  const hallMat = new THREE.MeshBasicMaterial({ color: 0xfff3e0, transparent: true, opacity: 0, toneMapped: false });
  const hall = new THREE.Mesh(new THREE.PlaneGeometry(W * 2.2, Hh * 1.2), hallMat); hall.position.set(0, Hh / 2, -1.1); g.add(hall);
  const spill = new THREE.Mesh(new THREE.PlaneGeometry(W * 1.6, 1.8), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, color: new THREE.Color('#fff1dc') }));
  spill.rotation.x = -Math.PI / 2; spill.position.set(0, 0.006, 0.7); spill.scale.set(1, 1, 1); g.add(spill);
  const hinge = new THREE.Group(); hinge.position.set(-W / 2, 0, 0); g.add(hinge);
  const leaf = at(box(W, Hh, 0.05, 0.02), W / 2, Hh / 2, 0); hinge.add(leaf);
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 12), darkMat); knob.position.set(W - 0.1, 1.0, 0.045); hinge.add(knob);
  g.userData = { hinge, hall, hallMat, spill, W, H: Hh };
  return g;
}

// ---------------------------------------------------------------- analog clock
export function clock(parent, { x, y, z, size = 0.5 }) {
  const state = { min: 7 };   // minutes after 3:00
  const p = panelMesh(parent, {
    w: size, h: size, x, y, z, ppu: 1100, boost: 1.0, key: () => state.min.toFixed(1),
    draw: (c, t, P) => {
      const R = P.cw / 2;
      c.save(); c.translate(R, R);
      c.fillStyle = '#e9ecf2'; c.beginPath(); c.arc(0, 0, R * 0.96, 0, 7); c.fill();
      c.strokeStyle = '#0b0c10'; c.lineWidth = R * 0.07; c.beginPath(); c.arc(0, 0, R * 0.86, 0, 7); c.stroke();
      for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; c.lineWidth = R * 0.05; c.beginPath(); c.moveTo(Math.sin(a) * R * 0.68, -Math.cos(a) * R * 0.68); c.lineTo(Math.sin(a) * R * 0.76, -Math.cos(a) * R * 0.76); c.stroke(); }
      const m = state.min, ha = (3 + m / 60) / 12 * Math.PI * 2, ma = m / 60 * Math.PI * 2;
      c.lineCap = 'round'; c.lineWidth = R * 0.09; c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.sin(ha) * R * 0.42, -Math.cos(ha) * R * 0.42); c.stroke();
      c.lineWidth = R * 0.06; c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.sin(ma) * R * 0.64, -Math.cos(ma) * R * 0.64); c.stroke();
      c.fillStyle = '#0b0c10'; c.beginPath(); c.arc(0, 0, R * 0.07, 0, 7); c.fill();
      c.restore();
    },
  });
  p.state = state;
  return p;
}

// ---------------------------------------------------------------- warning X, ghost text, eyes in the dark
export function redX(parent, opts) {
  return panelMesh(parent, Object.assign({ w: 0.42, h: 0.42, ppu: 900, boost: 2.2, draw: (c, t, P) => {
    const R = P.cw / 2; c.save(); c.translate(R, R);
    c.shadowColor = C.red; c.shadowBlur = R * 0.25; c.fillStyle = '#E63946'; c.beginPath(); c.arc(0, 0, R * 0.8, 0, 7); c.fill();
    c.shadowBlur = 0; c.strokeStyle = '#fff'; c.lineWidth = R * 0.17; c.lineCap = 'round';
    c.beginPath(); c.moveTo(-R * 0.32, -R * 0.32); c.lineTo(R * 0.32, R * 0.32); c.moveTo(R * 0.32, -R * 0.32); c.lineTo(-R * 0.32, R * 0.32); c.stroke(); c.restore();
  } }, opts));
}
export function eyesInDark() {
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.0, 0.25, 0.25).multiplyScalar(4), toneMapped: false });
  const eyes = [-0.07, 0.07].map(x => { const e = new THREE.Mesh(new THREE.SphereGeometry(0.022, 16, 12), mat); e.position.x = x; e.scale.y = 0.55; g.add(e); return e; });
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.25), new THREE.MeshBasicMaterial({ map: TEX.glow, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, color: new THREE.Color('#ff3040') }));
  glow.position.z = -0.01; g.add(glow);
  g.userData = { eyes, glow, mat };
  return g;
}

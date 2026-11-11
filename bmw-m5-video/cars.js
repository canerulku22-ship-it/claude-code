// The BMW M5 (G90 saloon, and the G99 Touring), described for car3d.js. Coordinates
// in metres: x forward (front axle ahead of the origin), y up from the road, z to the
// car's left. Dimensions are BMW's; the saloon's silhouette was matched to a side-on
// BMW press photo, and its lights, kidneys and diffuser to the studio shots.
import * as THREE from 'three';
import { K, both, frame, glassFill, glassOutline, poly, roundel, rrect, screenOutline, sideTrim, slats, trimAround, txt, ukPlate } from './decals.js';

const FRONT = [-1.0, 0.12, 1.0, 1.0], REAR = [-1.0, 0.12, 1.0, 1.24], REART = [-1.0, 0.12, 1.0, 1.46], SIDE = [-2.62, 0.08, 2.62, 1.56];

function mBadge(g, x, y, h) { // the M tricolour + "M5"
  ['#7fc0ec', '#22336e', '#e12a26'].forEach((c, i) => { g.beginPath(); g.moveTo(x + i * h * 0.38, y); g.lineTo(x + i * h * 0.38 + h * 0.32, y); g.lineTo(x + i * h * 0.38 + h * 0.55, y + h); g.lineTo(x + i * h * 0.38 + h * 0.23, y + h); g.closePath(); g.fillStyle = c; g.fill(); });
  txt(g, 'M5', x + h * 1.25, y + h * 0.5, h * 1.25, 'bold italic', '#d7dade', 'left');
}
const KIDNEY = k => K(k, [[0.045, 0.52], [0.37, 0.52], [0.44, 0.565], [0.45, 0.68], [0.42, 0.745], [0.33, 0.765], [0.08, 0.758], [0.045, 0.735]]);
function headlight(g, k) {
  return K(k, [[0.5, 0.775], [0.66, 0.8], [0.87, 0.85], [0.92, 0.81], [0.9, 0.735], [0.62, 0.72], [0.52, 0.725]]);
}
const DRL = k => [[k * 0.6, 0.735, k * 0.6, 0.79], [k * 0.76, 0.745, k * 0.76, 0.825]];

function front(g, W, H, lit) {
  frame(g, W, H, FRONT);
  if (!lit) {
    poly(g, [[-0.95, 0.14], [0.95, 0.14], [0.92, 0.2], [-0.92, 0.2]], '#0a0b0d');
    // lower centre intake + corner intakes
    poly(g, [[-0.42, 0.2], [0.42, 0.2], [0.48, 0.44], [0.34, 0.5], [-0.34, 0.5], [-0.48, 0.44]], '#07080a', '#22252a', 0.012);
    slats(g, [[-0.42, 0.2], [0.42, 0.2], [0.48, 0.44], [-0.48, 0.44]], 4, 0.2, 0.46, '#07080a', '#1a1c20');
    both(k => {
      poly(g, K(k, [[0.56, 0.22], [0.93, 0.24], [0.95, 0.56], [0.86, 0.6], [0.6, 0.42]]), '#06070a', '#2a2d33', 0.012);
      poly(g, K(k, [[0.66, 0.3], [0.72, 0.3], [0.86, 0.54], [0.8, 0.55]]), '#1b1e23');
    });
    ukPlate(g, 0, 0.34, 'M5 G90', false);
    // kidneys: black, two horizontal double bars, bright contour
    both(k => {
      poly(g, KIDNEY(k), '#050607');
      for (const y of [0.6, 0.665]) { poly(g, K(k, [[0.07, y], [0.42, y], [0.42, y + 0.018], [0.07, y + 0.018]]), '#2a2d33'); }
      poly(g, KIDNEY(k), null, '#c9cdd3', 0.016);
      poly(g, headlight(g, k), '#090a0d', '#2e3238', 0.008);
      g.beginPath(); g.arc(k * 0.68, 0.765, 0.024, 0, Math.PI * 2); g.fillStyle = '#3a4656'; g.fill();
      g.beginPath(); g.arc(k * 0.83, 0.785, 0.024, 0, Math.PI * 2); g.fill();
      g.lineCap = 'round'; g.strokeStyle = '#eef3fa'; g.lineWidth = 0.016;
      for (const [x0, y0, x1, y1] of DRL(k)) { g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); }
    });
    mBadge(g, 0.24, 0.545, 0.022);
    roundel(g, 0, 0.815, 0.04);
  } else {
    g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4);
    both(k => {
      poly(g, KIDNEY(k), null, '#ffffff', 0.016);   // Iconic Glow contour
      g.lineCap = 'round'; g.strokeStyle = '#ffffff'; g.lineWidth = 0.016;
      for (const [x0, y0, x1, y1] of DRL(k)) { g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke(); }
    });
  }
}
function rear(g, W, H, lit, touring) {
  frame(g, W, H, touring ? REART : REAR);
  const ty = touring ? 0.93 : 0.9;   // tail-light height
  if (!lit) {
    poly(g, [[-0.92, 0.14], [0.92, 0.14], [0.86, 0.42], [-0.86, 0.42]], '#08090b', '#25272b', 0.01);
    slats(g, [[-0.42, 0.15], [0.42, 0.15], [0.42, 0.36], [-0.42, 0.36]], 6, 0, 0, '#07080a', '#1c1e22', true, -0.42, 0.42);
    both(k => { rrect(g, k * 0.9 - 0.012, 0.42, 0.024, 0.16, 0.008, '#6a0b0e'); });
    poly(g, [[-0.44, 0.68], [0.44, 0.68], [0.46, 0.84], [-0.46, 0.84]], 'rgba(20,24,30,0.3)');
    ukPlate(g, 0, 0.76, 'M5 G90', true);
    // slim tail lights joined by a dark band
    poly(g, [[-0.42, ty - 0.02], [0.42, ty - 0.02], [0.42, ty + 0.025], [-0.42, ty + 0.025]], '#0d0e11');
    both(k => {
      poly(g, K(k, [[0.38, ty + 0.04], [0.8, ty + 0.045], [0.9, ty + 0.02], [0.88, ty - 0.035], [0.4, ty - 0.03]]), '#1a0507', '#151619', 0.008);
      for (const dy of [0.018, -0.012]) { g.beginPath(); g.moveTo(k * 0.42, ty + dy); g.lineTo(k * 0.86, ty + dy + 0.004); g.strokeStyle = '#d0141a'; g.lineWidth = 0.009; g.stroke(); }
    });
    roundel(g, 0, ty + 0.1, 0.04);
    mBadge(g, 0.46, ty + 0.07, 0.024);
  } else {
    g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4);
    both(k => { for (const dy of [0.018, -0.012]) { g.beginPath(); g.moveTo(k * 0.42, ty + dy); g.lineTo(k * 0.86, ty + dy + 0.004); g.strokeStyle = '#ff2a30'; g.lineWidth = 0.009; g.stroke(); } });
  }
}

const base = {
  L: 5.096, W: 1.97, xf: 1.64, xr: 1.64 - 3.006,
  Rf: 0.368, Rr: 0.37, rimR: 0.262, tyreW: 0.29, track: 1.68,
  paint: 0x1b7351, wheelColor: 0x8d939b, wheelRough: 0.3, caliper: 0xc9a227, spokes: 10, spokeFill: 0.34, splitSpoke: true,
  N: 180, M: 52, rF: 0.62, rR: 0.5, cornerP: 2.3, Wb: 1.9, flareF: 0.03, flareR: 0.038, flareLen: 0.5, archGap: 0.02, archRound: 1.0,
  ledge: 0.075, creaseIn: [[2.3, 0.02], [0.6, 0.025], [-0.6, 0.03], [-1.4, 0.045], [-2.5, 0.045]],
  crease: [[2.45, 0.75], [2.0, 0.84], [1.2, 0.88], [0, 0.89], [-1.5, 0.91], [-2.45, 0.92]],
  bottom: [[2.548, 0.33], [2.52, 0.2], [2.35, 0.17], [1.9, 0.16], [-1.8, 0.17], [-2.3, 0.22], [-2.548, 0.32]],
  mirror: [0.98, 1.13], mirrorPaint: false,
  exhausts: [{ y: 0.29, z: 0.52, ry: 0.048, rz: 0.048 }, { y: 0.29, z: 0.655, ry: 0.048, rz: 0.048 }],
};
const sideTrimM5 = (S, rearLine) => (g, W, H, B) => {
  frame(g, W, H, SIDE);
  sideTrim(g, S, B, { sill: 0.25, handles: [[0.15, 0.97], [-0.85, 0.99]],
    lines: [[[1.0, 1.08], [1.0, 0.3]], [[-0.29, 1.1], [-0.29, 0.3]], rearLine] });
  // tail light wrapping round the corner, headlight tip
  poly(g, [[-2.33, 0.97], [-2.6, 0.955], [-2.6, 0.88], [-2.4, 0.9]], '#3a0408', '#151619', 0.006);
  g.beginPath(); g.moveTo(-2.35, 0.94); g.lineTo(-2.6, 0.93); g.strokeStyle = '#d0141a'; g.lineWidth = 0.01; g.stroke();
  poly(g, [[2.25, 0.86], [2.6, 0.83], [2.6, 0.76], [2.33, 0.8]], '#0b0c10', '#2a2d33', 0.006);
};

// G90 saloon: roofline measured off BMW's side-on press photo
export const M5 = {
  ...base, name: 'BMW M5 Saloon', H: 1.51,
  roofRatio: [[1.0, 0.74], [-0.5, 0.73], [-1.4, 0.7], [-1.97, 0.67]],
  top: [[2.548, 0.42], [2.538, 0.56], [2.51, 0.69], [2.44, 0.79], [2.3, 0.865], [2.0, 0.935], [1.42, 1.03], [0.975, 1.085], [0.6, 1.27],
        [0.17, 1.468], [-0.2, 1.505], [-0.76, 1.47], [-1.16, 1.4], [-1.565, 1.3], [-1.97, 1.16], [-2.2, 1.1], [-2.36, 1.085],
        [-2.44, 1.02], [-2.49, 0.86], [-2.53, 0.66], [-2.548, 0.45]],
  belt: [[0.98, 1.08], [0.6, 1.075], [0, 1.09], [-0.8, 1.12], [-1.3, 1.15], [-1.55, 1.17], [-1.9, 1.17]],
  gh: [-1.97, 0.975],
  extra(car, { black }) {
    const sh = new THREE.Shape([[-2.26, 1.098], [-2.42, 1.115], [-2.43, 1.095], [-2.34, 1.088]].map(([x, y]) => new THREE.Vector2(x, y)));
    const lip = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 1.3, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.005, bevelSegments: 2 }), black);
    lip.position.z = -0.65; car.add(lip);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-0.9, 1.45], [-1.12, 1.41], [-1.1, 1.48]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SIDE);
        const o = glassOutline(B, -1.2, [[-1.56, 1.2], [-1.5, 1.165]], 0.08);
        glassFill(g, o, [[0.1, 1.3], [-0.95, 1.3]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.23, -0.34], [-1.2, -1.25]]) poly(g, [[a, 1.0], [b, 1.0], [b, 1.6], [a, 1.6]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], minFacing: 0.05,
      draw: (g, W, H, B) => sideTrimM5(M5, [[-1.2, 1.15], [-1.2, 0.85], [-1.0, 0.78], [-0.95, 0.62], [-0.95, 0.3]])(g, W, H, B) },
    { axis: '+y', kind: 'glass', rect: [-2.1, -1.0, 1.1, 1.0], tw: 2048, th: 640, segs: [120, 40], order: 2,
      draw(g, W, H, B) {
        frame(g, W, H, [-2.1, -1.0, 1.1, 1.0]);
        poly(g, screenOutline(B, M5, -1.2, 0.2, 0.03), '#121417');   // carbon roof
        for (const o of [screenOutline(B, M5, 0.15, 0.99), screenOutline(B, M5, -1.97, -1.2, 0.07)]) { poly(g, o, '#0d1117'); trimAround(g, o, 0.025); }
      } },
    { axis: '+x', rect: FRONT, tw: 2048, th: 900, segs: [64, 44], draw: (g, W, H) => front(g, W, H, false), glow: (g, W, H) => front(g, W, H, true) },
    { axis: '-x', rect: REAR, tw: 2048, th: 1150, segs: [64, 48], draw: (g, W, H) => rear(g, W, H, false, false), glow: (g, W, H) => rear(g, W, H, true, false) },
  ],
};

// G99 Touring: the same car from the B-pillar forward, with an estate roof and tailgate
export const M5T = {
  ...base, name: 'BMW M5 Touring', H: 1.515,
  roofRatio: [[1.0, 0.74], [-0.5, 0.73], [-1.6, 0.71], [-2.3, 0.69]],
  top: [[2.548, 0.42], [2.538, 0.56], [2.51, 0.69], [2.44, 0.79], [2.3, 0.865], [2.0, 0.935], [1.42, 1.03], [0.975, 1.085], [0.6, 1.27],
        [0.17, 1.468], [-0.2, 1.512], [-0.9, 1.508], [-1.6, 1.49], [-2.05, 1.465], [-2.24, 1.44], [-2.33, 1.37], [-2.4, 1.2],
        [-2.46, 1.02], [-2.5, 0.86], [-2.535, 0.66], [-2.548, 0.45]],
  belt: [[0.98, 1.08], [0.6, 1.075], [0, 1.09], [-0.8, 1.12], [-1.4, 1.15], [-2.0, 1.17], [-2.4, 1.17]],
  gh: [-2.38, 0.975],
  extra(car, { black }) {
    for (const s of [1, -1]) {   // roof rails
      const rail = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.035, 0.035), black);
      rail.position.set(-1.0, 1.505, s * 0.5); car.add(rail);
    }
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-2.05, 1.48], [-2.36, 1.45], [-2.37, 1.425], [-2.2, 1.44]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.15, bevelEnabled: true, bevelThickness: 0.008, bevelSize: 0.006, bevelSegments: 2 }), black);
    sp.position.z = -0.575; car.add(sp);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SIDE);
        const o = glassOutline(B, -2.0, [[-2.18, 1.19]], 0.08);
        glassFill(g, o, [[0.1, 1.3], [-0.95, 1.3]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.23, -0.34], [-1.32, -1.42]]) poly(g, [[a, 1.0], [b, 1.0], [b, 1.6], [a, 1.6]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], minFacing: 0.05,
      draw: (g, W, H, B) => sideTrimM5(M5T, [[-1.32, 1.15], [-1.3, 0.85], [-1.0, 0.78], [-0.95, 0.62], [-0.95, 0.3]])(g, W, H, B) },
    { axis: '+y', kind: 'glass', rect: [-2.4, -1.0, 1.1, 1.0], tw: 2048, th: 600, segs: [120, 40], order: 2,
      draw(g, W, H, B) {
        frame(g, W, H, [-2.4, -1.0, 1.1, 1.0]);
        const o = screenOutline(B, M5T, 0.15, 0.99); poly(g, o, '#0d1117'); trimAround(g, o, 0.025);
      } },
    { axis: '-x', kind: 'glass', rect: REART, tw: 1024, th: 740, segs: [50, 44], order: 2,
      draw(g, W, H) { frame(g, W, H, REART); const o = [[-0.66, 1.06], [0.66, 1.06], [0.56, 1.36], [-0.56, 1.36]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    { axis: '+x', rect: FRONT, tw: 2048, th: 900, segs: [64, 44], draw: (g, W, H) => front(g, W, H, false), glow: (g, W, H) => front(g, W, H, true) },
    { axis: '-x', rect: REART, tw: 2048, th: 1360, segs: [64, 52], draw: (g, W, H) => rear(g, W, H, false, true), glow: (g, W, H) => rear(g, W, H, true, true) },
  ],
};

export const CARS = { m5: { spec: M5, color: 0x3fa9f5 }, m5t: { spec: M5T, color: 0xe5322d } };

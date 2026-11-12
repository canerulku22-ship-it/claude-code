// The SEAT Leon Cupra 290 (Mk3, 2016), Volkswagen Golf R (Mk8.5) and Audi S3 Sportback
// (8Y facelift), described for car3d.js. The Golf and S3 are the same models as in
// ../golf-r-vs-s3; the Leon shares the Golf's MQB proportions with its own roof, lights
// and bumpers. Plus the S3 Saloon and Golf R Estate variants, which this film doesn't use.
// Original note: the Golf R and S3 are Coordinates in metres: x forward (front axle ahead of the origin), y up
// from the road, z to the car's left. Dimensions are the manufacturers'; the Golf's
// silhouette was checked against Volkswagen's side-on press photo, and the S3 shares
// its body shell with the RS3 in ../rs3-vs-m2 (narrower arches, its own bumpers).
import * as THREE from 'three';
import { K, both, frame, glassFill, glassOutline, honeycomb, poly, rings, rrect, screenOutline, sideTrim, slats, trimAround, txt, ukPlate } from './decals.js';

function vwLogo(g, x, y, r, col, lw) {
  g.strokeStyle = col; g.lineWidth = lw; g.lineJoin = 'round';
  g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.moveTo(x - r * 0.62, y + r * 0.62); g.lineTo(x - r * 0.3, y - r * 0.55); g.lineTo(x, y + r * 0.05); g.lineTo(x + r * 0.3, y - r * 0.55); g.lineTo(x + r * 0.62, y + r * 0.62); g.stroke();
  g.beginPath(); g.moveTo(x - r * 0.32, y + r * 0.82); g.lineTo(x, y + r * 0.22); g.lineTo(x + r * 0.32, y + r * 0.82); g.stroke();
}
function rBadge(g, x, y, h, col = '#d7dade') { txt(g, 'R', x, y, h, 'bold italic', col); }

/* ---------------------------------------------------------------- Volkswagen Golf R (Mk8.5) */
const G_FRONT = [-0.94, 0.1, 0.94, 0.86], G_REAR = [-0.94, 0.12, 0.94, 1.44], G_SIDE = [-2.2, 0.08, 2.2, 1.5];
const G_LAMP = k => K(k, [[0.3, 0.705], [0.62, 0.715], [0.84, 0.75], [0.87, 0.72], [0.82, 0.665], [0.34, 0.672]]);
function golfFront(g, W, H, lit) {
  frame(g, W, H, G_FRONT);
  if (lit) {
    g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4);
    g.strokeStyle = '#fff'; g.lineWidth = 0.008; g.beginPath(); g.moveTo(-0.84, 0.735); g.lineTo(0.84, 0.735); g.stroke();   // light strip across the nose
    both(k => { g.beginPath(); g.moveTo(k * 0.36, 0.69); g.lineTo(k * 0.8, 0.705); g.strokeStyle = '#fff'; g.lineWidth = 0.012; g.stroke(); });
    vwLogo(g, 0, 0.7, 0.062, '#fff', 0.012);
    return;
  }
  poly(g, [[-0.9, 0.12], [0.9, 0.12], [0.86, 0.18], [-0.86, 0.18]], '#0b0c0e');
  const low = [[-0.46, 0.19], [0.46, 0.19], [0.5, 0.42], [0.36, 0.47], [-0.36, 0.47], [-0.5, 0.42]];
  honeycomb(g, low, 0.02, '#060708', '#1d1f23'); poly(g, low, null, '#1b1d21', 0.01);
  both(k => {
    const side = K(k, [[0.56, 0.2], [0.88, 0.22], [0.92, 0.5], [0.8, 0.55], [0.6, 0.44]]);
    honeycomb(g, side, 0.018, '#060708', '#1d1f23'); poly(g, side, null, '#1b1d21', 0.01);
    poly(g, K(k, [[0.68, 0.24], [0.72, 0.24], [0.78, 0.52], [0.74, 0.53]]), '#2433b8');   // body-colour blade
  });
  ukPlate(g, 0, 0.32, 'G0 LF R', false);
  poly(g, [[-0.32, 0.64], [0.32, 0.64], [0.3, 0.73], [-0.3, 0.73]], '#07080a');   // slim upper grille
  both(k => {
    poly(g, G_LAMP(k), '#0a0b0e', '#2e3238', 0.006);
    g.beginPath(); g.moveTo(k * 0.36, 0.69); g.lineTo(k * 0.8, 0.705); g.strokeStyle = '#e8eef6'; g.lineWidth = 0.012; g.stroke();
    for (const x of [0.5, 0.64]) { g.beginPath(); g.arc(k * x, 0.688, 0.02, 0, Math.PI * 2); g.fillStyle = '#323c4a'; g.fill(); }
  });
  g.strokeStyle = '#d8dce2'; g.lineWidth = 0.005; g.beginPath(); g.moveTo(-0.84, 0.735); g.lineTo(0.84, 0.735); g.stroke();
  vwLogo(g, 0, 0.7, 0.062, '#e6e9ee', 0.011);
  rBadge(g, -0.22, 0.675, 0.05);
}
function golfRear(g, W, H, lit) {
  frame(g, W, H, G_REAR);
  const lamp = k => K(k, [[0.3, 0.985], [0.8, 0.99], [0.88, 0.96], [0.86, 0.9], [0.34, 0.915]]);
  if (lit) {
    g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4);
    both(k => { g.beginPath(); g.moveTo(k * 0.34, 0.955); g.lineTo(k * 0.84, 0.96); g.lineTo(k * 0.85, 0.91); g.strokeStyle = '#ff2a30'; g.lineWidth = 0.014; g.stroke(); });
    return;
  }
  poly(g, [[-0.88, 0.14], [0.88, 0.14], [0.84, 0.38], [-0.84, 0.38]], '#0a0b0d', '#24262a', 0.008);
  slats(g, [[-0.36, 0.15], [0.36, 0.15], [0.36, 0.32], [-0.36, 0.32]], 5, 0, 0, '#08090a', '#1c1e22', true, -0.36, 0.36);
  both(k => rrect(g, k * 0.86 - 0.012, 0.42, 0.024, 0.08, 0.006, '#6a0b0e'));
  ukPlate(g, 0, 0.74, 'G0 LF R', true);
  both(k => {
    poly(g, lamp(k), '#2a0306', '#14151a', 0.008);
    g.beginPath(); g.moveTo(k * 0.34, 0.955); g.lineTo(k * 0.84, 0.96); g.lineTo(k * 0.85, 0.91); g.strokeStyle = '#d0141a'; g.lineWidth = 0.014; g.stroke();
  });
  vwLogo(g, 0, 0.96, 0.07, '#e6e9ee', 0.012);
  txt(g, 'G O L F', 0, 0.86, 0.035, 'bold', '#d7dade');
  rBadge(g, 0.42, 0.86, 0.05);
  rrect(g, -0.2, 1.405, 0.4, 0.016, 0.006, '#6a0b0e');   // third brake light
}
export const GOLF = {
  name: 'Volkswagen Golf R',
  L: 4.29, W: 1.789, H: 1.458, xf: 1.285, xr: 1.285 - 2.628,
  Rf: 0.3236, Rr: 0.3236, rimR: 0.2413, tyreW: 0.235, track: 1.545,
  paint: 0x2433b8, wheelColor: 0x3d4148, wheelRough: 0.3, caliper: 0x1f4fd8, spokes: 10, spokeFill: 0.34, splitSpoke: true,
  N: 170, M: 52, rF: 0.6, rR: 0.45, cornerP: 2.3, Wb: 1.77, flareF: 0.01, flareR: 0.012, flareLen: 0.4, archGap: 0.03, archRound: 1.0,
  ledge: 0.07, roofRatio: [[0.85, 0.74], [-0.5, 0.73], [-1.4, 0.68], [-1.88, 0.64]],
  creaseIn: [[2.0, 0.015], [0.5, 0.02], [-0.8, 0.025], [-1.5, 0.04], [-2.1, 0.04]],
  crease: [[2.05, 0.72], [1.6, 0.8], [1.0, 0.84], [0, 0.85], [-1.4, 0.86], [-2.05, 0.87]],
  top: [[2.145, 0.4], [2.138, 0.55], [2.11, 0.67], [2.04, 0.75], [1.88, 0.805], [1.4, 0.875], [0.85, 0.965], [0.5, 1.13], [0.1, 1.32],
        [-0.28, 1.43], [-0.6, 1.455], [-1.0, 1.458], [-1.35, 1.445], [-1.55, 1.43], [-1.63, 1.4], [-1.72, 1.28], [-1.82, 1.13],
        [-1.9, 1.03], [-2.02, 0.96], [-2.11, 0.86], [-2.14, 0.68], [-2.145, 0.42]],
  bottom: [[2.145, 0.3], [2.12, 0.18], [1.95, 0.15], [1.5, 0.14], [-1.6, 0.15], [-2.0, 0.22], [-2.145, 0.3]],
  belt: [[0.85, 0.965], [0.3, 0.975], [-0.6, 0.99], [-1.2, 1.02], [-1.6, 1.05], [-1.95, 1.0]],
  gh: [-1.9, 0.85],
  mirror: [0.62, 1.02], mirrorColor: 0xc0c4c9,
  exhausts: [{ y: 0.29, z: 0.47, ry: 0.044, rz: 0.044 }, { y: 0.29, z: 0.58, ry: 0.044, rz: 0.044 }],
  extra(car, { paint, black }) {
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.35, 1.452], [-1.72, 1.4], [-1.73, 1.38], [-1.6, 1.39]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.04, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2 }), paint);
    sp.position.z = -0.52; sp.castShadow = true; car.add(sp);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.15, 1.45], [-1.35, 1.43], [-1.33, 1.49]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: G_SIDE, tw: 3072, th: 1000, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, G_SIDE);
        const o = glassOutline(B, -1.18, [[-1.27, 1.02]], 0.07);
        glassFill(g, o, [[0.0, 1.18], [-0.95, 1.2]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.26, -0.34], [-0.97, -1.0]]) poly(g, [[a, 0.9], [b, 0.9], [b, 1.5], [a, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: G_SIDE, tw: 3072, th: 1000, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, G_SIDE);
        sideTrim(g, GOLF, B, { sill: 0.21, handles: [[-0.12, 0.88], [-1.04, 0.92]],
          lines: [[[0.84, 0.96], [0.84, 0.3]], [[-0.3, 0.99], [-0.3, 0.3]], [[-1.25, 1.02], [-1.24, 0.75], [-1.05, 0.7], [-0.98, 0.6], [-0.98, 0.3]]] });
        poly(g, [[-1.92, 0.99], [-2.14, 0.975], [-2.14, 0.9], [-1.98, 0.915]], '#5a0610', '#14151a', 0.006);
        poly(g, [[1.82, 0.75], [2.14, 0.72], [2.14, 0.67], [1.88, 0.705]], '#0b0c0f', '#303338', 0.006);
        rBadge(g, 1.62, 0.72, 0.05);
      } },
    { axis: '+y', kind: 'glass', rect: [-0.4, -0.9, 0.9, 0.9], tw: 1024, th: 720, segs: [50, 50], order: 2,
      draw(g, W, H, B) { frame(g, W, H, [-0.4, -0.9, 0.9, 0.9]); const o = screenOutline(B, GOLF, -0.24, 0.86); poly(g, o, '#0d1117'); trimAround(g, o, 0.025); } },
    { axis: '-x', kind: 'glass', rect: G_REAR, tw: 1024, th: 780, segs: [50, 50], order: 2,
      draw(g, W, H) { frame(g, W, H, G_REAR); const o = [[-0.6, 1.04], [0.6, 1.04], [0.5, 1.36], [-0.5, 1.36]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    { axis: '+x', rect: G_FRONT, tw: 2048, th: 820, segs: [64, 40], draw: (g, W, H) => golfFront(g, W, H, false), glow: (g, W, H) => golfFront(g, W, H, true) },
    { axis: '-x', rect: G_REAR, tw: 2048, th: 1400, segs: [64, 52], draw: (g, W, H) => golfRear(g, W, H, false), glow: (g, W, H) => golfRear(g, W, H, true) },
  ],
};

/* ---------------------------------------------------------------- Audi S3 Sportback (8Y facelift) */
// Same A3 Sportback shell as the RS3 (see ../rs3-vs-m2/cars.js), 38 mm shorter and narrower.
const sx = 2.1755 / 2.1945, sy = 1.426 / 1.436;
const shell = pts => pts.map(([x, y]) => [x * sx, y > 1.2 ? y * sy : y]);
const S_FRONT = [-0.94, 0.1, 0.94, 0.9], S_REAR = [-0.94, 0.14, 0.94, 1.4], S_SIDE = [-2.24, 0.08, 2.24, 1.46];
function s3Front(g, W, H, lit) {
  frame(g, W, H, S_FRONT);
  const lamp = k => K(k, [[0.5, 0.7], [0.82, 0.76], [0.86, 0.725], [0.79, 0.675], [0.55, 0.65]]);
  const drl = k => { for (let i = 0; i < 10; i++) { const x = 0.55 + i * 0.026, y = 0.7 + (x - 0.5) * 0.18; rrect(g, k * x - 0.009, y - 0.006, 0.018, 0.012, 0.002, lit ? '#fff' : '#dfe6ee'); } };
  if (lit) { g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4); both(drl); return; }
  poly(g, [[-0.88, 0.12], [0.88, 0.12], [0.84, 0.18], [-0.84, 0.18]], '#0b0c0e');
  both(k => {
    const side = K(k, [[0.6, 0.22], [0.86, 0.24], [0.9, 0.5], [0.78, 0.53], [0.64, 0.45]]);
    honeycomb(g, side, 0.016, '#060708', '#1d1f23'); poly(g, side, null, '#2a2c30', 0.008);
    poly(g, K(k, [[0.6, 0.3], [0.88, 0.32], [0.88, 0.335], [0.6, 0.315]]), '#8d9198');   // horizontal blade
  });
  const grille = [[-0.42, 0.655], [0.42, 0.655], [0.52, 0.59], [0.56, 0.34], [0.48, 0.25], [-0.48, 0.25], [-0.56, 0.34], [-0.52, 0.59]];
  poly(g, grille, null, '#3a3d42', 0.024);
  honeycomb(g, grille, 0.026, '#050607', '#2a2d32');
  rings(g, 0, 0.6, 0.04, '#0d0e10', 0.012); rings(g, 0, 0.6, 0.04, '#6a6e75', 0.004);
  rrect(g, -0.34, 0.585, 0.06, 0.028, 0.004, '#c5c8ce'); txt(g, 'S3', -0.31, 0.6, 0.022, 'bold', '#c8161d');
  ukPlate(g, 0, 0.43, 'S3 AUD1', false);
  both(k => { poly(g, lamp(k), '#0b0c0f', '#303338', 0.006); drl(k); });
}
function s3Rear(g, W, H, lit) {
  frame(g, W, H, S_REAR);
  const leds = k => { for (let i = 0; i < 10; i++) { const x = 0.44 + i * 0.04; rrect(g, k * x - 0.014, 0.905 + (i % 2) * 0.022, 0.028, 0.022, 0.002, lit ? '#ff2a30' : '#c3141d'); } };
  if (lit) { g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4); both(leds); return; }
  poly(g, [[-0.88, 0.16], [0.88, 0.16], [0.86, 0.4], [-0.86, 0.4]], '#0a0b0d', '#24262a', 0.008);
  slats(g, [[-0.4, 0.17], [0.4, 0.17], [0.4, 0.34], [-0.4, 0.34]], 5, 0, 0, '#08090a', '#1c1e22', true, -0.4, 0.4);
  both(k => {
    poly(g, K(k, [[0.4, 0.955], [0.84, 0.975], [0.87, 0.9], [0.82, 0.86], [0.42, 0.885]]), '#2a0306', '#14151a', 0.008);
    leds(k);
  });
  rings(g, 0, 1.0, 0.045, '#101113', 0.012); rings(g, 0, 1.0, 0.045, '#8a8e95', 0.004);
  ukPlate(g, 0, 0.8, 'S3 AUD1', true);
  rrect(g, 0.36, 0.72, 0.09, 0.04, 0.005, '#c5c8ce'); txt(g, 'S3', 0.405, 0.74, 0.03, 'bold', '#c8161d');
}
export const S3 = {
  name: 'Audi S3 Sportback',
  L: 4.351, W: 1.816, H: 1.426, xf: 1.2705, xr: 1.2705 - 2.631,
  Rf: 0.3236, Rr: 0.3236, rimR: 0.2413, tyreW: 0.235, track: 1.55,
  paint: 0x6c7176, wheelColor: 0x50545a, wheelRough: 0.3, caliper: 0xc8161d, spokes: 10, spokeFill: 0.36, splitSpoke: true,
  N: 170, M: 52, rF: 0.62, rR: 0.48, cornerP: 2.3, Wb: 1.79, flareF: 0.013, flareR: 0.013, flareLen: 0.42, archGap: 0.035, archRound: 1.0,
  ledge: 0.07, roofRatio: [[0.7, 0.74], [-0.5, 0.72], [-1.4, 0.66], [-2.1, 0.62]],
  creaseIn: [[2.1, 0.015], [0.5, 0.02], [-0.8, 0.028], [-1.4, 0.042], [-2.2, 0.045]],
  crease: shell([[2.15, 0.7], [1.8, 0.79], [1.2, 0.845], [0, 0.86], [-1.5, 0.875], [-2.15, 0.88]]),
  top: shell([[2.1945, 0.34], [2.185, 0.5], [2.165, 0.62], [2.12, 0.72], [2.03, 0.79], [1.85, 0.83], [1.4, 0.885], [1.0, 0.935],
        [0.72, 0.975], [0.35, 1.16], [-0.05, 1.36], [-0.4, 1.434], [-0.7, 1.436], [-1.1, 1.412], [-1.42, 1.372], [-1.6, 1.336],
        [-1.7, 1.29], [-1.84, 1.15], [-1.96, 1.04], [-2.08, 0.96], [-2.16, 0.84], [-2.19, 0.66], [-2.1945, 0.45]]),
  bottom: shell([[2.1945, 0.28], [2.17, 0.18], [2.0, 0.15], [1.5, 0.14], [-1.6, 0.15], [-2.05, 0.22], [-2.1945, 0.3]]),
  belt: shell([[0.72, 0.985], [0.3, 0.99], [-0.6, 1.012], [-1.3, 1.05], [-1.7, 1.085], [-2.0, 1.04], [-2.2, 1.0]]),
  gh: [-1.94, 0.71],
  mirror: [0.5, 1.03], mirrorPaint: false,
  exhausts: [{ y: 0.31, z: 0.5, ry: 0.044, rz: 0.044 }, { y: 0.31, z: 0.61, ry: 0.044, rz: 0.044 }],
  extra(car, { paint, black }) {
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.41, 1.375], [-1.755, 1.283], [-1.762, 1.266], [-1.645, 1.281]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.06, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2 }), paint);
    sp.position.z = -0.53; sp.castShadow = true; car.add(sp);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.29, 1.4], [-1.49, 1.375], [-1.47, 1.43]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: S_SIDE, tw: 3072, th: 960, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, S_SIDE);
        const o = glassOutline(B, -1.29, [[-1.59, 1.08]], 0.085);
        glassFill(g, o, [[-0.1, 1.19], [-1.15, 1.19]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.58, -0.68], [-1.23, -1.27]]) poly(g, [[a, 0.9], [b, 0.9], [b, 1.5], [a, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: S_SIDE, tw: 3072, th: 960, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, S_SIDE);
        sideTrim(g, S3, B, { sill: 0.22, handles: [[0.0, 0.9], [-1.07, 0.93]],
          lines: [[[0.67, 0.98], [0.67, 0.3]], [[-0.62, 1.0], [-0.62, 0.3]], [[-1.25, 1.05], [-1.25, 0.8], [-1.04, 0.74], [-0.97, 0.62], [-0.97, 0.3]]] });
        poly(g, [[-1.96, 0.985], [-2.18, 0.975], [-2.18, 0.885], [-2.03, 0.905]], '#7a0710', '#14151a', 0.006);
        for (let i = 0; i < 4; i++) rrect(g, -1.98 - i * 0.045, 0.915, 0.03, 0.04, 0.004, '#c3141d');
        poly(g, [[1.84, 0.765], [2.18, 0.73], [2.18, 0.68], [1.9, 0.715]], '#0b0c0f', '#303338', 0.006);
      } },
    { axis: '+y', kind: 'glass', rect: [-0.3, -0.9, 0.8, 0.9], tw: 1024, th: 840, segs: [50, 50], order: 2,
      draw(g, W, H, B) { frame(g, W, H, [-0.3, -0.9, 0.8, 0.9]); const o = screenOutline(B, S3, -0.05, 0.73); poly(g, o, '#0d1117'); trimAround(g, o, 0.025); } },
    { axis: '-x', kind: 'glass', rect: S_REAR, tw: 1024, th: 760, segs: [50, 50], order: 2,
      draw(g, W, H) { frame(g, W, H, S_REAR); const o = [[-0.57, 1.05], [0.57, 1.05], [0.47, 1.27], [-0.47, 1.27]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    { axis: '+x', rect: S_FRONT, tw: 2048, th: 860, segs: [64, 40], draw: (g, W, H) => s3Front(g, W, H, false), glow: (g, W, H) => s3Front(g, W, H, true) },
    { axis: '-x', rect: S_REAR, tw: 2048, th: 1360, segs: [64, 48], draw: (g, W, H) => s3Rear(g, W, H, false), glow: (g, W, H) => s3Rear(g, W, H, true) },
  ],
};


/* ---------------------------------------------------------------- variants: Audi S3 Saloon, Golf R Estate */
// The front halves are the hatchbacks' (shifted so each car stays centred on its own length);
// the roofs, glass and tails are their own.
const shiftPts = (pts, dx, from) => pts.filter(([x]) => x >= from).map(([x, y]) => [x + dx, y]);

const SS_SIDE = [-2.32, 0.08, 2.32, 1.44];
export const S3S = {
  ...S3, name: 'Audi S3 Saloon', L: 4.495, H: 1.41, xf: 1.3425, xr: 1.3425 - 2.631,
  top: [...shiftPts(S3.top, 0.072, -0.42),
        [-0.75, 1.4], [-1.1, 1.34], [-1.45, 1.21], [-1.78, 1.075], [-2.05, 1.055], [-2.2, 1.06], [-2.235, 0.98], [-2.245, 0.8], [-2.2475, 0.45]],
  bottom: [[2.2475, 0.28], [2.22, 0.18], [2.05, 0.15], [1.5, 0.14], [-1.6, 0.15], [-2.1, 0.22], [-2.2475, 0.3]],
  belt: [...shiftPts(S3.belt, 0.072, -1.0), [-1.3, 1.04], [-1.6, 1.055], [-2.2, 1.055]],
  gh: [-1.78, 0.79],
  roofRatio: [[0.75, 0.74], [-0.5, 0.72], [-1.3, 0.68], [-1.78, 0.64]],
  extra(car, { paint, black }) {
    const lip = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-2.08, 1.06], [-2.21, 1.075], [-2.22, 1.06], [-2.15, 1.052]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.1, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.005, bevelSegments: 2 }), paint);
    lip.position.z = -0.55; car.add(lip);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-0.85, 1.395], [-1.05, 1.37], [-1.03, 1.42]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: SS_SIDE, tw: 3072, th: 960, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SS_SIDE);
        const o = glassOutline(B, -1.05, [[-1.36, 1.085], [-1.3, 1.045]], 0.085);
        glassFill(g, o, [[-0.03, 1.19], [-1.05, 1.17]]); trimAround(g, o, 0.03);
        poly(g, [[-0.51, 0.9], [-0.61, 0.9], [-0.61, 1.5], [-0.51, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: SS_SIDE, tw: 3072, th: 960, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SS_SIDE);
        sideTrim(g, S3S, B, { sill: 0.22, handles: [[0.07, 0.9], [-1.0, 0.93]],
          lines: [[[0.74, 0.98], [0.74, 0.3]], [[-0.55, 1.0], [-0.55, 0.3]], [[-1.33, 1.05], [-1.3, 0.78], [-1.0, 0.74], [-0.9, 0.62], [-0.9, 0.3]]] });
        poly(g, [[-2.02, 1.0], [-2.25, 0.99], [-2.25, 0.9], [-2.08, 0.92]], '#7a0710', '#14151a', 0.006);
        poly(g, [[1.91, 0.765], [2.25, 0.73], [2.25, 0.68], [1.97, 0.715]], '#0b0c0f', '#303338', 0.006);
      } },
    { axis: '+y', kind: 'glass', rect: [-1.9, -0.9, 0.9, 0.9], tw: 2048, th: 660, segs: [110, 44], order: 2,
      draw(g, W, H, B) {
        frame(g, W, H, [-1.9, -0.9, 0.9, 0.9]);
        for (const o of [screenOutline(B, S3S, 0.02, 0.8), screenOutline(B, S3S, -1.76, -1.12, 0.07)]) { poly(g, o, '#0d1117'); trimAround(g, o, 0.025); }
      } },
    S3.decals.find(d => d.axis === '+x'),
    { ...S3.decals.find(d => d.axis === '-x' && !d.kind) },
  ],
};

const GE_SIDE = [-2.4, 0.08, 2.4, 1.52], GE_REAR = [-0.94, 0.12, 0.94, 1.5];
export const GOLFE = {
  ...GOLF, name: 'Volkswagen Golf R Estate', L: 4.644, H: 1.465, xf: 1.462, xr: 1.462 - 2.671,
  top: [...shiftPts(GOLF.top, 0.177, -0.3),
        [-0.7, 1.462], [-1.3, 1.44], [-1.8, 1.405], [-2.06, 1.37], [-2.17, 1.28], [-2.26, 1.12], [-2.3, 1.0], [-2.315, 0.75], [-2.322, 0.42]],
  bottom: [[2.322, 0.3], [2.3, 0.18], [2.12, 0.15], [1.6, 0.14], [-1.8, 0.15], [-2.18, 0.22], [-2.322, 0.3]],
  belt: [...shiftPts(GOLF.belt, 0.177, -0.6), [-1.0, 1.0], [-1.6, 1.03], [-2.1, 1.05], [-2.3, 1.03]],
  gh: [-2.27, 1.03],
  roofRatio: [[1.0, 0.74], [-0.5, 0.73], [-1.6, 0.69], [-2.27, 0.65]],
  extra(car, { paint, black }) {
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.86, 1.44], [-2.19, 1.395], [-2.2, 1.375], [-2.06, 1.39]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.06, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2 }), paint);
    sp.position.z = -0.53; car.add(sp);
    const railMat = new THREE.MeshStandardMaterial({ color: 0x1a1c20, metalness: 0.6, roughness: 0.4 });
    for (const sd of [1, -1]) { const rail = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.03, 0.03), railMat); rail.position.set(-0.95, 1.47, sd * 0.5); rail.rotation.z = 0.012; car.add(rail); }
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: GE_SIDE, tw: 3200, th: 1000, segs: [160, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, GE_SIDE);
        const o = glassOutline(B, -2.0, [[-2.17, 1.06]], 0.07);
        glassFill(g, o, [[0.17, 1.18], [-0.78, 1.2]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.083, -0.163], [-1.07, -1.15]]) poly(g, [[a, 0.9], [b, 0.9], [b, 1.55], [a, 1.55]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: GE_SIDE, tw: 3200, th: 1000, segs: [160, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, GE_SIDE);
        sideTrim(g, GOLFE, B, { sill: 0.21, handles: [[0.06, 0.88], [-0.86, 0.92]],
          lines: [[[1.02, 0.96], [1.02, 0.3]], [[-0.12, 0.99], [-0.12, 0.3]], [[-1.09, 1.02], [-1.08, 0.75], [-0.9, 0.7], [-0.83, 0.6], [-0.83, 0.3]]] });
        poly(g, [[-2.1, 0.99], [-2.32, 0.975], [-2.32, 0.9], [-2.16, 0.915]], '#5a0610', '#14151a', 0.006);
        poly(g, [[2.0, 0.75], [2.32, 0.72], [2.32, 0.67], [2.06, 0.705]], '#0b0c0f', '#303338', 0.006);
      } },
    { axis: '+y', kind: 'glass', rect: [-0.3, -0.9, 1.1, 0.9], tw: 1024, th: 660, segs: [50, 50], order: 2,
      draw(g, W, H, B) { frame(g, W, H, [-0.3, -0.9, 1.1, 0.9]); const o = screenOutline(B, GOLFE, -0.07, 1.03); poly(g, o, '#0d1117'); trimAround(g, o, 0.025); } },
    { axis: '-x', kind: 'glass', rect: GE_REAR, tw: 1024, th: 800, segs: [50, 50], order: 2,
      draw(g, W, H) { frame(g, W, H, GE_REAR); const o = [[-0.62, 1.05], [0.62, 1.05], [0.53, 1.36], [-0.53, 1.36]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    GOLF.decals.find(d => d.axis === '+x'),
    GOLF.decals.find(d => d.axis === '-x' && !d.kind),
  ],
};

/* ---------------------------------------------------------------- SEAT Leon Cupra 290 (Mk3 5-door, 2016) */
// Built on the same MQB layout as the Golf: published length, width, height, wheelbase and
// 235/35 R19 tyres; the angular full-LED lights, trapezoid honeycomb grille, sharp "Leon
// line" shoulder crease, side-mounted tail lights and twin exhausts drawn to match the car.
const L_FRONT = [-0.94, 0.1, 0.94, 0.86], L_REAR = [-0.94, 0.12, 0.94, 1.42], L_SIDE = [-2.2, 0.08, 2.2, 1.48];
function seatS(g, x, y, h, col) { // the SEAT "S": two slanted blades
  g.fillStyle = col;
  poly(g, [[x - h * 0.5, y + h * 0.5], [x + h * 0.45, y + h * 0.5], [x + h * 0.3, y + h * 0.12], [x - h * 0.65, y + h * 0.12]], col);
  poly(g, [[x - h * 0.45, y - h * 0.5], [x + h * 0.5, y - h * 0.5], [x + h * 0.65, y - h * 0.12], [x - h * 0.3, y - h * 0.12]], col);
}
const L_LAMP = k => K(k, [[0.36, 0.7], [0.44, 0.752], [0.8, 0.788], [0.88, 0.762], [0.85, 0.69], [0.6, 0.664], [0.46, 0.66]]);
const L_DRL = k => [[k * 0.45, 0.742], [k * 0.8, 0.775], [k * 0.84, 0.75], [k * 0.6, 0.684]];
function leonFront(g, W, H, lit) {
  frame(g, W, H, L_FRONT);
  if (lit) {
    g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4);
    both(k => { g.beginPath(); L_DRL(k).forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.strokeStyle = '#fff'; g.lineWidth = 0.011; g.lineJoin = 'round'; g.stroke(); });
    return;
  }
  poly(g, [[-0.9, 0.12], [0.9, 0.12], [0.86, 0.18], [-0.86, 0.18]], '#0b0c0e');
  const low = [[-0.44, 0.2], [0.44, 0.2], [0.5, 0.36], [-0.5, 0.36]];          // lower intake
  honeycomb(g, low, 0.018, '#060708', '#1d1f23'); poly(g, low, null, '#1a1c20', 0.012);
  both(k => {                                                                       // corner intakes
    const side = K(k, [[0.56, 0.2], [0.88, 0.22], [0.9, 0.5], [0.7, 0.5], [0.6, 0.38]]);
    honeycomb(g, side, 0.016, '#060708', '#1d1f23'); poly(g, side, null, '#1a1c20', 0.01);
    poly(g, K(k, [[0.6, 0.4], [0.86, 0.42], [0.86, 0.44], [0.62, 0.43]]), '#2a2c30');
  });
  ukPlate(g, 0, 0.43, 'CUPR4 290', false);
  const grille = [[-0.33, 0.69], [0.33, 0.69], [0.44, 0.61], [0.38, 0.5], [-0.38, 0.5], [-0.44, 0.61]];
  honeycomb(g, grille, 0.021, '#050607', '#2a2d33'); poly(g, grille, null, '#3a3d43', 0.016);
  seatS(g, 0, 0.64, 0.055, '#c9ccd2');
  txt(g, 'CUPRA', -0.24, 0.535, 0.024, 'bold', '#b9bdc4');
  both(k => {
    poly(g, L_LAMP(k), '#0a0b0e', '#2e3238', 0.006);
    g.beginPath(); L_DRL(k).forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.strokeStyle = '#eef3fa'; g.lineWidth = 0.011; g.lineJoin = 'round'; g.stroke();
    for (const x of [0.55, 0.7]) { g.beginPath(); g.arc(k * x, 0.72, 0.024, 0, Math.PI * 2); g.fillStyle = '#333c4a'; g.fill(); }
  });
}
function leonRear(g, W, H, lit) {
  frame(g, W, H, L_REAR);
  const lamp = k => K(k, [[0.48, 0.995], [0.86, 0.985], [0.93, 0.94], [0.9, 0.875], [0.52, 0.895]]);
  const leds = k => { for (const dy of [0.0, 0.035]) { g.beginPath(); g.moveTo(k * 0.56, 0.94 + dy); g.lineTo(k * 0.86, 0.935 + dy * 0.8); g.strokeStyle = lit ? '#ff2a30' : '#d0141a'; g.lineWidth = 0.011; g.stroke(); } };
  if (lit) { g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4); both(leds); return; }
  poly(g, [[-0.9, 0.14], [0.9, 0.14], [0.86, 0.36], [-0.86, 0.36]], '#0a0b0d', '#24262a', 0.008);
  slats(g, [[-0.34, 0.15], [0.34, 0.15], [0.34, 0.31], [-0.34, 0.31]], 5, 0, 0, '#08090a', '#1c1e22', true, -0.34, 0.34);
  both(k => rrect(g, k * 0.86 - 0.012, 0.4, 0.024, 0.08, 0.006, '#6a0b0e'));
  poly(g, [[-0.5, 0.66], [0.5, 0.66], [0.52, 1.0], [-0.52, 1.0]], 'rgba(0,0,0,0.12)');   // tailgate shut line
  ukPlate(g, 0, 0.76, 'CUPR4 290', true);
  both(k => { poly(g, lamp(k), '#4a050a', '#14151a', 0.008); leds(k); });
  seatS(g, 0, 0.93, 0.07, '#d4d7dc');
  txt(g, 'CUPRA', 0.36, 0.85, 0.032, 'bold italic', '#d7dade');
  txt(g, 'Leon', -0.38, 0.85, 0.032, 'italic', '#d7dade');
  rrect(g, -0.2, 1.39, 0.4, 0.016, 0.006, '#6a0b0e');
}
export const LEON = {
  name: 'SEAT Leon Cupra 290',
  L: 4.271, W: 1.816, H: 1.435, xf: 1.2555, xr: 1.2555 - 2.636,
  Rf: 0.3236, Rr: 0.3236, rimR: 0.2413, tyreW: 0.235, track: 1.52,
  paint: 0xa50f19, wheelColor: 0x2c2e33, wheelRough: 0.3, caliper: 0xb01c1c, spokes: 10, spokeFill: 0.4, splitSpoke: false,
  N: 170, M: 52, rF: 0.58, rR: 0.45, cornerP: 2.3, Wb: 1.79, flareF: 0.012, flareR: 0.014, flareLen: 0.4, archGap: 0.03, archRound: 1.0,
  ledge: 0.07, roofRatio: [[0.85, 0.74], [-0.5, 0.72], [-1.3, 0.67], [-1.9, 0.62]],
  creaseIn: [[2.0, 0.015], [0.5, 0.022], [-0.8, 0.03], [-1.5, 0.05], [-2.1, 0.05]],
  crease: [[2.05, 0.72], [1.6, 0.795], [1.0, 0.83], [0, 0.85], [-1.4, 0.88], [-2.05, 0.9]],
  top: [[2.1355, 0.4], [2.128, 0.55], [2.1, 0.665], [2.03, 0.74], [1.87, 0.795], [1.4, 0.865], [0.85, 0.952], [0.5, 1.12], [0.1, 1.305],
        [-0.28, 1.405], [-0.6, 1.43], [-1.0, 1.435], [-1.3, 1.42], [-1.5, 1.395], [-1.6, 1.36], [-1.72, 1.24], [-1.84, 1.1],
        [-1.93, 1.0], [-2.05, 0.94], [-2.12, 0.84], [-2.13, 0.66], [-2.1355, 0.42]],
  bottom: [[2.1355, 0.3], [2.11, 0.18], [1.95, 0.15], [1.5, 0.14], [-1.6, 0.15], [-2.0, 0.22], [-2.1355, 0.3]],
  belt: [[0.85, 0.952], [0.3, 0.962], [-0.6, 0.982], [-1.2, 1.012], [-1.55, 1.04], [-1.93, 0.99]],
  gh: [-1.93, 0.85],
  mirror: [0.62, 1.01], mirrorPaint: true,
  exhausts: [{ y: 0.27, z: 0.6, ry: 0.045, rz: 0.068 }],
  extra(car, { paint, black }) {
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.32, 1.428], [-1.66, 1.35], [-1.67, 1.33], [-1.55, 1.345]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.0, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2 }), black);
    sp.position.z = -0.5; sp.castShadow = true; car.add(sp);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.1, 1.43], [-1.3, 1.41], [-1.28, 1.47]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: L_SIDE, tw: 3072, th: 1000, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, L_SIDE);
        const o = glassOutline(B, -1.12, [[-1.4, 1.02], [-1.33, 1.0]], 0.07);
        glassFill(g, o, [[0.0, 1.16], [-0.95, 1.18]]); trimAround(g, o, 0.03);
        poly(g, [[-0.27, 0.9], [-0.36, 0.9], [-0.36, 1.5], [-0.27, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: L_SIDE, tw: 3072, th: 1000, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, L_SIDE);
        sideTrim(g, LEON, B, { sill: 0.21, handles: [[-0.1, 0.88], [-1.02, 0.91]],
          lines: [[[0.84, 0.95], [0.84, 0.3]], [[-0.31, 0.98], [-0.31, 0.3]], [[-1.33, 1.0], [-1.3, 0.76], [-1.05, 0.7], [-0.98, 0.6], [-0.98, 0.3]]] });
        // the lower "Leon line": a crease rising from the front door to the rear arch
        g.strokeStyle = 'rgba(255,255,255,0.10)'; g.lineWidth = 0.008; g.beginPath(); g.moveTo(0.85, 0.5); g.lineTo(-0.6, 0.56); g.lineTo(-1.0, 0.62); g.stroke();
        g.strokeStyle = 'rgba(0,0,0,0.35)'; g.lineWidth = 0.006; g.beginPath(); g.moveTo(0.85, 0.49); g.lineTo(-0.6, 0.55); g.lineTo(-1.0, 0.61); g.stroke();
        poly(g, [[-1.84, 0.995], [-2.13, 0.975], [-2.13, 0.875], [-1.94, 0.895]], '#7a0812', '#14151a', 0.006);   // tail-light wrap
        for (const dy of [0, 0.035]) { g.beginPath(); g.moveTo(-1.9, 0.93 + dy); g.lineTo(-2.13, 0.925 + dy); g.strokeStyle = '#e0141c'; g.lineWidth = 0.01; g.stroke(); }
        poly(g, [[1.8, 0.75], [2.13, 0.72], [2.13, 0.66], [1.86, 0.7]], '#0b0c0f', '#303338', 0.006);        // headlight tip
        txt(g, 'CUPRA', 1.5, 0.66, 0.03, 'bold', '#c9ccd2');
      } },
    { axis: '+y', kind: 'glass', rect: [-0.4, -0.9, 0.9, 0.9], tw: 1024, th: 720, segs: [50, 50], order: 2,
      draw(g, W, H, B) { frame(g, W, H, [-0.4, -0.9, 0.9, 0.9]); const o = screenOutline(B, LEON, -0.24, 0.86); poly(g, o, '#0d1117'); trimAround(g, o, 0.025); } },
    { axis: '-x', kind: 'glass', rect: L_REAR, tw: 1024, th: 780, segs: [50, 50], order: 2,
      draw(g, W, H) { frame(g, W, H, L_REAR); const o = [[-0.58, 1.03], [0.58, 1.03], [0.47, 1.33], [-0.47, 1.33]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    { axis: '+x', rect: L_FRONT, tw: 2048, th: 820, segs: [64, 40], draw: (g, W, H) => leonFront(g, W, H, false), glow: (g, W, H) => leonFront(g, W, H, true) },
    { axis: '-x', rect: L_REAR, tw: 2048, th: 1400, segs: [64, 52], draw: (g, W, H) => leonRear(g, W, H, false), glow: (g, W, H) => leonRear(g, W, H, true) },
  ],
};

export const CARS = { leon: { spec: LEON, color: 0xf2a65a }, s3: { spec: S3, color: 0xff4a4a }, golf: { spec: GOLF, color: 0x3d8bff } };

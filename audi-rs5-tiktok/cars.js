// The 2026 Audi RS5 saloon (B10), described for car3d.js. Coordinates in metres: x
// forward (front axle ahead of the origin), y up from the road, z to the car's left.
// Length, width, height and wheelbase are Audi's; the fastback roof and ducktail, the
// slim pixel headlights with their checkered-flag daytime lights, the wide honeycomb
// Singleframe, the full-width OLED rear light and the central oval tailpipes were
// matched to Audi's press photos of the Progressive red launch car.
import * as THREE from 'three';
import { K, both, frame, glassFill, glassOutline, honeycomb, poly, rings, rrect, screenOutline, sideTrim, slats, trimAround, txt, ukPlate } from './decals.js';

const FRONT = [-1.0, 0.1, 1.0, 0.86], REAR = [-1.0, 0.12, 1.0, 1.16], SIDE = [-2.5, 0.08, 2.5, 1.48];

function checker(g, x0, y0, w, h, n, m, on, off) { // n x m checkered-flag pixels
  const cw = w / n, ch = h / m;
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) { g.fillStyle = (i + j) % 2 ? off : on; g.fillRect(x0 + i * cw, y0 + j * ch, cw * 0.86, ch * 0.8); }
}
const LAMP = k => K(k, [[0.44, 0.672], [0.52, 0.715], [0.86, 0.752], [0.94, 0.732], [0.91, 0.688], [0.62, 0.664], [0.5, 0.654]]);
function front(g, W, H, lit) {
  frame(g, W, H, FRONT);
  const drl = k => { for (let i = 0; i < 9; i++) { const x = 0.55 + i * 0.036, y = 0.708 + (x - 0.52) * 0.1; checker(g, k > 0 ? x : -x - 0.03, y, 0.03, 0.024, 2, 2, lit ? '#ffffff' : '#e8eef6', lit ? '#000' : '#1a1d22'); } };
  if (lit) { g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4); both(drl); return; }
  poly(g, [[-0.94, 0.12], [0.94, 0.12], [0.9, 0.18], [-0.9, 0.18]], '#0a0b0d');
  // dark mask: Singleframe + air curtains as one black band
  poly(g, [[-0.96, 0.2], [0.96, 0.2], [0.98, 0.5], [0.86, 0.58], [0.5, 0.64], [-0.5, 0.64], [-0.86, 0.58], [-0.98, 0.5]], '#0c0d10');
  const sf = [[-0.44, 0.63], [0.44, 0.63], [0.54, 0.54], [0.56, 0.3], [0.46, 0.21], [-0.46, 0.21], [-0.56, 0.3], [-0.54, 0.54]];
  honeycomb(g, sf, 0.03, '#050607', '#1f2227'); poly(g, sf, null, '#2a2d33', 0.014);
  both(k => {
    const ac = K(k, [[0.64, 0.22], [0.92, 0.23], [0.95, 0.5], [0.84, 0.56], [0.66, 0.46]]);
    honeycomb(g, ac, 0.022, '#050607', '#1c1f24'); poly(g, ac, null, '#24272c', 0.01);
    poly(g, K(k, [[0.93, 0.26], [0.97, 0.27], [0.97, 0.48], [0.94, 0.5]]), '#030304');   // air curtain slot
  });
  rings(g, 0, 0.66, 0.036, '#0b0c0e', 0.012);   // black rings on the leading edge
  ukPlate(g, 0, 0.33, 'RS5 HYB', false);
  rrect(g, -0.42, 0.565, 0.07, 0.03, 0.004, '#202227'); txt(g, 'RS 5', -0.385, 0.58, 0.022, 'bold', '#c8161d');
  both(k => { poly(g, LAMP(k), '#08090c', '#2a2d33', 0.006); drl(k); });
}
function rear(g, W, H, lit) {
  frame(g, W, H, REAR);
  const bar = () => {
    g.fillStyle = lit ? '#ff2a30' : '#b8121b'; g.fillRect(-0.62, 0.935, 1.24, 0.012);   // the full-width light strip
    both(k => checker(g, k > 0 ? 0.62 : -0.9, 0.915, 0.28, 0.05, 8, 2, lit ? '#ff2a30' : '#d0141c', lit ? '#000' : '#3a0408'));
  };
  if (lit) { g.fillStyle = '#000'; g.fillRect(-2, -2, 4, 4); bar(); return; }
  poly(g, [[-0.92, 0.14], [0.92, 0.14], [0.88, 0.42], [-0.88, 0.42]], '#0a0b0d', '#24262a', 0.008);
  slats(g, [[-0.62, 0.15], [0.62, 0.15], [0.62, 0.38], [-0.62, 0.38]], 7, 0, 0, '#08090a', '#202226', true, -0.62, 0.62);   // vertical fins
  poly(g, [[-0.94, 0.9], [0.94, 0.9], [0.95, 0.965], [-0.95, 0.965]], '#120305', '#18191d', 0.006);
  bar();
  rings(g, 0, 1.01, 0.04, '#0b0c0e', 0.011);
  ukPlate(g, 0, 0.74, 'RS5 HYB', true);
  rrect(g, -0.5, 0.64, 0.1, 0.034, 0.004, '#202227'); txt(g, 'RS 5', -0.45, 0.657, 0.026, 'bold', '#c8161d');
}

export const RS5 = {
  name: 'Audi RS 5 Saloon',
  L: 4.896, W: 1.952, H: 1.428, xf: 1.508, xr: 1.508 - 2.903,
  Rf: 0.345, Rr: 0.345, rimR: 0.254, tyreW: 0.275, track: 1.66,
  paint: 0x9c0f1a, wheelColor: 0x1d1f23, wheelRough: 0.34, caliper: 0x3a3c41, spokes: 10, spokeFill: 0.36, splitSpoke: true,
  N: 180, M: 52, rF: 0.62, rR: 0.5, cornerP: 2.3, Wb: 1.86, flareF: 0.042, flareR: 0.048, flareLen: 0.48, archGap: 0.025, archRound: 1.0,
  ledge: 0.075, roofRatio: [[0.95, 0.74], [-0.5, 0.72], [-1.3, 0.66], [-1.85, 0.6]],
  creaseIn: [[2.3, 0.02], [0.6, 0.028], [-0.6, 0.035], [-1.4, 0.06], [-2.4, 0.06]],
  crease: [[2.35, 0.72], [1.9, 0.82], [1.2, 0.86], [0, 0.87], [-1.5, 0.9], [-2.35, 0.91]],
  top: [[2.448, 0.4], [2.44, 0.55], [2.41, 0.67], [2.34, 0.75], [2.15, 0.8], [1.6, 0.875], [0.95, 0.968], [0.6, 1.14], [0.2, 1.33],
        [-0.15, 1.41], [-0.45, 1.428], [-0.9, 1.41], [-1.3, 1.345], [-1.65, 1.25], [-1.95, 1.155], [-2.17, 1.075], [-2.3, 1.075],
        [-2.38, 1.0], [-2.43, 0.82], [-2.448, 0.45]],
  bottom: [[2.448, 0.3], [2.42, 0.17], [2.2, 0.14], [1.8, 0.13], [-1.8, 0.14], [-2.3, 0.2], [-2.448, 0.32]],
  belt: [[0.95, 0.968], [0.4, 0.978], [-0.6, 0.998], [-1.3, 1.03], [-1.75, 1.06], [-2.0, 1.07]],
  gh: [-1.95, 0.95],
  mirror: [0.88, 1.03], mirrorPaint: false,
  exhausts: [{ y: 0.3, z: 0.3, ry: 0.05, rz: 0.088 }],
  extra(car, { black }) {
    const lip = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-2.2, 1.076], [-2.37, 1.094], [-2.38, 1.074], [-2.28, 1.066]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 1.3, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.005, bevelSegments: 2 }), black);
    lip.position.z = -0.65; car.add(lip);   // the ducktail's black lip
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-0.95, 1.41], [-1.17, 1.375], [-1.15, 1.44]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SIDE);
        const o = glassOutline(B, -1.22, [[-1.62, 1.07], [-1.55, 1.04]], 0.075);
        glassFill(g, o, [[0.15, 1.27], [-0.85, 1.25]]); trimAround(g, o, 0.032);
        poly(g, [[-0.33, 0.95], [-0.43, 0.95], [-0.43, 1.6], [-0.33, 1.6]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: SIDE, tw: 3600, th: 1060, segs: [170, 46], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, SIDE);
        sideTrim(g, RS5, B, { sill: 0.25, handles: [[0.1, 0.95], [-0.95, 0.98]],
          lines: [[[0.98, 1.0], [0.98, 0.3]], [[-0.38, 1.02], [-0.38, 0.3]], [[-1.52, 1.06], [-1.5, 0.82], [-1.15, 0.76], [-1.05, 0.62], [-1.05, 0.3]]] });
        poly(g, [[-2.15, 0.97], [-2.45, 0.955], [-2.45, 0.9], [-2.2, 0.91]], '#4a050a', '#151619', 0.006);   // light bar wrapping round
        g.beginPath(); g.moveTo(-2.18, 0.935); g.lineTo(-2.45, 0.928); g.strokeStyle = '#d0141c'; g.lineWidth = 0.01; g.stroke();
        poly(g, [[2.12, 0.75], [2.45, 0.72], [2.45, 0.67], [2.18, 0.7]], '#08090c', '#2a2d33', 0.006);    // headlight tip
        poly(g, [[1.02, 0.66], [0.94, 0.64], [0.95, 0.46], [1.03, 0.44]], '#0b0c0e');                       // air outlet behind the front wheel
      } },
    { axis: '+y', kind: 'glass', rect: [-2.25, -1.0, 1.1, 1.0], tw: 2048, th: 620, segs: [130, 40], order: 2,
      draw(g, W, H, B) {
        frame(g, W, H, [-2.25, -1.0, 1.1, 1.0]);
        for (const o of [screenOutline(B, RS5, 0.0, 0.96), screenOutline(B, RS5, -2.12, -1.2, 0.07)]) { poly(g, o, '#0d1117'); trimAround(g, o, 0.025); }
      } },
    { axis: '+x', rect: FRONT, tw: 2048, th: 820, segs: [64, 40], draw: (g, W, H) => front(g, W, H, false), glow: (g, W, H) => front(g, W, H, true) },
    { axis: '-x', rect: REAR, tw: 2048, th: 1060, segs: [64, 44], draw: (g, W, H) => rear(g, W, H, false), glow: (g, W, H) => rear(g, W, H, true) },
  ],
};

export const CARS = { rs5: { spec: RS5, color: 0xff3a3a } };

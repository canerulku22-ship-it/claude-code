// The two cars, described for car3d.js. Coordinates in metres: x forward (front axle
// ahead of the origin), y up from the road, z to the car's left. Dimensions are the
// published ones; the silhouettes, lights and grilles were matched to the press photos.
import * as THREE from 'three';

/* ---------------------------------------------------------------- drawing helpers */
// Every decal is drawn in metres as seen from outside the car: X to the right, Y up.
function frame(g, W, H, [u0, v0, u1, v1]) {
  g.transform(W / (u1 - u0), 0, 0, -H / (v1 - v0), -u0 * W / (u1 - u0), v1 * H / (v1 - v0));
}
function poly(g, pts, fill, stroke, lw) {
  g.beginPath(); pts.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath();
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 0.006; g.stroke(); }
}
const mirrorX = pts => pts.map(([x, y]) => [-x, y]);
function rrect(g, x, y, w, h, r, fill, stroke, lw) {
  g.beginPath(); g.roundRect(x, y, w, h, r);
  if (fill) { g.fillStyle = fill; g.fill(); }
  if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 0.006; g.stroke(); }
}
function txt(g, s, x, y, h, font, color, align = 'center') {
  g.save(); g.translate(x, y); g.scale(h / 100, -h / 100);
  g.font = `${font} 100px Arial, Helvetica, sans-serif`; g.fillStyle = color; g.textAlign = align; g.textBaseline = 'middle';
  g.fillText(s, 0, 0); g.restore();
}
function ukPlate(g, x, y, text, rear) {  // 520 x 111 mm
  rrect(g, x - 0.26, y - 0.0555, 0.52, 0.111, 0.012, rear ? '#f4c400' : '#f3f3ee', '#151515', 0.004);
  txt(g, text, x + 0.012, y - 0.003, 0.082, 'bold', '#111');
  rrect(g, x - 0.255, y - 0.05, 0.04, 0.1, 0.008, '#123b8c');
  txt(g, 'UK', x - 0.235, y - 0.03, 0.022, 'bold', '#fff');
}
function rings(g, x, y, r, color, lw) {
  g.strokeStyle = color; g.lineWidth = lw;
  for (let i = 0; i < 4; i++) { g.beginPath(); g.arc(x + (i - 1.5) * r * 1.45, y, r, 0, Math.PI * 2); g.stroke(); }
}
function roundel(g, x, y, r) {
  g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fillStyle = '#111'; g.fill();
  g.strokeStyle = '#c9ccd2'; g.lineWidth = r * 0.08; g.stroke();
  const ri = r * 0.62;
  for (let q = 0; q < 4; q++) {
    g.beginPath(); g.moveTo(x, y); g.arc(x, y, ri, q * Math.PI / 2, (q + 1) * Math.PI / 2); g.closePath();
    g.fillStyle = q % 2 ? '#f4f6f8' : '#1c69d4'; g.fill();
  }
  g.beginPath(); g.arc(x, y, ri, 0, Math.PI * 2); g.strokeStyle = '#c9ccd2'; g.lineWidth = r * 0.05; g.stroke();
}
function mStripes(g, x, y, h) {
  const w = h * 0.9;
  ['#7fc0ec', '#22336e', '#e12a26'].forEach((c, i) => {
    g.beginPath(); g.moveTo(x + i * w * 0.42, y); g.lineTo(x + i * w * 0.42 + w * 0.36, y); g.lineTo(x + i * w * 0.42 + w * 0.36 + h * 0.25, y + h); g.lineTo(x + i * w * 0.42 + h * 0.25, y + h); g.closePath(); g.fillStyle = c; g.fill();
  });
}
function honeycomb(g, pts, size, base, line) {
  g.save(); poly(g, pts, base); g.clip();
  g.strokeStyle = line; g.lineWidth = size * 0.28;
  const dx = size * Math.sqrt(3), dy = size * 1.5;
  for (let r = -30; r < 30; r++) for (let c = -40; c < 40; c++) {
    const cx = c * dx + (r & 1 ? dx / 2 : 0), cy = r * dy;
    if (Math.abs(cx) > 1.2 || cy < 0 || cy > 1.2) continue;
    g.beginPath();
    for (let k = 0; k < 6; k++) { const a = Math.PI / 6 + k * Math.PI / 3; g[k ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * size, cy + Math.sin(a) * size); }
    g.closePath(); g.stroke();
  }
  g.restore();
}
function slats(g, pts, n, y0, y1, base, line, vertical = false, x0 = -1, x1 = 1) {
  g.save(); poly(g, pts, base); g.clip(); g.strokeStyle = line; g.lineWidth = (vertical ? (x1 - x0) : (y1 - y0)) / n * 0.38;
  for (let i = 0; i <= n; i++) {
    g.beginPath();
    if (vertical) { const x = x0 + (x1 - x0) * i / n; g.moveTo(x, y0); g.lineTo(x, y1); }
    else { const y = y0 + (y1 - y0) * i / n; g.moveTo(x0, y); g.lineTo(x1, y); }
    g.stroke();
  }
  g.restore();
}

// Side glass: follows the body's own roofline and belt, so it always fits the shell.
const both = (fn) => { fn(1); fn(-1); };
const K = (k, pts) => pts.map(([x, y]) => [k * x, y]);

function trimAround(g, pts, w) { poly(g, pts, null, '#0a0b0d', w); }
// Side glass outline: follows the body's own roofline and belt, so it always fits the shell.
function glassOutline(B, xRearTop, rearEdge, drop = 0.06, xFront = 2) {
  let x0 = xFront;
  while (B.top(x0) - drop - B.belt(x0) < 0.012 && x0 > xRearTop) x0 -= 0.004;
  const pts = [];
  for (let x = x0; x > xRearTop; x -= 0.02) pts.push([x, B.top(x) - drop]);
  pts.push([xRearTop, B.top(xRearTop) - drop], ...rearEdge);
  for (let x = rearEdge[rearEdge.length - 1][0] + 0.02; x < x0; x += 0.02) pts.push([x, B.belt(x) + 0.006]);
  return pts;
}
// Windscreen / rear window outline seen from above, in (x, z)
function screenOutline(B, S, xA, xB, inset = 0.05) {
  const hw = x => Math.min(B.upperWidth(x) - B.ledge(x) - inset, B.widthBase(x) * B.roofRatio(x) + 0.03);
  const n = 24, L = [], R = [];
  for (let i = 0; i <= n; i++) { const x = xA + (xB - xA) * i / n; L.push([x, hw(x)]); R.unshift([x, -hw(x)]); }
  return [...L, ...R];
}
function glassFill(g, pts, heads = []) {
  g.save(); poly(g, pts, '#0e1319'); g.clip();
  const gr = g.createLinearGradient(0, 0.95, 0, 1.45); gr.addColorStop(0, 'rgba(40,48,58,0.0)'); gr.addColorStop(1, 'rgba(40,48,58,0.55)');
  g.fillStyle = gr; g.fillRect(-3, 0.8, 6, 0.8);
  for (const [x, y] of heads) rrect(g, x - 0.07, y - 0.06, 0.14, 0.13, 0.05, '#1c2129');
  g.restore();
}
function sideTrim(g, S, B, o) {
  // side skirt between the arches
  const xa = S.xf - S.Rf - S.archGap + 0.02, xb = S.xr + S.Rr + S.archGap - 0.02;
  poly(g, [[xa, 0.1], [xa, o.sill + 0.02], [xa - 0.12, o.sill], [xb + 0.12, o.sill], [xb, o.sill + 0.02], [xb, 0.1]], '#0c0d0f');
  g.strokeStyle = 'rgba(0,0,0,0.6)'; g.lineWidth = 0.004;
  for (const l of o.lines) { g.beginPath(); l.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); }
  for (const [x, y] of o.handles) {
    rrect(g, x - 0.085, y - 0.017, 0.17, 0.034, 0.015, 'rgba(0,0,0,0.38)');
    rrect(g, x - 0.075, y + 0.004, 0.15, 0.008, 0.004, 'rgba(255,255,255,0.18)');
  }
}

/* ---------------------------------------------------------------- Audi RS 3 Sportback (8Y, 2024) */
const RS3_FRONT = [-0.96, 0.10, 0.96, 0.92], RS3_REAR = [-0.96, 0.14, 0.96, 1.42], RS3_SIDE = [-2.25, 0.08, 2.25, 1.46];
export const RS3 = {
  name: 'Audi RS 3 Sportback',
  L: 4.389, W: 1.851, H: 1.436, xf: 1.2645, xr: 1.2645 - 2.631,
  Rf: 0.321, Rr: 0.321, rimR: 0.243, tyreW: 0.265, track: 1.575,
  paint: 0x5cb51c, wheelColor: 0x2b2d31, wheelRough: 0.32, caliper: 0xc8161d, spokes: 10, spokeFill: 0.42, splitSpoke: false,
  N: 170, M: 52, rF: 0.62, rR: 0.48, cornerP: 2.3, Wb: 1.80, flareF: 0.028, flareR: 0.032, flareLen: 0.42, archGap: 0.035, archRound: 1.0,
  ledge: 0.07, roofRatio: [[0.7, 0.74], [-0.5, 0.72], [-1.4, 0.66], [-2.1, 0.62]],
  creaseIn: [[2.1, 0.015], [0.5, 0.02], [-0.8, 0.03], [-1.4, 0.05], [-2.2, 0.055]],
  crease: [[2.15, 0.7], [1.8, 0.79], [1.2, 0.845], [0, 0.86], [-1.5, 0.875], [-2.15, 0.88]],
  top: [[2.1945, 0.34], [2.185, 0.5], [2.165, 0.62], [2.12, 0.72], [2.03, 0.79], [1.85, 0.83], [1.4, 0.885], [1.0, 0.935],
        [0.72, 0.975], [0.35, 1.16], [-0.05, 1.36], [-0.4, 1.434], [-0.7, 1.436], [-1.1, 1.412], [-1.42, 1.372], [-1.6, 1.336],
        [-1.7, 1.29], [-1.84, 1.15], [-1.96, 1.04], [-2.08, 0.96], [-2.16, 0.84], [-2.19, 0.66], [-2.1945, 0.45]],
  bottom: [[2.1945, 0.28], [2.17, 0.18], [2.0, 0.15], [1.5, 0.14], [-1.6, 0.15], [-2.05, 0.22], [-2.1945, 0.3]],
  belt: [[0.72, 0.985], [0.3, 0.99], [-0.6, 1.012], [-1.3, 1.05], [-1.7, 1.085], [-2.0, 1.04], [-2.2, 1.0]],
  gh: [-1.96, 0.72],
  mirror: [0.5, 1.03], mirrorPaint: false,
  exhausts: [{ y: 0.33, z: 0.6, ry: 0.052, rz: 0.075 }],
  extra(car, { paint, black }) {
    const sh = new THREE.Shape([[-1.42, 1.385], [-1.77, 1.292], [-1.777, 1.275], [-1.66, 1.29]].map(([x, y]) => new THREE.Vector2(x, y)));
    const sp = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 1.08, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.008, bevelSegments: 2 }), paint);
    sp.position.z = -0.54; sp.castShadow = true; car.add(sp);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-1.3, 1.41], [-1.5, 1.385], [-1.48, 1.44]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: RS3_SIDE, tw: 3072, th: 960, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, RS3_SIDE);
        const o = glassOutline(B, -1.3, [[-1.6, 1.09]], 0.085);
        glassFill(g, o, [[-0.1, 1.2], [-1.15, 1.2]]); trimAround(g, o, 0.03);
        for (const [a, b] of [[-0.58, -0.68], [-1.24, -1.28]]) poly(g, [[a, 0.9], [b, 0.9], [b, 1.5], [a, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: RS3_SIDE, tw: 3072, th: 960, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, RS3_SIDE);
        sideTrim(g, RS3, B, { sill: 0.29, handles: [[0.0, 0.9], [-1.08, 0.93]],
          lines: [[[0.68, 0.98], [0.68, 0.3]], [[-0.63, 1.0], [-0.63, 0.3]], [[-1.26, 1.05], [-1.26, 0.8], [-1.05, 0.74], [-0.98, 0.62], [-0.98, 0.3]]] });
        // vent behind the front wheel
        poly(g, [[0.85, 0.62], [0.78, 0.6], [0.8, 0.42], [0.87, 0.4]], '#0b0c0e');
        // tail light wrapping round the corner, and the headlight's tip
        poly(g, [[-1.98, 0.985], [-2.2, 0.975], [-2.2, 0.885], [-2.05, 0.905]], '#7a0710', '#14151a', 0.006);
        for (let i = 0; i < 4; i++) rrect(g, -2.0 - i * 0.045, 0.915, 0.03, 0.04, 0.004, '#c3141d');
        poly(g, [[1.86, 0.765], [2.2, 0.73], [2.2, 0.68], [1.92, 0.715]], '#0b0c0f', '#303338', 0.006);
      } },
    { axis: '+y', kind: 'glass', rect: [-0.3, -0.9, 0.8, 0.9], tw: 1024, th: 840, segs: [50, 50], order: 2,
      draw(g, W, H, B) { frame(g, W, H, [-0.3, -0.9, 0.8, 0.9]); const o = screenOutline(B, RS3, -0.05, 0.74); poly(g, o, '#0d1117'); trimAround(g, o, 0.025); } },
    { axis: '-x', kind: 'glass', rect: RS3_REAR, tw: 1024, th: 760, segs: [50, 50], order: 2,
      draw(g, W, H) { frame(g, W, H, RS3_REAR); const o = [[-0.58, 1.06], [0.58, 1.06], [0.48, 1.28], [-0.48, 1.28]]; poly(g, o, '#0d1117'); trimAround(g, o, 0.02); } },
    { axis: '+x', rect: RS3_FRONT, tw: 2048, th: 860, segs: [64, 40],
      draw(g, W, H) {
        frame(g, W, H, RS3_FRONT);
        poly(g, [[-0.9, 0.12], [0.9, 0.12], [0.86, 0.19], [-0.86, 0.19]], '#0b0c0e');
        both(k => {
          poly(g, K(k, [[0.58, 0.22], [0.9, 0.24], [0.94, 0.52], [0.78, 0.56], [0.62, 0.47]]), '#0d0e10', '#2a2c30', 0.008);
          honeycomb(g, K(k, [[0.6, 0.24], [0.88, 0.26], [0.91, 0.5], [0.78, 0.53], [0.64, 0.46]]), 0.018, '#060708', '#1d1f23');
          poly(g, K(k, [[0.74, 0.24], [0.77, 0.24], [0.79, 0.54], [0.76, 0.545]]), '#1a1c20');
        });
        const grille = [[-0.44, 0.665], [0.44, 0.665], [0.53, 0.6], [0.58, 0.33], [0.5, 0.24], [-0.5, 0.24], [-0.58, 0.33], [-0.53, 0.6]];
        poly(g, grille, null, '#2b2e33', 0.03);
        honeycomb(g, grille, 0.024, '#050607', '#1e2125');
        rings(g, 0, 0.605, 0.042, '#0d0e10', 0.012);
        rings(g, 0, 0.605, 0.042, '#4a4d53', 0.004);
        rrect(g, -0.32, 0.585, 0.06, 0.03, 0.004, '#3a3d42'); rrect(g, -0.318, 0.587, 0.022, 0.026, 0.003, '#d0141a');
        ukPlate(g, 0, 0.42, 'RS3 VS', false);
        both(k => {
          poly(g, K(k, [[0.5, 0.705], [0.83, 0.765], [0.87, 0.73], [0.8, 0.68], [0.55, 0.655]]), '#0b0c0f', '#303338', 0.006);
          for (let i = 0; i < 12; i++) { const x = 0.54 + i * 0.025, y = 0.703 + (x - 0.5) * 0.18; rrect(g, k * x - 0.009, y - 0.006, 0.018, 0.012, 0.002, '#dfe6ee'); }
          poly(g, K(k, [[0.62, 0.69], [0.76, 0.705], [0.76, 0.685], [0.62, 0.672]]), '#1d2128');
        });
      },
      glow(g, W, H) {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); frame(g, W, H, RS3_FRONT);
        both(k => { for (let i = 0; i < 12; i++) { const x = 0.54 + i * 0.025, y = 0.703 + (x - 0.5) * 0.18; rrect(g, k * x - 0.009, y - 0.006, 0.018, 0.012, 0.002, '#ffffff'); } });
      } },
    { axis: '-x', rect: RS3_REAR, tw: 2048, th: 1360, segs: [64, 48],
      draw(g, W, H) {
        frame(g, W, H, RS3_REAR);
        poly(g, [[-0.9, 0.16], [0.9, 0.16], [0.88, 0.42], [0.72, 0.44], [-0.72, 0.44], [-0.88, 0.42]], '#0a0b0d', '#24262a', 0.008);
        slats(g, [[-0.5, 0.17], [0.5, 0.17], [0.5, 0.36], [-0.5, 0.36]], 6, 0, 0, '#08090a', '#1c1e22', true, -0.5, 0.5);
        both(k => { rrect(g, k * 0.84 - 0.012, 0.48, 0.024, 0.09, 0.006, '#7a0d10'); });
        both(k => {
          poly(g, K(k, [[0.4, 0.955], [0.84, 0.975], [0.87, 0.9], [0.82, 0.86], [0.42, 0.885]]), '#2a0306', '#14151a', 0.008);
          for (let i = 0; i < 10; i++) { const x = 0.44 + i * 0.041; rrect(g, k * x - 0.014, 0.905 + (i % 2) * 0.022, 0.028, 0.022, 0.002, '#c3141d'); }
        });
        poly(g, [[-0.42, 0.885], [0.42, 0.885], [0.4, 0.955], [-0.4, 0.955]], 'rgba(0,0,0,0.25)');
        rings(g, 0, 1.0, 0.045, '#101113', 0.012);
        rings(g, 0, 1.0, 0.045, '#5c6067', 0.004);
        ukPlate(g, 0, 0.8, 'RS3 VS', true);
        rrect(g, -0.47, 0.72, 0.12, 0.04, 0.005, '#c5c8ce'); txt(g, 'RS 3', -0.405, 0.74, 0.03, 'bold italic', '#111');
        rrect(g, -0.47, 0.72, 0.03, 0.04, 0.005, '#d0141a');
      },
      glow(g, W, H) {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); frame(g, W, H, RS3_REAR);
        both(k => { for (let i = 0; i < 10; i++) { const x = 0.44 + i * 0.041; rrect(g, k * x - 0.014, 0.905 + (i % 2) * 0.022, 0.028, 0.022, 0.002, '#ff2a30'); } });
      } },
  ],
};

/* ---------------------------------------------------------------- BMW M2 (G87, 2024) */
const M2_FRONT = [-0.99, 0.10, 0.99, 0.92], M2_REAR = [-0.99, 0.12, 0.99, 1.14], M2_SIDE = [-2.35, 0.08, 2.35, 1.44];
export const M2 = {
  name: 'BMW M2',
  L: 4.580, W: 1.887, H: 1.403, xf: 1.557, xr: 1.557 - 2.747,
  Rf: 0.338, Rr: 0.34, rimR: 0.25, tyreW: 0.28, track: 1.605,
  paint: 0x6d7782, wheelColor: 0xb9bdc4, wheelRough: 0.26, caliper: 0xc8161d, spokes: 10, spokeFill: 0.36, splitSpoke: true,
  N: 170, M: 52, rF: 0.6, rR: 0.45, cornerP: 2.3, Wb: 1.79, flareF: 0.035, flareR: 0.052, flareLen: 0.45, archGap: 0.025, archRound: 1.0,
  ledge: 0.075, roofRatio: [[0.9, 0.7], [-0.5, 0.68], [-1.3, 0.62], [-1.85, 0.6]],
  creaseIn: [[2.2, 0.02], [0.6, 0.03], [-0.5, 0.05], [-1.2, 0.1], [-2.25, 0.1]],
  crease: [[2.25, 0.68], [1.9, 0.77], [1.2, 0.8], [0, 0.815], [-1.5, 0.85], [-2.25, 0.86]],
  top: [[2.29, 0.4], [2.282, 0.55], [2.26, 0.66], [2.21, 0.76], [2.065, 0.855], [1.54, 0.93], [0.93, 1.0], [0.55, 1.19], [0.16, 1.385],
        [-0.2, 1.403], [-0.6, 1.395], [-0.98, 1.35], [-1.4, 1.22], [-1.79, 1.09], [-2.0, 1.065], [-2.14, 1.078],
        [-2.2, 1.045], [-2.25, 0.93], [-2.28, 0.75], [-2.29, 0.5]],
  bottom: [[2.29, 0.3], [2.26, 0.17], [2.05, 0.15], [1.6, 0.14], [-1.5, 0.15], [-2.0, 0.2], [-2.29, 0.3]],
  belt: [[0.93, 0.99], [0.6, 0.965], [0.0, 0.975], [-0.9, 1.0], [-1.12, 1.01], [-1.3, 1.06], [-1.6, 1.085], [-1.9, 1.09]],
  gh: [-1.85, 0.93],
  mirror: [0.8, 1.02], mirrorPaint: false,
  exhausts: [{ y: 0.29, z: 0.47, ry: 0.045, rz: 0.045 }, { y: 0.29, z: 0.585, ry: 0.045, rz: 0.045 }],
  extra(car, { paint, black }) {
    const sh = new THREE.Shape([[-2.06, 1.07], [-2.19, 1.09], [-2.205, 1.072], [-2.14, 1.062]].map(([x, y]) => new THREE.Vector2(x, y)));
    const dt = new THREE.Mesh(new THREE.ExtrudeGeometry(sh, { depth: 1.1, bevelEnabled: true, bevelThickness: 0.008, bevelSize: 0.006, bevelSegments: 2 }), paint);
    dt.position.z = -0.55; car.add(dt);
    const fin = new THREE.Mesh(new THREE.ExtrudeGeometry(new THREE.Shape([[-0.85, 1.37], [-1.05, 1.335], [-1.03, 1.39]].map(([x, y]) => new THREE.Vector2(x, y))), { depth: 0.05, bevelEnabled: false }), black);
    fin.position.z = -0.025; car.add(fin);
  },
  decals: [
    { axis: '±z', kind: 'glass', rect: M2_SIDE, tw: 3072, th: 900, segs: [150, 44], order: 2, minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, M2_SIDE);
        const o = glassOutline(B, -0.97, [[-1.11, 1.12], [-1.06, 1.015]], 0.07);
        glassFill(g, o, [[0.0, 1.17], [-0.95, 1.13]]); trimAround(g, o, 0.03);
        poly(g, [[-0.37, 0.9], [-0.5, 0.9], [-0.5, 1.5], [-0.37, 1.5]], '#08090b');
      } },
    { axis: '±z', kind: 'trim', rect: M2_SIDE, tw: 3072, th: 900, segs: [150, 44], minFacing: 0.05,
      draw(g, W, H, B) {
        frame(g, W, H, M2_SIDE);
        sideTrim(g, M2, B, { sill: 0.22, handles: [[-0.18, 0.86]],
          lines: [[[0.92, 0.99], [0.92, 0.3]], [[-0.5, 1.0], [-0.52, 0.6], [-0.48, 0.3]]] });
        poly(g, [[-1.98, 1.0], [-2.3, 0.995], [-2.3, 0.88], [-2.08, 0.9]], '#3a0408', '#1a1b1f', 0.006);
        g.beginPath(); g.moveTo(-2.0, 0.975); g.lineTo(-2.3, 0.965); g.strokeStyle = '#d0141a'; g.lineWidth = 0.018; g.stroke();
        poly(g, [[1.98, 0.8], [2.3, 0.76], [2.3, 0.67], [2.06, 0.72]], '#0b0c10', '#2a2d33', 0.006);
      } },
    { axis: '+y', kind: 'glass', rect: [-1.95, -0.9, 1.0, 0.9], tw: 2048, th: 620, segs: [110, 40], order: 2,
      draw(g, W, H, B) {
        frame(g, W, H, [-1.95, -0.9, 1.0, 0.9]);
        for (const o of [screenOutline(B, M2, 0.14, 0.92), screenOutline(B, M2, -1.8, -1.0, 0.07)]) { poly(g, o, '#0d1117'); trimAround(g, o, 0.025); }
      } },
    { axis: '+x', rect: M2_FRONT, tw: 2048, th: 850, segs: [64, 40],
      draw(g, W, H) {
        frame(g, W, H, M2_FRONT);
        poly(g, [[-0.92, 0.12], [0.92, 0.12], [0.9, 0.18], [-0.9, 0.18]], '#0b0c0e');
        poly(g, [[-0.38, 0.2], [0.38, 0.2], [0.42, 0.38], [0.3, 0.42], [-0.3, 0.42], [-0.42, 0.38]], '#08090b', '#2c2f34', 0.01);
        both(k => {
          const intake = K(k, [[0.48, 0.2], [0.9, 0.22], [0.93, 0.5], [0.82, 0.55], [0.5, 0.45]]);
          poly(g, intake, '#08090b', '#2c2f34', 0.01);
          slats(g, intake, 3, 0.2, 0.56, '#08090b', '#3a3e45', true, k > 0 ? 0.5 : -0.93, k > 0 ? 0.93 : -0.5);
        });
        ukPlate(g, 0, 0.31, 'M2 G87', false);
        both(k => {
          const kid = K(k, [[0.035, 0.455], [0.36, 0.455], [0.39, 0.5], [0.385, 0.63], [0.35, 0.665], [0.06, 0.665], [0.035, 0.63]]);
          poly(g, kid, null, '#1d2024', 0.026);
          slats(g, kid, 5, 0.455, 0.665, '#050607', '#22252a');
        });
        mStripes(g, 0.24, 0.62, 0.022);
        both(k => {
          poly(g, K(k, [[0.47, 0.68], [0.6, 0.705], [0.83, 0.77], [0.88, 0.73], [0.86, 0.66], [0.62, 0.635], [0.5, 0.64]]), '#0b0c10', '#2a2d33', 0.008);
          g.lineCap = 'round';
          for (const [ox, oy] of [[0.0, 0.0], [0.19, 0.035]]) {
            g.beginPath(); g.moveTo(k * (0.53 + ox), 0.695 + oy); g.lineTo(k * (0.66 + ox), 0.695 + oy - 0.004); g.lineTo(k * (0.68 + ox), 0.66 + oy * 0.7);
            g.strokeStyle = '#e9eef6'; g.lineWidth = 0.011; g.stroke();
          }
          g.beginPath(); g.arc(k * 0.62, 0.668, 0.02, 0, Math.PI * 2); g.fillStyle = '#2b3442'; g.fill();
          g.beginPath(); g.arc(k * 0.78, 0.702, 0.02, 0, Math.PI * 2); g.fillStyle = '#2b3442'; g.fill();
        });
        roundel(g, 0, 0.745, 0.04);
      },
      glow(g, W, H) {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); frame(g, W, H, M2_FRONT);
        both(k => { g.lineCap = 'round'; for (const [ox, oy] of [[0.0, 0.0], [0.19, 0.035]]) {
          g.beginPath(); g.moveTo(k * (0.53 + ox), 0.695 + oy); g.lineTo(k * (0.66 + ox), 0.695 + oy - 0.004); g.lineTo(k * (0.68 + ox), 0.66 + oy * 0.7);
          g.strokeStyle = '#ffffff'; g.lineWidth = 0.011; g.stroke(); } });
      } },
    { axis: '-x', rect: M2_REAR, tw: 2048, th: 1060, segs: [64, 44],
      draw(g, W, H) {
        frame(g, W, H, M2_REAR);
        poly(g, [[-0.86, 0.14], [0.86, 0.14], [0.8, 0.4], [-0.8, 0.4]], '#0a0b0d', '#25272b', 0.008);
        slats(g, [[-0.4, 0.15], [0.4, 0.15], [0.4, 0.34], [-0.4, 0.34]], 5, 0, 0, '#08090a', '#1c1e22', true, -0.4, 0.4);
        both(k => { rrect(g, k * 0.84 - 0.016, 0.3, 0.032, 0.2, 0.012, '#0b0c0e', '#2a2c30', 0.006); rrect(g, k * 0.84 - 0.008, 0.33, 0.016, 0.14, 0.006, '#7a0d10'); });
        poly(g, [[-0.48, 0.72], [0.48, 0.72], [0.52, 0.9], [-0.52, 0.9]], 'rgba(20,24,30,0.35)');
        ukPlate(g, 0, 0.8, 'M2 G87', true);
        both(k => {
          poly(g, K(k, [[0.44, 0.985], [0.76, 0.99], [0.83, 0.93], [0.78, 0.86], [0.47, 0.87]]), '#120607', '#1a1b1f', 0.008);
          g.beginPath(); g.moveTo(k * 0.48, 0.955); g.lineTo(k * 0.74, 0.965); g.lineTo(k * 0.78, 0.92);
          g.strokeStyle = '#d0141a'; g.lineWidth = 0.02; g.lineJoin = 'round'; g.stroke();
        });
        roundel(g, 0, 0.98, 0.04);
        mStripes(g, 0.22, 0.855, 0.022); txt(g, 'M2', 0.3, 0.866, 0.028, 'bold italic', '#c9ccd2', 'left');
      },
      glow(g, W, H) {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); frame(g, W, H, M2_REAR);
        both(k => { g.beginPath(); g.moveTo(k * 0.48, 0.955); g.lineTo(k * 0.74, 0.965); g.lineTo(k * 0.78, 0.92); g.strokeStyle = '#ff2a30'; g.lineWidth = 0.02; g.lineJoin = 'round'; g.stroke(); });
      } },
  ],
};

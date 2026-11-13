// Drawing helpers for the cars' decals (lights, grilles, glass, badges, plates).
// Shared, unchanged, between the films. Every decal is drawn in metres as seen from
// outside the car: X to the right, Y up.

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

export { K, both, frame, glassFill, glassOutline, honeycomb, mStripes, mirrorX, poly, rings, roundel, rrect, screenOutline, sideTrim, slats, trimAround, txt, ukPlate };

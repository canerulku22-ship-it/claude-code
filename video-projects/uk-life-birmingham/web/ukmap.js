// Flat UK map (Natural Earth 1:10m via world-atlas), transverse Mercator fitted to the vertical frame, with zoom-to-
// a-town, nation borders, town dots and a bouncing map pin.
import { geoTransverseMercator, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import { c, PAL, PI, W, H, circle, ellipse, txt, lerp, clamp01, mulberry32 } from './core.js';
import { pin } from './globe.js';

let UKF, NEAR, IOM, S0, T0;
const ROT = [2.6, 0];
export async function loadUK() {
  const cs = await (await fetch('/node_modules/world-atlas/countries-10m.json')).json();
  const fc = feature(cs, cs.objects.countries);
  const get = id => fc.features.find(f => f.id === id);
  UKF = get('826'); IOM = get('833');
  NEAR = { type: 'FeatureCollection', features: ['372', '250', '056', '528', '831', '832'].map(get).filter(Boolean) };
  const p0 = geoTransverseMercator().rotate(ROT).fitExtent([[90, 360], [990, 1470]], UKF);
  S0 = p0.scale(); T0 = p0.translate();
}
export const BRUM = [-1.89, 52.48];
export const TOWNS = {
  Glasgow: [-4.25, 55.86], Edinburgh: [-3.19, 55.95], Aberdeen: [-2.09, 57.15], Inverness: [-4.22, 57.48], Belfast: [-5.93, 54.6],
  Newcastle: [-1.62, 54.98], Leeds: [-1.55, 53.8], Manchester: [-2.24, 53.48], Liverpool: [-2.99, 53.41], Cardiff: [-3.18, 51.48],
  Bristol: [-2.59, 51.45], London: [-0.13, 51.51], Norwich: [1.3, 52.63], Plymouth: [-4.14, 50.38], Hull: [-0.33, 53.77], Southampton: [-1.4, 50.91],
  Birmingham: BRUM,
};
const MAJOR = ['Glasgow', 'Edinburgh', 'Aberdeen', 'Belfast', 'Newcastle', 'Manchester', 'Cardiff', 'London', 'Norwich', 'Plymouth', 'Leeds'];
const BORDERS = [
  [[-3.07, 54.98], [-2.93, 55.03], [-2.75, 55.12], [-2.62, 55.2], [-2.47, 55.3], [-2.33, 55.36], [-2.2, 55.44], [-2.2, 55.55], [-2.28, 55.64], [-2.12, 55.72], [-2.03, 55.81]],
  [[-3.08, 53.26], [-2.95, 53.16], [-2.78, 53.0], [-2.98, 52.9], [-3.09, 52.75], [-3.12, 52.6], [-3.03, 52.45], [-3.02, 52.33], [-3.1, 52.2], [-3.04, 52.07], [-2.94, 51.97], [-2.84, 51.85], [-2.7, 51.74], [-2.65, 51.62]],
];
// projection for a zoom level; `focus` slides from where it sits on the full map toward `to` as kz goes 0 → 1
export function projFor({ zoom = 1, focus = BRUM, to = [W / 2, 900], kz = 0 } = {}) {
  const p0 = geoTransverseMercator().rotate(ROT).scale(S0).translate(T0);
  const b = p0(focus), p = geoTransverseMercator().rotate(ROT).scale(S0 * zoom).translate([0, 0]);
  const f = p(focus), tx = lerp(b[0], to[0], kz), ty = lerp(b[1], to[1], kz);
  return p.translate([tx - f[0], ty - f[1]]).clipExtent([[-80, -80], [W + 80, H + 80]]);
}
const WAVES = (() => { const R = mulberry32(6); return Array.from({ length: 40 }, () => [R() * W, R() * H]); })();
export function ukMap({ zoom = 1, focus = BRUM, to = [W / 2, 900], kz = 0, glow = 0, labels = 1, t = 0, hide = [] } = {}) {
  const p = projFor({ zoom, focus, to, kz }), path = geoPath(p, c);
  const g = c.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#7cc0ea'); g.addColorStop(1, '#4a93d0'); c.fillStyle = g; c.fillRect(0, 0, W, H);
  c.strokeStyle = 'rgba(255,255,255,.35)'; c.lineWidth = 5; c.lineCap = 'round';
  for (const [x, y] of WAVES) { const dx = Math.sin(t * 0.8 + x) * 6; c.beginPath(); c.arc(x + dx, y, 14, PI * 1.15, PI * 1.85); c.stroke(); c.beginPath(); c.arc(x + dx + 26, y, 14, PI * 1.15, PI * 1.85); c.stroke(); }
  c.lineJoin = 'round';
  c.beginPath(); path(NEAR); c.fillStyle = '#cdd5c3'; c.fill(); c.strokeStyle = PAL.ink; c.lineWidth = 4; c.stroke();
  c.beginPath(); path(UKF); path(IOM); c.fillStyle = '#a8d277'; c.fill();
  if (glow > 0) { c.fillStyle = `rgba(255,214,90,${0.6 * glow})`; c.fill(); }
  c.strokeStyle = PAL.ink; c.lineWidth = 5; c.stroke();
  // nation borders
  c.setLineDash([14, 12]); c.strokeStyle = 'rgba(255,255,255,.85)'; c.lineWidth = 5;
  for (const ln of BORDERS) { c.beginPath(); ln.forEach((q, i) => { const [x, y] = p(q); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.stroke(); }
  c.setLineDash([]);
  if (labels > 0) {
    c.globalAlpha = labels;
    for (const [s, q] of [['Scotland', [-4.3, 56.75]], ['England', [-0.95, 53.25]], ['Wales', [-3.75, 52.3]], ['N. Ireland', [-6.7, 54.82]], ['Ireland', [-8.0, 53.2]]]) {
      const [x, y] = p(q); txt(s, x, y, { font: 'Patrick Hand', weight: 400, size: s === 'Ireland' ? 44 : 50, color: s === 'Ireland' ? 'rgba(60,70,60,.45)' : 'rgba(30,70,30,.55)' });
    }
    c.globalAlpha = 1;
  }
  return p;
}
export function townDots(p, { major = 1, show = [], size = 1 } = {}) {
  for (const [name, q] of Object.entries(TOWNS)) {
    const isMaj = MAJOR.includes(name), on = show.includes(name);
    if (!isMaj && !on) continue;
    const [x, y] = p(q); circle(x, y, 9 * size, '#ffffff', PAL.ink, 4);
    if ((isMaj && major) || on) txt(name, x, y - 30 * size, { size: 30 * size, color: '#ffffff', stroke: PAL.ink, lw: 7 }), txt(name, x, y - 30 * size, { size: 30 * size, color: '#ffffff' });
  }
}
// pin hopping between towns: stops = [[name, landTime], ...]
export function hopPin(p, stops, t, s = 1) {
  let x, y, h = 0, land = -1;
  const P = n => p(TOWNS[n]);
  if (t < stops[0][1]) { const [x0, y0] = P(stops[0][0]); const k = clamp01((t - (stops[0][1] - 0.45)) / 0.45); x = x0; y = y0; h = (1 - k * k) * 900; }
  else {
    let i = stops.length - 1; for (let j = 0; j < stops.length - 1; j++) if (t >= stops[j][1] && t < stops[j + 1][1]) i = j;
    const [a, ta] = stops[i], nx = stops[i + 1];
    const dwell = 0.12;
    if (!nx || t < ta + dwell) { [x, y] = P(a); land = t - ta; }
    else { const k = clamp01((t - ta - dwell) / (nx[1] - ta - dwell)); const A = P(a), B = P(nx[0]); x = lerp(A[0], B[0], k); y = lerp(A[1], B[1], k); h = Math.sin(PI * k) * (120 + Math.hypot(B[0] - A[0], B[1] - A[1]) * 0.35); }
  }
  ellipse(x, y + 4, 34 * s * (1 - Math.min(0.6, h / 900)), 12 * s * (1 - Math.min(0.6, h / 900)), 'rgba(0,0,0,.28)', null, 0);
  let sq = 1; if (land >= 0 && land < 0.4) sq = 1 - 0.25 * Math.exp(-land * 10) * Math.cos(land * 30);
  c.save(); c.translate(x, y - h); c.scale(1 / Math.sqrt(sq), sq); pin(0, 0, 1.0 * s); c.restore();
  if (land >= 0 && land < 0.45) { const k = land / 0.45; c.strokeStyle = `rgba(255,255,255,${1 - k})`; c.lineWidth = 6; c.beginPath(); c.ellipse(x, y, 20 + 70 * k, 8 + 28 * k, 0, 0, PI * 2); c.stroke(); }
  return { x, y, h, land };
}

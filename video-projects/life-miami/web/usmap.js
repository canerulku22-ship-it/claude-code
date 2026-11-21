// Neon map of the lower 48 (us-atlas 1:10m states) on an Albers projection fitted to the vertical frame, with the
// neighbours (Canada, Mexico, Cuba, the Bahamas…) dimmed, zoom-to-a-city, glowing borders, city dots and a hopping pin.
import { geoAlbers, geoPath } from 'd3-geo';
import { feature, merge, mesh } from 'topojson-client';
import { c, PI, W, H, lerp, clamp01, circle, ellipse, txt, mulberry32 } from './core.js';
import { pin } from './globe.js';
import { NEON, neonStroke, flagPattern } from './miami.js';

let STATES, L48, INNER, FL, NEAR, CAN, S0, T0;
const SKIP = new Set(['02', '15', '60', '66', '69', '72', '78']);
export async function loadUS() {
  const us = await (await fetch('/node_modules/us-atlas/states-10m.json')).json();
  const geoms = us.objects.states.geometries.filter(g => !SKIP.has(g.id));
  STATES = { type: 'FeatureCollection', features: geoms.map(g => feature(us, g)) };
  L48 = merge(us, geoms);
  INNER = mesh(us, { type: 'GeometryCollection', geometries: geoms }, (a, b) => a !== b);
  FL = feature(us, geoms.find(g => g.id === '12'));
  const cs = await (await fetch('/node_modules/world-atlas/countries-50m.json')).json();
  const fc = feature(cs, cs.objects.countries);
  CAN = fc.features.find(f => f.id === '124');
  NEAR = { type: 'FeatureCollection', features: ['484', '192', '044', '332', '214', '388', '630', '320', '084', '340'].map(id => fc.features.find(f => f.id === id)).filter(Boolean) };
  const p0 = geoAlbers().fitExtent([[40, 640], [1040, 1250]], L48);
  S0 = p0.scale(); T0 = p0.translate();
}
export const MIAMI = [-80.19, 25.76];
export const CITY = {
  Seattle: [-122.33, 47.61], 'San Francisco': [-122.42, 37.77], 'Los Angeles': [-118.24, 34.05], 'Las Vegas': [-115.14, 36.17], Phoenix: [-112.07, 33.45],
  Denver: [-104.99, 39.74], Dallas: [-96.8, 32.78], Houston: [-95.37, 29.76], Chicago: [-87.63, 41.88], Detroit: [-83.05, 42.33], Nashville: [-86.78, 36.16],
  'New Orleans': [-90.07, 29.95], Atlanta: [-84.39, 33.75], 'New York': [-74.0, 40.71], Boston: [-71.06, 42.36], Washington: [-77.04, 38.9],
  Orlando: [-81.38, 28.54], Tampa: [-82.46, 27.95], 'Key West': [-81.78, 24.56], Miami: MIAMI,
};
const LBL = { Seattle: [16, -22, 'left'], 'Los Angeles': [6, 34, 'left'], 'Las Vegas': [16, -20, 'left'], Denver: [16, -22, 'left'], Houston: [16, 24, 'left'], 'San Francisco': [16, -22, 'left'], Phoenix: [16, 26, 'left'], Miami: [-16, 24, 'right'], Boston: [16, -22, 'left'], Detroit: [16, -22, 'left'] };
const MAJOR = ['Seattle', 'Los Angeles', 'Las Vegas', 'Denver', 'Chicago', 'New York', 'Houston', 'Atlanta'];
export function projFor({ zoom = 1, focus = MIAMI, to = [W / 2, 1000], kz = 0 } = {}) {
  const p0 = geoAlbers().scale(S0).translate(T0);
  const b = p0(focus), p = geoAlbers().scale(S0 * zoom).translate([0, 0]);
  const f = p(focus), tx = lerp(b[0], to[0], kz), ty = lerp(b[1], to[1], kz);
  return p.translate([tx - f[0], ty - f[1]]).clipExtent([[-80, -80], [W + 80, H + 80]]);
}
// sweep: 0..1 reveals the map left → right with a bright scan line. fl: Florida lights up.
// static layers (neighbours, states, borders) are cached per view, so steady shots cost one drawImage
const CACHE = new Map();
function baseLayers(g, p, lw) {
  const path = geoPath(p, g);
  g.lineJoin = 'round';
  g.beginPath(); path(NEAR); g.fillStyle = 'rgba(40,14,78,.92)'; g.fill(); g.strokeStyle = 'rgba(185,103,255,.55)'; g.lineWidth = 3 * lw; g.stroke();
  g.beginPath(); path(CAN); g.strokeStyle = 'rgba(185,103,255,.45)'; g.lineWidth = 2.5 * lw; g.stroke();
  const gr = g.createLinearGradient(0, 600, 0, 1300); gr.addColorStop(0, '#3a1170'); gr.addColorStop(1, '#25094d');
  g.beginPath(); path(STATES); g.fillStyle = gr; g.fill();
  g.beginPath(); path(INNER); g.globalAlpha = 0.75; neonStroke(NEON.teal, 1.6 * lw, 0.6, g); g.globalAlpha = 1;
  g.beginPath(); path(L48); neonStroke(NEON.pink, 3.4 * lw, 1, g);
}
// sweep: 0..1 reveals the map left → right with a bright scan line. fl: Florida lights up.
export function usMap({ zoom = 1, focus = MIAMI, to = [W / 2, 1000], kz = 0, t = 0, sweep = 1, fl = 0, labels = 0, lw = 1, cache = null } = {}) {
  const p = projFor({ zoom, focus, to, kz }), path = geoPath(p, c);
  const key = cache ?? ((kz === 0 || kz === 1) ? JSON.stringify([zoom, focus, to, kz, lw]) : null);
  const sx = lerp(-60, W + 60, sweep);
  c.save();
  if (sweep < 1) { c.beginPath(); c.rect(-100, -100, sx + 100, H + 200); c.clip(); }
  if (key) {
    let cv = CACHE.get(key);
    if (!cv) { cv = document.createElement('canvas'); cv.width = W; cv.height = H; baseLayers(cv.getContext('2d'), p, lw); CACHE.set(key, cv); }
    c.drawImage(cv, 0, 0);
  } else baseLayers(c, p, lw);
  if (fl > 0) {
    const [[x0, y0], [x1, y1]] = geoPath(p).bounds(FL), gf = c.createLinearGradient(x0, y0, x1, y1); gf.addColorStop(0, '#ff2a6d'); gf.addColorStop(1, '#ff901f');
    c.save(); c.globalAlpha = fl; c.beginPath(); path(FL); c.fillStyle = gf; c.fill();
    c.globalAlpha = fl * (0.25 + 0.15 * Math.sin(t * 6)); c.fillStyle = '#ffffff'; c.fill(); c.restore();
    c.beginPath(); path(FL); c.globalAlpha = fl; neonStroke(NEON.yellow, 3.6 * lw, 1); c.globalAlpha = 1;
  }
  if (labels > 0) {
    c.globalAlpha = labels;
    for (const [s, q, sz] of [['CANADA', [-100, 52.5], 40], ['MEXICO', [-103, 24.5], 40], ['Gulf of Mexico', [-90, 25.6], 30], ['Atlantic', [-66, 33], 34]]) { const [x, y] = p(q); txt(s, x, y, { font: 'Nunito', weight: 900, size: sz, color: 'rgba(205,160,255,.55)' }); }
    c.globalAlpha = 1;
  }
  c.restore();
  if (sweep > 0 && sweep < 1) { const sg = c.createLinearGradient(sx - 80, 0, sx + 10, 0); sg.addColorStop(0, 'rgba(5,217,232,0)'); sg.addColorStop(1, 'rgba(5,217,232,.8)'); c.fillStyle = sg; c.fillRect(sx - 80, 560, 90, 760); c.fillStyle = '#e8feff'; c.fillRect(sx - 3, 560, 6, 760); }
  return p;
}
// the country filled with stars and stripes (cached), revealed left → right by `k`
let FLAGCV = null;
export function usFlagFill(p, k, alpha = 0.9) {
  if (!FLAGCV) { FLAGCV = document.createElement('canvas'); FLAGCV.width = W; FLAGCV.height = H; const g = FLAGCV.getContext('2d'), path = geoPath(p, g); g.save(); g.beginPath(); path(L48); g.clip(); g.fillStyle = flagPattern(); g.fillRect(0, 0, W, H); g.restore(); g.beginPath(); path(L48); neonStroke(NEON.pink, 3.4, 1, g); }
  const [[x0, y0], [x1, y1]] = geoPath(p).bounds(L48);
  c.save(); c.beginPath(); c.rect(x0 - 40, y0 - 40, (x1 - x0 + 80) * k, y1 - y0 + 80); c.clip(); c.globalAlpha = alpha; c.drawImage(FLAGCV, 0, 0); c.restore();
}
export const flPath = p => { const path = geoPath(p, c); c.beginPath(); path(FL); };
export const usPath = p => { const path = geoPath(p, c); c.beginPath(); path(L48); };
export const usBounds = p => geoPath(p).bounds(L48);
export function cityDots(p, { major = 1, show = [], size = 1, alpha = 1 } = {}) {
  if (alpha <= 0.01) return;
  c.save(); c.globalAlpha = alpha;
  for (const [name, q] of Object.entries(CITY)) {
    const isMaj = MAJOR.includes(name), on = show.includes(name);
    if (!isMaj && !on) continue;
    const [x, y] = p(q);
    c.beginPath(); c.arc(x, y, 8 * size, 0, PI * 2); c.fillStyle = '#ffffff'; c.fill(); neonStroke(NEON.teal, 3 * size, 1);
    if ((isMaj && major) || on) { const [dx, dy, al] = LBL[name] || [-16, -22, 'right']; txt(name, x + dx * size, y + dy * size, { size: 28 * size, color: '#ffffff', stroke: '#12051f', lw: 7, align: al }); }
  }
  c.restore();
}
// simple pin hopping between cities: stops = [[name, landTime], ...]
export function hopPin(p, stops, t, s = 1, col = NEON.pink) {
  let x, y, h = 0, land = -1;
  const P = n => p(CITY[n]);
  if (t < stops[0][1]) { const [x0, y0] = P(stops[0][0]); const k = clamp01((t - (stops[0][1] - 0.45)) / 0.45); x = x0; y = y0; h = (1 - k * k) * 900; }
  else {
    let i = stops.length - 1; for (let j = 0; j < stops.length - 1; j++) if (t >= stops[j][1] && t < stops[j + 1][1]) i = j;
    const [a, ta] = stops[i], nx = stops[i + 1];
    if (!nx || t < ta + 0.12) { [x, y] = P(a); land = t - ta; }
    else { const k = clamp01((t - ta - 0.12) / (nx[1] - ta - 0.12)); const A = P(a), B = P(nx[0]); x = lerp(A[0], B[0], k); y = lerp(A[1], B[1], k); h = Math.sin(PI * k) * (120 + Math.hypot(B[0] - A[0], B[1] - A[1]) * 0.35); }
  }
  ellipse(x, y + 4, 34 * s * (1 - Math.min(0.6, h / 900)), 12 * s * (1 - Math.min(0.6, h / 900)), 'rgba(0,0,0,.4)', null, 0);
  let sq = 1; if (land >= 0 && land < 0.4) sq = 1 - 0.25 * Math.exp(-land * 10) * Math.cos(land * 30);
  c.save(); c.translate(x, y - h); c.scale(1 / Math.sqrt(sq), sq); pin(0, 0, 1.0 * s, col); c.restore();
  if (land >= 0 && land < 0.45) { const k = land / 0.45; c.beginPath(); c.ellipse(x, y, 20 + 70 * k, 8 + 28 * k, 0, 0, PI * 2); c.globalAlpha = 1 - k; neonStroke(NEON.teal, 4, 1); c.globalAlpha = 1; }
  return { x, y, h, land };
}

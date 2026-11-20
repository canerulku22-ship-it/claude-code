// Orthographic Earth from Natural Earth (world-atlas) outlines, drawn with d3-geo onto the 2D canvas.
import { geoOrthographic, geoPath, geoGraticule10 } from 'd3-geo';
import { feature } from 'topojson-client';
import { c, PAL, PI, W, H, circle, txt, mulberry32 } from './core.js';

let LAND = null, DETAIL = null, UK = null;
export async function loadGlobe() {
  const land = await (await fetch('/node_modules/world-atlas/land-110m.json')).json();
  LAND = feature(land, land.objects.land);
  const cs = await (await fetch('/node_modules/world-atlas/countries-50m.json')).json();
  const fc = feature(cs, cs.objects.countries);
  const near = new Set(['826', '372', '250', '056', '528', '276', '208', '578', '442', '752', '724', '620', '756', '040', '380', '056']);
  DETAIL = { type: 'FeatureCollection', features: fc.features.filter(f => near.has(f.id)) };
  UK = fc.features.find(f => f.id === '826');
}
const grat = geoGraticule10();
const STARS = (() => { const R = mulberry32(8); return Array.from({ length: 140 }, () => [R() * W, R() * H, 1 + R() * 2.4, R() * 6]); })();
export function space(t) {
  c.fillStyle = '#1d2a4d'; c.fillRect(0, 0, W, H);
  for (const [x, y, r, ph] of STARS) { c.globalAlpha = 0.35 + 0.35 * Math.sin(t * 2 + ph); c.fillStyle = '#ffffff'; c.beginPath(); c.arc(x, y, r, 0, PI * 2); c.fill(); }
  c.globalAlpha = 1;
}
// lon/lat = point at the centre of the disc; r = radius in px
export function globe({ cx = W / 2, cy = 900, r = 340, lon = 0, lat = 0, ukGlow = 0 }) {
  const proj = geoOrthographic().translate([cx, cy]).scale(r).rotate([-lon, -lat]).clipAngle(90).precision(0.3);
  const path = geoPath(proj, c);
  // halo + ocean
  if (r < 3000) { c.beginPath(); c.arc(cx, cy, r + 26, 0, PI * 2); c.fillStyle = '#2a3c6b'; c.fill(); }
  const g = c.createRadialGradient(cx - r * 0.3, cy - r * 0.35, r * 0.1, cx, cy, r);
  g.addColorStop(0, '#5aa2dd'); g.addColorStop(1, '#2f6db0');
  c.beginPath(); path({ type: 'Sphere' }); c.fillStyle = g; c.fill();
  c.beginPath(); path(grat); c.strokeStyle = 'rgba(255,255,255,.12)'; c.lineWidth = 2; c.stroke();
  // land
  const data = r > 1400 ? DETAIL : LAND;
  c.beginPath(); path(data); c.fillStyle = '#a8cf74'; c.fill(); c.strokeStyle = '#2f4a22'; c.lineWidth = r > 1400 ? 5 : 3; c.lineJoin = 'round'; c.stroke();
  if (ukGlow > 0) { c.beginPath(); path(UK); c.fillStyle = `rgba(255,213,74,${0.75 * ukGlow})`; c.fill(); c.strokeStyle = PAL.ink; c.lineWidth = 6; c.stroke(); }
  if (r < 3000) { c.beginPath(); path({ type: 'Sphere' }); c.strokeStyle = PAL.ink; c.lineWidth = 6; c.stroke(); }
  return proj;
}
// classic map pin, tip at (x, y)
export function pin(x, y, s = 1, col = '#e63946') {
  c.save(); c.translate(x, y); c.scale(s, s);
  c.beginPath(); c.moveTo(0, 0); c.bezierCurveTo(-20, -40, -46, -62, -46, -96); c.arc(0, -96, 46, PI, 0); c.bezierCurveTo(46, -62, 20, -40, 0, 0); c.closePath();
  c.fillStyle = col; c.fill(); c.strokeStyle = PAL.ink; c.lineWidth = 6; c.stroke();
  circle(0, -98, 18, '#ffffff', PAL.ink, 5);
  c.restore();
}

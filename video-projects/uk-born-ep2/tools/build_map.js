// Extract UK (+ neighbours for context) outlines from world-atlas (Natural Earth 1:10m, public domain) into
// web/mapdata.js as lon/lat rings: window.MAP = { uk: [[ring, hole...], ...], ie: [...], iom: [...], fr: [...] }.
// Small islets are dropped and points thinned so the 3D extrusion stays light.
const fs = require('fs'), path = require('path');
const topo = require('topojson-client');
const world = require('world-atlas/countries-10m.json');
const fc = topo.feature(world, world.objects.countries);
const BOX = { lon0: -11, lon1: 3.2, lat0: 48.5, lat1: 61.2 };
const area = r => { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]); return Math.abs(a / 2) * Math.cos(54 * Math.PI / 180); };
function thin(r, minD) { const out = [r[0]]; for (const p of r) { const q = out[out.length - 1]; if (Math.hypot((p[0] - q[0]) * 0.6, p[1] - q[1]) >= minD) out.push(p); } return out.map(([x, y]) => [+x.toFixed(4), +y.toFixed(4)]); }
function grab(id, { minArea = 0.004, minD = 0.012, clip = false } = {}) {
  const f = fc.features.find(f => f.id === id);
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  return polys
    .filter(p => area(p[0]) >= minArea)
    .filter(p => !clip || p[0].some(([x, y]) => x > BOX.lon0 && x < BOX.lon1 && y > BOX.lat0 && y < BOX.lat1))
    .map(p => p.filter((r, i) => i === 0 || area(r) >= minArea).map(r => thin(r, minD)));
}
const MAP = { uk: grab('826'), ie: grab('372'), iom: grab('833', { minArea: 0 }), fr: grab('250', { minArea: 0.05, minD: 0.03, clip: true }) };
// France: keep only the northern coast area (crop far-off territories by bounding box of the ring)
MAP.fr = MAP.fr.filter(p => p[0].every(([x, y]) => y > 41 && x < 10));
const n = k => MAP[k].reduce((s, p) => s + p.reduce((a, r) => a + r.length, 0), 0);
fs.writeFileSync(path.join(__dirname, '..', 'web', 'mapdata.js'), 'window.MAP = ' + JSON.stringify(MAP) + ';\n');
console.log(Object.keys(MAP).map(k => `${k}: ${MAP[k].length} polys, ${n(k)} pts`).join(' | '));

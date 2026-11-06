// EUROPE'S BOMB HOAX WAVE (2–5 November 2026): a 60-second vertical news explainer.
// Every route, outcome and number on screen comes from the reporting listed in SOURCES.md.
import { feature, mesh } from './node_modules/topojson-client/src/index.js';

const W = 1080, H = 1920, D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a), 0, 1); return k * k * (3 - 2 * k); };
const ease = k => (k = clamp(k, 0, 1), k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const easeOut = k => 1 - Math.pow(1 - clamp(k, 0, 1), 3);
const backOut = k => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const $ = id => document.getElementById(id);
const win = (t, a, b, fi = 0.3, fo = 0.3) => smooth(a, a + fi, t) * (1 - smooth(b - fo, b, t));

// ------------------------------------------------------------------ DATA
const APT = {
  LTN: [51.8747, -0.3683, 'LONDON LUTON'], SOF: [42.6967, 23.4114, 'SOFIA'], BUD: [47.4369, 19.2556, 'BUDAPEST'],
  LHR: [51.47, -0.4543, 'LONDON HEATHROW'], WAW: [52.1657, 20.9671, 'WARSAW'], WMI: [52.4511, 20.6518, 'MODLIN'],
  CPH: [55.618, 12.656, 'COPENHAGEN'], LIS: [38.7742, -9.1342, 'LISBON'], FCO: [41.8003, 12.2389, 'ROME'], DUB: [53.4213, -6.2701, 'DUBLIN'],
  MAN: [53.365, -2.2728, 'MANCHESTER'], RMU: [37.803, -1.125, 'MURCIA'], BGY: [45.6739, 9.7042, 'BERGAMO'],
  EVX: [49.0287, 1.2198, 'ÉVREUX AIR BASE'], HEL: [60.3172, 24.9633, 'HELSINKI'], VIE: [48.1103, 16.5697, 'VIENNA'],
  LON: [51.885, 0.235, 'LONDON'], PDV: [42.0678, 24.8508, 'PLOVDIV'], MAD: [40.4719, -3.5626, 'MADRID'], MIL: [45.63, 8.72, 'MILAN'],
  NCL: [55.0375, -1.6917, 'NEWCASTLE'], GLA: [55.8719, -4.4331, 'GLASGOW'], PRG: [50.1008, 14.26, 'PRAGUE'],
  BEG: [44.8184, 20.3091, 'BELGRADE'], OTP: [44.5711, 26.085, 'BUCHAREST'], BRU: [50.901, 4.4844, 'BRUSSELS'],
};
// day 0 = Mon 2 Nov, 1 = Tue 3 Nov, 3 = Thu 5 Nov.  cnt/dvc/esc feed the counters.
const INC = [
  { id: 'M1', day: 0, t: 5.3, from: 'LTN', to: 'SOF', thrNear: [44.3, 17.9], fly: 2.3, div: 'BUD', dv: 1.5, esc: { dt: 0.35, lab: 'HUNGARIAN GRIPEN' }, cnt: 1, dvc: 1, escc: 1 },
  { id: 'T1', day: 1, t: 11.1, from: 'LHR', to: 'WAW', thrF: 0.8, fly: 1.4, div: 'WMI', dv: 0.8, cnt: 1, dvc: 1 },
  { id: 'T2', day: 1, t: 12.7, from: 'CPH', to: 'WAW', thrF: 0.55, fly: 0.9, cnt: 1 },
  { id: 'T3', day: 1, t: 14.2, from: 'LIS', to: 'FCO', thrF: 0.6, fly: 1.1, cnt: 1 },
  { id: 'T4', day: 1, t: 14.5, from: 'DUB', to: 'FCO', thrF: 0.6, fly: 1.1, cnt: 1 },
  { id: 'T5', day: 1, t: 16.5, from: 'MAN', to: 'RMU', thrF: 0.6, fly: 1.1, cnt: 1, cordon: true },
  { id: 'T6', day: 1, t: 18.3, from: 'BGY', to: 'SOF', thrF: 0.6, fly: 0.9, cnt: 1 },
  { id: 'T7', day: 1, t: 18.6, from: 'DUB', to: 'SOF', thrF: 0.7, fly: 1.2, cnt: 1 },
  { id: 'H1', day: 3, t: 24.5, from: 'DUB', to: 'FCO', thrNear: [48.3, 2.4], fly: 1.7, div: 'EVX', dv: 1.0, esc: { dt: 0.3, lab: 'FRENCH AIR FORCE' }, cnt: 1, dvc: 1, escc: 1 },
  { id: 'H2', day: 3, t: 27.2, from: 'HEL', to: 'FCO', thrF: 0.6, fly: 1.4, esc: { dt: 0.3, lab: 'ITALIAN AIR FORCE' }, cnt: 1, escc: 1 },
  { id: 'H3', day: 3, t: 29.6, from: 'LON', to: 'SOF', thrF: 0.82, fly: 1.5, div: 'PDV', dv: 0.8, esc: { dt: 0.25, lab: 'BULGARIAN AIR FORCE' }, cnt: 1, dvc: 1, escc: 1 },
  { id: 'H4', day: 3, t: 29.9, from: 'CPH', to: 'SOF', thrF: 0.78, fly: 1.3, esc: { dt: 0.25 }, cnt: 1, escc: 1 },
  { id: 'H5', day: 3, t: 30.2, from: 'MAD', to: 'SOF', thrF: 0.82, fly: 1.3, esc: { dt: 0.25 }, cnt: 1, escc: 1 },
  { id: 'H6', day: 3, t: 32.3, from: 'MIL', to: 'WAW', thrF: 0.3, fly: 0.8, div: 'VIE', dv: 0.8, cnt: 1, dvc: 1 },
  { id: 'H7', day: 3, t: 33.9, from: 'NCL', to: 'PRG', thrF: 0.7, fly: 1.1, cnt: 1, police: true },
  { id: 'H8', day: 3, t: 34.2, from: 'GLA', to: 'PRG', thrF: 0.7, fly: 1.1, cnt: 1, police: true },
  { id: 'H9', day: 3, t: 35.9, from: 'HEL', to: 'VIE', thrF: 0.6, fly: 0.9, cnt: 1 },
  { id: 'H10', day: 3, t: 36.2, from: 'BEG', to: 'OTP', thrF: 0.5, fly: 0.7, cnt: 1 },
  { id: 'H11', day: 3, t: 36.5, from: 'WAW', to: 'BRU', thrF: 0.6, fly: 0.9, cnt: 1 },
  { id: 'G1', day: 3, t: 38.3, ground: 'WAW', cnt: 1, chip: 'JET STOPPED ON TAXIWAY' },
  { id: 'G2', day: 3, t: 38.8, ground: 'MAD', cnt: 6, chip: '3 EMAILS · 6 FLIGHTS' },
];
const ORBIT = { t0: 15.3, t1: 17.4, at: 'FCO', escc: 1, lab: 'ITALIAN AIR FORCE' };   // Tue: a Ryanair jet escorted into Rome
const EXTRA = { t0: 41.6, t1: 43.0, cnt: 9 };   // rest of Thursday's reported 27+ flights (not individually mapped)

const AIR = { WIZZ: '#C6007E', LOT: '#0B3D91', SAS: '#1F3F99', RYANAIR: '#073590', AERLINGUS: '#00826F', FINNAIR: '#1A2A80', EASYJET: '#FF6600', GREY: '#4A5675', RED: '#C9252C' };
const CARDS = [
  { t0: 5.5, t1: 10.6, tag: 'MONDAY 2 NOV', air: 'WIZZ AIR', ac: AIR.WIZZ, fn: 'W6 4302', route: 'LONDON LUTON → SOFIA', out: 'DIVERTED TO BUDAPEST', oc: '#FF8A1F', det: 'Threat came in over Bosnia & Herzegovina · Hungarian Gripen escort', src: 'EURONEWS · AVIATION24' },
  { t0: 11.3, t1: 13.0, tag: 'TUESDAY 3 NOV', air: 'LOT', ac: AIR.LOT, fn: '', route: 'LONDON HEATHROW → WARSAW', out: 'DIVERTED TO MODLIN', oc: '#FF8A1F', det: 'Modlin airport closed, then reopened after the search', src: 'REUTERS · CNN' },
  { t0: 13.0, t1: 14.7, tag: 'TUESDAY 3 NOV', air: 'SAS', ac: AIR.SAS, fn: '', route: 'COPENHAGEN → WARSAW', out: 'LANDED · AIRCRAFT CHECKED', oc: '#FFD21F', det: 'Polish authorities: the threat was not confirmed', src: 'REUTERS' },
  { t0: 14.7, t1: 17.0, tag: 'TUESDAY 3 NOV', air: 'RYANAIR', ac: AIR.RYANAIR, fn: '2 FLIGHTS', route: 'LISBON & DUBLIN → ROME', out: 'SEARCHED AT FIUMICINO', oc: '#FFD21F', det: 'Italian Air Force jets escorted a Ryanair plane into Rome', src: 'REUTERS · AEROTIME' },
  { t0: 17.0, t1: 18.7, tag: 'TUESDAY 3 NOV', air: 'RYANAIR', ac: AIR.RYANAIR, fn: '', route: 'MANCHESTER → MURCIA', out: 'PARTS OF THE AIRPORT CORDONED OFF', oc: '#FFD21F', det: 'One of two targeted flights that left the UK that day', src: 'REUTERS · CNN' },
  { t0: 18.7, t1: 20.7, tag: 'TUESDAY 3 NOV', air: '2 FLIGHTS', ac: AIR.GREY, fn: '', route: 'MILAN-BERGAMO & DUBLIN → SOFIA', out: 'THREATS AGAINST BOTH', oc: '#FFD21F', det: 'Confirmed by Bulgaria’s transport ministry', src: 'REUTERS' },
  { t0: 20.7, t1: 23.3, tag: 'TUESDAY · TOTAL', air: '7 FLIGHTS', ac: AIR.RED, fn: '', route: 'RYANAIR ×4 · LOT · SAS · WIZZ AIR', out: '“MALICIOUS HOAX THREATS”', oc: '#3DF5A0', det: '— the UK government', src: 'REUTERS · AIRHELP' },
  { t0: 24.7, t1: 27.5, tag: 'THURSDAY 5 NOV', air: 'AER LINGUS', ac: AIR.AERLINGUS, fn: 'EI402', route: 'DUBLIN → ROME', out: 'DIVERTED TO ÉVREUX AIR BASE', oc: '#FF8A1F', det: '151 passengers & 6 crew safe · French Air Force jets dispatched', src: 'FRANCE 24 · IRISH TIMES' },
  { t0: 27.5, t1: 29.8, tag: 'THURSDAY 5 NOV', air: 'FINNAIR', ac: AIR.FINNAIR, fn: 'AY1761', route: 'HELSINKI → ROME', out: 'ESCORTED INTO ROME', oc: '#5FB8FF', det: 'Italian Air Force jets alongside · the bomb squad found nothing', src: 'REUTERS · NBC NEWS' },
  { t0: 29.8, t1: 32.5, tag: 'THURSDAY 5 NOV', air: 'RYANAIR', ac: AIR.RYANAIR, fn: '3 FLIGHTS', route: 'LONDON, COPENHAGEN & MADRID → SOFIA', out: 'LONDON FLIGHT DIVERTED TO PLOVDIV', oc: '#FF8A1F', det: 'Bulgaria’s air force escorted all three', src: 'AL JAZEERA · GULF NEWS' },
  { t0: 32.5, t1: 34.2, tag: 'THURSDAY 5 NOV', air: 'WIZZ AIR', ac: AIR.WIZZ, fn: '', route: 'MILAN → WARSAW', out: 'DIVERTED TO VIENNA', oc: '#FF8A1F', det: 'Wizz Air: “established safety protocols” followed', src: 'AL JAZEERA' },
  { t0: 34.2, t1: 36.2, tag: 'THURSDAY 5 NOV', air: 'EASYJET', ac: AIR.EASYJET, fn: '2 FLIGHTS', route: 'NEWCASTLE & GLASGOW → PRAGUE', out: 'MET BY POLICE IN PRAGUE', oc: '#FFD21F', det: 'Prague Airport got one anonymous email naming 4 flights', src: 'CNN · REUTERS' },
  { t0: 36.2, t1: 38.4, tag: 'THURSDAY 5 NOV', air: 'FINNAIR · AIR SERBIA · LOT', ac: AIR.GREY, fn: '', route: 'HELSINKI → VIENNA · BELGRADE → BUCHAREST · WARSAW → BRUSSELS', out: 'ALL LANDED · NOTHING FOUND', oc: '#3DF5A0', det: '', src: 'REUTERS · CNBC' },
  { t0: 38.4, t1: 41.4, tag: 'THURSDAY 5 NOV', air: 'MADRID', ac: AIR.RED, fn: '', route: '3 EMAILED THREATS IN UNDER 20 MINUTES', out: '6 FLIGHTS AFFECTED', oc: '#FF3B3B', det: 'Iberia & Air Europa · in Warsaw a LOT jet was stopped on the taxiway', src: 'REUTERS · CNN' },
  { t0: 41.4, t1: 44.2, tag: 'THURSDAY · TOTAL', air: '27+ FLIGHTS', ac: AIR.RED, fn: '', route: 'FRANCE · BULGARIA · ROMANIA · SPAIN · POLAND · DENMARK…', out: 'NO EXPLOSIVES FOUND', oc: '#3DF5A0', det: 'Counts vary: CNN 14+ · France 24 25+ · RTÉ 27+', src: 'RTÉ · FRANCE 24 · CNN' },
];
const SPLASH = [
  { t0: 4.35, t1: 5.45, big: 'MONDAY', sub: '2 NOVEMBER', col: '#FF8A1F' },
  { t0: 10.6, t1: 11.7, big: 'TUESDAY', sub: '3 NOVEMBER', col: '#FF5A3B' },
  { t0: 23.3, t1: 24.6, big: 'THURSDAY', sub: 'THE BIGGEST WAVE', col: '#FF3B3B' },
];
const QA = [
  { t0: 44.4, t1: 47.5, big: 'HOW?', ans: 'Anonymous emails', note: 'sent to airports — Czech, Italian & Spanish authorities say', col: '#FF8A1F' },
  { t0: 47.5, t1: 50.7, big: 'WHO?', ans: 'Not yet identified', note: 'Investigations continue · the EU says it is not yet clear whether the threats are linked', col: '#FF3B3B' },
];
const DAYS = [{ big: 'MON', sub: '2 NOV 2026', t0: 4.4, t1: 10.6 }, { big: 'TUE', sub: '3 NOV 2026', t0: 10.6, t1: 23.3 }, { big: 'WED', sub: '4 NOV 2026', t0: 23.3, t1: 23.3 }, { big: 'THU', sub: '5 NOV 2026', t0: 23.3, t1: 44.3 }];
const T_FIN = 50.8;

// ------------------------------------------------------------------ GEO
const [land, ctry] = await Promise.all([fetch('node_modules/world-atlas/land-50m.json').then(r => r.json()), fetch('node_modules/world-atlas/countries-50m.json').then(r => r.json())]);
const inBox = ([lo, la]) => lo > -45 && lo < 60 && la > 22 && la < 80;
function simp(line, tol = 0.03) { const o = []; let p = null; for (const q of line) { if (!p || Math.abs(q[0] - p[0]) > tol || Math.abs(q[1] - p[1]) > tol) { o.push(q); p = q; } } return o; }
const LAND = [];
for (const f of feature(land, land.objects.land).features) {
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) for (const ring of poly) if (ring.some(inBox)) LAND.push(Float64Array.from(simp(ring).flatMap(([lo, la]) => [la * D2R, lo * D2R])));
}
const BORD = [];
for (const ln of mesh(ctry, ctry.objects.countries, (a, b) => a !== b).coordinates) if (ln.some(inBox)) BORD.push(Float64Array.from(simp(ln, 0.04).flatMap(([lo, la]) => [la * D2R, lo * D2R])));

// camera: [t, lat, lon, k(px per earth radius)]
const CAMK = [
  [0, 50.5, 11, 1450], [3.0, 50, 10, 1640], [4.6, 48.0, 10.8, 2320], [10.5, 48.0, 10.8, 2320], [11.4, 47.6, 6.5, 1870], [23.2, 47.6, 6.5, 1870],
  [24.3, 47.6, 4.5, 2380], [26.8, 47.6, 4.5, 2380], [27.6, 50.5, 14, 1800], [29.3, 50.5, 14, 1800], [30.0, 47.5, 10, 1720], [32.1, 47.5, 10, 1720],
  [32.9, 50.5, 9, 2000], [35.4, 50.5, 9, 2000], [36.1, 51.5, 15.5, 1900], [37.8, 51.5, 15.5, 1900], [38.6, 47.2, 8.5, 1750], [41.0, 47.2, 8.5, 1750],
  [42.0, 49.5, 9.5, 1630], [44.3, 49.5, 9.5, 1630], [45.2, 49.5, 9.5, 1500], [60, 49.5, 9.5, 1500],
];
const CX = 540, CY = 790;
let cam = { la: 0, lo: 0, k: 1, s0: 0, c0: 1 };
function setCam(t) {
  let i = 0; while (i < CAMK.length - 2 && t > CAMK[i + 1][0]) i++;
  const a = CAMK[i], b = CAMK[i + 1], e = ease((t - a[0]) / (b[0] - a[0]));
  cam.la = lerp(a[1], b[1], e) * D2R; cam.lo = lerp(a[2], b[2], e) * D2R; cam.k = lerp(a[3], b[3], e);
  cam.s0 = Math.sin(cam.la); cam.c0 = Math.cos(cam.la);
}
function projR(phi, lam, out) {
  const cp = Math.cos(phi), sp = Math.sin(phi), dl = lam - cam.lo, cd = Math.cos(dl);
  let x = cp * Math.sin(dl), y = cam.c0 * sp - cam.s0 * cp * cd; const cz = cam.s0 * sp + cam.c0 * cp * cd;
  if (cz < 0) { const n = Math.hypot(x, y) || 1; x /= n; y /= n; }
  out[0] = CX + cam.k * x; out[1] = CY - cam.k * y; return out;
}
const proj = (la, lo) => projR(la * D2R, lo * D2R, [0, 0]);
const P = (code) => proj(APT[code][0], APT[code][1]);
const vec = (la, lo) => { la *= D2R; lo *= D2R; return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)]; };
function slerp(a, b, s) {
  const d = Math.acos(clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1)); if (d < 1e-6) return a;
  const k0 = Math.sin((1 - s) * d) / Math.sin(d), k1 = Math.sin(s * d) / Math.sin(d);
  const v = [a[0] * k0 + b[0] * k1, a[1] * k0 + b[1] * k1, a[2] * k0 + b[2] * k1];
  return [Math.asin(v[2]), Math.atan2(v[1], v[0])];
}

// ------------------------------------------------------------------ INCIDENT TIMING
for (const I of INC) {
  if (I.ground) { I.tT = I.t + 0.2; I.tE = I.t + 3.2; continue; }
  I.va = vec(APT[I.from][0], APT[I.from][1]); I.vb = vec(APT[I.to][0], APT[I.to][1]);
  if (I.thrNear) { const tv = vec(...I.thrNear); let best = 1e9; for (let s = 0.02; s < 0.98; s += 0.005) { const [p, l] = slerp(I.va, I.vb, s); const v = [Math.cos(p) * Math.cos(l), Math.cos(p) * Math.sin(l), Math.sin(p)]; const d = (v[0] - tv[0]) ** 2 + (v[1] - tv[1]) ** 2 + (v[2] - tv[2]) ** 2; if (d < best) { best = d; I.thrF = s; } } }
  I.tF0 = I.t + 0.35; I.tT = I.tF0 + I.fly;
  if (I.div) I.tL = I.tT + 0.15 + I.dv; else { I.rem = clamp(2 * I.fly * (1 - I.thrF) / I.thrF, 0.6, 1.6); I.tL = I.tT + I.rem; }
  I.tE = I.tL + 0.9;
}
// route point on screen with a lifted arc
function routePt(I, s, out = [0, 0]) {
  const [p, l] = slerp(I.va, I.vb, s); projR(p, l, out);
  const a = I._pa, b = I._pb; const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  out[1] -= Math.sin(Math.PI * s) * len * 0.10; return out;
}
function bez(p0, p1, p2, u) { const v = 1 - u; return [v * v * p0[0] + 2 * v * u * p1[0] + u * u * p2[0], v * v * p0[1] + 2 * v * u * p1[1] + u * u * p2[1]]; }
function divCtl(I) {
  const p0 = routePt(I, I.thrF), pa = routePt(I, Math.max(0, I.thrF - 0.02)), p2 = P(I.div);
  let dx = p0[0] - pa[0], dy = p0[1] - pa[1]; const n = Math.hypot(dx, dy) || 1; dx /= n; dy /= n;
  const L = Math.hypot(p2[0] - p0[0], p2[1] - p0[1]) * 0.5; return [p0, [p0[0] + dx * L, p0[1] + dy * L], p2];
}
// plane state: {x, y, hd, mode} or null
function plane(I, t) {
  if (I.ground || t < I.tF0 - 0.05 || t > I.tL + 0.25) return null;
  let pos, pos2, s;
  if (t < I.tT) { s = I.thrF * clamp((t - I.tF0) / I.fly, 0, 1); pos = routePt(I, s); pos2 = routePt(I, Math.min(1, s + 0.01)); return { x: pos[0], y: pos[1], hd: Math.atan2(pos2[1] - pos[1], pos2[0] - pos[0]), s, alert: false }; }
  if (I.div) {
    const [p0, p1, p2] = divCtl(I); const u = clamp((t - I.tT) / (0.15 + I.dv), 0, 1), ue = 1 - Math.pow(1 - u, 1.7);
    pos = bez(p0, p1, p2, ue); pos2 = bez(p0, p1, p2, Math.min(1, ue + 0.01)); if (ue >= 0.995) { const q = bez(p0, p1, p2, 0.985); pos2 = [2 * pos[0] - q[0], 2 * pos[1] - q[1]]; }
    return { x: pos[0], y: pos[1], hd: Math.atan2(pos2[1] - pos[1], pos2[0] - pos[0]), s: I.thrF, u: ue, alert: true };
  }
  const k = clamp((t - I.tT) / I.rem, 0, 1); s = I.thrF + (1 - I.thrF) * (2 * k - k * k);
  pos = routePt(I, s); pos2 = routePt(I, Math.min(1, s + 0.01)); if (s > 0.985) { const q = routePt(I, s - 0.01); pos2 = [2 * pos[0] - q[0], 2 * pos[1] - q[1]]; }
  return { x: pos[0], y: pos[1], hd: Math.atan2(pos2[1] - pos[1], pos2[0] - pos[0]), s, alert: true };
}

// ------------------------------------------------------------------ CANVAS DRAWING
const cv = $('map'), gMain = cv.getContext('2d'); let g = gMain;
const baseCv = document.createElement('canvas'); baseCv.width = W; baseCv.height = H; const gBase = baseCv.getContext('2d'); let baseKey = '';
const tmp = [0, 0];
function ringPath(arr, close) {
  const p = new Path2D(); for (let i = 0; i < arr.length; i += 2) { projR(arr[i], arr[i + 1], tmp); if (i === 0) p.moveTo(tmp[0], tmp[1]); else p.lineTo(tmp[0], tmp[1]); } if (close) p.closePath(); return p;
}
const sea = g.createRadialGradient(540, 760, 80, 540, 820, 1200); sea.addColorStop(0, '#0a1630'); sea.addColorStop(0.6, '#060d1f'); sea.addColorStop(1, '#03060e');
function drawBase() {
  g.fillStyle = sea; g.fillRect(0, 0, W, H);
  // graticule
  g.strokeStyle = 'rgba(80,110,180,0.10)'; g.lineWidth = 1; g.beginPath();
  for (let lo = -40; lo <= 60; lo += 10) for (let la = 24; la <= 78; la += 2) { projR(la * D2R, lo * D2R, tmp); if (la === 24) g.moveTo(tmp[0], tmp[1]); else g.lineTo(tmp[0], tmp[1]); }
  for (let la = 30; la <= 70; la += 10) for (let lo = -40; lo <= 60; lo += 2) { projR(la * D2R, lo * D2R, tmp); if (lo === -40) g.moveTo(tmp[0], tmp[1]); else g.lineTo(tmp[0], tmp[1]); }
  g.stroke();
  const lp = new Path2D(); for (const r of LAND) lp.addPath(ringPath(r, true));
  g.fillStyle = '#0e1a33'; g.fill(lp);
  g.strokeStyle = 'rgba(70,130,255,0.10)'; g.lineWidth = 8; g.stroke(lp);
  g.strokeStyle = 'rgba(110,160,255,0.55)'; g.lineWidth = 1.4; g.stroke(lp);
  const bp = new Path2D(); for (const r of BORD) bp.addPath(ringPath(r, false));
  g.strokeStyle = 'rgba(110,140,210,0.28)'; g.lineWidth = 1; g.stroke(bp);
}
function polyline(I, s0, s1, n = 40) { const p = new Path2D(); for (let i = 0; i <= n; i++) { const s = lerp(s0, s1, i / n); routePt(I, s, tmp); if (i === 0) p.moveTo(tmp[0], tmp[1]); else p.lineTo(tmp[0], tmp[1]); } return p; }
function bezPath(c, u1, n = 30) { const p = new Path2D(); for (let i = 0; i <= n; i++) { const q = bez(c[0], c[1], c[2], u1 * i / n); if (i === 0) p.moveTo(q[0], q[1]); else p.lineTo(q[0], q[1]); } return p; }
function glowStroke(path, col, w, a) { g.globalAlpha = a * 0.22; g.strokeStyle = col; g.lineWidth = w * 3.2; g.stroke(path); g.globalAlpha = a; g.lineWidth = w; g.stroke(path); g.globalAlpha = 1; }
const PLANE = [[0.5, 0], [0.42, 0.055], [0.12, 0.07], [-0.1, 0.5], [-0.2, 0.5], [-0.07, 0.075], [-0.33, 0.065], [-0.43, 0.2], [-0.5, 0.2], [-0.46, 0]];
const JET = [[0.5, 0], [0.1, 0.1], [-0.25, 0.42], [-0.32, 0.42], [-0.22, 0.1], [-0.45, 0.13], [-0.5, 0]];
function glyph(shape, x, y, hd, size, col, a) {
  g.save(); g.translate(x, y); g.rotate(hd); g.scale(size, size); g.beginPath();
  shape.forEach(([px, py], i) => i ? g.lineTo(px, py) : g.moveTo(px, py)); for (let i = shape.length - 1; i >= 0; i--) g.lineTo(shape[i][0], -shape[i][1]);
  g.closePath(); g.globalAlpha = a; g.fillStyle = col; g.fill(); g.restore(); g.globalAlpha = 1;
}
function ring(x, y, r, col, w, a) { if (a <= 0.01) return; g.globalAlpha = a; g.strokeStyle = col; g.lineWidth = w; g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.stroke(); g.globalAlpha = 1; }
function dot(x, y, r, col, a) { if (a <= 0.01) return; g.globalAlpha = a * 0.25; g.fillStyle = col; g.beginPath(); g.arc(x, y, r * 2.6, 0, 6.2832); g.fill(); g.globalAlpha = a; g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.fill(); g.globalAlpha = 1; }
function chip(x, y, text, bg, fg, a, sc = 1, fs = 17) {
  if (a <= 0.01) return; g.save(); g.translate(x, y); g.scale(sc, sc); g.font = `900 ${fs}px Inter`; const w = g.measureText(text).width + 22, h = fs + 14;
  g.globalAlpha = a; g.fillStyle = bg; g.beginPath(); g.roundRect(-w / 2, -h / 2, w, h, 8); g.fill(); g.fillStyle = fg; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 0, 1); g.restore(); g.globalAlpha = 1;
}
function label(x, y, text, a, col = '#e8eeff', fs = 17) {
  if (a <= 0.01) return; g.font = `800 ${fs}px Inter`; g.textAlign = 'center'; g.textBaseline = 'bottom'; g.globalAlpha = a;
  g.lineWidth = 5; g.strokeStyle = 'rgba(2,4,10,0.9)'; g.strokeText(text, x, y); g.fillStyle = col; g.fillText(text, x, y); g.globalAlpha = 1;
}
const popA = (t, t0, t1) => win(t, t0, t1, 0.18, 0.3), popS = (t, t0) => lerp(0.5, 1, backOut(clamp((t - t0) / 0.3, 0, 1)));

function drawIncidents(t) {
  const aptA = {};   // airport label alpha
  const bump = (c, a) => { aptA[c] = Math.max(aptA[c] || 0, a); };
  for (const I of INC) {
    if (t < I.t) continue;
    if (I.ground) {
      const [x, y] = P(I.ground); const live = win(t, I.t, I.tE, 0.2, 0.6);
      for (let k = 0; k < 3; k++) { const u = (t - I.t - k * 0.55) / 1.3; if (u > 0 && u < 1 && t < I.tE) ring(x, y, 8 + u * 60, '#FF3B3B', 3, (1 - u) * 0.9); }
      dot(x, y, 6, '#FF3B3B', 0.5 + 0.5 * live); chip(x, y - 40, I.chip, '#C9252C', '#fff', live, popS(t, I.t)); bump(I.ground, live);
      continue;
    }
    I._pa = P(I.from); I._pb = P(I.to);
    const hist = smooth(I.tE, I.tE + 0.8, t);          // 0 = live, 1 = history
    const fade = lerp(1, 0.32, hist);
    // planned route (draws on)
    const dr = clamp((t - I.t) / 0.5, 0, 1);
    g.setLineDash([7, 7]);
    if (I.div && t > I.tT) {
      glowStroke(polyline(I, 0, I.thrF), '#dfe6ff', 1.8, 0.45 * fade);
      glowStroke(polyline(I, I.thrF, 1), '#FF5A5A', 1.8, lerp(0.55, 0.16, smooth(I.tT, I.tL, t)) * fade);
    } else glowStroke(polyline(I, 0, dr), '#dfe6ff', 1.8, 0.45 * fade * (1 - 0.6 * hist));
    g.setLineDash([]);
    const pl = plane(I, t);
    const sNow = pl ? pl.s : (t >= I.tL ? (I.div ? I.thrF : 1) : 0);
    // flown trail
    if (t > I.tF0) {
      const sCut = Math.min(sNow, I.thrF); glowStroke(polyline(I, 0, sCut), '#38C8FF', 2.6, 0.95 * fade);
      if (!I.div && sNow > I.thrF) glowStroke(polyline(I, I.thrF, sNow), '#FFB547', 2.8, 0.95 * fade);
    }
    if (I.div && t > I.tT) { const c = divCtl(I); const u = pl ? pl.u : 1; glowStroke(bezPath(c, u), '#FF8A1F', 3.4, lerp(1, 0.55, hist)); }
    // endpoints
    dot(I._pa[0], I._pa[1], 4.5, '#38C8FF', 0.9 * fade);
    if (I.div) { const [x, y] = I._pb; g.globalAlpha = (t > I.tT ? 0.8 : 0.5) * fade; g.strokeStyle = '#FF5A5A'; g.lineWidth = 2.5; g.beginPath(); g.moveTo(x - 6, y - 6); g.lineTo(x + 6, y + 6); g.moveTo(x + 6, y - 6); g.lineTo(x - 6, y + 6); g.stroke(); g.globalAlpha = 1; }
    else dot(I._pb[0], I._pb[1], 4.5, t > I.tL ? '#FFD21F' : '#dfe6ff', 0.8 * fade);
    const landC = I.div || I.to, [lx, ly] = P(landC);
    if (t > I.tL) { dot(lx, ly, 5.5, I.div ? '#FF8A1F' : '#FFD21F', lerp(1, 0.7, hist)); const u = (t - I.tL) / 1.1; if (u < 1) ring(lx, ly, 8 + u * 46, I.div ? '#FF8A1F' : '#FFD21F', 3, 1 - u); }
    const live = win(t, I.t, I.tE + 0.2, 0.25, 0.5);
    bump(I.from, live); bump(I.to, live * (I.div ? 0.7 : 1)); if (I.div) bump(I.div, win(t, I.tT, I.tE + 0.2, 0.3, 0.5));
    // threat burst
    if (t > I.tT - 0.05 && t < I.tT + 2.0) {
      const tp = routePt(I, I.thrF);
      for (let k = 0; k < 3; k++) { const u = (t - I.tT - k * 0.28) / 1.0; if (u > 0 && u < 1) ring(tp[0], tp[1], 6 + u * 70, '#FF3B3B', 3.2, (1 - u) * 0.95); }
    }
    // escort fighters
    if (I.esc && pl && t > I.tT + I.esc.dt) {
      const e = easeOut((t - I.tT - I.esc.dt) / 0.7), a = e * (1 - smooth(I.tL - 0.1, I.tL + 0.2, t));
      for (const sd of [1, -1]) { const off = lerp(150, 24, e), bx = -Math.cos(pl.hd) * 12, by = -Math.sin(pl.hd) * 12;
        glyph(JET, pl.x + bx - Math.sin(pl.hd) * off * sd, pl.y + by + Math.cos(pl.hd) * off * sd, pl.hd, 17, '#9fd4ff', a); }
      if (I.esc.lab) chip(pl.x, pl.y + 46, I.esc.lab, 'rgba(20,60,110,0.92)', '#cfe8ff', win(t, I.tT + I.esc.dt + 0.2, I.tL + 0.1, 0.2, 0.3), 1, 14);
    }
    // the aircraft
    if (pl) {
      const a = 1 - smooth(I.tL, I.tL + 0.25, t), col = pl.alert ? '#FF6A4A' : '#ffffff';
      g.globalAlpha = 0.35 * a; g.fillStyle = pl.alert ? '#FF3B3B' : '#38C8FF'; g.beginPath(); g.arc(pl.x, pl.y, 17, 0, 6.2832); g.fill(); g.globalAlpha = 1;
      glyph(PLANE, pl.x, pl.y, pl.hd, 26, col, a);
    }
    if (t > I.tT - 0.05) { const tp = routePt(I, I.thrF); chip(tp[0], tp[1] - 44, '⚠ BOMB THREAT', '#E5262D', '#fff', popA(t, I.tT, I.tT + 1.6), popS(t, I.tT)); }
    if (I.police) chip(lx + (I.id === 'H7' ? -52 : 52), ly - 58, 'POLICE', 'rgba(20,60,140,0.95)', '#fff', popA(t, I.tL, I.tL + 1.4), popS(t, I.tL), 14);
    if (I.cordon) chip(lx, ly + 38, 'CORDONED OFF', 'rgba(150,100,0,0.95)', '#fff', popA(t, I.tL, I.tL + 1.6), popS(t, I.tL), 14);
  }
  // Tuesday: Italian Air Force escort circling Rome
  if (t > ORBIT.t0 && t < ORBIT.t1 + 0.4) {
    const [x, y] = P(ORBIT.at), a = win(t, ORBIT.t0, ORBIT.t1, 0.4, 0.4);
    for (const ph of [0, Math.PI]) { const an = (t - ORBIT.t0) * 2.4 + ph; glyph(JET, x + Math.cos(an) * 44, y + Math.sin(an) * 30, an + Math.PI / 2, 17, '#9fd4ff', a); }
    chip(x, y + 62, ORBIT.lab, 'rgba(20,60,110,0.92)', '#cfe8ff', a, 1, 14);
  }
  for (const c in aptA) { const [x, y] = P(c); label(x, y - 12, APT[c][2], aptA[c]); }
}
// intro teaser: every threat location pulses
function drawTeaser(t, a) {
  if (a <= 0.01) return;
  INC.forEach((I, i) => {
    let la, lo; if (I.ground) [la, lo] = APT[I.ground]; else { const [p, l] = slerp(I.va, I.vb, I.thrF); la = p / D2R; lo = l / D2R; }
    const [x, y] = proj(la, lo), t0 = 0.15 + i * 0.12, u = ((t - t0) % 1.6) / 1.6;
    if (t > t0) { ring(x, y, 5 + u * 44, '#FF3B3B', 2.5, (1 - u) * a); dot(x, y, 4, '#FF3B3B', a); }
  });
}

// ------------------------------------------------------------------ KINETIC TYPE
const WORD_TICKS = [];
function kinPrep(el, text, mode, cols) {
  const key = text + '|' + mode; if (el.__k === key) return el.__sp; el.__k = key; el.textContent = '';
  const parts = mode === 'char' ? [...text] : text.split(/(\s+)/), sp = [];
  for (const p of parts) { if (p === '') continue; if (/^\s+$/.test(p)) { el.appendChild(document.createTextNode(' ')); continue; }
    const s = document.createElement('span'); s.textContent = p; s.style.display = 'inline-block'; s.style.whiteSpace = 'pre'; s.style.transformOrigin = '50% 70%'; el.appendChild(s); sp.push(s); }
  if (cols) sp.forEach((s, i) => s.style.color = gradAt(cols, (i + 0.5) / sp.length));
  el.__sp = sp; return sp;
}
function hex(c) { return [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)); }
function gradAt(cols, f) { const k = clamp(f, 0, 1) * (cols.length - 1), i = Math.min(cols.length - 2, Math.floor(k)); const a = hex(cols[i]), b = hex(cols[i + 1]), u = k - i; return `rgb(${a.map((v, j) => Math.round(lerp(v, b[j], u))).join(',')})`; }
function kin(el, text, tIn, tOut, t, o = {}) {
  const sp = kinPrep(el, text, o.mode || 'word', o.cols);
  const st = o.stagger ?? 0.05, dIn = o.dIn ?? 0.32, dOut = o.dOut ?? 0.2, so = o.outStagger ?? st * 0.5; let vis = 0;
  sp.forEach((s, i) => {
    const a = clamp((t - (tIn + i * st)) / dIn, 0, 1), b = tOut == null ? 0 : clamp((t - (tOut + i * so)) / dOut, 0, 1);
    const ein = backOut(a), eo = b * b, op = clamp(a * 2.2, 0, 1) * (1 - b); vis = Math.max(vis, op);
    const sc = lerp(o.s0 ?? 0.35, 1, ein) * lerp(1, 0.6, eo), ty = lerp(o.y0 ?? 24, 0, ein) - 16 * eo, bl = (1 - a) * (o.blur ?? 6) + b * 6, rot = lerp(o.r0 ?? -8, 0, clamp(ein, 0, 1));
    s.style.opacity = op.toFixed(3); s.style.transform = `translateY(${ty.toFixed(1)}px) scale(${sc.toFixed(3)}) rotate(${rot.toFixed(2)}deg)`; s.style.filter = bl > 0.15 ? `blur(${bl.toFixed(1)}px)` : 'none';
  });
  return vis;
}
function pop(el, tIn, tOut, t, o = {}) {
  const a = clamp((t - tIn) / (o.dIn ?? 0.32), 0, 1), b = tOut == null ? 0 : clamp((t - tOut) / (o.dOut ?? 0.22), 0, 1);
  const sc = lerp(o.s0 ?? 0.6, 1, backOut(a)) * lerp(1, 0.75, b * b);
  el.style.opacity = (clamp(a * 2, 0, 1) * (1 - b)).toFixed(3);
  el.style.transform = `translateY(${((1 - backOut(a)) * (o.y0 ?? 18) - 10 * b * b).toFixed(1)}px) scale(${sc.toFixed(3)})`; return a * (1 - b);
}

// ------------------------------------------------------------------ COUNTERS
function odoPos(v, i) { const q = Math.pow(10, i); const fl = Math.floor(v / q); return (fl % 10) + smooth(q - 0.4, q, v - fl * q); }
class Odo {
  constructor(el, nd, fs, cw, col) { this.lh = Math.round(fs * 1.12); this.items = []; el.classList.add('odo'); el.style.fontSize = fs + 'px'; el.style.height = this.lh + 'px'; el.style.lineHeight = this.lh + 'px'; el.style.color = col;
    for (let i = nd - 1; i >= 0; i--) { const c = document.createElement('div'); c.className = 'col'; c.style.width = cw + 'px'; c.style.height = this.lh + 'px'; const s = document.createElement('div'); s.className = 'strip';
      s.innerHTML = Array.from({ length: 11 }, (_, d) => `<div style="height:${this.lh}px">${d % 10}</div>`).join(''); c.appendChild(s); el.appendChild(c); this.items.push({ i, c, s }); } this.cw = cw; }
  set(v) { v = Math.max(0, v); const n = Math.max(1, String(Math.floor(v + 0.4)).length); for (const it of this.items) { const on = it.i < n; it.c.style.display = on ? 'block' : 'none'; if (on) it.s.style.transform = `translateY(${-odoPos(v, it.i) * this.lh}px)`; } return n * this.cw; }
}
// counter events
const EV = { cnt: [], dvc: [], escc: [] };
for (const I of INC) { if (I.cnt) EV.cnt.push([I.tT, I.cnt]); if (I.dvc) EV.dvc.push([I.tT + 0.3, I.dvc]); if (I.escc) EV.escc.push([I.tT + (I.esc ? I.esc.dt + 0.3 : 0.3), I.escc]); }
EV.escc.push([ORBIT.t0 + 0.3, 1]); for (let k = 0; k < EXTRA.cnt; k++) EV.cnt.push([EXTRA.t0 + k * (EXTRA.t1 - EXTRA.t0) / EXTRA.cnt, 1]);
const val = (key, t) => EV[key].reduce((s, [te, n]) => s + n * smooth(te, te + 0.35, t), 0);
const TOT = { cnt: EV.cnt.reduce((s, e) => s + e[1], 0), dvc: EV.dvc.reduce((s, e) => s + e[1], 0), escc: EV.escc.reduce((s, e) => s + e[1], 0) };
const CTR = [
  { key: 'cnt', lab: 'FLIGHTS HIT', col: '#FF5A5A', acc: 'linear-gradient(180deg,#FF8A1F,#FF3B3B)' },
  { key: 'dvc', lab: 'DIVERTED', col: '#FF9A3F', acc: '#FF8A1F' },
  { key: 'escc', lab: 'FIGHTER ESCORTS', col: '#8FCBFF', acc: '#5FB8FF' },
  { key: 'zero', lab: 'BOMBS FOUND', col: '#3DF5A0', acc: '#3DF5A0' },
];
CTR.forEach((c, i) => {
  const d = document.createElement('div'); d.className = 'ctr'; d.style.left = (70 + i * 219.3) + 'px';
  d.innerHTML = `<div class="glow" style="background:radial-gradient(ellipse at 30% 60%, ${c.col}55, transparent 70%)"></div><div class="acc" style="background:${c.acc}"></div><div class="k" style="color:${c.col}"></div><div class="odv"></div><div class="plus" style="color:${c.col}"></div>`;
  $('ctrs').appendChild(d); c.el = d; c.k = d.querySelector('.k'); c.glow = d.querySelector('.glow'); c.plus = d.querySelector('.plus'); c.odo = new Odo(d.querySelector('.odv'), 2, 50, 31, c.col); d.querySelector('.odv').style.cssText += ';position:absolute;left:18px;top:34px';
});
// day bar
const DB = [];
['MON 2', 'TUE 3', 'WED 4', 'THU 5'].forEach((l, i) => { const d = document.createElement('div'); d.className = 'dseg'; d.style.left = (i * 215) + 'px'; d.style.width = '215px'; d.innerHTML = `<div class="lab">${l}</div><div class="cnt"></div><div class="bar"><div class="fill"></div></div>`; $('dayBar').appendChild(d); DB.push({ el: d, fill: d.querySelector('.fill'), cnt: d.querySelector('.cnt'), lab: d.querySelector('.lab') }); });
const dayCount = (d, t) => INC.filter(I => I.day === d).reduce((s, I) => s + I.cnt * smooth(I.tT, I.tT + 0.35, t), 0) + (d === 3 ? EV.cnt.filter(e => e[0] >= EXTRA.t0 - 0.01).reduce((s, [te, n]) => s + n * smooth(te, te + 0.35, t), 0) : 0);

// finale rows
const FROWS = [
  { lab: 'FLIGHTS HIT', key: 'cnt', col: '#FF5A5A', acc: 'linear-gradient(180deg,#FF8A1F,#FF3B3B)', pre: 'ABOUT' },
  { lab: 'DIVERTED', key: 'dvc', col: '#FF9A3F', acc: '#FF8A1F', pre: 'AT LEAST' },
  { lab: 'FIGHTER ESCORTS', key: 'escc', col: '#8FCBFF', acc: '#5FB8FF', pre: 'AT LEAST' },
  { lab: 'BOMBS FOUND', key: 'zero', col: '#3DF5A0', acc: '#3DF5A0', pre: '' },
];
FROWS.forEach((r, i) => { const d = document.createElement('div'); d.className = 'frow'; d.style.top = (930 + i * 126) + 'px'; d.innerHTML = `<div class="acc" style="background:${r.acc}"></div><div class="k" style="color:${r.col}"></div><div class="pre"></div><div class="odv"></div>`; $('fRows').appendChild(d); r.el = d; r.k = d.querySelector('.k'); r.preEl = d.querySelector('.pre'); r.odo = new Odo(d.querySelector('.odv'), 2, 64, 40, r.col); d.querySelector('.odv').style.cssText += ';position:absolute;right:30px;top:22px'; r.t = 53.0 + i * 0.5; });

// ------------------------------------------------------------------ FRAME
const RED3 = ['#FF8A1F', '#FF3B3B', '#FF2D6F'];
function renderFrame(t) {
  setCam(t);
  const curDay = DAYS.find(d => t >= d.t0 && t < d.t1) || (t < 4.4 ? null : DAYS[3]);
  const alarm = 0.35 + 0.65 * Math.max(...INC.map(I => win(t, I.tT - 0.1, I.tT + 1.4, 0.1, 0.8)), 0);
  const key = `${cam.la.toFixed(6)},${cam.lo.toFixed(6)},${cam.k.toFixed(2)}`;
  if (key !== baseKey) { g = gBase; drawBase(); g = gMain; baseKey = key; }
  g.drawImage(baseCv, 0, 0);
  $('alarm').style.opacity = (0.15 + 0.85 * (alarm - 0.35) / 0.65).toFixed(3);
  drawTeaser(t, 1 - smooth(2.7, 3.5, t));
  drawIncidents(t);

  // global dim for intro / Q&A / finale
  const qaDim = Math.max(...QA.map(q => win(t, q.t0, q.t1, 0.35, 0.35)));
  $('dim').style.opacity = (Math.max(0.45 * (1 - smooth(2.6, 3.4, t)), 0.55 * qaDim, 0.6 * smooth(T_FIN, T_FIN + 0.8, t))).toFixed(3);
  $('shadeBot').style.opacity = (smooth(3.0, 3.8, t) * (1 - smooth(T_FIN - 0.3, T_FIN + 0.3, t))).toFixed(3);
  $('shadeTop').style.opacity = (smooth(3.0, 3.8, t) * (1 - smooth(T_FIN - 0.3, T_FIN + 0.3, t))).toFixed(3);

  // intro
  kin($('iKick'), 'THIS WEEK IN EUROPE', 0.05, 2.55, t, { stagger: 0.05 });
  kin($('iBig'), 'BOMB THREATS', 0.22, 2.6, t, { mode: 'char', stagger: 0.04, s0: 0.2, y0: 40, cols: RED3, outStagger: 0.012 });
  kin($('iSky'), 'HIT DOZENS OF FLIGHTS', 0.75, 2.65, t, { stagger: 0.07 });
  pop($('iRule'), 1.0, 2.6, t, { s0: 0.1 });
  kin($('iSub'), '4 days. ~35 flights. 0 bombs found.', 1.3, 2.7, t, { stagger: 0.07, cols: ['#FFFFFF', '#FFD0C0', '#3DF5A0'] });

  // header
  const hOut = T_FIN - 0.2;
  pop($('live'), 3.0, hOut, t);
  $('live').style.background = (Math.floor(t * 1.6) % 2 && t < T_FIN) ? '#e5262d' : '#b31a20';
  kin($('hTitle'), 'EUROPE’S BOMB HOAX WAVE', 3.05, hOut, t, { cols: RED3 });
  kin($('hSub'), 'HOAX THREATS AGAINST FLIGHTS · 2–5 NOV 2026', 3.25, hOut, t, { stagger: 0.03 });
  const dLab = t < 4.4 ? null : t < 44.3 ? curDay : { big: 'WEEK', sub: '2–5 NOV 2026' };
  if (dLab) { const t0 = t < 44.3 ? dLab.t0 : 44.3; kin($('dayBig'), dLab.big, Math.max(3.4, t0 + 0.05), dLab === curDay && t < 44.3 ? (dLab.t1 < 44.3 ? dLab.t1 - 0.22 : 44.08) : hOut, t, { mode: 'char', stagger: 0.04, cols: RED3 }); kin($('daySub'), dLab.sub, Math.max(3.5, t0 + 0.12), dLab === curDay && t < 44.3 ? (dLab.t1 < 44.3 ? dLab.t1 - 0.22 : 44.08) : hOut, t, { stagger: 0.03 }); }
  else { kin($('dayBig'), ' ', 0, 0, t); kin($('daySub'), ' ', 0, 0, t); }

  // counters
  CTR.forEach((c, i) => {
    const t0 = 3.3 + i * 0.12; pop(c.el, t0, hOut, t);
    kin(c.k, c.lab, t0 + 0.1, hOut, t, { stagger: 0.03 });
    const v = c.key === 'zero' ? 0 : val(c.key, t); const w = c.odo.set(v);
    const done = c.key !== 'zero' && t > 44.2; c.plus.textContent = done && c.key !== 'cnt' ? '+' : ''; c.plus.style.left = (18 + w + 2) + 'px';
    let pulse = 0; if (c.key !== 'zero') for (const [te] of EV[c.key]) pulse = Math.max(pulse, Math.exp(-Math.max(0, t - te) * 4) * (t >= te ? 1 : 0));
    if (c.key === 'zero') pulse = 0.25 + 0.25 * Math.sin(t * 3);
    c.glow.style.opacity = pulse.toFixed(3);
  });
  // day bar
  pop($('dayBar'), 3.6, hOut, t);
  DB.forEach((d, i) => {
    const D = DAYS[i]; const f = i === 2 ? smooth(23.0, 23.3, t) : clamp((t - D.t0) / (D.t1 - D.t0), 0, 1);
    d.fill.style.width = (f * 100).toFixed(1) + '%';
    const n = Math.round(dayCount(i, t)); d.cnt.textContent = n ? `${n} ✈` : '';
    d.lab.style.color = curDay === D && t < 44.3 ? '#ffffff' : '#9aa8cc';
  });
  pop($('legend'), 3.9, hOut, t);

  // incident card
  const C = CARDS.find(c => t >= c.t0 - 0.05 && t < c.t1 + 0.25) || null;
  const cardVis = CARDS.some(c => t >= c.t0 && t < c.t1);
  pop($('card'), 4.6, hOut, t, { s0: 0.85 });
  if (C) {
    const o = C.t1 - 0.22;
    $('cAcc').style.background = C.oc;
    kin($('cTag'), C.tag, C.t0, o, t, { stagger: 0.03 });
    kin($('cSrc'), 'SOURCE: ' + C.src, C.t0 + 0.1, o, t, { stagger: 0.02 });
    const b = $('cAirB'); b.style.background = C.ac; b.textContent = C.air; pop(b, C.t0 + 0.05, o, t, { s0: 0.4 });
    kin($('cFn'), C.fn || ' ', C.t0 + 0.12, o, t);
    kin($('cRoute'), C.route, C.t0 + 0.16, o, t, { stagger: 0.04 });
    $('cOut').style.color = C.oc; kin($('cOut'), C.out, C.t0 + 0.4, o, t, { stagger: 0.06, s0: 0.2 });
    kin($('cDet'), C.det || ' ', C.t0 + 0.65, o, t, { stagger: 0.025 });
    $('cDet').style.top = ($('cOut').offsetHeight > 40 ? 226 : 192) + 'px';
    $('cOut').style.top = ($('cRoute').offsetHeight > 40 ? 182 : 146) + 'px';
    if ($('cRoute').offsetHeight > 40) $('cDet').style.top = ($('cOut').offsetHeight > 40 ? 262 : 226) + 'px';
  } else ['cTag', 'cSrc', 'cFn', 'cRoute', 'cOut', 'cDet'].forEach(id => kin($(id), ' ', 0, 0, t));
  if (!C) $('cAirB').style.opacity = 0;
  if (t > 44.2) $('card').style.opacity = (1 - smooth(44.2, 44.5, t)).toFixed(3);

  // splashes
  const SP = SPLASH.find(s => t >= s.t0 - 0.05 && t < s.t1 + 0.3), Q = QA.find(q => t >= q.t0 - 0.05 && t < q.t1 + 0.3);
  if (SP) { kin($('sBig'), SP.big, SP.t0, SP.t1 - 0.25, t, { mode: 'char', stagger: 0.035, cols: [SP.col, '#FFFFFF'], s0: 0.2, y0: 40 }); kin($('sSub'), SP.sub, SP.t0 + 0.2, SP.t1 - 0.2, t, { stagger: 0.06 }); $('sBig').style.top = '640px'; }
  else if (Q) { kin($('sBig'), Q.big, Q.t0, Q.t1 - 0.3, t, { mode: 'char', stagger: 0.05, cols: [Q.col, '#FFFFFF'], s0: 0.2, y0: 40 }); kin($('sSub'), ' ', 0, 0, t); $('sBig').style.top = '600px'; }
  else { kin($('sBig'), ' ', 0, 0, t); kin($('sSub'), ' ', 0, 0, t); }
  if (Q) { kin($('sAns'), Q.ans, Q.t0 + 0.35, Q.t1 - 0.3, t, { stagger: 0.08, s0: 0.3 }); kin($('sNote'), Q.note, Q.t0 + 0.75, Q.t1 - 0.3, t, { stagger: 0.03 }); }
  else { kin($('sAns'), ' ', 0, 0, t); kin($('sNote'), ' ', 0, 0, t); }

  // finale
  kin($('fL1'), 'HOAX THREATS.', T_FIN + 0.25, 59.3, t, { stagger: 0.09, s0: 0.2 });
  kin($('fL2'), 'REAL DISRUPTION.', T_FIN + 0.9, 59.35, t, { stagger: 0.09, s0: 0.2, cols: RED3 });
  FROWS.forEach(r => {
    pop(r.el, r.t, 59.4, t, { s0: 0.8 }); kin(r.k, r.lab, r.t + 0.08, 59.4, t, { stagger: 0.04 }); kin(r.preEl, r.pre || ' ', r.t + 0.3, 59.4, t);
    const tot = r.key === 'zero' ? 0 : TOT[r.key]; const v = tot * easeOut((t - r.t - 0.15) / 1.3); const w = r.odo.set(v);
    r.preEl.style.right = (30 + w + 16) + 'px';
  });
  kin($('fFoot'), 'Figures as reported 2–6 Nov 2026 by Reuters, CNN, RTÉ, AP, France 24, Euronews & others. Counts vary by outlet. No one has been publicly identified as responsible.', 55.6, 59.4, t, { stagger: 0.012, dIn: 0.25 });
}

function getAudioEvents() {
  const ev = { departs: [], threats: [], diverts: [], escorts: [], lands: [], grounds: [], splashes: [], qa: [], cards: [], ticks: [], words: [...WORD_TICKS], intro: [0.22, 0.75, 1.3], finale: [T_FIN + 0.25, T_FIN + 0.9], rows: FROWS.map(r => r.t), T_FIN };
  for (const I of INC) {
    if (I.ground) { ev.grounds.push(I.t); continue; }
    ev.departs.push(I.tF0); ev.threats.push(I.tT); if (I.div) ev.diverts.push(I.tT + 0.15); if (I.esc) ev.escorts.push(I.tT + I.esc.dt); ev.lands.push(I.tL);
  }
  ev.escorts.push(ORBIT.t0);
  for (const k of ['cnt', 'dvc', 'escc']) for (const [te] of EV[k]) ev.ticks.push(te);
  ev.splashes = SPLASH.map(s => s.t0); ev.qa = QA.map(q => q.t0); ev.cards = CARDS.map(c => c.t0 + 0.4);
  return ev;
}
window.renderFrame = renderFrame; window.getAudioEvents = getAudioEvents;
await document.fonts.ready; renderFrame(0); window.READY = true;

// HEATHROW: 80 YEARS IN 60 SECONDS (1946–2026). Facts and sources: README.md
import { feature } from './node_modules/topojson-client/src/index.js';

const W = 1080, H = 1920, D2R = Math.PI / 180;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a), 0, 1); return k * k * (3 - 2 * k); };
const ease = k => (k = clamp(k, 0, 1), k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const easeOut = k => 1 - Math.pow(1 - clamp(k, 0, 1), 3);
const backOut = k => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const $ = id => document.getElementById(id);
const win = (t, a, b, fi = 0.3, fo = 0.3) => smooth(a, a + fi, t) * (1 - smooth(b - fo, b, t));
const fmt = n => Math.round(n).toLocaleString('en-GB');

// ------------------------------------------------------------------ TIMELINE
const T_SWEEP0 = 3.2, T_SWEEP1 = 43.6, T_ROUTES = 44.0, T_FUT = 50.4, T_FIN = 53.4;
// the year odometer is keyed so each milestone card appears exactly as its year rolls in
const YK = [[T_SWEEP0, 1946], [6.4, 1946.5], [7.0, 1951], [8.6, 1952], [10.2, 1955], [12.0, 1961], [13.6, 1966], [15.1, 1968], [16.7, 1970], [18.3, 1976], [19.9, 1977],
  [21.5, 1979], [23.0, 1986], [24.7, 1994], [26.5, 2003], [28.3, 2005], [30.3, 2008], [32.3, 2014], [34.2, 2019], [36.6, 2020], [39.3, 2024], [41.6, 2025], [T_SWEEP1, 2026.0]];
function yearAt(t) { if (t <= YK[0][0]) return YK[0][1]; for (let i = 0; i < YK.length - 1; i++) { const [a, ya] = YK[i], [b, yb] = YK[i + 1]; if (t <= b) return lerp(ya, yb, (t - a) / (b - a)); } return YK[YK.length - 1][1]; }
function tOfYear(y) { for (let i = 0; i < YK.length - 1; i++) { const [a, ya] = YK[i], [b, yb] = YK[i + 1]; if (y <= yb) return lerp(a, b, (y - ya) / (yb - ya)); } return T_SWEEP1; }

// passengers (millions). Sourced: 1946, 1951, 1968, 1979, 1986–2025. ≈ marks 1958 (">2m") and 1972 (below 2021's 19.4m).
const PAXK = { 1946: 0.063, 1951: 0.796, 1958: 2.0, 1968: 14.0, 1972: 18.5, 1979: 27.0,
  1986: 31.7, 1987: 34.7, 1988: 37.8, 1989: 39.9, 1990: 42.95, 1991: 40.5, 1992: 45.2, 1993: 47.9, 1994: 51.7, 1995: 54.5, 1996: 56.0, 1997: 58.2, 1998: 60.7, 1999: 62.3,
  2000: 64.6, 2001: 60.8, 2002: 63.4, 2003: 63.5, 2004: 67.3, 2005: 67.9, 2006: 67.5, 2007: 68.1, 2008: 67.1, 2009: 66.0, 2010: 65.9, 2011: 69.4, 2012: 70.0, 2013: 72.4, 2014: 73.4,
  2015: 75.0, 2016: 75.7, 2017: 78.0, 2018: 80.1, 2019: 80.9, 2020: 22.1, 2021: 19.4, 2022: 61.6, 2023: 79.2, 2024: 83.9, 2025: 84.463 };
const PY = Object.keys(PAXK).map(Number).sort((a, b) => a - b);
const SOURCED = y => y === 1946 || y === 1951 || y === 1968 || y === 1979 || y >= 1986;
function paxYear(y) {   // value for a (possibly fractional) year, log-interpolated between anchors
  if (y >= 2025) return PAXK[2025];
  let i = 0; while (i < PY.length - 2 && y > PY[i + 1]) i++;
  const a = PY[i], b = PY[i + 1], k = clamp((y - a) / (b - a), 0, 1);
  return Math.exp(lerp(Math.log(PAXK[a]), Math.log(PAXK[b]), k));
}

// airport plan (schematic, metres; x east, y south). Hexagram runways: 3 in 1946, 6 by the early 1950s.
const RWY = [
  { a: 1946, c: 9999, p: [[-1300, -700], [1500, -700]], ext: { y: 1970, p: [[-1950, -700], [1950, -700]] }, lab: ['09L', '27R'] },
  { a: 1946, c: 1965, p: [[-1356, -950], [-202, 1050]] },
  { a: 1946, c: 2005, p: [[1356, -950], [202, 1050]], lab: ['23', '05'] },
  { a: 1951, c: 9999, p: [[-1300, 715], [1500, 715]], ext: { y: 1970, p: [[-1800, 715], [1860, 715]] }, lab: ['09R', '27L'] },
  { a: 1951, c: 1959, p: [[-1356, 950], [-202, -1050]] },
  { a: 1951, c: 1972, p: [[1356, 950], [202, -1050]] },
];
const BLD = [
  { a: 1946, c: 1955.9, r: [-700, -1135, 900, 70], lab: 'TENTS', col: '#d8c79a' },
  { a: 1955.9, c: 2009.8, r: [-110, -330, 400, 150], lab: 'EUROPA T2', col: '#7fb2ff', term: 1 },
  { a: 1955.9, c: 2009.8, r: [-110, -170, 400, 70], lab: '', col: '#6c8fd0' },
  { a: 1961.85, c: 9999, r: [300, 70, 300, 230], lab: 'T3', col: '#7fb2ff', term: 1 },
  { a: 1968.3, c: 2015.5, r: [-440, -60, 270, 260], lab: 'T1', col: '#7fb2ff', term: 1 },
  { a: 1968.0, c: 9999, r: [-980, 990, 640, 220], lab: 'CARGO', col: '#c99b5a' },
  { a: 1986.25, c: 9999, r: [880, 990, 440, 180], lab: 'T4', col: '#7fb2ff', term: 1 },
  { a: 2008.24, c: 9999, r: [-1560, -230, 560, 330], lab: 'T5', col: '#9fd0ff', term: 1 },
  { a: 2008.24, c: 9999, r: [-930, -200, 150, 270], lab: '', col: '#8cc0f0' },
  { a: 2014.42, c: 9999, r: [-140, -350, 460, 230], lab: 'T2', col: '#9fd0ff', term: 1 },
];
const RAIL = [
  { a: 1977.95, p: [[2400, 1300], [1400, 1170], [500, 450], [150, 50]], lab: 'PICCADILLY LINE' },
  { a: 1986.3, p: [[1400, 1170], [1150, 1120]] },
  { a: 2008.24, p: [[150, 50], [-400, 120], [-1250, 60]] },
];
const ROADS = [{ a: 1946, p: [[-2600, -1200], [2600, -1200]], lab: 'BATH ROAD' }, { a: 1955.9, p: [[120, -1200], [120, -350]], lab: '' }];
const RWY3 = { p: [[-4200, -2050], [-700, -2050]] };   // proposed third runway (north-west), schematic

// milestone cards
const CARDS = [
  { y: '1 JAN 1946', t0: 3.4, t1: 5.3, title: 'THE FIRST DEPARTURE', det: 'A BSAA Lancastrian, “Star Light”, leaves for Buenos Aires' },
  { y: '1946', t0: 5.3, t1: 7.0, title: 'TERMINALS? TENTS.', det: '63,000 passengers in year one · BOAC & Pan Am fly to New York' },
  { y: '1951', t0: 7.0, t1: 8.6, title: '6 RUNWAYS IN A STAR', det: 'By the early 1950s the hexagram layout is complete' },
  { y: '1952', t0: 8.6, t1: 10.2, title: 'THE JET AGE BEGINS', det: 'BOAC’s Comet: the first jet airliner service, to Johannesburg' },
  { y: '1955', t0: 10.2, t1: 12.0, title: 'THE FIRST PERMANENT TERMINAL', det: 'The Queen opens the Europa Building (later T2) and the Queen’s Building' },
  { y: '1961', t0: 12.0, t1: 13.6, title: 'OCEANIC TERMINAL (T3)', det: 'Built for long-haul flights' },
  { y: '1966', t0: 13.6, t1: 15.1, title: '“LONDON AIRPORT” BECOMES HEATHROW', det: 'The diagonal runways close one by one (1950s–70s)' },
  { y: '1968', t0: 15.1, t1: 16.7, title: 'TERMINAL 1 OPENS', det: '14 million passengers a year' },
  { y: '1970', t0: 16.7, t1: 18.3, title: 'THE JUMBO JET LANDS', det: 'Pan Am’s first Boeing 747 from New York · runways lengthened' },
  { y: '1976', t0: 18.3, t1: 19.9, title: 'CONCORDE TAKES OFF', det: 'First commercial flight: Heathrow → Bahrain' },
  { y: '1977', t0: 19.9, t1: 21.5, title: 'THE TUBE REACHES THE AIRPORT', det: 'Piccadilly line: a world first for a capital and its main airport' },
  { y: '1979', t0: 21.5, t1: 23.0, title: '27 MILLION A YEAR', det: 'The 1970s brought wide-body jets and Concorde' },
  { y: '1986', t0: 23.0, t1: 24.7, title: 'TERMINAL 4 OPENS', det: 'Opened by Prince Charles and Princess Diana' },
  { y: '1994', t0: 24.7, t1: 26.5, title: '50 MILLION PASSENGERS', det: 'Passed for the first time in 1994' },
  { y: '2003', t0: 26.5, t1: 28.3, title: 'CONCORDE RETIRES', det: 'Its last commercial flights end at Heathrow' },
  { y: '2005', t0: 28.3, t1: 30.3, title: 'DOWN TO 2 RUNWAYS', det: 'Crosswind runway 23 closes (last used in 2002)' },
  { y: '2008', t0: 30.3, t1: 32.3, title: 'TERMINAL 5 OPENS', det: 'Opened by the Queen, to passengers on 27 March' },
  { y: '2014', t0: 32.3, t1: 34.2, title: 'A NEW TERMINAL 2', det: 'The Queen’s Terminal replaces the 1955 building · T1 closes in 2015' },
  { y: '2019', t0: 34.2, t1: 36.6, title: '80.9 MILLION PASSENGERS', det: 'A new record' },
  { y: '2020', t0: 36.6, t1: 39.3, title: 'COVID-19', det: '22.1m in 2020 · 19.4m in 2021, the lowest since 1972' },
  { y: '2024', t0: 39.3, t1: 41.6, title: 'RECORDS AGAIN', det: '83.9 million passengers' },
  { y: '2025', t0: 41.6, t1: 43.9, title: '84.5 MILLION · ~480,000 FLIGHTS', det: 'Its busiest year ever · 80 years old in 2026' },
  { y: 'NEXT', t0: T_FUT + 0.3, t1: T_FIN - 0.1, title: 'A THIRD RUNWAY?', det: 'Planning consent targeted by 2029 · opening now expected ~2039' },
];
const BIG = { 1952: 'jet', 1970: 'jet', 1976: 'jet', 2020: 'down', 2019: 'rec', 2024: 'rec', 2025: 'rec' };

// routes (2024 passengers on each route, Heathrow data)
const LHR = [51.47, -0.4543];
const ROUTES = [
  { code: 'JFK', name: 'NEW YORK', ll: [40.6413, -73.7781], pax: 3.24, col: '#5AA9FF', note: 'ON THE MAP SINCE 1946' },
  { code: 'DXB', name: 'DUBAI', ll: [25.2532, 55.3657], pax: 2.86, col: '#A06BFF', note: '' },
  { code: 'DOH', name: 'DOHA', ll: [25.2731, 51.6081], pax: 2.01, col: '#D46BFF', note: '' },
  { code: 'DUB', name: 'DUBLIN', ll: [53.4213, -6.2701], pax: 1.90, col: '#FF6FB5', note: '' },
];
const EZE = { name: 'BUENOS AIRES', ll: [-34.8222, -58.5358] };

const FROWS = [
  { k: 'PASSENGERS / YEAR', a: '63,000', b: '84.5 MILLION', col: '#FFC27A' },
  { k: 'FLIGHTS / YEAR', a: '~9,000', b: '~480,000', col: '#38C8FF' },
  { k: 'DESTINATIONS', a: '18', b: '200+', col: '#3DF5A0' },
  { k: 'AIRLINES', a: 'A HANDFUL', b: '~90', col: '#A06BFF' },
  { k: 'RUNWAYS', a: '3', b: '2', col: '#FF8A5A' },
  { k: 'TERMINALS', a: 'TENTS', b: '4', col: '#5AA9FF' },
];

// ------------------------------------------------------------------ GEO (routes map)
const land = await fetch('node_modules/world-atlas/land-110m.json').then(r => r.json());
const LANDR = []; for (const f of feature(land, land.objects.land).features) { const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates; for (const poly of polys) LANDR.push(poly[0]); }

// ------------------------------------------------------------------ CANVAS
const cv = $('cv'), g = cv.getContext('2d');
const PL = { x0: 70, y0: 300, w: 860, h: 590 };
let pv = { cx: 0, cy: 0, s: 0.183 };   // plan view: world centre + scale
const toS = (x, y) => [PL.x0 + PL.w / 2 + (x - pv.cx) * pv.s, PL.y0 + PL.h / 2 + 10 + (y - pv.cy) * pv.s];
function rr(x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }
function label(x, y, text, a, col = '#e8eeff', fs = 15, align = 'center') {
  if (a <= 0.01) return; g.font = `800 ${fs}px Inter`; g.textAlign = align; g.textBaseline = 'middle'; g.globalAlpha = a;
  g.lineWidth = 4; g.strokeStyle = 'rgba(2,4,10,0.9)'; g.strokeText(text, x, y); g.fillStyle = col; g.fillText(text, x, y); g.globalAlpha = 1;
}
// static field texture for the plan background
const fieldCv = document.createElement('canvas'); fieldCv.width = 1600; fieldCv.height = 1200; {
  const f = fieldCv.getContext('2d'); f.fillStyle = '#0b1422'; f.fillRect(0, 0, 1600, 1200);
  let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 420; i++) { f.fillStyle = `rgba(${40 + r() * 30},${60 + r() * 40},${50 + r() * 30},${0.10 + r() * 0.12})`; f.save(); f.translate(r() * 1600, r() * 1200); f.rotate((r() - 0.5) * 0.6); f.fillRect(0, 0, 60 + r() * 140, 40 + r() * 100); f.restore(); }
  f.strokeStyle = 'rgba(120,150,220,0.06)'; f.lineWidth = 1; for (let x = 0; x < 1600; x += 40) { f.beginPath(); f.moveTo(x, 0); f.lineTo(x, 1200); f.stroke(); } for (let y = 0; y < 1200; y += 40) { f.beginPath(); f.moveTo(0, y); f.lineTo(1600, y); f.stroke(); }
}
function drawPlan(t, yr, alpha) {
  if (alpha <= 0.01) return;
  g.save(); g.globalAlpha = alpha; rr(PL.x0, PL.y0, PL.w, PL.h, 20); g.clip();
  // background texture scaled with the plan zoom
  const k = pv.s / 0.183, [ox, oy] = toS(-4400, -3300); g.drawImage(fieldCv, ox, oy, 8800 * 0.183 * k, 6600 * 0.183 * k);
  // airport boundary (grows with cargo 1968 and T5 2008)
  const bx0 = yr >= 2008.2 ? -2050 : -1750, by1 = yr >= 1968 ? 1250 : 1150;
  { const [x0, y0] = toS(bx0, -1150), [x1, y1] = toS(2050, by1); g.fillStyle = 'rgba(40,60,90,0.25)'; g.fillRect(x0, y0, x1 - x0, y1 - y0); g.setLineDash([6, 6]); g.strokeStyle = 'rgba(160,190,255,0.35)'; g.lineWidth = 1.5; g.strokeRect(x0, y0, x1 - x0, y1 - y0); g.setLineDash([]); }
  // roads
  for (const rd of ROADS) { if (yr < rd.a) continue; const a = smooth(rd.a, rd.a + 0.6, yr); g.globalAlpha = alpha * a; g.strokeStyle = 'rgba(200,190,160,0.55)'; g.lineWidth = 5; g.beginPath(); rd.p.forEach(([x, y], i) => { const [sx, sy] = toS(x, y); i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); }); g.stroke(); g.globalAlpha = alpha;
    if (rd.lab) { const [sx, sy] = toS(1900, rd.p[0][1]); label(sx, sy - 13, rd.lab, 0.7 * a, '#d8cfb4', 12); } }
  // runways
  let nR = 0;
  for (const R of RWY) {
    const on = yr >= R.a && yr < R.c; const born = smooth(R.a - 0.01, R.a + 0.7, yr), dead = smooth(R.c, R.c + 0.8, yr);
    if (born <= 0) continue; if (on) nR++;
    let p = R.p; if (R.ext) { const e = smooth(R.ext.y, R.ext.y + 0.8, yr); p = [[lerp(R.p[0][0], R.ext.p[0][0], e), R.p[0][1]], [lerp(R.p[1][0], R.ext.p[1][0], e), R.p[1][1]]]; }
    const [x0, y0] = toS(...p[0]), [x1, y1] = toS(...p[1]);
    const len = Math.hypot(x1 - x0, y1 - y0), ang = Math.atan2(y1 - y0, x1 - x0), w = 60 * pv.s;
    const grow = easeOut((yr - R.a) / 0.7);
    g.save(); g.translate(x0, y0); g.rotate(ang);
    if (dead < 1) {
      g.globalAlpha = alpha * (1 - dead); g.fillStyle = '#3a4150'; g.fillRect(0, -w / 2, len * grow, w);
      g.setLineDash([9, 9]); g.strokeStyle = 'rgba(255,255,255,0.75)'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(8, 0); g.lineTo(len * grow - 8, 0); g.stroke(); g.setLineDash([]);
      if (dead > 0) { g.globalAlpha = alpha * Math.sin(dead * Math.PI); g.fillStyle = '#ff4a4a'; g.fillRect(0, -w / 2 - 2, len, w + 4); }
    } else { g.globalAlpha = alpha * 0.18; g.fillStyle = '#5a6272'; g.fillRect(0, -w / 4, len, w / 2); }   // closed: ghost / taxiway
    g.restore(); g.globalAlpha = alpha;
    if (R.lab && on && yr > 1970) { label(x0 - Math.cos(ang) * 22, y0 - Math.sin(ang) * 22, R.lab[0], 0.85, '#ffffff', 13); label(x1 + Math.cos(ang) * 22, y1 + Math.sin(ang) * 22, R.lab[1], 0.85, '#ffffff', 13); }
    if (dead > 0 && dead < 1) label((x0 + x1) / 2, (y0 + y1) / 2 - 16, 'CLOSED', Math.sin(dead * Math.PI), '#ff8a8a', 13);
  }
  // buildings
  let nT = 0;
  for (const B of BLD) {
    const born = smooth(B.a, B.a + 0.6, yr), dead = smooth(B.c, B.c + 0.6, yr); if (born <= 0 || dead >= 1) continue;
    if (B.term && yr >= B.a && yr < B.c) nT++;
    const [x, y] = toS(B.r[0], B.r[1]), w = B.r[2] * pv.s, h = B.r[3] * pv.s, sc = lerp(0.6, 1, backOut(clamp((yr - B.a) / 0.6, 0, 1)));
    g.save(); g.translate(x + w / 2, y + h / 2); g.scale(sc, sc); g.globalAlpha = alpha * born * (1 - dead);
    g.fillStyle = B.col; g.globalAlpha *= 0.2; g.fillRect(-w / 2 - 6, -h / 2 - 6, w + 12, h + 12); g.globalAlpha = alpha * born * (1 - dead) * 0.85;
    rr(-w / 2, -h / 2, w, h, 4); g.fill(); g.restore(); g.globalAlpha = alpha;
    if (B.lab) label(x + w / 2, y + h / 2, B.lab, born * (1 - dead), '#06101f', 14);
    const fl = win(yr, B.a, B.a + 1.4, 0.05, 0.8); if (fl > 0) { g.globalAlpha = alpha * fl; g.strokeStyle = '#ffffff'; g.lineWidth = 2; g.strokeRect(x - 8 * fl, y - 8 * fl, w + 16 * fl, h + 16 * fl); g.globalAlpha = alpha; }
  }
  // rail
  for (const L of RAIL) { const e = clamp((yr - L.a) / 0.8, 0, 1); if (e <= 0) continue;
    g.strokeStyle = '#2f6bff'; g.lineWidth = 3.5; g.setLineDash([10, 6]); g.beginPath(); const pts = L.p.map(q => toS(...q)); const n = pts.length - 1, upto = e * n;
    for (let i = 0; i <= Math.floor(upto); i++) { const [sx, sy] = pts[i]; i ? g.lineTo(sx, sy) : g.moveTo(sx, sy); }
    if (upto < n) { const i = Math.floor(upto), f = upto - i; g.lineTo(lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f)); }
    g.stroke(); g.setLineDash([]); if (L.lab) label(pts[1][0] + 40, pts[1][1] + 24, L.lab, e * win(yr, L.a, L.a + 6, 0.2, 1), '#8fb0ff', 12); }
  // proposed third runway
  const f3 = smooth(T_FUT, T_FUT + 0.8, t) * (1 - smooth(T_FIN - 0.4, T_FIN, t));
  if (f3 > 0) { const [x0, y0] = toS(...RWY3.p[0]), [x1, y1] = toS(...RWY3.p[1]); g.globalAlpha = alpha * f3; g.setLineDash([12, 8]); g.strokeStyle = '#3DF5A0'; g.lineWidth = 2.5; g.strokeRect(x0, y0 - 30 * pv.s, x1 - x0, 60 * pv.s); g.setLineDash([]);
    g.globalAlpha = alpha * f3 * (0.5 + 0.5 * Math.sin(t * 5)); g.fillStyle = 'rgba(61,245,160,0.25)'; g.fillRect(x0, y0 - 30 * pv.s, x1 - x0, 60 * pv.s); g.globalAlpha = alpha;
    label((x0 + x1) / 2, y0 - 26, 'PROPOSED THIRD RUNWAY', f3, '#3DF5A0', 15); }
  g.restore(); g.globalAlpha = 1;
  return { nR, nT };
}
// world route map
const WM = { x0: 70, y0: 300, w: 860, h: 640, lo0: -80, lo1: 62, la0: 66 };
const wmS = WM.w / (WM.lo1 - WM.lo0);
const wp = (la, lo) => [WM.x0 + (lo - WM.lo0) * wmS, WM.y0 + (WM.la0 - la) * wmS];
function gcPts(a, b, n = 60) {
  const v = (la, lo) => [Math.cos(la * D2R) * Math.cos(lo * D2R), Math.cos(la * D2R) * Math.sin(lo * D2R), Math.sin(la * D2R)];
  const A = v(...a), B = v(...b), d = Math.acos(clamp(A[0] * B[0] + A[1] * B[1] + A[2] * B[2], -1, 1)), o = [];
  for (let i = 0; i <= n; i++) { const s = i / n, k0 = Math.sin((1 - s) * d) / Math.sin(d), k1 = Math.sin(s * d) / Math.sin(d); const q = [A[0] * k0 + B[0] * k1, A[1] * k0 + B[1] * k1, A[2] * k0 + B[2] * k1]; o.push(wp(Math.asin(q[2]) / D2R, Math.atan2(q[1], q[0]) / D2R)); }
  return o;
}
const PLANE = [[0.5, 0], [0.42, 0.055], [0.12, 0.07], [-0.1, 0.5], [-0.2, 0.5], [-0.07, 0.075], [-0.33, 0.065], [-0.43, 0.2], [-0.5, 0.2], [-0.46, 0]];
function glyph(x, y, hd, size, col, a) { g.save(); g.translate(x, y); g.rotate(hd); g.scale(size, size); g.beginPath(); PLANE.forEach(([px, py], i) => i ? g.lineTo(px, py) : g.moveTo(px, py)); for (let i = PLANE.length - 1; i >= 0; i--) g.lineTo(PLANE[i][0], -PLANE[i][1]); g.closePath(); g.globalAlpha = a; g.fillStyle = col; g.fill(); g.restore(); g.globalAlpha = 1; }
function drawRoutes(t, alpha) {
  if (alpha <= 0.01) return;
  g.save(); g.globalAlpha = alpha; rr(WM.x0, WM.y0, WM.w, WM.h, 20); g.clip();
  g.fillStyle = '#060d1f'; g.fillRect(WM.x0, WM.y0, WM.w, WM.h);
  g.beginPath(); for (const ring of LANDR) { let prev = null; ring.forEach(([lo, la], i) => { const [x, y] = wp(la, lo); if (i === 0 || (prev && Math.abs(lo - prev) > 180)) g.moveTo(x, y); else g.lineTo(x, y); prev = lo; }); g.closePath(); }
  g.fillStyle = '#122041'; g.fill(); g.strokeStyle = 'rgba(120,160,255,0.45)'; g.lineWidth = 1; g.stroke();
  const [lx, ly] = wp(...LHR);
  // 1946 first flight (dashed, gold)
  { const pts = gcPts(LHR, EZE.ll), e = easeOut((t - (T_ROUTES + 0.4)) / 1.2); if (e > 0) { g.setLineDash([6, 6]); g.strokeStyle = '#FFD27A'; g.lineWidth = 2; g.beginPath(); pts.slice(0, Math.max(2, Math.round(e * pts.length))).forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke(); g.setLineDash([]);
    const [ex, ey] = pts[pts.length - 1]; label(ex + 8, ey + 4, '1946 · BUENOS AIRES', e, '#FFD27A', 14, 'left'); } }
  ROUTES.forEach((R, i) => {
    const t0 = T_ROUTES + 0.9 + i * 0.55, e = easeOut((t - t0) / 1.1); if (e <= 0) return;
    const pts = gcPts(LHR, R.ll), n = Math.max(2, Math.round(e * pts.length));
    g.strokeStyle = R.col; g.globalAlpha = alpha * 0.25; g.lineWidth = 9; g.beginPath(); pts.slice(0, n).forEach(([x, y], j) => j ? g.lineTo(x, y) : g.moveTo(x, y)); g.stroke();
    g.globalAlpha = alpha; g.lineWidth = 3; g.stroke();
    const [px, py] = pts[n - 1], [qx, qy] = pts[Math.max(0, n - 2)];
    if (e < 1) glyph(px, py, Math.atan2(py - qy, px - qx), 22, '#ffffff', alpha);
    else { const u = ((t - t0 - 1.1) % 1.4) / 1.4; g.globalAlpha = alpha * (1 - u); g.strokeStyle = R.col; g.lineWidth = 2.5; g.beginPath(); g.arc(px, py, 6 + u * 26, 0, 6.283); g.stroke(); g.globalAlpha = alpha; }
    g.fillStyle = R.col; g.beginPath(); g.arc(pts[pts.length - 1][0], pts[pts.length - 1][1], 5 * e, 0, 6.283); g.fill();
    const [ex, ey] = pts[pts.length - 1], L = { JFK: [8, 18, 'left'], DUB: [-12, -10, 'right'], DXB: [0, -16, 'center'], DOH: [0, 22, 'center'] }[R.code]; label(ex + L[0], ey + L[1], R.name, e, '#ffffff', 15, L[2]);
  });
  g.fillStyle = '#ffffff'; g.beginPath(); g.arc(lx, ly, 7, 0, 6.283); g.fill(); label(lx + 10, ly + 18, 'HEATHROW', 1, '#ffffff', 16, 'left');
  g.restore(); g.globalAlpha = 1;
}
// passenger chart (own canvas inside the panel)
const ch = $('chart').getContext('2d'), CW = 812, CHh = 112;
function drawChart(yr, a) {
  ch.clearRect(0, 0, CW, CHh); if (a <= 0.01) return; ch.globalAlpha = a;
  const X = y => (y - 1946) / 80 * (CW - 10) + 4, Y = v => CHh - 14 - v / 90 * (CHh - 24);
  ch.strokeStyle = 'rgba(255,255,255,0.08)'; ch.lineWidth = 1; for (const v of [20, 40, 60, 80]) { ch.beginPath(); ch.moveTo(0, Y(v)); ch.lineTo(CW, Y(v)); ch.stroke(); }
  ch.font = '700 11px Inter'; ch.fillStyle = 'rgba(160,175,215,0.7)'; ch.textBaseline = 'bottom';
  for (const d of [1946, 1960, 1980, 2000, 2026]) { ch.textAlign = d === 1946 ? 'left' : d === 2026 ? 'right' : 'center'; ch.fillText(String(d), X(d), CHh); }
  ch.textAlign = 'left'; ch.textBaseline = 'middle'; for (const v of [40, 80]) ch.fillText(v + 'M', 6, Y(v) - 7);
  const end = Math.min(yr, 2025.999); const pts = []; for (let y = 1946; y <= end; y += 0.25) pts.push([X(y), Y(paxYear(y))]); pts.push([X(end), Y(paxYear(end))]);
  const grd = ch.createLinearGradient(0, 0, CW, 0); grd.addColorStop(0, '#FFD27A'); grd.addColorStop(1, '#FF6FB5');
  ch.beginPath(); ch.moveTo(pts[0][0], Y(0)); pts.forEach(([x, y]) => ch.lineTo(x, y)); ch.lineTo(pts[pts.length - 1][0], Y(0)); ch.closePath(); ch.globalAlpha = a * 0.22; ch.fillStyle = grd; ch.fill();
  ch.globalAlpha = a; ch.beginPath(); pts.forEach(([x, y], i) => i ? ch.lineTo(x, y) : ch.moveTo(x, y)); ch.strokeStyle = grd; ch.lineWidth = 3; ch.stroke();
  const [hx, hy] = pts[pts.length - 1]; ch.fillStyle = '#ffffff'; ch.beginPath(); ch.arc(hx, hy, 5, 0, 6.283); ch.fill(); ch.globalAlpha = a * 0.3; ch.beginPath(); ch.arc(hx, hy, 12, 0, 6.283); ch.fill(); ch.globalAlpha = 1;
}

// ------------------------------------------------------------------ KINETIC TYPE + ODOMETERS (shared with the other videos)
function kinPrep(el, text, mode, cols) {
  const key = text + '|' + mode; if (el.__k === key) return el.__sp; el.__k = key; el.textContent = '';
  const parts = mode === 'char' ? [...text] : text.split(/(\s+)/), sp = [];
  for (const p of parts) { if (p === '') continue; if (/^\s+$/.test(p)) { el.appendChild(document.createTextNode(' ')); continue; }
    const s = document.createElement('span'); s.textContent = p; s.style.display = 'inline-block'; s.style.whiteSpace = 'pre'; s.style.transformOrigin = '50% 70%'; el.appendChild(s); sp.push(s); }
  if (cols) sp.forEach((s, i) => s.style.color = gradAt(cols, (i + 0.5) / sp.length));
  el.__sp = sp; return sp;
}
const hex = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
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
const blank = (...ids) => ids.forEach(id => kin($(id), ' ', 0, 0, 0));
function pop(el, tIn, tOut, t, o = {}) {
  const a = clamp((t - tIn) / (o.dIn ?? 0.32), 0, 1), b = tOut == null ? 0 : clamp((t - tOut) / (o.dOut ?? 0.22), 0, 1);
  const sc = lerp(o.s0 ?? 0.6, 1, backOut(a)) * lerp(1, 0.75, b * b);
  el.style.opacity = (clamp(a * 2, 0, 1) * (1 - b)).toFixed(3);
  el.style.transform = `translateY(${((1 - backOut(a)) * (o.y0 ?? 18) - 10 * b * b).toFixed(1)}px) scale(${sc.toFixed(3)})`; return a * (1 - b);
}
function odoPos(v, i) { const q = Math.pow(10, i); const fl = Math.floor(v / q); return (fl % 10) + smooth(q - 0.4, q, v - fl * q); }
class Odo {
  constructor(el, nd, fs, cw, col, commas) { this.lh = Math.round(fs * 1.12); this.items = []; el.classList.add('odo'); el.style.fontSize = fs + 'px'; el.style.height = this.lh + 'px'; el.style.lineHeight = this.lh + 'px'; if (col) el.style.color = col;
    for (let i = nd - 1; i >= 0; i--) { const c = document.createElement('div'); c.className = 'col'; c.style.width = cw + 'px'; c.style.height = this.lh + 'px'; const s = document.createElement('div'); s.className = 'strip';
      s.innerHTML = Array.from({ length: 11 }, (_, d) => `<div style="height:${this.lh}px">${d % 10}</div>`).join(''); c.appendChild(s); el.appendChild(c); this.items.push({ i, c, s, w: cw, digit: true });
      if (commas && i > 0 && i % 3 === 0) { const sp = document.createElement('div'); sp.className = 'sepc'; sp.textContent = ','; sp.style.width = (cw * 0.42) + 'px'; sp.style.height = this.lh + 'px'; el.appendChild(sp); this.items.push({ i: i - 0.5, c: sp, w: cw * 0.42, digit: false }); } } }
  set(v) { v = Math.max(0, v); const n = Math.max(1, String(Math.floor(v + 0.4)).length); let w = 0;
    for (const it of this.items) { const on = it.digit ? it.i < n : it.i < n - 1; it.c.style.display = on ? 'block' : 'none'; if (!on) continue; w += it.w; if (it.digit) it.s.style.transform = `translateY(${-odoPos(v, it.i) * this.lh}px)`; } return w; }
}
const GR = ['#5AA9FF', '#A06BFF', '#FF6FB5'];
const yearOdo = new Odo($('yearOdo'), 4, 92, 56, null, false);
yearOdo.items.forEach(it => { it.s.style.background = 'linear-gradient(90deg,#5AA9FF,#FF6FB5)'; it.s.style.webkitBackgroundClip = 'text'; it.s.style.color = 'transparent'; });
const paxOdo = new Odo($('paxOdo'), 8, 62, 39, '#FFC27A', true);
const CTR = [{ lab: 'RUNWAYS', col: '#FF8A5A' }, { lab: 'TERMINALS', col: '#5AA9FF' }, { lab: 'YEARS OPEN', col: '#3DF5A0' }];
CTR.forEach((c, i) => { const d = document.createElement('div'); d.className = 'ctr'; d.style.left = (70 + i * 292) + 'px'; d.innerHTML = `<div class="glow" style="background:radial-gradient(ellipse at 30% 60%, ${c.col}55, transparent 70%)"></div><div class="acc" style="background:${c.col}"></div><div class="k" style="color:${c.col}"></div><div class="v" style="color:${c.col}"></div>`; $('ctrs').appendChild(d); c.el = d; c.k = d.querySelector('.k'); c.v = d.querySelector('.v'); c.glow = d.querySelector('.glow'); });
const RROWS = ROUTES.map((R, i) => { const d = document.createElement('div'); d.className = 'rrow'; d.style.top = (972 + i * 88) + 'px'; d.innerHTML = `<div class="bar" style="width:${(R.pax / 3.24 * 100).toFixed(1)}%;background:linear-gradient(90deg,${R.col},transparent)"></div><div class="rk">${i + 1}</div><div class="rn"></div><div class="rs"></div><div class="rv" style="color:${R.col}"></div>`; $('rRows').appendChild(d); return { el: d, rn: d.querySelector('.rn'), rs: d.querySelector('.rs'), rv: d.querySelector('.rv'), R }; });
const FR = FROWS.map((r, i) => { const d = document.createElement('div'); d.className = 'frow'; d.style.top = (560 + i * 118) + 'px'; d.innerHTML = `<div class="acc" style="background:${r.col}"></div><div class="k" style="color:${r.col}"></div><div class="a"></div><div class="ar">→</div><div class="b" style="color:${r.col}"></div>`; $('fRows').appendChild(d); return { el: d, k: d.querySelector('.k'), a: d.querySelector('.a'), ar: d.querySelector('.ar'), b: d.querySelector('.b'), r, t: T_FIN + 1.2 + i * 0.32 }; });

// ------------------------------------------------------------------ FRAME
const PLAN_ZOOM = [[0, 0, 60, 0.183], [T_FUT, 0, 60, 0.183], [T_FUT + 1.0, -1150, -500, 0.123], [60, -1150, -500, 0.12]];
function setPlanView(t) { let i = 0; while (i < PLAN_ZOOM.length - 2 && t > PLAN_ZOOM[i + 1][0]) i++; const a = PLAN_ZOOM[i], b = PLAN_ZOOM[i + 1], e = ease((t - a[0]) / (b[0] - a[0])); pv.cx = lerp(a[1], b[1], e); pv.cy = lerp(a[2], b[2], e); pv.s = lerp(a[3], b[3], e); }
const lastYearTick = [];
function renderFrame(t) {
  const yr = yearAt(t), Y = Math.floor(yr + 1e-6);
  g.fillStyle = '#03070f'; g.fillRect(0, 0, W, H);
  setPlanView(t);
  const planA = Math.max(win(t, 0, T_ROUTES + 0.1, 0.01, 0.45), win(t, T_FUT - 0.2, T_FIN + 0.3, 0.5, 0.5)) * (t < 3.0 ? 0.55 : 1);
  const st = drawPlan(t, t > T_FUT - 0.3 ? 2026 : yr, planA) || { nR: 2, nT: 4 };
  drawRoutes(t, win(t, T_ROUTES - 0.1, T_FUT, 0.5, 0.45));
  $('dim').style.opacity = Math.max(0.55 * (1 - smooth(2.6, 3.3, t)), 0.7 * smooth(T_FIN - 0.2, T_FIN + 0.6, t)).toFixed(3);
  $('planFrame').style.opacity = planA.toFixed(3); kin($('planTag'), 'THE AIRPORT · SCHEMATIC PLAN', 3.4, T_ROUTES - 0.3, t, { stagger: 0.03 });
  if (t > T_FUT - 0.5) kin($('planTag'), 'THE AIRPORT · SCHEMATIC PLAN', T_FUT + 0.2, T_FIN - 0.3, t, { stagger: 0.03 });

  // intro
  kin($('iKick'), 'LONDON’S AIRPORT, 1946 → 2026', 0.05, 2.55, t, { stagger: 0.05 });
  kin($('iBig'), 'HEATHROW', 0.22, 2.6, t, { mode: 'char', stagger: 0.045, s0: 0.2, y0: 40, cols: GR, outStagger: 0.012 });
  kin($('iSky'), '80 YEARS IN 60 SECONDS', 0.8, 2.65, t, { stagger: 0.07 });
  pop($('iRule'), 1.0, 2.6, t, { s0: 0.1 });
  kin($('iSub'), 'From a field of tents to 84 million a year', 1.3, 2.7, t, { stagger: 0.05, cols: ['#FFFFFF', '#FFD27A'] });

  // header (sweep)
  const hOut = T_ROUTES - 0.25;
  kin($('hTitle'), 'HEATHROW', 3.0, hOut, t, { mode: 'char', stagger: 0.03, cols: GR });
  kin($('hSub'), '80 YEARS IN 60 SECONDS', 3.15, hOut, t, { stagger: 0.04 });
  pop($('yearBox'), 3.05, hOut, t, { s0: 0.5 }); yearOdo.set(yr);
  kin($('yearLab'), Y >= 2026 ? 'TODAY' : 'YEAR', 3.2, hOut, t, { stagger: 0.03 });

  // passengers
  pop($('paxP'), 3.3, hOut, t, { s0: 0.85 });
  const py = clamp(Y, 1946, 2025), disp = y => { const v = paxYear(y) * 1e6; return SOURCED(y) ? v : Math.round(v / 1e5) * 1e5; };
  const pv0 = py >= 2025 ? disp(2025) : lerp(disp(py), disp(py + 1), smooth(0.55, 1.0, yr - py));
  kin($('paxK'), `PASSENGERS IN ${py}`, 3.4, hOut, t, { stagger: 0.03 });
  const pw = paxOdo.set(pv0); $('paxApprox').style.left = (22 + pw + 16) + 'px';
  kin($('paxApprox'), SOURCED(py) ? (py === 2025 ? 'RECORD' : ' ') : '≈ ESTIMATE', 3.4, hOut, t, { stagger: 0.03 });
  drawChart(yr, win(t, 3.4, hOut + 0.2, 0.4, 0.25));

  // counters
  CTR.forEach((c, i) => {
    const t0 = 3.5 + i * 0.1; pop(c.el, t0, hOut, t); kin(c.k, c.lab, t0 + 0.1, hOut, t, { stagger: 0.03 });
    const txt = i === 0 ? String(st.nR) : i === 1 ? (yr < 1955.9 ? 'TENTS' : String(st.nT)) : String(clamp(Y - 1946, 0, 80));
    if (c.v.textContent !== txt) { c.v.textContent = txt; c.ch = t; } const k = clamp((t - (c.ch ?? -9)) / 0.3, 0, 1); c.v.style.transform = `scale(${lerp(1.35, 1, backOut(k)).toFixed(3)})`;
    c.glow.style.opacity = (i < 2 ? Math.exp(-Math.max(0, t - (c.ch ?? -9)) * 3) : 0.2).toFixed(3);
  });

  // milestone card
  const C = CARDS.find(c => t >= c.t0 - 0.05 && t < c.t1 + 0.25);
  const cardOn = (t > 3.3 && t < hOut + 0.3) || (t > T_FUT && t < T_FIN + 0.2);
  pop($('card'), t < T_FUT ? 3.4 : T_FUT + 0.2, t < T_FUT ? hOut : T_FIN - 0.1, t, { s0: 0.85 });
  if (!cardOn) $('card').style.opacity = 0;
  if (C) { const o = C.t1 - 0.2; pop($('cYear'), C.t0, o, t, { s0: 0.4 }); $('cYear').textContent = C.y;
    kin($('cTitle'), C.title, C.t0 + 0.08, o, t, { stagger: 0.05, s0: 0.25 }); kin($('cDet'), C.det, C.t0 + 0.35, o, t, { stagger: 0.025 });
    $('cTitle').style.fontSize = C.title.length > 30 ? '32px' : '38px'; }
  else { $('cYear').style.opacity = 0; blank('cTitle', 'cDet'); }

  // routes section
  const rIn = T_ROUTES + 0.2, rOut = T_FUT - 0.3;
  if (t > T_ROUTES - 0.3 && t < T_FUT) { kin($('secT'), 'WHERE HEATHROW FLIES MOST', rIn, rOut, t, { stagger: 0.05, cols: GR }); kin($('secS'), 'TOP ROUTES BY PASSENGERS · 2024', rIn + 0.2, rOut, t, { stagger: 0.03 }); }
  else if (t > T_FUT - 0.1 && t < T_FIN + 0.2) { kin($('secT'), 'WHAT’S NEXT?', T_FUT + 0.1, T_FIN - 0.2, t, { stagger: 0.06, cols: ['#3DF5A0', '#5AA9FF'] }); kin($('secS'), 'HEATHROW TODAY + THE PLANNED THIRD RUNWAY', T_FUT + 0.3, T_FIN - 0.2, t, { stagger: 0.03 }); }
  else blank('secT', 'secS');
  RROWS.forEach((r, i) => { const t0 = T_ROUTES + 1.2 + i * 0.55; pop(r.el, t0, rOut, t, { s0: 0.8 }); kin(r.rn, r.R.name + ' · ' + r.R.code, t0 + 0.1, rOut, t, { stagger: 0.04 }); kin(r.rs, r.R.note || ' ', t0 + 0.3, rOut, t, { stagger: 0.03 });
    const v = r.R.pax * easeOut((t - t0 - 0.2) / 1.0); r.rv.textContent = v.toFixed(2) + 'M'; });
  kin($('rNote'), 'Today: 200+ destinations · ~90 airlines · New York is Europe’s busiest route', T_ROUTES + 3.6, rOut, t, { stagger: 0.025 });

  kin($('sizeA'), '1,227 HECTARES', T_FUT + 0.6, T_FIN - 0.2, t, { stagger: 0.08, s0: 0.2, cols: ['#3DF5A0', '#5AA9FF'] });
  kin($('sizeB'), 'today’s site: about 20× the 60-hectare Great West Aerodrome it grew from (1930)', T_FUT + 0.9, T_FIN - 0.2, t, { stagger: 0.02 });
  kin($('sizeC'), '2 RUNWAYS · 4 TERMINALS · 84.5 MILLION PASSENGERS', T_FUT + 1.2, T_FIN - 0.2, t, { stagger: 0.04 });
  // finale
  kin($('fL1'), '80 YEARS.', T_FIN + 0.2, 59.3, t, { stagger: 0.09, s0: 0.2 });
  kin($('fL2'), 'ONE AIRPORT.', T_FIN + 0.55, 59.35, t, { stagger: 0.09, s0: 0.2, cols: GR });
  kin($('fHead'), '1946  →  TODAY', T_FIN + 0.9, 59.35, t, { stagger: 0.1 });
  FR.forEach(r => { pop(r.el, r.t, 59.4, t, { s0: 0.85 }); kin(r.k, r.r.k, r.t + 0.08, 59.4, t, { stagger: 0.03 }); kin(r.a, r.r.a, r.t + 0.15, 59.4, t, { stagger: 0.03 }); pop(r.ar, r.t + 0.3, 59.4, t, { s0: 0.3 }); kin(r.b, r.r.b, r.t + 0.42, 59.4, t, { stagger: 0.05, s0: 0.2 }); });
  kin($('fFoot'), 'Sources: Heathrow, CAA, London Museum, Reuters, OAG and others (see README). Passenger totals 1952–85 are estimates between published milestones. Plan is schematic.', 56.6, 59.4, t, { stagger: 0.01, dIn: 0.25 });
}

function getAudioEvents() {
  const ev = { years: [], cards: CARDS.map(c => c.t0), big: [], runwayClose: [], build: [], routes: ROUTES.map((_, i) => T_ROUTES + 0.9 + i * 0.55), rows: FR.map(r => r.t), intro: [0.22, 0.8, 1.3], fin: [T_FIN + 0.2, T_FIN + 0.55], T_ROUTES, T_FUT, T_FIN };
  for (let y = 1947; y <= 2026; y++) ev.years.push(tOfYear(y));
  for (const c of CARDS) { const y = parseInt(c.y.slice(-4)); if (BIG[y]) ev.big.push([c.t0, BIG[y]]); }
  for (const R of RWY) if (R.c < 3000) ev.runwayClose.push(tOfYear(R.c));
  for (const B of BLD) if (B.term) ev.build.push(tOfYear(B.a));
  ev.covidT = tOfYear(2020); ev.recoverT = tOfYear(2022);
  return ev;
}
window.renderFrame = renderFrame; window.getAudioEvents = getAudioEvents;
await document.fonts.ready; renderFrame(0); window.READY = true;

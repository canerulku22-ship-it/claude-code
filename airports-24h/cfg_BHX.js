// Birmingham (BHX). Local frame: metres; -x = landing direction on runway 33 (true 328°), -z = right of track (terminal side).
const line = (px, pz, dx, dz, L) => [[px - dx * L, pz - dz * L], [px + dx * L, pz + dz * L]];
const NORTH = [-0.85, -0.53], EAST = [0.53, -0.85];   // true north / east expressed in the local frame
export default {
  code: 'BHX', city: 'BIRMINGHAM', header: 'BIRMINGHAM · BHX', titleBig: 'BIRMINGHAM:', titleSize: 100, tz: 'GMT', utcOff: 0,
  lat: 52.4539, lon: -1.748, decl: -15.0, eot: 16.4, mistName: 'MIST',
  runways: [{ id: '33', z: 0, w: -1500, e: 1552, labE: '33', labW: '15' }],
  rwyText: m => 'RWY 33 · ARR + DEP',
  ground: {
    base: '#4a5a3e', grass: '#587548', grid: null, gridSpacing: [110, 170],
    fields: ['#4f6a40', '#5b7447', '#667a4a', '#4a6239', '#6d7f4f', '#757a50'],
    house: ['#6e625a', '#625f5c', '#77695f', '#5a5a52', '#6e6a62'],
    density(x, z) {
      if (x > -1900 && x < 2000 && z > -1050 && z < 950) return 0;                 // airfield
      if (x > 100 && x < 1300 && z > -2700 && z < -1650) return 0;                 // NEC
      const n = 0.65 + 0.35 * Math.sin(x * 0.0012 + Math.sin(z * 0.0008) * 2) * Math.cos(z * 0.0010 - x * 0.0004);
      const city = -0.88 * x + 0.47 * z;                                           // towards Birmingham city centre
      let d = 0.2;
      if (z > 1150) d = 0.85;                                                      // Sheldon / Solihull
      if (city > 2300) d = Math.max(d, 0.95);
      if (x > 2600 && z < 1150) d = 0.12;                                          // Hampton-in-Arden countryside
      if (z < -1100 && x > -1500) d = Math.min(d, 0.25);
      return d * n;
    },
    woods: [[2600, -6000, 9000, 1000, 60], [-1500, -6000, 2600, -2900, 30]],
    airfield: [[-1900, -1050, 2000, 950]],
    roads: [
      { pts: line(1300, -2400, NORTH[0], NORTH[1], 9000), w: 40, light: 0.95 },   // M42
      { pts: line(-2400, -900, EAST[0], EAST[1], 9000), w: 26, light: 0.85 },    // A45 Coventry Road
      { pts: line(200, -1300, NORTH[0], NORTH[1], 9000), w: 10, light: 0.0 },     // West Coast Main Line
      { pts: [[-1900, -1050], [2000, -1050], [2000, 950], [-1900, 950], [-1900, -1050]], w: 12, light: 0.6 },
      { pts: [[-200, -1050], [300, -1600], [700, -2200]], w: 18, light: 0.8 },     // airport way to the NEC
    ],
  },
  aprons: [[-850, -620, 450, -380], [100, 380, 700, 760], [-1100, 420, -500, 760]],
  taxi: [[[-1450, -210], [1500, -210]], [[-1450, 0], [-1450, -210]], [[1500, 0], [1500, -210]], [[-700, 0], [-880, -210]], [[400, 0], [220, -210]], [[-300, 0], [-300, 380]], [[700, 0], [700, 380]]],
  buildings: [
    [-200, -720, 440, 24, 100, 0xb8c0c8], [-450, -520, 40, 14, 220, 0xbcc2c8], [100, -520, 40, 14, 220, 0xbcc2c8], [-650, -650, 120, 16, 70, 0x9aa0a6],
    [400, 640, 200, 28, 120, 0xc0c5ca], [-800, 650, 160, 14, 60, 0xd8d2c4],
    // NEC halls + Resorts World
    [450, -1900, 180, 18, 240, 0xa8aeb4], [700, -1900, 180, 18, 240, 0xa8aeb4], [950, -1900, 180, 18, 240, 0xa8aeb4], [450, -2250, 180, 18, 240, 0xa8aeb4], [700, -2250, 180, 18, 240, 0xa8aeb4], [950, -2250, 180, 18, 240, 0xa8aeb4],
    [1150, -2050, 60, 70, 60, 0x8fa3b8],
    [260, -1350, 120, 14, 40, 0xb0b6bc],
  ],
  extraBuildings(r) { const b = []; for (let i = 0; i < 18; i++) b.push([-2600 - r() * 2500, 1400 + r() * 2200, 40 + r() * 30, 14 + r() * 30, 40, 0x9c968f]); return b; },
  tower: { x: -640, z: -860, h: 46 },
  landmark: 'none',
  stands: (() => { const s = [];
    for (const x of [-450, 100]) for (const z of [-590, -520, -450]) { s.push([x - 52, z, 0, 0]); s.push([x + 52, z, Math.PI, 0]); }
    for (let x = -800; x <= -560; x += 70) s.push([x, -440, Math.PI / 2, 0]);
    for (let x = 200; x <= 420; x += 75) s.push([x, -430, Math.PI / 2, x > 350 ? 1 : 0]);
    for (let x = 160; x <= 640; x += 80) s.push([x, 460, -Math.PI / 2, 0]);
    return s; })(),
  tailCols: ['#c8102e', '#003876', '#f2a900', '#e2e6ea', '#00a1de', '#7a1fa0', '#0b6e4f', '#ff6600'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 220, 9, 0, 9, 0.90, 0.40, 0],
    [240, 225, 8, 0, 8.5, 0.85, 0.25, 0],
    [420, 230, 10, 0, 8, 0.80, 0.15, 0],
    [540, 235, 12, 0, 9, 0.70, 0, 0],
    [700, 240, 14, 23, 11, 0.45, 0, 0],
    [860, 250, 15, 25, 11.5, 0.40, 0, 0],
    [1000, 260, 10, 0, 9.5, 0.25, 0, 0],
    [1140, 270, 6, 0, 7, 0.15, 0, 0.15],
    [1320, 280, 4, 0, 5, 0.10, 0, 0.45],
    [1440, 280, 3, 0, 4.5, 0.10, 0, 0.55],
  ],
  introCam: { P0: [5200, 560, 320], P1: [4500, 470, 280], Q0: [-900, 0, -150], Q1: [-1050, 0, -160] },
  introEvents: [{ type: 'A', t: 1.6, rw: '33', cat: 1, wide: false }, { type: 'A', t: 3.3, rw: '33', cat: 2, wide: true }],
  shots: [
    { t0: 5.0, t1: 12.5, name: 'CAM 1 · AERIAL', p0: [3300, 980, 2300], p1: [2900, 860, 2000], q0: [-400, 0, -250], q1: [-500, 0, -250], fov: 42, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 12.5, t1: 19.5, name: 'CAM 2 · APPROACH 33', p0: [1230, 34, 230], p1: [1320, 36, 235], q0: [6200, 240, 0], q1: [6200, 220, 0], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 19.5, t1: 26.5, name: 'CAM 3 · TERMINAL APRON', p0: [-260, 40, -430], p1: [-330, 40, -440], q0: [-1250, 60, 40], q1: [-1350, 60, 40], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 26.5, t1: 33.5, name: 'CAM 4 · TOWER VIEW', p0: [-520, 72, -690], p1: [-560, 72, -700], q0: [-4400, 0, -50], q1: [-4400, 0, -30], fov: 50, sc: 1.5, sf: 0.75, near: 0.9 },
    { t0: 33.5, t1: 40.5, name: 'CAM 5 · SUNSET', p0: [80, 66, -760], p1: [0, 64, -760], q0: [-500, 40, 3000], q1: [-560, 40, 3000], fov: 52, sc: 1.5, sf: 0.6, near: 1.0 },
    { t0: 40.5, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [0, 0, -200], r: 3600, h: 1300, a0: 0.25, a1: 1.05 }, fov: 42, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 640, rw: '33' }, { m: 1150, rw: '33' }],
  globe: {
    keys: [
      [3.4, 52.45, -1.75, 1.08, 960],
      [6.4, 38, 4, 13.5, 615],
      [13.5, 38, 6, 13.5, 615],
      [16.0, 47, 4, 5.4, 615],
      [22.5, 46, 8, 5.2, 615],
      [25.0, 37, -6, 7.4, 615],
      [31.5, 35, -2, 7.2, 615],
      [34.0, 32, 22, 9.5, 615],
      [40.5, 31, 30, 9.3, 615],
      [43.0, 38, 4, 13.5, 615],
      [52.0, 38, 10, 13.5, 615],
      [54.6, 32, -4, 11.0, 840],
      [60.0, 30, -18, 10.8, 840],
    ],
    views: [[6.4, 'WORLDWIDE'], [16.0, 'EUROPE'], [25.0, 'SUN DESTINATIONS'], [34.0, 'EAST MED & GULF'], [43.0, 'WORLDWIDE']],
    worldLabels: ['DXB', 'DOH', 'CUN', 'IST', 'TFS', 'HRG', 'LCA', 'FNC', 'RAK', 'OTP'],
    regionLabels: ['EDI', 'GLA', 'ABZ', 'BHD', 'CDG', 'FRA', 'MUC', 'ZRH', 'BCN', 'MAD', 'FCO', 'KRK', 'BUD', 'PRG', 'WAW', 'FAO', 'PMI', 'GVA'],
    names: { AGP: 'MALAGA', BGY: 'MILAN', SAW: 'ISTANBUL SAW' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const firstArr = FL.find(f => f.type === 'A' && f.t > 240);
    const wave = FL.filter(f => f.type === 'D' && f.t >= 360 && f.t < 420).length;
    const lastDep = [...FL].reverse().find(f => f.type === 'D');
    return [
      { m: 362, tm: '06:00', a: 'THE 6AM WAVE', b: `${wave} departures in the first hour` },
      { m: 425, tm: '07:05', a: 'SUNRISE', b: 'grey skies and drizzle over the Midlands' },
      { m: 700, tm: '11:40', a: 'SKIES CLEAR', b: 'breezy south-westerly, gusts 25 kt' },
      { m: S.stats.busiest * 60 + 30, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} movements on one runway` },
      { m: 990, tm: '16:30', a: 'SUNSET', b: 'evening flights to the sun' },
      { m: 'pax20', a: '20,000 PASSENGERS', b: 'and counting' },
      { m: lastDep.t, a: 'LAST DEPARTURE', b: `${lastDep.fn} to ${ROUTES[lastDep.r].city}` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 328, name: 'BIRMINGHAM RADAR',
    fixes: [{ name: 'HONILEY', brg: 185, dist: 12, hold: true }, { name: 'NORTH', brg: 20, dist: 20, hold: true }, { name: 'WEST', brg: 262, dist: 18, hold: false }, { name: 'EAST', brg: 95, dist: 20, hold: false }],
    places: [{ name: 'BIRMINGHAM', brg: 295, dist: 6 }, { name: 'COVENTRY', brg: 110, dist: 9 }, { name: 'WOLVERHAMPTON', brg: 300, dist: 17 }, { name: 'LEICESTER', brg: 58, dist: 26 }, { name: 'EAST MIDLANDS', brg: 32, dist: 27 }],
    holdRate: 18, depTurn: {}, straightOut: 3,
  },
};

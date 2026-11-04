// Istanbul Airport (IST). Local frame: metres; -x = landing direction on runways 34/35 (true ~352°), -z = right of track.
const line = (px, pz, dx, dz, L) => [[px - dx * L, pz - dz * L], [px + dx * L, pz + dz * L]];
const EAST = [0.139, -0.99];
const lakes = [[-2600, -3200, 700, 380], [-3400, 3600, 900, 500], [3200, -3600, 600, 420], [-1500, 4200, 500, 300], [4200, 3300, 800, 450], [-4300, -1800, 650, 400]];
export default {
  code: 'IST', city: 'ISTANBUL', header: 'İSTANBUL · IST', titleBig: 'İSTANBUL:', titleSize: 112, tz: 'TRT', utcOff: 3,
  lat: 41.2753, lon: 28.7519, decl: -15.4, eot: 16.4, mistName: 'MIST', insetRate: 2.3,
  runways: [
    { id: '34L', z: 2400, w: -1900, e: 1850, labE: '34L', labW: '16R' },
    { id: '34R', z: 2020, w: -2000, e: 2100, labE: '34R', labW: '16L' },
    { id: '35L', z: -1400, w: -2050, e: 2050, labE: '35L', labW: '17R' },
    { id: '35R', z: -1780, w: -1900, e: 1850, labE: '35R', labW: '17L' },
  ],
  rwyText: m => 'ARR 34L · 35R   DEP 34R · 35L',
  ground: {
    base: '#33482f', grass: '#5b7246', grid: null, gridSpacing: [120, 180], farColor: 0x2c3d2b,
    fields: ['#4d6440', '#58703f', '#617848', '#6c7a4c', '#47603a'],
    house: ['#a89f92', '#b5ab9b', '#988f84', '#c2b8a6', '#8f8a80'],
    density(x, z) {
      if (x < -5500) return 0;                                                     // Black Sea
      if (x > -2500 && x < 2600 && z > -2300 && z < 2900) return 0;                // airfield
      for (const [lx, lz, w, h] of lakes) if (Math.abs(x - lx) < w / 2 + 80 && Math.abs(z - lz) < h / 2 + 80) return 0;
      const n = 0.65 + 0.35 * Math.sin(x * 0.0012 + Math.sin(z * 0.0008) * 2) * Math.cos(z * 0.0010 - x * 0.0004);
      let d = 0.06;
      if (Math.hypot(x - 3800, z - 5200) < 2600) d = 0.9;                          // Arnavutköy
      if (Math.hypot(x - 6800, z + 5200) < 3200) d = 0.9;                          // Göktürk / Kemerburgaz
      if (Math.hypot(x + 4600, z - 700) < 900) d = 0.55;                           // Black Sea villages
      if (0.8 * x - 0.6 * z > 9000) d = 0.95;                                      // towards the city
      return d * n;
    },
    water: [[[-5500, -12000], [-5300, 0], [-5650, 12000], [-12000, 12000], [-12000, -12000]], ...lakes.map(([x, z, w, h]) => [[x - w / 2, z - h / 2], [x + w / 2, z - h / 2 + 60], [x + w / 2 - 40, z + h / 2], [x - w / 2 + 50, z + h / 2 - 30]])],
    ocean: { poly: [[-5500, -60000], [-5300, 0], [-5650, 60000], [-90000, 60000], [-90000, -60000]] },
    sand: [[[-5500, -12000], [-5300, 0], [-5650, 12000], [-5520, 12000], [-5170, 0], [-5370, -12000]]],
    woods: [[-5300, -9000, -2500, 9000, 140], [2600, -9000, 9000, 9000, 160], [-2500, -9000, 2600, -2300, 90], [-2500, 2900, 2600, 9000, 90]],
    airfield: [[-2500, -2300, 2600, 2900]],
    roads: [
      { pts: line(2475, 348, EAST[0], EAST[1], 12000), w: 44, light: 0.95 },        // Northern Marmara Motorway
      { pts: [[2475, 348], [1800, 330], [1200, 300]], w: 32, light: 0.95 },          // terminal access
      { pts: [[2475, 348], [3800, 3000], [3900, 5200]], w: 20, light: 0.8 },          // to Arnavutköy
      { pts: [[-2500, -400], [-4400, -200], [-5200, 600]], w: 14, light: 0.5 },       // coast road
      { pts: [[-2500, -2300], [2600, -2300], [2600, 2900], [-2500, 2900], [-2500, -2300]], w: 12, light: 0.6 },
    ],
  },
  aprons: [[-1450, -750, 380, 1350], [380, -300, 1000, 900], [1150, -1100, 1800, -750], [1150, 1350, 1850, 1700], [-1900, 1450, -1250, 1700]],
  taxi: [
    [[-2000, -1160], [2100, -1160]], [[-2000, 1780], [2150, 1780]], [[-2050, -1400], [-2050, -1160]], [[2050, -1400], [2050, -1160]],
    [[-2000, 2020], [-2000, 1780]], [[2100, 2020], [2100, 1780]], [[-1900, -1780], [-1900, -1400]], [[1850, -1780], [1850, -1400]],
    [[-1900, 2400], [-1900, 2020]], [[1850, 2400], [1850, 2020]], [[-800, -1400], [-980, -1160]], [[400, -1400], [220, -1160]],
    [[-800, 2020], [-980, 1780]], [[400, 2020], [220, 1780]], [[-1600, -1160], [-1600, 1780]], [[1150, -1160], [1150, 1780]],
  ],
  buildings: [
    [650, 300, 520, 42, 760, 0xd3d8dd],                                                   // main terminal processor
    [-480, 300, 1700, 18, 70, 0xc9ced3],                                                   // pier spine
    [-1150, 300, 44, 16, 1500, 0xc9ced3], [-750, 300, 44, 16, 1500, 0xc9ced3], [-350, 300, 44, 16, 1500, 0xc9ced3], [50, 300, 44, 16, 1500, 0xc9ced3],
    [1500, -950, 520, 24, 260, 0xa9afb5], [1500, 1520, 560, 20, 240, 0x9aa0a6],             // cargo + remote
    [-1600, 1580, 420, 34, 180, 0xc0c5ca], [-1000, -1950, 300, 20, 120, 0xa9afb5],           // hangars
  ],
  extraBuildings(r) { const b = []; for (let i = 0; i < 16; i++) b.push([2900 + r() * 900, -1800 + r() * 1400, 60 + r() * 40, 14 + r() * 26, 60, 0x9c968f]); return b; },
  tower: { x: 1150, z: 400, h: 86 },
  landmark: 'tulipTower', tulip: { x: 1150, z: 400 },
  stands: (() => { const s = [];
    for (const x of [-1150, -750, -350, 50]) for (let z = -400; z <= 1000; z += 75) { if (Math.abs(z - 300) < 80) continue; s.push([x - 56, z, 0, (z + x) % 3 === 0 ? 0 : 1]); s.push([x + 56, z, Math.PI, z % 2 === 0 ? 1 : 0]); }
    for (let x = 1200; x <= 1760; x += 80) { s.push([x, -820, Math.PI / 2, 1]); s.push([x, 1410, -Math.PI / 2, 1]); }
    return s; })(),
  tailCols: ['#c8102e', '#c8102e', '#c8102e', '#c8102e', '#e2e6ea', '#ffcc00', '#1d3c78', '#5c0632', '#0b6e4f'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 30, 10, 0, 11, 0.60, 0.10, 0],
    [300, 35, 12, 0, 10, 0.75, 0.30, 0],
    [480, 30, 15, 0, 11, 0.70, 0.20, 0.10],
    [600, 25, 18, 27, 13, 0.55, 0, 0],
    [780, 30, 17, 26, 15, 0.35, 0, 0],
    [960, 35, 14, 0, 15, 0.25, 0, 0],
    [1140, 40, 10, 0, 13, 0.20, 0, 0],
    [1440, 40, 8, 0, 11, 0.30, 0, 0],
  ],
  introCam: { P0: [6200, 720, 320], P1: [5300, 610, 300], Q0: [-1500, 0, 300], Q1: [-1700, 0, 300] },
  introEvents: [{ type: 'A', t: 1.6, rw: '35R', cat: 3, wide: true }, { type: 'A', t: 3.3, rw: '34L', cat: 1, wide: false }],
  shots: [
    { t0: 5.0, t1: 12.5, name: 'CAM 1 · AERIAL', p0: [4400, 1150, 600], p1: [3900, 1000, 520], q0: [-1300, 0, 300], q1: [-1450, 0, 300], fov: 46, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 12.5, t1: 19.5, name: 'CAM 2 · APPROACH 35R', p0: [1530, 34, -1560], p1: [1620, 36, -1565], q0: [6500, 240, -1780], q1: [6500, 220, -1780], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 19.5, t1: 26.5, name: 'CAM 3 · TERMINAL APRON', p0: [-300, 44, -960], p1: [-380, 44, -970], q0: [-1350, 70, -1500], q1: [-1450, 70, -1500], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 26.5, t1: 33.5, name: 'CAM 4 · TULIP TOWER', p0: [1640, 46, 690], p1: [1580, 46, 640], q0: [-1500, 55, -1100], q1: [-1560, 55, -1120], fov: 50, sc: 1.7, sf: 0.6, near: 1.0 },
    { t0: 33.5, t1: 40.5, name: 'CAM 5 · SUNSET', p0: [260, 80, -2150], p1: [180, 78, -2150], q0: [-300, 30, 4200], q1: [-380, 30, 4200], fov: 54, sc: 1.6, sf: 0.6, near: 1.0 },
    { t0: 40.5, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [0, 0, 300], r: 4700, h: 1550, a0: 0.2, a1: 1.0 }, fov: 46, sc: 2.6, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 675, rw: '35R' }, { m: 1255, rw: '34L' }],
  globe: {
    keys: [
      [3.4, 41.28, 28.75, 1.08, 960],
      [6.4, 38, 30, 13.5, 615],
      [13.5, 38, 32, 13.5, 615],
      [16.0, 47, 15, 5.6, 615],
      [22.5, 47, 18, 5.4, 615],
      [25.0, 18, 35, 9.5, 615],
      [31.5, 16, 38, 9.3, 615],
      [34.0, 30, 75, 11.5, 615],
      [40.5, 28, 82, 11.3, 615],
      [43.0, 40, 20, 14.0, 615],
      [52.0, 40, 25, 14.0, 615],
      [54.6, 34, 25, 11.5, 840],
      [60.0, 32, 10, 11.3, 840],
    ],
    views: [[6.4, 'WORLDWIDE'], [16.0, 'EUROPE'], [25.0, 'MIDDLE EAST & AFRICA'], [34.0, 'ASIA'], [43.0, 'WORLDWIDE']],
    worldLabels: ['JFK', 'ORD', 'GRU', 'JNB', 'LOS', 'NBO', 'ADD', 'DXB', 'DOH', 'DEL', 'BKK', 'SIN', 'HKG', 'HND', 'ICN', 'PEK', 'ALA', 'TAS', 'CMN', 'SVO', 'CAI', 'JED'],
    regionLabels: ['AMS', 'MUC', 'VIE', 'BUD', 'WAW', 'ATH', 'FCO', 'BCN', 'LIS', 'ARN', 'OSL', 'HEL', 'ZRH', 'BER', 'PRG', 'SOF', 'BEG', 'MAD', 'DUB', 'TBS', 'GYD'],
    names: { JFK: 'NEW YORK', LHR: 'LONDON', CDG: 'PARIS', HND: 'TOKYO', MXP: 'MILAN', SVO: 'MOSCOW' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const night = FL.filter(f => f.type === 'D' && f.t < 180).length;
    const amer = FL.filter(f => f.type === 'D' && ROUTES[f.r].dur >= 600 && ROUTES[f.r].lon < -30).length;
    const evening = FL.filter(f => f.type === 'D' && f.t >= 1080 && f.t < 1200).length;
    return [
      { m: 60, tm: '01:00', a: 'THE NIGHT BANK', b: `${night} departures between midnight and 3 am` },
      { m: 330, tm: '05:30', a: 'DAWN ARRIVALS', b: 'red-eyes landing from Asia and Africa' },
      { m: 459, tm: '07:39', a: 'SUNRISE', b: 'drizzle and a north-easterly over the Black Sea' },
      { m: 600, tm: '10:00', a: 'POYRAZ WIND', b: 'north-easterly gusts near 27 kt' },
      { m: 795, tm: '13:15', a: 'TRANSATLANTIC WAVE', b: `${amer} long-haul departures to the Americas` },
      { m: S.stats.busiest * 60 + 45, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings` },
      { m: 1078, tm: '17:58', a: 'SUNSET', b: 'lights come on across the mega-hub' },
      { m: 1140, tm: '19:00', a: 'THE EVENING BANK', b: `${evening} departures in two hours` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 352, name: 'ISTANBUL APPROACH',
    fixes: [{ name: 'SOUTH', brg: 182, dist: 20, hold: true }, { name: 'EAST', brg: 112, dist: 22, hold: true }, { name: 'WEST', brg: 245, dist: 20, hold: true }, { name: 'NORTH', brg: 30, dist: 20, hold: false }],
    places: [{ name: 'İSTANBUL', brg: 132, dist: 17 }, { name: 'BOSPHORUS', brg: 95, dist: 16 }, { name: 'BLACK SEA', brg: 10, dist: 13 }, { name: 'SEA OF MARMARA', brg: 185, dist: 26 }, { name: 'ÇATALCA', brg: 255, dist: 16 }],
    holdRate: 95, depTurn: {}, straightOut: 4,
  },
};

// Los Angeles International (LAX). Local frame: metres, x = east, z = south, origin at the central terminal area.
const coastX = z => -3150 + 0.31 * z;
export default {
  code: 'LAX', city: 'LOS ANGELES', header: 'LAX · LOS ANGELES', titleBig: 'LAX:', tz: 'PST', utcOff: -8,
  lat: 33.9425, lon: -118.4081, decl: -14.7, eot: 16.4, mistName: 'MARINE LAYER',
  runways: [
    { id: '24R', z: -790, w: -1720, e: 1000, labE: '24R', labW: '06L' },
    { id: '24L', z: -580, w: -1900, e: 1420, labE: '24L', labW: '06R' },
    { id: '25R', z: 560, w: -1880, e: 2060, labE: '25R', labW: '07L' },
    { id: '25L', z: 770, w: -1500, e: 1880, labE: '25L', labW: '07R' },
  ],
  rwyText: m => 'ARR 24R · 25L   DEP 24L · 25R',
  // ---------------------------------------------------------------- ground
  ground: {
    base: '#3e423b', grass: '#7a7756', grid: 0.0, gridJitter: 0.06, gridSpacing: [150, 200],
    house: ['#6a6660', '#7a7068', '#5f6460', '#837a70', '#6c6a64', '#77736b'],
    fields: ['#6b6a52', '#7a7558', '#5e6a4c'],
    density(x, z) {
      if (x < coastX(z) + 60) return 0;                                   // ocean
      if (x > -2350 && x < 2500 && z > -1300 && z < 1300) return 0;        // airfield
      if (x < -2350 && z > -1300 && z < 1300) return 0.08;                 // dunes
      if (x > -2600 && x < -900 && z > 1500 && z < 2700) return 0;         // refinery
      const n = 0.7 + 0.3 * Math.sin(x * 0.0009 + Math.sin(z * 0.0006) * 2) * Math.cos(z * 0.0011 - x * 0.0003);
      return Math.min(1, 0.95 * n);
    },
    water: [[[coastX(-12000), -12000], [coastX(12000), 12000], [-40000, 12000], [-40000, -12000]]],
    ocean: { poly: [[coastX(-60000), -60000], [coastX(60000), 60000], [-90000, 60000], [-90000, -60000]] },
    industry: [[-2600, 1500, -900, 2700]],
    sand: [[[coastX(-3000) + 40, -3000], [coastX(3000) + 40, 3000], [coastX(3000) + 380, 3000], [coastX(-3000) + 380, -3000]],
           [[coastX(-1300) + 380, -1300], [-2350, -1300], [-2350, 1300], [coastX(1300) + 380, 1300]]],
    airfield: [[-2350, -1300, 2500, 1300]],
    roads: [
      { pts: [[3900, -12000], [3800, -2000], [3700, 0], [3900, 3000], [4300, 12000]], w: 46, light: 0.95 },        // I-405
      { pts: [[300, 1650], [3800, 1700], [12000, 1720]], w: 42, light: 0.95 },                                       // I-105
      { pts: [[900, 0], [3700, 0], [12000, 0]], w: 30, light: 0.9 },                                                   // Century Blvd
      { pts: [[-2300, -2300], [12000, -2300]], w: 24, light: 0.8 },                                                    // Manchester
      { pts: [[-2400, 1350], [12000, 1350]], w: 24, light: 0.8 },                                                      // Imperial
      { pts: [[300, -12000], [300, -1350], [300, 1350], [250, 12000]], w: 24, light: 0.8 },                           // Sepulveda
      { pts: [[2650, -12000], [2650, 12000]], w: 20, light: 0.7 },                                                     // Aviation
      { pts: [[coastX(-12000) + 260, -12000], [coastX(12000) + 260, 12000]], w: 18, light: 0.7 },                      // Vista del Mar
      { pts: [[-2400, -1300], [2500, -1300], [2500, 1300], [-2400, 1300], [-2400, -1300]], w: 12, light: 0.6 },        // perimeter
    ],
  },
  aprons: [[-1150, -420, 1050, 420], [-1700, -330, -1250, 330], [1350, -1150, 2050, -900], [1500, 950, 2300, 1200]],
  taxi: [
    [[-1950, -680], [1500, -680]], [[-1900, -440], [1300, -440]], [[-1900, 430], [2100, 430]], [[-1600, 660], [1950, 660]],
    [[-1950, -680], [-1950, 660]], [[1500, -680], [1500, -440]], [[2100, 430], [2100, 660]], [[-1300, -440], [-1300, 430]],
    [[-300, -440], [-300, -680]], [[600, -440], [600, -680]], [[-300, 430], [-300, 660]], [[800, 430], [800, 660]],
  ],
  buildings: [
    // Tom Bradley International (west end of the horseshoe) + West Gates
    [-860, 0, 240, 34, 520, 0xc9d0d8], [-1480, 0, 70, 22, 560, 0xb8c0c8],
    // north terminals T1-T3 and concourses
    [450, -300, 260, 20, 70, 0xb0b7be], [180, -300, 220, 20, 70, 0xb0b7be], [-120, -300, 260, 20, 70, 0xb0b7be],
    [520, -380, 40, 14, 150, 0xb8bec4], [240, -380, 40, 14, 150, 0xb8bec4], [-60, -380, 40, 14, 150, 0xb8bec4], [-430, -360, 300, 14, 40, 0xb8bec4],
    // south terminals T4-T8 and concourses
    [520, 300, 240, 20, 70, 0xb0b7be], [260, 300, 220, 20, 70, 0xb0b7be], [10, 300, 220, 20, 70, 0xb0b7be], [-260, 300, 220, 20, 70, 0xb0b7be],
    [560, 380, 40, 14, 150, 0xb8bec4], [300, 380, 40, 14, 150, 0xb8bec4], [40, 380, 40, 14, 150, 0xb8bec4], [-240, 380, 40, 14, 150, 0xb8bec4], [-470, 350, 280, 14, 40, 0xb8bec4],
    // central parking structures
    [-360, -120, 160, 16, 90, 0x8e9196], [-360, 120, 160, 16, 90, 0x8e9196], [560, -120, 150, 16, 90, 0x8e9196], [560, 120, 150, 16, 90, 0x8e9196],
    // cargo + hangars
    [1700, -1050, 420, 22, 120, 0x9aa0a6], [1900, 1100, 500, 24, 140, 0x9aa0a6], [2150, -800, 180, 30, 140, 0xc0c5ca],
  ],
  extraBuildings(r) { // hotels along Century Blvd and offices
    const b = [];
    for (let x = 2800; x < 6000; x += 180 + r() * 140) { b.push([x, -110 - r() * 60, 60 + r() * 30, 30 + r() * 50, 40, 0xa39d96]); b.push([x + 60, 110 + r() * 60, 60 + r() * 30, 25 + r() * 45, 40, 0x9a958e]); }
    for (let x = -1800; x < 1800; x += 300 + r() * 200) b.push([x, -1500 - r() * 200, 70, 18 + r() * 30, 50, 0x9c968f]);
    return b;
  },
  tower: { x: 330, z: -20, h: 84 },
  landmark: 'themeBuilding',
  stands: (() => { const s = [];
    for (const x of [520, 240, -60]) for (let z = -480; z >= -560; z -= 80) { s.push([x - 50, z + 20, 0, 1]); s.push([x + 50, z + 20, Math.PI, 0]); }
    for (const x of [560, 300, 40, -240]) for (let z = 470; z <= 540; z += 70) { s.push([x - 50, z - 20, 0, 0]); s.push([x + 50, z - 20, Math.PI, 1]); }
    for (let z = -240; z <= 240; z += 70) { s.push([-1030, z, 0, 1]); s.push([-1580, z, 0, 1]); s.push([-1380, z, Math.PI, 1]); }
    for (let x = -700; x <= -150; x += 60) { s.push([x, -420, Math.PI / 2, 0]); s.push([x, 410, -Math.PI / 2, 0]); }
    return s; })(),
  tailCols: ['#c8102e', '#0b3d91', '#1a5aa8', '#0f2d6b', '#e2e6ea', '#7a1f3d', '#f2a900', '#2b7a4b'],
  // ---------------------------------------------------------------- weather (local minutes)
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 70, 4, 0, 15, 0.05, 0, 0],
    [300, 90, 3, 0, 14, 0.30, 0, 0.25],
    [390, 250, 4, 0, 14, 0.80, 0, 0.60],
    [540, 250, 6, 0, 16, 0.60, 0, 0.35],
    [660, 250, 9, 0, 20, 0.15, 0, 0],
    [840, 255, 12, 18, 23, 0.05, 0, 0],
    [1000, 260, 11, 0, 21, 0.05, 0, 0],
    [1140, 265, 7, 0, 18, 0.05, 0, 0],
    [1440, 70, 4, 0, 15, 0.05, 0, 0],
  ],
  // ---------------------------------------------------------------- cameras
  introCam: { P0: [5300, 640, -380], P1: [4600, 540, -440], Q0: [-700, 0, -700], Q1: [-900, 0, -720] },
  introEvents: [{ type: 'A', t: 3.7, rw: '24R', cat: 3, wide: true }, { type: 'A', t: 6.4, rw: '24R', cat: 1, wide: false }],
  shots: [
    { t0: 9.0, t1: 17.0, name: 'CAM 1 · AERIAL', p0: [4300, 1050, 1300], p1: [3800, 900, 1100], q0: [-700, 0, -50], q1: [-850, 0, -60], fov: 42, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 17.0, t1: 24.0, name: 'CAM 2 · APPROACH 24R', p0: [640, 36, -1010], p1: [740, 38, -1020], q0: [5200, 240, -800], q1: [5200, 220, -800], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 24.0, t1: 31.0, name: 'CAM 3 · DOCKWEILER BEACH', p0: [-2780, 34, -420], p1: [-2740, 34, -440], q0: [-500, 120, -600], q1: [-600, 125, -600], fov: 50, sc: 1.7, sf: 0.5, near: 1.3 },
    { t0: 31.0, t1: 38.0, name: 'CAM 4 · TOWER VIEW', p0: [420, 120, 60], p1: [380, 120, 40], q0: [-3200, 0, 60], q1: [-3200, 0, 40], fov: 50, sc: 1.5, sf: 0.75, near: 0.9 },
    { t0: 38.0, t1: 45.0, name: 'CAM 5 · THEME BUILDING', p0: [520, 46, 210], p1: [470, 44, 190], q0: [0, 40, -40], q1: [-40, 40, -60], fov: 48, sc: 1.4, sf: 0.6, near: 1.0 },
    { t0: 45.0, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [-150, 0, 0], r: 3800, h: 1350, a0: 0.25, a1: 1.05 }, fov: 42, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 645, rw: '24R' }, { m: 1215, rw: '25L' }],
  // ---------------------------------------------------------------- globe
  globe: {
    keys: [
      [7.0, 33.94, -118.4, 1.08, 960],
      [10.2, 40, -118, 13.5, 615],
      [19.0, 40, -112, 13.5, 615],
      [21.5, 38, -98, 6.4, 615],
      [27.5, 39, -96, 6.2, 615],
      [30.0, 24, -160, 11.8, 615],
      [35.5, 22, -165, 11.6, 615],
      [38.0, 14, -96, 9.6, 615],
      [43.5, 12, -92, 9.4, 615],
      [46.0, 40, -118, 13.5, 615],
      [52.0, 40, -112, 13.5, 615],
      [54.6, 30, -120, 11.0, 840],
      [60.0, 28, -138, 10.8, 840],
    ],
    views: [[10.2, 'WORLDWIDE'], [21.5, 'ACROSS AMERICA'], [30.0, 'THE PACIFIC'], [38.0, 'LATIN AMERICA'], [46.0, 'WORLDWIDE']],
    worldLabels: ['LHR', 'HND', 'SYD', 'ICN', 'HKG', 'MEX', 'HNL', 'MIA', 'BOS', 'LIM', 'AKL', 'TPE', 'DXB', 'ATL'],
    regionLabels: ['SEA', 'PDX', 'SLC', 'MSP', 'IAH', 'YVR', 'MEX', 'GDL', 'MIA', 'BOS', 'ATL', 'IAD', 'CUN', 'HNL', 'AUS'],
    names: { JFK: 'NEW YORK', LHR: 'LONDON', HND: 'TOKYO', CDG: 'PARIS', SJD: 'LOS CABOS' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const firstArr = FL.find(f => f.type === 'A' && f.t > 240), firstDep = FL.find(f => f.type === 'D' && f.t > 300);
    const red = FL.filter(f => f.type === 'D' && f.t >= 1290).length;
    return [
      { m: firstArr.t, a: 'FIRST ARRIVAL OF THE DAY', b: `${firstArr.fn} from ${ROUTES[firstArr.r].city}` },
      { m: 374, tm: '06:14', a: 'SUNRISE', b: 'marine layer hugging the coast' },
      { m: 580, tm: '09:40', a: 'MARINE LAYER BURNS OFF', b: 'sunshine and a westerly sea breeze' },
      { m: S.stats.busiest * 60 + 20, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings in 60 minutes` },
      { m: 1021, tm: '17:01', a: 'SUNSET OVER THE PACIFIC', b: 'the evening push to Asia and Europe' },
      { m: 'pax150', a: '150,000 PASSENGERS', b: 'and counting' },
      { m: 1300, tm: '21:40', a: 'THE RED-EYE WAVE', b: `${red} overnight departures to the East Coast & Asia` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 263, name: 'SOCAL APPROACH',
    fixes: [{ name: 'EAST', brg: 72, dist: 24, hold: true }, { name: 'SOUTH-EAST', brg: 125, dist: 22, hold: true }, { name: 'NORTH', brg: 20, dist: 22, hold: false }, { name: 'COAST', brg: 318, dist: 20, hold: false }],
    places: [{ name: 'DOWNTOWN LA', brg: 40, dist: 9.5 }, { name: 'SANTA MONICA', brg: 325, dist: 6 }, { name: 'LONG BEACH', brg: 128, dist: 14 }, { name: 'PACIFIC OCEAN', brg: 235, dist: 16 }, { name: 'BURBANK', brg: 12, dist: 18 }],
    holdRate: 80, depTurn: { '24L': 1, '25R': -1 }, straightOut: 4,
  },
};

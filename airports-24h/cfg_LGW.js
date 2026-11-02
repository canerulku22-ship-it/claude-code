// London Gatwick (LGW). Local frame: metres, x = east, z = south, origin at the runway centre.
export default {
  code: 'LGW', city: 'LONDON GATWICK', header: 'GATWICK · LONDON', titleBig: 'GATWICK:', tz: 'GMT', utcOff: 0,
  lat: 51.1537, lon: -0.1821, decl: -14.7, eot: 16.4, mistName: 'FOG', insetRate: 1.8,
  runways: [{ id: '26L', z: 0, w: -1650, e: 1666, labE: '26L', labW: '08R' }],
  rwyText: m => 'RWY 26L · ARR + DEP',
  ground: {
    base: '#465a3c', grass: '#557146', grid: null, gridSpacing: [120, 190],
    fields: ['#4f6a40', '#5b7447', '#667a4a', '#4a6239', '#6d7f4f', '#7a7a52'],
    house: ['#6b625a', '#5f5f5c', '#74695f', '#57594f', '#6e6a62'],
    density(x, z) {
      if (x > -2300 && x < 2200 && z > -700 && z < 1500) return 0;                      // airfield
      const n = 0.65 + 0.35 * Math.sin(x * 0.0012 + Math.sin(z * 0.0008) * 2) * Math.cos(z * 0.0010 - x * 0.0004);
      if (z > 2100 && x > -4200 && x < 4200) return 0.95 * n;                            // Crawley
      if (x > 1100 && x < 3800 && z > -3000 && z < -700) return 0.85 * n;                // Horley
      if (x > -3400 && x < -2400 && z > -900 && z < 0) return 0.5 * n;                   // Charlwood
      return 0.08;
    },
    woods: [[-9000, -9000, -2600, 9000, 90], [-2600, -6000, 1000, -1500, 40], [3800, -9000, 9000, 2000, 60], [-6000, 1500, -2200, 9000, 50]],
    airfield: [[-2300, -700, 2200, 1500]],
    roads: [
      { pts: [[3100, -12000], [3000, -3000], [2900, 1200], [3200, 6000], [3600, 12000]], w: 40, light: 0.95 },   // M23
      { pts: [[2900, 1200], [1800, 1300], [600, 1500], [-500, 1300]], w: 24, light: 0.85 },                     // M23 spur to the terminals
      { pts: [[1800, -12000], [1750, -2600], [1600, -800], [1700, 1600], [1600, 4000], [1500, 12000]], w: 20, light: 0.8 }, // A23
      { pts: [[1350, -12000], [1350, 12000]], w: 10, light: 0.0 },                                                // railway
      { pts: [[-2300, -700], [2200, -700], [2200, 1500], [-2300, 1500], [-2300, -700]], w: 12, light: 0.6 },    // perimeter
      { pts: [[-12000, -400], [-3400, -400], [-2300, -650]], w: 14, light: 0.4 },
    ],
  },
  aprons: [[-1550, 280, -250, 900], [150, 320, 1500, 1050], [-2100, 380, -1600, 760]],
  taxi: [
    [[-1700, 190], [1720, 190]], [[-1350, -200], [1300, -200]], [[-1700, 0], [-1700, 190]], [[1720, 0], [1720, 190]],
    [[-900, 0], [-1080, 190]], [[0, 0], [-180, 190]], [[700, 0], [520, 190]], [[-1350, -200], [-1500, 0]], [[1300, -200], [1450, 0]],
  ],
  buildings: [
    [-930, 1000, 320, 28, 130, 0xb6bec6], [-1220, 600, 44, 14, 420, 0xb8bec4], [-900, 600, 44, 14, 420, 0xb8bec4], [-580, 650, 44, 14, 320, 0xb8bec4],
    [900, 1180, 420, 26, 150, 0xb0b8c0], [480, 820, 44, 14, 360, 0xb8bec4], [760, 820, 44, 14, 360, 0xb8bec4], [1100, 900, 44, 14, 260, 0xb8bec4],
    [-1850, 570, 220, 30, 160, 0xc0c5ca], [-300, 1200, 200, 20, 90, 0x8e9196], [300, 1300, 260, 22, 100, 0x8e9196],
  ],
  extraBuildings(r) { const b = []; for (let x = -1800; x < 1800; x += 260 + r() * 200) b.push([x, 1650 + r() * 120, 60, 18 + r() * 20, 40, 0x9c968f]); return b; },
  tower: { x: -20, z: 640, h: 60 },
  landmark: 'gatwickSatellite', satellite: { x: 1300, z: 600 },
  stands: (() => { const s = [];
    for (const x of [-1220, -900, -580]) for (let z = 420; z <= 760; z += 70) { s.push([x - 52, z, 0, x === -900 ? 1 : 0]); s.push([x + 52, z, Math.PI, 0]); }
    for (const x of [480, 760, 1100]) for (let z = 660; z <= 980; z += 70) { s.push([x - 52, z, 0, 0]); s.push([x + 52, z, Math.PI, x === 1100 ? 1 : 0]); }
    for (let a = 0; a < 6.2; a += 0.75) s.push([1300 + Math.cos(a) * 125, 600 + Math.sin(a) * 125, -a + Math.PI, 1]);
    for (let x = -2050; x <= -1650; x += 80) s.push([x, 420, Math.PI / 2, 0]);
    return s; })(),
  tailCols: ['#ff6600', '#ff6600', '#ff6600', '#1d3c78', '#c8102e', '#e2e6ea', '#7a1fa0', '#0b6e4f', '#d4003b'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 200, 8, 0, 9, 0.85, 0.30, 0],
    [180, 210, 7, 0, 8.5, 0.70, 0.10, 0],
    [300, 220, 4, 0, 7, 0.40, 0, 0.40],
    [400, 230, 3, 0, 6, 0.30, 0, 0.78],
    [520, 230, 5, 0, 8, 0.40, 0, 0.35],
    [660, 230, 10, 0, 11, 0.50, 0, 0],
    [840, 240, 14, 24, 12.5, 0.60, 0, 0],
    [930, 250, 17, 29, 12, 0.92, 0.75, 0],
    [1020, 270, 15, 25, 11, 0.60, 0.15, 0],
    [1140, 290, 9, 0, 9, 0.25, 0, 0],
    [1440, 300, 6, 0, 6.5, 0.15, 0, 0],
  ],
  introCam: { P0: [5300, 600, 420], P1: [4600, 510, 380], Q0: [-800, 0, 40], Q1: [-1000, 0, 40] },
  introEvents: [{ type: 'A', t: 3.7, rw: '26L', cat: 2, wide: true }, { type: 'A', t: 6.4, rw: '26L', cat: 0, wide: false }],
  shots: [
    { t0: 9.0, t1: 17.0, name: 'CAM 1 · AERIAL', p0: [3300, 1000, 2500], p1: [2900, 880, 2200], q0: [-500, 0, 300], q1: [-600, 0, 300], fov: 42, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 17.0, t1: 24.0, name: 'CAM 2 · APPROACH 26L', p0: [1330, 34, 230], p1: [1420, 36, 235], q0: [6200, 240, 0], q1: [6200, 220, 0], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 24.0, t1: 31.0, name: 'CAM 3 · NORTH TERMINAL', p0: [-520, 42, 430], p1: [-600, 42, 440], q0: [-1500, 60, -60], q1: [-1600, 60, -60], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 31.0, t1: 38.0, name: 'CAM 4 · TOWER VIEW', p0: [-60, 92, 540], p1: [-100, 92, 520], q0: [-4200, 0, 60], q1: [-4200, 0, 40], fov: 50, sc: 1.5, sf: 0.75, near: 0.9 },
    { t0: 38.0, t1: 45.0, name: 'CAM 5 · SOUTH TERMINAL', p0: [1650, 70, 980], p1: [1580, 66, 960], q0: [700, 30, 150], q1: [620, 30, 140], fov: 48, sc: 1.4, sf: 0.6, near: 1.0 },
    { t0: 45.0, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [0, 0, 350], r: 3700, h: 1350, a0: 0.35, a1: 1.15 }, fov: 42, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 470, rw: '26L' }, { m: 930, rw: '26L' }],
  globe: {
    keys: [
      [7.0, 51.15, -0.18, 1.08, 960],
      [10.2, 36, 2, 13.5, 615],
      [19.0, 36, 6, 13.5, 615],
      [21.5, 47, 6, 5.2, 615],
      [27.5, 47, 9, 5.0, 615],
      [30.0, 37, -6, 7.4, 615],
      [35.5, 36, -2, 7.2, 615],
      [38.0, 32, -38, 11.0, 615],
      [43.5, 30, -42, 10.8, 615],
      [46.0, 36, 2, 13.5, 615],
      [52.0, 36, 8, 13.5, 615],
      [54.6, 30, -6, 11.0, 840],
      [60.0, 28, -20, 10.8, 840],
    ],
    views: [[10.2, 'WORLDWIDE'], [21.5, 'EUROPE'], [30.0, 'SUN DESTINATIONS'], [38.0, 'ACROSS THE ATLANTIC'], [46.0, 'WORLDWIDE']],
    worldLabels: ['JFK', 'MCO', 'BGI', 'DXB', 'DOH', 'HKG', 'PEK', 'GOI', 'TFS', 'IST', 'YYZ', 'CUN', 'LAS', 'HRG', 'KEF'],
    regionLabels: ['GLA', 'BFS', 'CPH', 'BER', 'PRG', 'VIE', 'BUD', 'KRK', 'FCO', 'NCE', 'LIS', 'MAD', 'PMI', 'OSL', 'MXP', 'ACE', 'FAO', 'ATH'],
    names: { JFK: 'NEW YORK', MCO: 'ORLANDO', AGP: 'MALAGA', MXP: 'MILAN' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const firstArr = FL.find(f => f.type === 'A' && f.t > 240);
    const wave = FL.filter(f => f.type === 'D' && f.t >= 360 && f.t < 420).length;
    const lastDep = [...FL].reverse().find(f => f.type === 'D');
    return [
      { m: firstArr.t, a: 'FIRST ARRIVAL OF THE DAY', b: `${firstArr.fn} from ${ROUTES[firstArr.r].city}` },
      { m: 362, tm: '06:00', a: 'THE 6AM DEPARTURE WAVE', b: `${wave} take-offs in the first hour` },
      { m: 410, tm: '06:50', a: 'FOG ON THE AIRFIELD', b: 'low visibility procedures in force' },
      { m: S.stats.busiest * 60 + 60, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} movements on a single runway` },
      { m: 'pax50', a: '50,000 PASSENGERS', b: 'and counting' },
      { m: 880, tm: '14:40', a: 'SQUALLY SHOWERS', b: 'wind veering west, gusts near 30 kt' },
      { m: 995, tm: '16:35', a: 'SUNSET', b: 'the evening wave of holiday flights' },
      { m: lastDep.t, a: 'LAST DEPARTURE', b: `${lastDep.fn} to ${ROUTES[lastDep.r].city}` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 258, name: 'GATWICK DIRECTOR',
    fixes: [{ name: 'TIMBA', brg: 126, dist: 20, hold: true }, { name: 'WILLO', brg: 236, dist: 18, hold: true }, { name: 'NORTH', brg: 10, dist: 22, hold: false }, { name: 'EAST', brg: 78, dist: 24, hold: false }],
    places: [{ name: 'LONDON', brg: 5, dist: 21 }, { name: 'HEATHROW', brg: 332, dist: 21.6 }, { name: 'BRIGHTON', brg: 175, dist: 20 }, { name: 'ENGLISH CHANNEL', brg: 195, dist: 27 }, { name: 'CRAWLEY', brg: 190, dist: 3.4 }],
    holdRate: 46, depTurn: {}, straightOut: 3,
  },
};

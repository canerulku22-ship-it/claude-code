// Izmir Adnan Menderes (ADB). Local frame: metres; -x = landing direction on runway 34 (true 342°), -z = right of track.
const line = (px, pz, dx, dz, L) => [[px - dx * L, pz - dz * L], [px + dx * L, pz + dz * L]];
const NORTH = [-0.95, -0.31], EAST = [0.31, -0.95];
export default {
  code: 'ADB', city: 'IZMIR', header: 'İZMİR · ADB', titleBig: 'İZMİR:', tz: 'TRT', utcOff: 3,
  lat: 38.2924, lon: 27.157, decl: -15.0, eot: 16.4, mistName: 'HAZE',
  runways: [{ id: '34R', z: -160, w: -1600, e: 1640, labE: '34R', labW: '16L' }, { id: '34L', z: 160, w: -1450, e: 1550, labE: '34L', labW: '16R' }],
  rwyText: m => 'ARR 34R · DEP 34L',
  ground: {
    base: '#6a6448', grass: '#7c7a54', grid: null, gridSpacing: [90, 150],
    fields: ['#6b6b45', '#7a7550', '#5e6440', '#807a52', '#6e6a46', '#5a6038'],
    house: ['#b9b2a3', '#c4bba9', '#a9a497', '#b0a08a', '#9c968a', '#d0c8b6'],
    density(x, z) {
      if (x > -1900 && x < 2000 && z > -900 && z < 1150) return 0;                 // airfield
      if (x < -6000 && z > 2500 + (-x - 6000) * 0.3) return 0;                     // Gulf of Izmir
      const n = 0.65 + 0.35 * Math.sin(x * 0.0013 + Math.sin(z * 0.0009) * 2) * Math.cos(z * 0.0011 - x * 0.0005);
      const city = -0.95 * x - 0.31 * z;                                           // towards Izmir city centre
      let d = 0.15;
      if (z > 1300 && x < 1500) d = 0.85;                                          // Gaziemir
      if (city > 2200) d = Math.max(d, 0.95);
      if (x > 2300) d = Math.min(d, 0.12);                                         // olive groves to the south
      return d * n;
    },
    water: [[[-20000, 2500], [-6000, 2500], [-4500, 9000], [-6000, 20000], [-20000, 20000]]],
    woods: [[2300, -9000, 9000, 9000, 70]],
    airfield: [[-1900, -900, 2000, 1150]],
    roads: [
      { pts: line(400, -1500, NORTH[0], NORTH[1], 9000), w: 40, light: 0.95 },    // Izmir–Aydın motorway
      { pts: line(-2600, 1700, NORTH[0], NORTH[1], 9000), w: 26, light: 0.85 },   // Akçay Cd. through Gaziemir
      { pts: line(-2000, 2600, EAST[0], EAST[1], 9000), w: 20, light: 0.8 },
      { pts: [[-1900, -900], [2000, -900], [2000, 1150], [-1900, 1150], [-1900, -900]], w: 12, light: 0.6 },
      { pts: [[-500, 1150], [-900, 1600], [-1600, 2000]], w: 18, light: 0.85 },
    ],
  },
  aprons: [[-1000, 420, 700, 760], [900, 420, 1500, 700]],
  taxi: [[[-1500, 330], [1600, 330]], [[-1500, 160], [-1500, 330]], [[1600, 160], [1600, 330]], [[-600, 160], [-780, 330]], [[500, 160], [320, 330]], [[-1550, -160], [-1550, 160]], [[1640, -160], [1640, 160]], [[0, -160], [0, 160]]],
  buildings: [
    [-450, 880, 520, 26, 150, 0xcfd4d8], [380, 860, 400, 22, 130, 0xc4cad0],     // international + domestic terminals
    [-650, 640, 40, 14, 200, 0xc8cdd2], [-250, 640, 40, 14, 200, 0xc8cdd2], [380, 650, 40, 14, 180, 0xc8cdd2],
    [1200, 820, 260, 28, 140, 0xbfc4c9], [1500, 820, 200, 26, 120, 0xbfc4c9],     // SunExpress / maintenance hangars
    [-1300, 900, 300, 14, 120, 0x9aa0a6],
  ],
  extraBuildings(r) { const b = []; for (let i = 0; i < 40; i++) b.push([-2200 - r() * 6000, -2600 - r() * 5000, 30 + r() * 30, 18 + r() * 45, 30, 0xc8bfae]); return b; },
  tower: { x: 60, z: 980, h: 52 },
  landmark: 'none',
  stands: (() => { const s = [];
    for (const x of [-650, -250, 380]) for (const z of [520, 590, 660, 730]) { s.push([x - 52, z, 0, x === -650 && z > 600 ? 1 : 0]); s.push([x + 52, z, Math.PI, 0]); }
    for (let x = 960; x <= 1440; x += 80) s.push([x, 520, Math.PI / 2, 0]);
    return s; })(),
  tailCols: ['#c8102e', '#ffcc00', '#fdb913', '#c8102e', '#e2e6ea', '#004b93', '#ff6600'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 20, 6, 0, 13, 0.05, 0, 0],
    [360, 15, 8, 0, 12, 0.10, 0, 0.15],
    [480, 10, 12, 0, 14, 0.10, 0, 0.05],
    [720, 360, 15, 24, 20, 0.15, 0, 0],
    [900, 350, 16, 25, 22, 0.20, 0, 0],
    [1050, 345, 12, 0, 19, 0.10, 0, 0],
    [1200, 20, 7, 0, 16, 0.05, 0, 0],
    [1440, 25, 5, 0, 14, 0.05, 0, 0],
  ],
  introCam: { P0: [5200, 560, 420], P1: [4500, 470, 380], Q0: [-900, 0, -100], Q1: [-1050, 0, -120] },
  introEvents: [{ type: 'A', t: 1.6, rw: '34R', cat: 0, wide: false }, { type: 'A', t: 3.3, rw: '34R', cat: 1, wide: false }],
  shots: [
    { t0: 5.0, t1: 12.5, name: 'CAM 1 · AERIAL', p0: [3300, 980, 2400], p1: [2900, 860, 2100], q0: [-400, 0, 150], q1: [-500, 0, 150], fov: 42, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 12.5, t1: 19.5, name: 'CAM 2 · APPROACH 34R', p0: [1330, 34, -430], p1: [1420, 36, -440], q0: [6200, 240, -160], q1: [6200, 220, -160], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 19.5, t1: 26.5, name: 'CAM 3 · TERMINAL APRON', p0: [-200, 42, 470], p1: [-280, 42, 480], q0: [-1300, 70, 120], q1: [-1400, 70, 120], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 26.5, t1: 33.5, name: 'CAM 4 · TOWER VIEW', p0: [40, 78, 820], p1: [0, 78, 800], q0: [-4400, 0, 0], q1: [-4400, 0, -20], fov: 50, sc: 1.5, sf: 0.75, near: 0.9 },
    { t0: 33.5, t1: 40.5, name: 'CAM 5 · AEGEAN SUNSET', p0: [380, 70, -1000], p1: [300, 68, -1000], q0: [-600, 40, 3200], q1: [-680, 40, 3200], fov: 52, sc: 1.5, sf: 0.6, near: 1.0 },
    { t0: 40.5, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [0, 0, 250], r: 3600, h: 1300, a0: 0.35, a1: 1.15 }, fov: 42, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 575, rw: '34R' }, { m: 1170, rw: '34R' }],
  globe: {
    keys: [
      [3.4, 38.29, 27.16, 1.08, 960],
      [6.4, 42, 22, 13.5, 615],
      [13.5, 42, 24, 13.5, 615],
      [16.0, 39, 33, 4.6, 615],
      [22.5, 39, 34, 4.4, 615],
      [25.0, 48, 14, 5.6, 615],
      [31.5, 48, 11, 5.4, 615],
      [34.0, 33, 40, 8.5, 615],
      [40.5, 33, 42, 8.3, 615],
      [43.0, 42, 22, 13.5, 615],
      [52.0, 42, 26, 13.5, 615],
      [54.6, 36, 22, 11.0, 840],
      [60.0, 34, 10, 10.8, 840],
    ],
    views: [[6.4, 'WORLDWIDE'], [16.0, 'TÜRKİYE'], [25.0, 'EUROPE'], [34.0, 'MIDDLE EAST'], [43.0, 'WORLDWIDE']],
    worldLabels: ['STN', 'CDG', 'AMS', 'FRA', 'DXB', 'DOH', 'GYD', 'BER', 'VIE', 'HAM', 'BRU'],
    regionLabels: ['AYT', 'ADA', 'TZX', 'DIY', 'GZT', 'ASR', 'ERZ', 'VAN', 'SZF', 'MLX', 'MQM', 'GNY', 'HTY', 'KYA', 'ECN'],
    names: { SAW: 'ISTANBUL SAW', STN: 'LONDON' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const firstDep = FL.find(f => f.type === 'D' && f.t > 300);
    const lastArr = [...FL].reverse().find(f => f.type === 'A');
    const ist = FL.filter(f => ['IST', 'SAW'].includes(ROUTES[f.r].code)).length;
    return [
      { m: firstDep.t, a: 'FIRST WAVE', b: `${firstDep.fn} to ${ROUTES[firstDep.r].city}` },
      { m: 459, tm: '07:39', a: 'SUNRISE', b: 'clear skies over the Aegean' },
      { m: 640, tm: '10:40', a: 'POYRAZ WIND', b: 'northerly wind, gusts 25 kt' },
      { m: S.stats.busiest * 60 + 30, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings` },
      { m: 'pax20', a: '20,000 PASSENGERS', b: 'and counting' },
      { m: 1091, tm: '18:11', a: 'SUNSET OVER THE AEGEAN', b: 'the evening shuttle to Istanbul' },
      { m: 1300, tm: '21:40', a: 'ISTANBUL SHUTTLE', b: `${ist} flights to Istanbul today` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 342, name: 'IZMIR APPROACH',
    fixes: [{ name: 'SOUTH', brg: 172, dist: 20, hold: true }, { name: 'EAST', brg: 95, dist: 22, hold: false }, { name: 'NORTH', brg: 15, dist: 22, hold: true }, { name: 'WEST', brg: 268, dist: 18, hold: false }],
    places: [{ name: 'İZMİR', brg: 0, dist: 7 }, { name: 'MANISA', brg: 30, dist: 20 }, { name: 'EPHESUS', brg: 165, dist: 23 }, { name: 'GULF OF İZMİR', brg: 318, dist: 11 }, { name: 'AEGEAN SEA', brg: 250, dist: 24 }],
    holdRate: 18, depTurn: {}, straightOut: 3,
  },
};

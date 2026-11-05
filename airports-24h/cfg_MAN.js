// Manchester (MAN). Local frame: metres; -x = landing direction on runways 23 (true 231°), -z = right of track (terminal side).
const line = (px, pz, dx, dz, L) => [[px - dx * L, pz - dz * L], [px + dx * L, pz + dz * L]];
const NORTH = [0.629, -0.777], EAST = [0.777, 0.629];
export default {
  code: 'MAN', city: 'MANCHESTER', header: 'MANCHESTER · MAN', titleBig: 'MANCHESTER:', titleSize: 100, tz: 'GMT', utcOff: 0,
  lat: 53.3537, lon: -2.275, decl: -15.6, eot: 16.4, mistName: 'MIST',
  runways: [
    { id: '23R', z: -200, w: -1500, e: 1548, labE: '23R', labW: '05L' },
    { id: '23L', z: 190, w: -3000, e: 50, labE: '23L', labW: '05R' },
  ],
  rwyText: m => 'ARR 23R · DEP 23L',
  ground: {
    base: '#465a3c', grass: '#557146', grid: null, gridSpacing: [110, 170],
    fields: ['#4f6a40', '#5b7447', '#667a4a', '#4a6239', '#6d7f4f', '#577045'],
    house: ['#7a5a4c', '#6e5a50', '#80655a', '#5f5a55', '#746a62'],
    density(x, z) {
      if (x > -3300 && x < 1900 && z > -1150 && z < 700) return 0;               // airfield
      const n = 0.65 + 0.35 * Math.sin(x * 0.0012 + Math.sin(z * 0.0008) * 2) * Math.cos(z * 0.0010 - x * 0.0004);
      let d = 0.12;
      if (x > 2100) d = 0.88;                                                      // Wythenshawe / Heald Green
      if (z < -1500 && x > -1500 && x < 2100) d = 0.6;                             // Hale Barns / Ringway
      if (Math.hypot(x + 500, z + 4800) < 2200) d = 0.92;                          // Altrincham
      if (Math.hypot(x + 3150, z - 3900) < 1800) d = 0.85;                         // Wilmslow
      if (0.81 * x - 0.59 * z > 6000) d = 0.95;                                    // towards the city
      return d * n;
    },
    woods: [[-9000, 700, -3300, 9000, 60], [-9000, -9000, -3300, -1500, 40], [-3300, 1500, 2100, 9000, 30]],
    airfield: [[-3300, -1150, 1900, 700]],
    roads: [
      { pts: line(943, -1166, EAST[0], EAST[1], 12000), w: 42, light: 0.95 },    // M56
      { pts: [[943, -1166], [700, -1050], [500, -1000]], w: 26, light: 0.9 },      // airport spur
      { pts: line(2600, 1200, NORTH[0], NORTH[1], 9000), w: 20, light: 0.8 },     // A34 / A538
      { pts: line(6000, -2000, NORTH[0], NORTH[1], 9000), w: 38, light: 0.95 },   // M60
      { pts: [[-3300, -1150], [1900, -1150], [1900, 700], [-3300, 700], [-3300, -1150]], w: 12, light: 0.6 },
    ],
  },
  aprons: [[-500, -820, 1500, -420], [-1350, -720, -700, -430], [-2500, -460, -1800, -300]],
  taxi: [[[-1500, -390], [1600, -390]], [[-3000, 380], [50, 380]], [[-1500, -200], [-1500, -390]], [[1548, -200], [1548, -390]],
    [[-3000, 190], [-3000, 380]], [[50, 190], [50, 380]], [[-1000, 380], [-1000, -390]], [[-300, 380], [-300, -390]], [[-2200, 380], [-2200, -390]],
    [[600, -200], [420, -390]], [[-600, -200], [-780, -390]]],
  buildings: [
    [-100, -930, 300, 22, 130, 0xb6bec6], [-250, -620, 40, 14, 300, 0xbcc2c8], [100, -620, 40, 14, 300, 0xbcc2c8],
    [750, -980, 340, 24, 150, 0xc3cad1], [750, -640, 50, 16, 340, 0xc3cad1], [1000, -640, 50, 16, 300, 0xbcc2c8],
    [1300, -900, 220, 20, 110, 0xb0b8c0], [-1000, -800, 360, 18, 120, 0x9aa0a6], [-2100, -620, 260, 30, 160, 0xc0c5ca],
    [200, -1180, 200, 26, 90, 0x8e9196], [1150, -1200, 160, 30, 80, 0x8e9196],
  ],
  extraBuildings(r) { const b = []; for (let i = 0; i < 14; i++) b.push([1700 + r() * 1200, -1500 - r() * 900, 40 + r() * 40, 16 + r() * 30, 40, 0x9c968f]); return b; },
  tower: { x: 350, z: -680, h: 60 },
  landmark: 'none',
  stands: (() => { const s = [];
    for (const x of [-250, 100]) for (const z of [-720, -650, -580, -510]) { s.push([x - 50, z, 0, 0]); s.push([x + 50, z, Math.PI, 0]); }
    for (const x of [750, 1000]) for (const z of [-760, -690, -620, -550, -480]) { s.push([x - 56, z, 0, x === 750 ? 1 : 0]); s.push([x + 56, z, Math.PI, 0]); }
    for (let x = -2400; x <= -1850; x += 80) s.push([x, -380, Math.PI / 2, 0]);
    return s; })(),
  tailCols: ['#ff6600', '#d40e14', '#073590', '#e2e6ea', '#c8102e', '#1d3c78', '#00a1de', '#5c0632', '#f2a900'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 220, 12, 0, 10, 0.85, 0.35, 0],
    [240, 225, 14, 0, 9.5, 0.90, 0.55, 0],
    [420, 230, 16, 26, 9.5, 0.85, 0.45, 0],
    [560, 240, 18, 30, 10.5, 0.70, 0.15, 0],
    [700, 245, 17, 28, 12, 0.55, 0.05, 0],
    [820, 250, 18, 30, 12, 0.88, 0.75, 0],
    [900, 255, 16, 27, 11.5, 0.75, 0.30, 0],
    [1000, 260, 12, 0, 10, 0.40, 0, 0],
    [1200, 265, 9, 0, 8.5, 0.25, 0, 0],
    [1440, 270, 7, 0, 7.5, 0.30, 0, 0],
  ],
  introCam: { P0: [5200, 560, -100], P1: [4500, 470, -150], Q0: [-1000, 0, -250], Q1: [-1150, 0, -260] },
  introEvents: [{ type: 'A', t: 1.6, rw: '23R', cat: 1, wide: false }, { type: 'A', t: 3.3, rw: '23R', cat: 2, wide: true }],
  shots: [
    { t0: 5.0, t1: 12.5, name: 'CAM 1 · AERIAL', p0: [3200, 1000, 2400], p1: [2800, 880, 2100], q0: [-800, 0, -300], q1: [-950, 0, -300], fov: 42, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 12.5, t1: 19.5, name: 'CAM 2 · APPROACH 23R', p0: [1250, 34, -430], p1: [1340, 36, -435], q0: [6200, 240, -200], q1: [6200, 220, -200], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 19.5, t1: 26.5, name: 'CAM 3 · RUNWAY 23L', p0: [-1250, 40, 440], p1: [-1330, 40, 445], q0: [-2400, 75, 190], q1: [-2500, 75, 190], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 26.5, t1: 33.5, name: 'CAM 4 · TOWER VIEW', p0: [420, 80, -560], p1: [380, 80, -560], q0: [-400, 0, 4200], q1: [-480, 0, 4200], fov: 52, sc: 1.6, sf: 0.75, near: 0.9 },
    { t0: 33.5, t1: 40.5, name: 'CAM 5 · SUNSET', p0: [900, 62, -780], p1: [840, 60, -780], q0: [-5200, 30, 0], q1: [-5200, 30, 40], fov: 52, sc: 1.5, sf: 0.6, near: 1.0 },
    { t0: 40.5, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [-500, 0, -200], r: 4200, h: 1400, a0: 0.25, a1: 1.05 }, fov: 44, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 590, rw: '23R' }, { m: 1130, rw: '23R' }],
  globe: {
    keys: [
      [3.4, 53.35, -2.28, 1.08, 960],
      [6.4, 38, 6, 13.5, 615],
      [13.5, 38, 8, 13.5, 615],
      [16.0, 48, 4, 5.4, 615],
      [22.5, 47, 8, 5.2, 615],
      [25.0, 37, -6, 7.4, 615],
      [31.5, 35, -2, 7.2, 615],
      [34.0, 33, 30, 11.0, 615],
      [40.5, 31, 40, 10.8, 615],
      [43.0, 38, 4, 13.5, 615],
      [52.0, 38, 10, 13.5, 615],
      [54.6, 34, -8, 11.0, 840],
      [60.0, 32, -22, 10.8, 840],
    ],
    views: [[6.4, 'WORLDWIDE'], [16.0, 'EUROPE'], [25.0, 'SUN DESTINATIONS'], [34.0, 'MIDDLE EAST & ASIA'], [43.0, 'WORLDWIDE']],
    worldLabels: ['JFK', 'MCO', 'BGI', 'CUN', 'YYZ', 'DXB', 'DOH', 'SIN', 'HKG', 'ISB', 'ADD', 'IST', 'HRG', 'KEF'],
    regionLabels: ['CDG', 'FRA', 'MUC', 'ZRH', 'GVA', 'CPH', 'BER', 'BUD', 'KRK', 'BCN', 'MAD', 'LIS', 'FCO', 'MXP', 'PMI', 'OSL', 'ATH', 'FAO'],
    names: { JFK: 'NEW YORK', LHR: 'LONDON', MCO: 'ORLANDO', AGP: 'MALAGA', SAW: 'ISTANBUL SAW' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const wave = FL.filter(f => f.type === 'D' && f.t >= 360 && f.t < 420).length;
    const atl = FL.filter(f => f.type === 'D' && ROUTES[f.r].lon < -30).length;
    const lastDep = [...FL].reverse().find(f => f.type === 'D');
    return [
      { m: 362, tm: '06:00', a: 'THE 6AM WAVE', b: `${wave} departures in the first hour` },
      { m: 433, tm: '07:13', a: 'SUNRISE', b: 'rain sweeping in from the south-west' },
      { m: S.stats.busiest * 60 + 70, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings` },
      { m: 660, tm: '11:00', a: 'TRANSATLANTIC', b: `${atl} flights to the USA, Canada and the Caribbean` },
      { m: 820, tm: '13:40', a: 'MANCHESTER RAIN', b: 'a squall sweeps across the runways, gusts 30 kt' },
      { m: 995, tm: '16:35', a: 'SUNSET', b: 'skies clear behind the last shower' },
      { m: lastDep.t, a: 'LAST DEPARTURE', b: `${lastDep.fn} to ${ROUTES[lastDep.r].city}` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 231, name: 'MANCHESTER RADAR',
    fixes: [{ name: 'DAYNE', brg: 150, dist: 20, hold: true }, { name: 'ROSUN', brg: 10, dist: 22, hold: true }, { name: 'MIRSI', brg: 255, dist: 20, hold: true }, { name: 'EAST', brg: 75, dist: 20, hold: false }],
    places: [{ name: 'MANCHESTER', brg: 15, dist: 8 }, { name: 'LIVERPOOL', brg: 285, dist: 26 }, { name: 'WARRINGTON', brg: 285, dist: 13 }, { name: 'STOKE', brg: 170, dist: 22 }, { name: 'PEAK DISTRICT', brg: 105, dist: 15 }, { name: 'CHESTER', brg: 245, dist: 27 }],
    holdRate: 34, depTurn: {}, straightOut: 3,
  },
};

// Liverpool John Lennon (LPL). Local frame: metres; -x = landing direction on runway 27 (true 267°), +z = south (the River Mersey).
const mersey = [[12000, 3200], [6000, 1800], [2000, 820], [-2000, 650], [-5000, 300], [-6800, -1500], [-7600, -5000], [-8200, -9000], [-9000, -12000],
  [-12000, -12000], [-10000, -9000], [-9500, -5000], [-8800, -1000], [-7000, 2500], [-3000, 3600], [2000, 3300], [6000, 3700], [12000, 4800]];
export default {
  code: 'LPL', city: 'LIVERPOOL', header: 'LIVERPOOL · LPL', titleBig: 'LIVERPOOL:', titleSize: 108, tz: 'GMT', utcOff: 0,
  lat: 53.3336, lon: -2.8497, decl: -16.0, eot: 16.4, mistName: 'MIST', insetRate: 3.0,
  runways: [{ id: '27', z: 0, w: -1100, e: 1185, labE: '27', labW: '09' }],
  rwyText: m => 'RWY 27 · ARR + DEP',
  ground: {
    base: '#465a3c', grass: '#557146', grid: null, gridSpacing: [100, 160],
    fields: ['#4f6a40', '#5b7447', '#667a4a', '#4a6239', '#6d7f4f'],
    house: ['#7a5a4c', '#6e5a50', '#80655a', '#5f5a55', '#746a62'],
    density(x, z) {
      if (x > -1600 && x < 1700 && z > -700 && z < 600) return 0;                  // airfield
      // inside the Mersey?
      let inside = false; for (let i = 0, j = mersey.length - 1; i < mersey.length; j = i++) { const [xi, zi] = mersey[i], [xj, zj] = mersey[j]; if (((zi > z) !== (zj > z)) && (x < (xj - xi) * (z - zi) / (zj - zi) + xi)) inside = !inside; }
      if (inside) return 0;
      const n = 0.65 + 0.35 * Math.sin(x * 0.0012 + Math.sin(z * 0.0008) * 2) * Math.cos(z * 0.0010 - x * 0.0004);
      let d = 0.15;
      if (z < -900) d = 0.85;                                                       // Speke / Halewood
      if (x < -3500 && z < -1500) d = 0.95;                                         // Liverpool
      if (x > 2200 && z > -900 && z < 1600) d = 0.25;                               // Hale
      if (z > 3500) d = 0.7;                                                        // Wirral / Ellesmere Port
      if (x > 6500 && z > -1000 && z < 3000) d = 0.85;                              // Widnes / Runcorn
      return d * n;
    },
    water: [mersey],
    ocean: { poly: mersey },
    industry: [[-1200, 4000, 2200, 5400], [7000, -800, 9000, 1200]],                  // Stanlow refinery, Widnes works
    sand: [[[-5000, 300], [-2000, 650], [2000, 820], [6000, 1800], [6000, 1550], [2000, 640], [-2000, 520], [-5000, 180]]],
    airfield: [[-1600, -700, 1700, 600]],
    roads: [
      { pts: [[-9000, -1300], [-3000, -1300], [3000, -1250], [9000, -1500]], w: 30, light: 0.95 },    // A561 Speke Boulevard
      { pts: [[300, -1300], [500, -800], [650, -560]], w: 20, light: 0.9 },                             // airport access
      { pts: [[7800, -3000], [7900, 1000], [8100, 3800], [8300, 7000]], w: 30, light: 1.0 },            // Mersey Gateway bridge
      { pts: [[-9000, 5200], [-3000, 4400], [3000, 4300], [9000, 5200]], w: 36, light: 0.95 },          // M53 / M56 across the river
      { pts: [[-1600, -700], [1700, -700], [1700, 600], [-1600, 600], [-1600, -700]], w: 12, light: 0.6 },
    ],
  },
  aprons: [[-250, -520, 1050, -260], [-2700, -1100, -2100, -800]],
  taxi: [[[-1100, -200], [1185, -200]], [[-1100, 0], [-1100, -200]], [[1185, 0], [1185, -200]], [[0, 0], [-160, -200]], [[600, 0], [440, -200]]],
  buildings: [
    [550, -560, 360, 18, 90, 0xbfc6cd], [200, -470, 40, 12, 120, 0xbcc2c8], [-150, -600, 200, 26, 90, 0xc0c5ca],
    [-2400, -1150, 260, 14, 70, 0xd8d0bc], [-2400, -1000, 60, 22, 30, 0xd8d0bc],   // the old 1930s terminal (now a hotel)
    [1250, -700, 160, 14, 90, 0x8e9196],
  ],
  extraBuildings(r) { const b = []; for (let i = 0; i < 10; i++) b.push([-1200 + r() * 2400, -1600 - r() * 600, 50 + r() * 50, 14 + r() * 16, 50, 0x9c968f]); return b; },
  tower: { x: 40, z: -560, h: 38 },
  landmark: 'yellowSub', sub: { x: 760, z: -860, rot: 0.35 },
  stands: (() => { const s = []; for (let x = -150; x <= 1000; x += 72) s.push([x, -330, Math.PI / 2, 0]); return s; })(),
  tailCols: ['#ff6600', '#ff6600', '#073590', '#073590', '#c6007e', '#e2e6ea', '#f2a900'],
  //   min  dir  kt gust temp cloud rain mist
  wx: [
    [0, 250, 10, 0, 10, 0.50, 0.10, 0],
    [300, 255, 12, 0, 9.5, 0.40, 0, 0],
    [480, 260, 15, 24, 10, 0.35, 0, 0],
    [660, 265, 20, 34, 11.5, 0.50, 0.10, 0],
    [780, 270, 22, 38, 11.5, 0.60, 0.20, 0],
    [900, 275, 20, 34, 11, 0.90, 0.75, 0],
    [980, 285, 15, 25, 10, 0.60, 0.20, 0],
    [1080, 295, 10, 0, 9, 0.30, 0, 0],
    [1440, 300, 6, 0, 7.5, 0.20, 0, 0],
  ],
  introCam: { P0: [5200, 520, 1500], P1: [4500, 440, 1350], Q0: [-1000, 0, -150], Q1: [-1150, 0, -160] },
  introEvents: [{ type: 'A', t: 1.6, rw: '27', cat: 1, wide: false }, { type: 'A', t: 3.3, rw: '27', cat: 0, wide: false }],
  shots: [
    { t0: 5.0, t1: 12.5, name: 'CAM 1 · OVER THE MERSEY', p0: [2600, 900, 3400], p1: [2300, 800, 3100], q0: [-800, 0, -200], q1: [-900, 0, -220], fov: 44, sc: 2.4, sf: 1.0, near: 0.6 },
    { t0: 12.5, t1: 19.5, name: 'CAM 2 · APPROACH 27', p0: [900, 30, -240], p1: [980, 32, -245], q0: [6000, 230, 0], q1: [6000, 210, 0], fov: 44, sc: 1.35, sf: 0.4, near: 1.25 },
    { t0: 19.5, t1: 26.5, name: 'CAM 3 · MERSEY SHORE', p0: [-300, 24, 560], p1: [-380, 24, 565], q0: [-1300, 70, 0], q1: [-1400, 70, 0], fov: 48, sc: 1.6, sf: 0.5, near: 1.2 },
    { t0: 26.5, t1: 33.5, name: 'CAM 4 · YELLOW SUBMARINE', p0: [840, 13, -985], p1: [800, 13, -990], q0: [450, 45, 300], q1: [380, 45, 300], fov: 52, sc: 1.6, sf: 0.75, near: 0.9 },
    { t0: 33.5, t1: 40.5, name: 'CAM 5 · SUNSET OVER THE MERSEY', p0: [700, 55, -460], p1: [640, 54, -460], q0: [-5000, 20, 3600], q1: [-5060, 20, 3600], fov: 52, sc: 1.5, sf: 0.6, near: 1.0 },
    { t0: 40.5, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: { c: [0, 0, 200], r: 3600, h: 1200, a0: 0.3, a1: 1.1 }, fov: 44, sc: 2.5, sf: 1.0, near: 0.6 },
  ],
  goArounds: [{ m: 600, rw: '27' }, { m: 1150, rw: '27' }],
  globe: {
    keys: [
      [3.4, 53.33, -2.85, 1.08, 960],
      [6.4, 40, 4, 13.5, 615],
      [13.5, 40, 6, 13.5, 615],
      [16.0, 49, 4, 5.2, 615],
      [22.5, 48, 7, 5.0, 615],
      [25.0, 37, -6, 7.4, 615],
      [31.5, 35, -2, 7.2, 615],
      [34.0, 50, 18, 5.0, 615],
      [40.5, 49, 21, 4.9, 615],
      [43.0, 40, 4, 13.5, 615],
      [52.0, 40, 10, 13.5, 615],
      [54.6, 36, -6, 11.0, 840],
      [60.0, 34, -20, 10.8, 840],
    ],
    views: [[6.4, 'WORLDWIDE'], [16.0, 'EUROPE'], [25.0, 'SUN DESTINATIONS'], [34.0, 'CENTRAL & EASTERN EUROPE'], [43.0, 'WORLDWIDE']],
    worldLabels: ['TFS', 'HRG', 'PFO', 'RAK', 'LIS', 'FCO', 'OTP', 'AGP', 'DUB'],
    regionLabels: ['AMS', 'CDG', 'GVA', 'BER', 'KRK', 'GDN', 'WAW', 'BUD', 'SOF', 'RIX', 'VNO', 'PRG', 'BGY', 'PSA', 'MAD', 'PMI', 'FAO', 'CLJ', 'IOM', 'BFS'],
    names: { AGP: 'MALAGA', BGY: 'MILAN', NOC: 'KNOCK' },
  },
  toasts(FL, ROUTES, S, hhmm, pad2) {
    const lastDep = [...FL].reverse().find(f => f.type === 'D');
    const firstDep = FL.find(f => f.type === 'D');
    return [
      { m: firstDep.t, a: 'FIRST DEPARTURE', b: `${firstDep.fn} to ${ROUTES[firstDep.r].city}` },
      { m: 440, tm: '07:20', a: 'SUNRISE', b: 'bright and breezy over the Mersey' },
      { m: 660, tm: '11:00', a: 'ABOVE US ONLY SKY', b: "the airport's motto, from John Lennon's Imagine" },
      { m: 780, tm: '13:00', a: 'GALE ON THE MERSEY', b: 'westerly gusts up to 38 kt' },
      { m: 900, tm: '15:00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings` },
      { m: 985, tm: '16:25', a: 'SUNSET OVER THE MERSEY', b: 'skies clear behind the squall' },
      { m: lastDep.t, a: 'LAST DEPARTURE', b: `${lastDep.fn} to ${ROUTES[lastDep.r].city}` },
    ];
  },
  radar: {
    range: 30, rwyTrue: 267, name: 'LIVERPOOL RADAR',
    fixes: [{ name: 'EAST', brg: 95, dist: 18, hold: true }, { name: 'NORTH', brg: 15, dist: 20, hold: true }, { name: 'WEST', brg: 285, dist: 18, hold: false }, { name: 'SOUTH', brg: 185, dist: 18, hold: false }],
    places: [{ name: 'LIVERPOOL', brg: 305, dist: 6 }, { name: 'MANCHESTER', brg: 78, dist: 22 }, { name: 'CHESTER', brg: 205, dist: 13 }, { name: 'LIVERPOOL BAY', brg: 305, dist: 20 }, { name: 'WIRRAL', brg: 260, dist: 9 }, { name: 'SOUTHPORT', brg: 345, dist: 21 }],
    holdRate: 999, depTurn: {}, straightOut: 3,
  },
};

// ================================================================== AIRPORT
const sceneA = new THREE.Scene();
const camA = new THREE.PerspectiveCamera(40, 426 / 350, 5, 90000);
const GS = 20000;
const RW = {}; for (const r of AP.runways) RW[r.id] = { z: r.z, e: r.e, w: r.w, len: r.e - r.w, labE: r.labE, labW: r.labW };
const APRONS = AP.aprons, TAXI = AP.taxi, G0 = AP.ground;
const density = G0.density;
const RES = G0.reservoirs || [];

const STREET = [], MWAY = [];
function makeGround() {
  const GT = 4096, GE = 2048;
  const c = document.createElement('canvas'); c.width = c.height = GT; const g = c.getContext('2d');
  const e = document.createElement('canvas'); e.width = e.height = GE; const ge = e.getContext('2d');
  const P = v => (v + GS / 2) / GS * GT, PE = v => (v + GS / 2) / GS * GE, M = v => v / GS * GT, ME = v => v / GS * GE;
  const r = rng(42);
  g.fillStyle = G0.base; g.fillRect(0, 0, GT, GT);
  ge.fillStyle = '#000'; ge.fillRect(0, 0, GE, GE);
  // fields
  for (let i = 0; i < 1400; i++) {
    const x = (r() - 0.5) * GS, z = (r() - 0.5) * GS; const w = 150 + r() * 500, h = 120 + r() * 400;
    const d = density(x, z); if (d > 0.5 && r() < 0.8) continue;
    { const fc = G0.fields || ['#4a6340', '#556d45', '#5d7348', '#475b3d', '#62754c']; g.fillStyle = fc[r() * fc.length | 0]; }
    g.save(); g.translate(P(x), P(z)); g.rotate((r() - 0.5) * 0.5); g.fillRect(-M(w) / 2, -M(h) / 2, M(w), M(h)); g.restore();
  }
  // suburban street grids
  for (let tx = -GS / 2; tx < GS / 2; tx += 900) for (let tz = -GS / 2; tz < GS / 2; tz += 900) {
    const d = density(tx + 450, tz + 450); if (d < 0.2) continue;
    const ang = G0.grid != null ? G0.grid + (r() - 0.5) * G0.gridJitter : (r() - 0.5) * 0.9, sp = G0.gridSpacing ? G0.gridSpacing[0] + r() * (G0.gridSpacing[1] - G0.gridSpacing[0]) : 110 + r() * 80;
    g.save(); g.translate(P(tx + 450), P(tz + 450)); g.rotate(ang);
    ge.save(); ge.translate(PE(tx + 450), PE(tz + 450)); ge.rotate(ang);
    // houses
    const nh = Math.round(d * 260);
    for (let k = 0; k < nh; k++) {
      const hx = (r() - 0.5) * 900, hz = (r() - 0.5) * 900;
      if (density(tx + 450 + hx, tz + 450 + hz) < 0.15) continue;
      { const hc = G0.house || ['#5d5f60', '#6c6158', '#575a55', '#74695f', '#4f5a4b', '#646a6d']; g.fillStyle = hc[r() * hc.length | 0]; }
      g.fillRect(M(hx), M(hz), M(10 + r() * 14), M(8 + r() * 12));
      if (r() < 0.55) { ge.fillStyle = `rgba(255,${170 + r() * 60 | 0},${90 + r() * 60 | 0},${0.35 + r() * 0.5})`; ge.fillRect(ME(hx), ME(hz), 1, 1); }
    }
    g.strokeStyle = 'rgba(120,124,128,0.75)'; g.lineWidth = 1.6;
    ge.strokeStyle = 'rgba(255,170,80,0.55)'; ge.lineWidth = 0.8; ge.setLineDash([0.8, 2.2]);
    for (let s = -450; s <= 450; s += sp) {
      g.beginPath(); g.moveTo(M(-450), M(s)); g.lineTo(M(450), M(s)); g.moveTo(M(s), M(-450)); g.lineTo(M(s), M(450)); g.stroke();
      ge.beginPath(); ge.moveTo(ME(-450), ME(s)); ge.lineTo(ME(450), ME(s)); ge.moveTo(ME(s), ME(-450)); ge.lineTo(ME(s), ME(450)); ge.stroke();
    }
    ge.setLineDash([]);
    g.restore(); ge.restore();
    const ca = Math.cos(ang), sa = Math.sin(ang), cx = tx + 450, cz = tz + 450;
    for (let s2 = -450; s2 <= 450; s2 += sp) for (let q = -450; q <= 450; q += 62) {
      for (const [lx, lz] of [[q, s2], [s2, q]]) {
        const wx = cx + lx * ca - lz * sa, wz = cz + lx * sa + lz * ca;
        if (density(wx, wz) > 0.12) STREET.push(wx, wz);
      }
    }
  }
  // reservoirs
  for (const [x, z, w, h] of RES) {
    g.fillStyle = '#7e8f86'; rr(g, P(x) - M(w) / 2 - 4, P(z) - M(h) / 2 - 4, M(w) + 8, M(h) + 8, M(140));
    g.fillStyle = '#21405a'; rr(g, P(x) - M(w) / 2, P(z) - M(h) / 2, M(w), M(h), M(120));
  }
  const poly = (ctx, pts, F) => { ctx.beginPath(); pts.forEach(([x, z], i) => i ? ctx.lineTo(F(x), F(z)) : ctx.moveTo(F(x), F(z))); ctx.closePath(); ctx.fill(); };
  for (const p of G0.water || []) { g.fillStyle = '#0d2a40'; poly(g, p, P); ge.fillStyle = '#000'; poly(ge, p, PE); }
  for (const p of G0.sand || []) { g.fillStyle = '#b4a483'; poly(g, p, P); }
  for (const [x0, z0, x1, z1] of G0.industry || []) {
    g.fillStyle = '#56585b'; g.fillRect(P(x0), P(z0), M(x1 - x0), M(z1 - z0));
    for (let i = 0; i < 260; i++) { const x = lerp(x0, x1, r()), z = lerp(z0, z1, r()); g.fillStyle = r() < 0.5 ? '#8a8d90' : '#6b6e72'; g.fillRect(P(x), P(z), M(15 + r() * 40), M(15 + r() * 40)); if (r() < 0.7) STREET.push(x, z); }
    ge.fillStyle = 'rgba(255,235,190,0.35)'; ge.fillRect(PE(x0), PE(z0), ME(x1 - x0), ME(z1 - z0));
  }
  for (const [x0, z0, x1, z1, n] of G0.woods || []) for (let i = 0; i < n; i++) { const x = lerp(x0, x1, r()), z = lerp(z0, z1, r()); g.fillStyle = r() < 0.5 ? '#2f4a2c' : '#38532f'; g.beginPath(); g.ellipse(P(x), P(z), M(40 + r() * 120), M(30 + r() * 90), r() * 3, 0, 6.283); g.fill(); }
  // motorways & roads
  const road = (pts, wd, lightA) => {
    g.strokeStyle = '#7a7e81'; g.lineWidth = M(wd); g.lineCap = 'round';
    g.beginPath(); pts.forEach(([x, z], i) => i ? g.lineTo(P(x), P(z)) : g.moveTo(P(x), P(z))); g.stroke();
    ge.strokeStyle = `rgba(255,178,90,${lightA})`; ge.lineWidth = Math.max(1.2, ME(wd) * 0.7);
    ge.beginPath(); pts.forEach(([x, z], i) => i ? ge.lineTo(PE(x), PE(z)) : ge.moveTo(PE(x), PE(z))); ge.stroke();
    for (let i = 1; i < pts.length; i++) { const [x0, z0] = pts[i - 1], [x1, z1] = pts[i]; const L = Math.hypot(x1 - x0, z1 - z0); for (let d = 0; d < L; d += 45) { const u = d / L; MWAY.push(lerp(x0, x1, u), lerp(z0, z1, u)); } }
  };
  for (const rd of G0.roads) road(rd.pts, rd.w, rd.light);
  // airport grass
  for (const [x0, z0, x1, z1] of G0.airfield) {
    g.fillStyle = G0.grass || '#4f6b44'; g.fillRect(P(x0), P(z0), M(x1 - x0), M(z1 - z0));
    for (let i = 0; i < 300; i++) { g.fillStyle = `rgba(${70 + r() * 30},${100 + r() * 30},${60 + r() * 20},0.25)`; g.fillRect(P(lerp(x0, x1, r())), P(lerp(z0, z1, r())), M(60 + r() * 300), M(40 + r() * 200)); }
  }
  // aprons
  for (const [x0, z0, x1, z1] of APRONS) {
    g.fillStyle = '#8d9297'; g.fillRect(P(x0), P(z0), M(x1 - x0), M(z1 - z0));
    const gr = ge.createRadialGradient(PE((x0 + x1) / 2), PE((z0 + z1) / 2), 0, PE((x0 + x1) / 2), PE((z0 + z1) / 2), ME(Math.max(x1 - x0, z1 - z0) * 0.7));
    gr.addColorStop(0, 'rgba(255,236,190,0.55)'); gr.addColorStop(1, 'rgba(255,220,160,0.0)');
    ge.fillStyle = gr; ge.fillRect(PE(x0) - 40, PE(z0) - 40, ME(x1 - x0) + 80, ME(z1 - z0) + 80);
    g.strokeStyle = 'rgba(230,200,80,0.6)'; g.lineWidth = 1;
    for (let x = x0 + 40; x < x1; x += 70) { g.beginPath(); g.moveTo(P(x), P(z0 + 10)); g.lineTo(P(x), P(z0 + 90)); g.stroke(); }
  }
  // taxiways
  for (const pl of TAXI) {
    g.strokeStyle = '#555a60'; g.lineWidth = M(26); g.lineCap = 'round';
    g.beginPath(); pl.forEach(([x, z], i) => i ? g.lineTo(P(x), P(z)) : g.moveTo(P(x), P(z))); g.stroke();
    g.strokeStyle = 'rgba(225,195,70,0.85)'; g.lineWidth = 1;
    g.beginPath(); pl.forEach(([x, z], i) => i ? g.lineTo(P(x), P(z)) : g.moveTo(P(x), P(z))); g.stroke();
  }
  // runway shoulders / strips
  for (const k in RW) { const R = RW[k]; g.fillStyle = '#5b7a4d'; g.fillRect(P(R.w - 60), P(R.z - 150), M(R.len + 120), M(300)); g.fillStyle = '#4b4f54'; g.fillRect(P(R.w - 30), P(R.z - 38), M(R.len + 60), M(76)); }
  const tex = canvasTex(c); tex.generateMipmaps = true;
  const etex = canvasTex(e);
  return { tex, etex };
}
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); g.fill(); }

const ground = makeGround();
const streetGeo = pointsGeo(STREET.length / 2 + MWAY.length / 2);
{ const r = rng(55); let i = 0;
  for (let k = 0; k < STREET.length; k += 2, i++) { streetGeo.attributes.position.setXYZ(i, STREET[k], 6, STREET[k + 1]); streetGeo.attributes.acol.setXYZ(i, 1, 0.62 + r() * 0.15, 0.30 + r() * 0.12); streetGeo.attributes.size.setX(i, 7 + r() * 3); streetGeo.attributes.alpha.setX(i, 0.35 + r() * 0.4); }
  for (let k = 0; k < MWAY.length; k += 2, i++) { streetGeo.attributes.position.setXYZ(i, MWAY[k], 10, MWAY[k + 1]); streetGeo.attributes.acol.setXYZ(i, 1, 0.75, 0.45); streetGeo.attributes.size.setX(i, 11); streetGeo.attributes.alpha.setX(i, 0.9); } }
const streetMat = glowMat(false);
const streetPts = new THREE.Points(streetGeo, streetMat); streetPts.frustumCulled = false; sceneA.add(streetPts);
const groundMat = new THREE.MeshLambertMaterial({ map: ground.tex, emissiveMap: ground.etex, emissive: 0xffffff, emissiveIntensity: 0 });
{ const pg = new THREE.PlaneGeometry(GS, GS); pg.rotateX(-Math.PI / 2); sceneA.add(new THREE.Mesh(pg, groundMat)); }
// far ground ring (beyond texture)
{ const pg = new THREE.RingGeometry(GS * 0.7, 90000, 64, 1); pg.rotateX(-Math.PI / 2); const m = new THREE.Mesh(pg, new THREE.MeshLambertMaterial({ color: G0.farColor || 0x39463a, emissive: 0x3a2a18, emissiveIntensity: 0 })); m.position.y = -2; sceneA.add(m); sceneA.userData.far = m; }
let oceanMat = null;
if (G0.ocean) { const sh = new THREE.Shape(G0.ocean.poly.map(([x, z]) => new THREE.Vector2(x, -z))); const og = new THREE.ShapeGeometry(sh); og.rotateX(-Math.PI / 2);
  oceanMat = new THREE.MeshPhongMaterial({ color: 0x0b2a44, specular: 0xffe6c0, shininess: 70, emissive: 0x020812 }); const om = new THREE.Mesh(og, oceanMat); om.position.y = 0.6; sceneA.add(om); }

function runwayTex(len, labE, labW) {
  const c = document.createElement('canvas'); c.width = 4096; c.height = 64; const g = c.getContext('2d');
  const sx = 4096 / len, sy = 64 / 60;
  g.fillStyle = '#2d3035'; g.fillRect(0, 0, 4096, 64);
  const r = rng(len); for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.12})`; g.fillRect(r() * 4096, 5 + r() * 54, 8 + r() * 60, 1 + r() * 3); }
  for (const x0 of [300 * sx, (len - 900) * sx]) { g.fillStyle = 'rgba(10,10,10,0.35)'; g.fillRect(x0, 20, 600 * sx, 24); }
  g.fillStyle = '#e8ebee';
  g.fillRect(0, 4, 4096, 1.6); g.fillRect(0, 58.4, 4096, 1.6);
  for (let x = 120; x < len - 120; x += 50) g.fillRect(x * sx, 31, 30 * sx, 1.8);
  for (const end of [0, 1]) {
    for (let k = 0; k < 8; k++) { const y = 8 + k * 3.2 + (k >= 4 ? 16 : 0); const x = end ? (len - 8 - 45) * sx : 8 * sx; g.fillRect(x, y, 45 * sx, 1.9); }
    for (const d of [150, 300, 450, 600]) { const x = end ? (len - d - 22) * sx : d * sx; g.fillRect(x, 20, 22 * sx, 2.5); g.fillRect(x, 42, 22 * sx, 2.5); }
    const ax = end ? (len - 400 - 60) * sx : 400 * sx; g.fillRect(ax, 16, 60 * sx, 6); g.fillRect(ax, 42, 60 * sx, 6);
  }
  g.font = 'bold 22px Inter'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.save(); g.translate((len - 75) * sx, 32); g.rotate(Math.PI / 2); g.fillText(labE, 0, 0); g.restore();
  g.save(); g.translate(75 * sx, 32); g.rotate(-Math.PI / 2); g.fillText(labW, 0, 0); g.restore();
  const t = canvasTex(c); return t;
}
for (const k in RW) {
  const R = RW[k]; const pg = new THREE.PlaneGeometry(R.len, 60); pg.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(pg, new THREE.MeshLambertMaterial({ map: runwayTex(R.len, R.labE, R.labW) }));
  m.position.set((R.e + R.w) / 2, 0.5, R.z); sceneA.add(m);
}

// ---- lights
const LT = []; // {x,y,z,c:[r,g,b],s,kind}
function addL(x, y, z, c, s, kind = 0) { LT.push({ x, y, z, c, s, kind }); }
const WH = [1, 0.95, 0.85], GR = [0.25, 1, 0.45], RD = [1, 0.18, 0.15], BL = [0.3, 0.5, 1], AM = [1, 0.8, 0.45];
for (const k in RW) {
  const R = RW[k];
  for (let x = R.w; x <= R.e; x += 60) { addL(x, 1, R.z - 31, WH, 10); addL(x, 1, R.z + 31, WH, 10); }
  for (let x = R.w + 15; x < R.e; x += 30) addL(x, 0.8, R.z, (R.e - x < 300 || x - R.w < 300) ? RD : WH, 7);
  for (let s = -28; s <= 28; s += 5) { addL(R.e + 2, 1, R.z + s, GR, 11); addL(R.w - 2, 1, R.z + s, GR, 11); addL(R.e - 4, 1, R.z + s, RD, 7); addL(R.w + 4, 1, R.z + s, RD, 7); }
  for (const [side, dir] of [[R.e, 1], [R.w, -1]]) {
    for (let d = 30; d <= 900; d += 30) {
      const x = side + dir * d;
      for (let s = -8; s <= 8; s += 4) addL(x, 2 + d * 0.01, R.z + s, WH, 12, 2);
      if (d === 300) for (let s = -30; s <= 30; s += 5) addL(x, 3, R.z + s, WH, 12, 2);
      addL(x, 4 + d * 0.01, R.z, WH, 26, 3); LT[LT.length - 1].ref = side; // sequenced flasher
    }
  }
}
for (const pl of TAXI) for (let i = 1; i < pl.length; i++) {
  const [x0, z0] = pl[i - 1], [x1, z1] = pl[i]; const L = Math.hypot(x1 - x0, z1 - z0);
  for (let d = 0; d < L; d += 40) { const u = d / L; addL(lerp(x0, x1, u), 0.6, lerp(z0, z1, u), GR, 5.5); }
  for (let d = 20; d < L; d += 90) { const u = d / L; const nx = -(z1 - z0) / L * 16, nz = (x1 - x0) / L * 16; addL(lerp(x0, x1, u) + nx, 0.6, lerp(z0, z1, u) + nz, BL, 5.5); }
}
for (const [x0, z0, x1, z1] of APRONS) for (let x = x0; x <= x1; x += 130) { addL(x, 28, z0, AM, 34, 1); addL(x, 28, z1, AM, 34, 1); }
const ltGeo = pointsGeo(LT.length);
LT.forEach((l, i) => { ltGeo.attributes.position.setXYZ(i, l.x, l.y, l.z); ltGeo.attributes.acol.setXYZ(i, ...l.c); ltGeo.attributes.size.setX(i, l.s); ltGeo.attributes.alpha.setX(i, 1); });
const ltMat = glowMat(false);
const ltPts = new THREE.Points(ltGeo, ltMat); ltPts.frustumCulled = false; sceneA.add(ltPts);


// night light haze over the aprons
const HAZE = [];
{ const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,214,160,0.55)'); gr.addColorStop(0.4, 'rgba(255,190,130,0.18)'); gr.addColorStop(1, 'rgba(255,170,110,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const ht = canvasTex(c);
  for (const [x0, z0, x1, z1] of APRONS) { const m = new THREE.SpriteMaterial({ map: ht, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0, fog: false }); const s = new THREE.Sprite(m); const w = Math.max(x1 - x0, z1 - z0) * 1.6; s.scale.set(w, w * 0.45, 1); s.position.set((x0 + x1) / 2, 60, (z0 + z1) / 2); sceneA.add(s); HAZE.push(s); } }
// ---- buildings
const winC = document.createElement('canvas'); winC.width = 64; winC.height = 64;
{ const g = winC.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 64, 64); const r = rng(3);
  for (let row = 0; row < 4; row++) for (let col = 0; col < 8; col++) { const b = r(); if (b < 0.15) continue; g.fillStyle = `rgba(255,${225 + r() * 25 | 0},${185 + r() * 50 | 0},${0.45 + b * 0.55})`; g.fillRect(col * 8, row * 16 + 6, 8, 4); } }
const winTex = canvasTex(winC); winTex.wrapS = winTex.wrapT = THREE.RepeatWrapping;
const roofMat = new THREE.MeshLambertMaterial({ color: 0x9aa1a8 });
const bMats = {};
function bMat(col, glass) {
  const k = col + (glass ? 'g' : '');
  if (!bMats[k]) bMats[k] = new THREE.MeshLambertMaterial({ color: col, emissive: 0xffd9a0, emissiveMap: winTex, emissiveIntensity: 0 });
  return bMats[k];
}
function building(x, z, sx, sy, sz, col = 0xa9b0b8, ry = 0) {
  const g = new THREE.BoxGeometry(sx, sy, sz);
  const uv = g.attributes.uv;
  for (let f = 0; f < 6; f++) {
    const wdt = f < 2 ? sz : f < 4 ? 0 : sx;
    for (let v = 0; v < 4; v++) { const i = f * 4 + v; if (f === 2 || f === 3) uv.setXY(i, 0.01, 0.01); else uv.setXY(i, uv.getX(i) * wdt / 16, uv.getY(i) * sy / 16); }
  }
  const m = bMat(col);
  const mesh = new THREE.Mesh(g, [m, m, roofMat, roofMat, m, m]);
  mesh.position.set(x, sy / 2, z); mesh.rotation.y = ry; sceneA.add(mesh); return mesh;
}
for (const b of AP.buildings) building(...b);
{ const r = rng(77); for (const b of (AP.extraBuildings ? AP.extraBuildings(r) : [])) building(...b); }
// control tower
{ const T = AP.tower; const s = new THREE.Mesh(new THREE.CylinderGeometry(5, 7, T.h, 16), new THREE.MeshLambertMaterial({ color: 0xc9ced3 })); s.position.set(T.x, T.h / 2, T.z); sceneA.add(s);
  const cab = new THREE.Mesh(new THREE.CylinderGeometry(15, 11, 11, 20), new THREE.MeshLambertMaterial({ color: 0x5c6f80, emissive: 0x9fd0ff, emissiveIntensity: 0 })); cab.position.set(T.x, T.h + 4, T.z); sceneA.add(cab); sceneA.userData.cab = cab;
  addL(T.x, T.h + 15, T.z, RD, 14, 4); }
// ---- aircraft geometry
function airliner() {
  const col = (g, c) => { g = g.index ? g.toNonIndexed() : g; const n = g.attributes.position.count; const a = new Float32Array(n * 3); const cc = new THREE.Color(c); for (let i = 0; i < n; i++) { a[i * 3] = cc.r; a[i * 3 + 1] = cc.g; a[i * 3 + 2] = cc.b; } g.setAttribute('color', new THREE.BufferAttribute(a, 3)); return g; };
  const prof = [[0, -18.8], [0.4, -18.5], [1.0, -16.2], [1.6, -13.2], [1.97, -9.5], [2.0, -6], [2.0, 12.5], [1.86, 15], [1.45, 16.9], [0.85, 18.1], [0.3, 18.7], [0.01, 18.85]];
  const fus = new THREE.LatheGeometry(prof.map(p => new THREE.Vector2(p[0], p[1])), 14); fus.rotateZ(-Math.PI / 2);
  const flat = (pts, depth) => { const s = new THREE.Shape(pts.map(p => new THREE.Vector2(p[0], p[1]))); return new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false }); };
  const wing = flat([[4.5, 1.6], [-7.6, 17.6], [-9.9, 17.6], [-5.2, 1.6], [-5.2, -1.6], [-9.9, -17.6], [-7.6, -17.6], [4.5, -1.6]], 0.5); wing.rotateX(Math.PI / 2); wing.translate(0, -0.7, 0);
  const stab = flat([[-14.2, 0.4], [-17.4, 6.4], [-18.7, 6.4], [-17.8, 0.4], [-17.8, -0.4], [-18.7, -6.4], [-17.4, -6.4], [-14.2, -0.4]], 0.35); stab.rotateX(Math.PI / 2); stab.translate(0, 1.0, 0);
  const eng = () => { const e = new THREE.CylinderGeometry(1.0, 0.85, 4.4, 14); e.rotateZ(-Math.PI / 2); return e; };
  const e1 = eng(); e1.translate(1.6, -1.9, 5.8); const e2 = eng(); e2.translate(1.6, -1.9, -5.8);
  const body = mergeGeometries([col(fus, '#f3f5f8'), col(wing, '#aab3bd'), col(stab, '#b5bdc6'), col(e1, '#c9ced6'), col(e2, '#c9ced6')], false);
  body.computeVertexNormals();
  const fin = flat([[-11.6, 1.2], [-16.4, 8.3], [-18.6, 8.3], [-18.7, 1.2]], 0.45); fin.translate(0, 0, -0.22);
  const tail = fin.toNonIndexed(); tail.computeVertexNormals();
  return { body, tail };
}
const AC = airliner();
const bodyMatShared = new THREE.MeshLambertMaterial({ vertexColors: true, emissive: 0x334455, emissiveIntensity: 0 });
// parked
{
  const stands = AP.stands;
  const r = rng(5);
  const tailCols = AP.tailCols;
  const sel = stands.filter(() => r() < 0.82);
  const nb = new THREE.InstancedMesh(AC.body, bodyMatShared, sel.length);
  const tb = new THREE.InstancedMesh(AC.tail, new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x223344, emissiveIntensity: 0 }), sel.length);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), cc = new THREE.Color();
  sel.forEach(([x, z, h, wide], i) => {
    const s = (wide && r() < 0.65 ? 1.75 : 1.0) * 1.15;
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), h);
    m4.compose(new THREE.Vector3(x, 2.6 * s, z), q, new THREE.Vector3(s, s, s));
    nb.setMatrixAt(i, m4); tb.setMatrixAt(i, m4); tb.setColorAt(i, cc.set(tailCols[r() * tailCols.length | 0]));
  });
  sceneA.add(nb); sceneA.add(tb); sceneA.userData.parkedTail = tb;
}
// moving pool
const POOL = [];
for (let i = 0; i < 48; i++) {
  const g = new THREE.Group();
  const bm = new THREE.MeshLambertMaterial({ vertexColors: true, transparent: true, emissive: 0x334455, emissiveIntensity: 0 });
  const tm = new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, emissive: 0xffffff, emissiveIntensity: 0 });
  const b = new THREE.Mesh(AC.body, bm), tl = new THREE.Mesh(AC.tail, tm);
  g.add(b); g.add(tl); g.visible = false; g.rotation.order = 'YZX'; sceneA.add(g);
  POOL.push({ g, bm, tm });
}
const acLtGeo = pointsGeo(48 * 8); const acLt = new THREE.Points(acLtGeo, glowMat(false)); acLt.frustumCulled = false; sceneA.add(acLt);
const AC_LIGHTS = [ // local x,y,z, color, size, kind (0 steady,1 strobe,2 beacon,3 landing)
  [-8.6, -0.6, -17.6, RD, 9, 0], [-8.6, -0.6, 17.6, GR, 9, 0], [-18.9, 1.4, 0, WH, 8, 0], [0, 2.2, 0, RD, 11, 2], [-0.5, -2.2, 0, RD, 10, 2],
  [-9.4, -0.6, -17.7, WH, 13, 1], [3.5, -1.4, 2.5, [1, 0.97, 0.9], 34, 3], [3.5, -1.4, -2.5, [1, 0.97, 0.9], 34, 3]];

// sky dome
const skyMat = new THREE.ShaderMaterial({
  uniforms: { zen: { value: new THREE.Color() }, hor: { value: new THREE.Color() }, sunDir: { value: new THREE.Vector3() }, sunCol: { value: new THREE.Color() }, sunAmt: { value: 0 }, stars: { value: 0 } },
  vertexShader: `varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `uniform vec3 zen; uniform vec3 hor; uniform vec3 sunDir; uniform vec3 sunCol; uniform float sunAmt; uniform float stars; varying vec3 vD;
    float hash(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,45.164)))*43758.5453); }
    void main(){ vec3 d = normalize(vD); float h = d.y;
      vec3 c = mix(hor, zen, pow(clamp(h,0.0,1.0), 0.45));
      if (h < 0.0) c = hor*0.85;
      float sd = max(dot(d, sunDir), 0.0);
      c += sunCol * (pow(sd, 6.0)*0.35 + pow(sd, 64.0)*0.6 + pow(sd, 900.0)*2.0) * sunAmt;
      vec3 q = floor(d*420.0); float s = hash(q); if (s > 0.9965 && h > 0.05) c += vec3(0.8,0.85,1.0)*stars*(s-0.9965)*260.0*smoothstep(0.05,0.3,h);
      gl_FragColor = vec4(c, 1.0); }`,
  side: THREE.BackSide, depthWrite: false, fog: false,
});
const sky = new THREE.Mesh(new THREE.SphereGeometry(40000, 48, 24), skyMat); sky.renderOrder = -10; sky.frustumCulled = false; sceneA.add(sky);
sceneA.fog = new THREE.Fog(0x000000, 3000, 20000);
const hemi = new THREE.HemisphereLight(0xffffff, 0x445544, 1); sceneA.add(hemi);
const sunL = new THREE.DirectionalLight(0xffffff, 1); sceneA.add(sunL); sceneA.add(sunL.target);

// clouds
const cloudTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); const r = rng(8);
  for (let i = 0; i < 60; i++) { const x = 128 + (r() - 0.5) * 150, y = 128 + (r() - 0.5) * 70, rad = 30 + r() * 50; const gr = g.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, 'rgba(255,255,255,0.22)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 256, 256); }
  return canvasTex(c); })();
const CLOUDS = [];
{ const r = rng(21); for (let i = 0; i < 46; i++) { const m = new THREE.SpriteMaterial({ map: cloudTex, transparent: true, depthWrite: false, opacity: 0, fog: true }); const s = new THREE.Sprite(m); const sc = 2500 + r() * 3000; s.scale.set(sc, sc * 0.45, 1); s.userData = { x: (r() - 0.5) * 26000, z: (r() - 0.5) * 26000, y: 1100 + r() * 900, ph: r() }; sceneA.add(s); CLOUDS.push(s); } }
// rain
const RAIN_N = 2200; const rainGeo = new THREE.BufferGeometry(); rainGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(RAIN_N * 6), 3));
const rainSeed = []; { const r = rng(31); for (let i = 0; i < RAIN_N; i++) rainSeed.push([r(), r(), r(), r()]); }
const rainMat = new THREE.LineBasicMaterial({ color: 0xc8d4e6, transparent: true, opacity: 0, depthWrite: false, fog: false });
const rain = new THREE.LineSegments(rainGeo, rainMat); rain.frustumCulled = false; sceneA.add(rain);
// wind streaks
const WS_N = 70, WS_SEG = 10; const windSeed = []; { const r = rng(41); for (let i = 0; i < WS_N; i++) windSeed.push([r(), r(), r(), r()]); }
const windMat = new LineMaterial({ vertexColors: true, linewidth: 2.0, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, worldUnits: false });
let windObj = null;


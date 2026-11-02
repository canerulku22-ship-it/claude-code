import * as THREE from 'three';
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js';
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js';
import { LineMaterial } from 'three/addons/lines/LineMaterial.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { feature, mesh } from './node_modules/topojson-client/src/index.js';

// ------------------------------------------------------------------ basics
const W = 1080, H = 1920, D2R = Math.PI / 180;
const CATS = ['#FFD21F', '#FF8A1F', '#FF3B3B', '#B65CFF'];
const CATC = CATS.map(c => new THREE.Color(c));
const DEPC = new THREE.Color('#38C8FF'), ARRC = new THREE.Color('#3DF5A0');
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a), 0, 1); return k * k * (3 - 2 * k); };
const ease = k => (k = clamp(k, 0, 1), k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
const easeOut = k => 1 - Math.pow(1 - clamp(k, 0, 1), 3);
function rng(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const $ = id => document.getElementById(id);
const pad2 = n => String(n).padStart(2, '0');
const hhmm = m => { m = Math.floor(m); if (m >= 1440) m = 1439; if (m < 0) m += 1440; return pad2(Math.floor(m / 60)) + ':' + pad2(m % 60); };
const fmt = n => Math.round(n).toLocaleString('en-GB');

const APC = new URLSearchParams(location.search).get('ap') || 'LAX';
const AP = (await import(`./cfg_${APC}.js`)).default;
const S = await (await fetch(`schedule_${APC}.json`)).json();
const topo = await (await fetch('node_modules/world-atlas/countries-50m.json')).json();
const ROUTES = S.routes, FL = S.flights;
const WIDE = new Set(['A330', '787', '777', 'A350', 'A380']);

// ------------------------------------------------------------------ timeline
// 0-6.6 intro aerial + titles | 6.6-9 rise into the globe | 9-52 the day (00:00-24:00) | 52-60 finale
const T_RISE = 6.6, T0 = 9.0, TN = 13.0, TE = 52.0;
function dayMin(t) {
  if (t <= T0) return 0;
  if (t <= TN) return (t - T0) / (TN - T0) * 300;
  if (t <= TE) return 300 + (t - TN) / (TE - TN) * 1140;
  return 1440;
}
function vidT(m) {
  if (m <= 0) return T0;
  if (m <= 300) return T0 + m / 300 * (TN - T0);
  if (m <= 1440) return TN + (m - 300) / 1140 * (TE - TN);
  return TE + (m - 1440) / 10;
}
const visMin = t => t > TE ? 1440 + (t - TE) * 10 : t < T0 ? (t - T0) * 14 : dayMin(t);

// ------------------------------------------------------------------ geo / sun
function llv(lat, lon, r = 1) { const a = lat * D2R, b = lon * D2R; return new THREE.Vector3(Math.cos(a) * Math.cos(b) * r, Math.sin(a) * r, -Math.cos(a) * Math.sin(b) * r); }
const LHR = { lat: AP.lat, lon: AP.lon };
const LV = llv(LHR.lat, LHR.lon);
function sunECEF(min) { const u = min - AP.utcOff * 60; return llv(AP.decl, -((u + AP.eot) / 60 - 12) * 15); }
const _east = new THREE.Vector3(-Math.sin(LHR.lon * D2R), 0, -Math.cos(LHR.lon * D2R));
const _north = new THREE.Vector3(-Math.sin(LHR.lat * D2R) * Math.cos(LHR.lon * D2R), Math.cos(LHR.lat * D2R), Math.sin(LHR.lat * D2R) * Math.sin(LHR.lon * D2R));
function sunLocal(min) { const s = sunECEF(min); return new THREE.Vector3(s.dot(_east), s.dot(LV), -s.dot(_north)).normalize(); }
const mod1440 = m => ((m % 1440) + 1440) % 1440;

// ------------------------------------------------------------------ weather
//        min  dir  kt gust temp cloud rain mist
const WX = AP.wx;
function wxAt(min) {
  min = clamp(min, 0, 1440);
  let i = 0; while (i < WX.length - 2 && WX[i + 1][0] < min) i++;
  const a = WX[i], b = WX[i + 1], k = smooth(a[0], b[0], min);
  const v = a.map((x, j) => lerp(x, b[j], k));
  const wob = Math.sin(min * 0.21) * 3 + Math.sin(min * 0.057) * 4;
  return { dir: v[1] + wob, kt: Math.max(2, v[2] + Math.sin(min * 0.13) * 1.2), gust: v[3], temp: v[4], cloud: v[5], rain: v[6], mist: v[7] };
}
function condOf(w, el) {
  if (w.rain > 0.45) return 'SHOWERS';
  if (w.rain > 0.12) return 'LIGHT RAIN';
  if (w.mist > 0.35) return AP.mistName || 'MIST';
  if (w.cloud > 0.7) return 'CLOUDY';
  if (w.cloud > 0.35) return 'PARTLY CLOUDY';
  return el > 0 ? 'SUNNY' : 'CLEAR NIGHT';
}
const compassPt = d => ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][Math.round(((d % 360) + 360) % 360 / 22.5) % 16];

// ------------------------------------------------------------------ renderers (globe below, airport above)
function mkRenderer(id, w, h) {
  const r = new THREE.WebGLRenderer({ canvas: $(id), antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  r.setPixelRatio(1); r.setSize(w, h, false); r.outputColorSpace = THREE.SRGBColorSpace; return r;
}
const rG = mkRenderer('glG', W, H);
const rA = mkRenderer('glA', W, H);
const MAXANI = rA.capabilities.getMaxAnisotropy();
function canvasTex(c, srgb = true) { const t = new THREE.CanvasTexture(c); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = MAXANI; return t; }

function glowMat(screen) {
  return new THREE.ShaderMaterial({
    uniforms: { uScale: { value: 700 }, uInt: { value: 1 }, uFog: { value: 1e9 }, uMin: { value: 1.2 } },
    vertexShader: `
      attribute float size; attribute vec3 acol; attribute float alpha;
      varying vec3 vC; varying float vA;
      uniform float uScale; uniform float uFog; uniform float uMin;
      void main(){
        vec4 mv = modelViewMatrix * vec4(position,1.0);
        float d = -mv.z;
        ${screen ? 'gl_PointSize = size;' : 'gl_PointSize = clamp(size*uScale/d, uMin, 90.0);'}
        float f = ${screen ? '1.0' : 'exp(-d/uFog)'};
        ${screen ? '' : 'f *= clamp(size*uScale/d/uMin, 0.25, 1.0);'}
        vC = acol; vA = alpha * f;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      varying vec3 vC; varying float vA; uniform float uInt;
      void main(){
        vec2 p = gl_PointCoord*2.0-1.0; float r = dot(p,p);
        if (r > 1.0) discard;
        float core = exp(-r*12.0); float halo = exp(-r*3.2)*0.45;
        vec3 c = vC*(core*1.6+halo) + vec3(1.0)*core*0.35;
        gl_FragColor = vec4(c*vA*uInt, 1.0);
      }`,
    blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
  });
}
function pointsGeo(n, extra = []) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute('acol', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute('size', new THREE.BufferAttribute(new Float32Array(n), 1));
  g.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(n), 1));
  for (const k of extra) g.setAttribute(k, new THREE.BufferAttribute(new Float32Array(n), 1));
  return g;
}
// aircraft glyph (top view, nose up), rotated per point to follow its path on screen
const planeTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  g.translate(64, 64); g.fillStyle = '#fff'; g.beginPath();
  const P = [[0, -56], [6, -46], [7, -14], [52, 8], [52, 17], [7, 6], [6, 34], [20, 46], [20, 53], [0, 47], [-20, 53], [-20, 46], [-6, 34], [-7, 6], [-52, 17], [-52, 8], [-7, -14], [-6, -46]];
  P.forEach(([x, y], i) => i ? g.lineTo(x, y) : g.moveTo(x, y)); g.closePath(); g.fill();
  const t = new THREE.CanvasTexture(c); t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; return t;
})();
const glyphMat = new THREE.ShaderMaterial({
  uniforms: { tex: { value: planeTex } },
  vertexShader: `attribute float size; attribute vec3 acol; attribute float alpha; attribute float ang;
    varying vec3 vC; varying float vA; varying float vAng;
    void main(){ vC = acol; vA = alpha; vAng = ang; vec4 mv = modelViewMatrix*vec4(position,1.0); gl_PointSize = size; gl_Position = projectionMatrix*mv; }`,
  fragmentShader: `uniform sampler2D tex; varying vec3 vC; varying float vA; varying float vAng;
    void main(){
      vec2 q = vec2(gl_PointCoord.x - 0.5, 0.5 - gl_PointCoord.y);
      float a = -(vAng - 1.5707963); float c = cos(a), s = sin(a);
      vec2 r = vec2(c*q.x - s*q.y, s*q.x + c*q.y);
      float sh = texture2D(tex, r*1.55 + 0.5).a;
      float halo = exp(-dot(q,q)*22.0)*0.65;
      vec3 col = vC*halo*0.9 + mix(vC, vec3(1.0), 0.45)*sh*1.25;
      gl_FragColor = vec4(col*vA, 1.0);
    }`,
  blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
});
const ringMat = new THREE.ShaderMaterial({
  vertexShader: `attribute float size; attribute vec3 acol; attribute float alpha; varying vec3 vC; varying float vA;
    void main(){ vC = acol; vA = alpha; vec4 mv = modelViewMatrix*vec4(position,1.0); gl_PointSize = size; gl_Position = projectionMatrix*mv; }`,
  fragmentShader: `varying vec3 vC; varying float vA;
    void main(){ float r = length(gl_PointCoord*2.0-1.0); float ring = smoothstep(0.16, 0.0, abs(r - 0.8)) + exp(-r*r*18.0)*0.25; gl_FragColor = vec4(vC*ring*vA, 1.0); }`,
  blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
});

// ================================================================== GLOBE
const sceneG = new THREE.Scene();
const camG = new THREE.PerspectiveCamera(40, 1, 0.05, 150);
function setGlobeCenter(gx, gy) { const FW = 2 * Math.max(W - gx, gx), FH = 2 * Math.max(H - gy, gy); camG.aspect = FW / FH; camG.setViewOffset(FW, FH, FW / 2 - gx, FH / 2 - gy, W, H); }

const EXTRA_CITIES = [[55.75, 37.62], [59.93, 30.33], [50.45, 30.52], [53.9, 27.56], [39.93, 32.86], [35.69, 51.39], [24.86, 67.0], [22.57, 88.36], [29.56, 106.55], [22.54, 114.06], [23.13, 113.26], [34.69, 135.5], [14.6, 120.98], [-6.2, 106.85], [10.82, 106.63], [21.03, 105.85], [25.03, 121.56], [-33.87, 151.21], [-37.81, 144.96], [-27.47, 153.03], [-36.85, 174.76], [-12.05, -77.04], [4.71, -74.07], [-33.45, -70.67], [10.49, -66.88], [23.11, -82.37], [20.67, -103.35], [25.69, -100.32], [45.42, -75.69], [42.33, -83.05], [44.98, -93.27], [38.63, -90.2], [39.1, -94.58], [40.76, -111.89], [45.52, -122.68], [32.72, -117.16], [-4.44, 15.27], [-8.84, 13.23], [15.5, 32.56], [-6.79, 39.21], [33.31, 44.36], [41.3, 69.24], [43.24, 76.89], [55.03, 82.92], [56.84, 60.6], [40.85, 14.27], [52.49, -1.89], [53.8, -1.55], [50.63, 3.06], [44.84, -0.58], [37.39, -5.98], [39.47, -0.38], [50.06, 19.94], [45.46, 9.19], [51.23, 6.78], [50.94, 6.96], [52.52, 13.4], [48.86, 2.35], [51.51, -0.13], [53.48, -2.24], [32.08, 34.78], [30.04, 31.24], [36.8, 10.18], [33.57, -7.59], [-23.55, -46.63], [-22.9, -43.2], [19.43, -99.13], [6.52, 3.38], [-1.29, 36.82], [-26.2, 28.04], [1.35, 103.82], [13.75, 100.5], [37.57, 126.98], [39.9, 116.4], [31.23, 121.47], [35.68, 139.69], [28.61, 77.2], [19.07, 72.88], [12.97, 77.59], [25.2, 55.27], [40.71, -74.0], [34.05, -118.24], [41.88, -87.63], [29.76, -95.36], [43.65, -79.38], [37.77, -122.42], [47.6, -122.33], [49.28, -123.12], [25.76, -80.19], [33.75, -84.39], [32.78, -96.8], [39.95, -75.16], [38.9, -77.03], [42.36, -71.06], [41.01, 28.98], [37.98, 23.73], [41.9, 12.5], [40.42, -3.7], [38.72, -9.14], [59.33, 18.07], [52.23, 21.01], [47.5, 19.04], [48.21, 16.37], [50.08, 14.44], [44.43, 26.1], [-34.6, -58.38], [-31.95, 115.86], [53.35, -6.26], [55.95, -3.19], [52.37, 4.9], [50.11, 8.68], [47.37, 8.54], [55.68, 12.57], [48.14, 11.58], [60.17, 24.94], [59.91, 10.75], [45.76, 4.84], [43.3, 5.37], [53.55, 9.99]];

function makeEarthTextures() {
  const Wt = 4096, Ht = 2048;
  const land = feature(topo, topo.objects.land);
  const borders = mesh(topo, topo.objects.countries, (a, b) => a !== b);
  const X = (lo, w) => (lo + 180) / 360 * w, Y = (la, h) => (90 - la) / 180 * h;
  function polyPath(ctx, g, w, h) {
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
    for (const poly of polys) for (const ring of poly) { ring.forEach(([lo, la], i) => i ? ctx.lineTo(X(lo, w), Y(la, h)) : ctx.moveTo(X(lo, w), Y(la, h))); ctx.closePath(); }
  }
  function linePath(ctx, g) {
    const lines = g.type === 'LineString' ? [g.coordinates] : g.coordinates;
    for (const l of lines) { let px = null; l.forEach(([lo, la], i) => { const x = X(lo, Wt), y = Y(la, Ht); if (i === 0 || Math.abs(x - px) > Wt / 2) ctx.moveTo(x, y); else ctx.lineTo(x, y); px = x; }); }
  }
  function draw(day) {
    const c = document.createElement('canvas'); c.width = Wt; c.height = Ht;
    const ctx = c.getContext('2d');
    const og = ctx.createLinearGradient(0, 0, 0, Ht);
    if (day) { og.addColorStop(0, '#0c1938'); og.addColorStop(0.5, '#0f2357'); og.addColorStop(1, '#0c1938'); }
    else { og.addColorStop(0, '#02050c'); og.addColorStop(0.5, '#040a18'); og.addColorStop(1, '#02050c'); }
    ctx.fillStyle = og; ctx.fillRect(0, 0, Wt, Ht);
    ctx.strokeStyle = day ? 'rgba(120,150,255,0.10)' : 'rgba(120,150,255,0.05)'; ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (let lo = -180; lo <= 180; lo += 15) { ctx.moveTo(X(lo, Wt), 0); ctx.lineTo(X(lo, Wt), Ht); }
    for (let la = -75; la <= 75; la += 15) { ctx.moveTo(0, Y(la, Ht)); ctx.lineTo(Wt, Y(la, Ht)); }
    ctx.stroke();
    ctx.beginPath(); for (const f of land.features) polyPath(ctx, f.geometry, Wt, Ht);
    ctx.fillStyle = day ? '#22356c' : '#0a1228'; ctx.fill();
    ctx.lineJoin = 'round';
    ctx.strokeStyle = day ? 'rgba(115,145,240,0.95)' : 'rgba(60,80,150,0.7)'; ctx.lineWidth = day ? 2.4 : 1.6; ctx.stroke();
    ctx.beginPath(); linePath(ctx, borders);
    ctx.strokeStyle = day ? 'rgba(95,120,205,0.75)' : 'rgba(40,55,110,0.6)'; ctx.lineWidth = 1.3; ctx.stroke();
    if (!day) {
      const r = rng(7);
      const pts = EXTRA_CITIES.concat(ROUTES.map(x => [x.lat, x.lon]));
      for (const [la, lo] of pts) {
        const x = X(lo, Wt), y = Y(la, Ht);
        const gr = ctx.createRadialGradient(x, y, 0, x, y, 16);
        gr.addColorStop(0, 'rgba(255,214,150,0.85)'); gr.addColorStop(0.35, 'rgba(255,180,100,0.35)'); gr.addColorStop(1, 'rgba(255,160,80,0)');
        ctx.fillStyle = gr; ctx.fillRect(x - 16, y - 16, 32, 32);
        for (let k = 0; k < 26; k++) { const a = r() * 6.283, d = Math.pow(r(), 1.6) * 26; ctx.fillStyle = `rgba(255,${190 + r() * 50 | 0},120,${0.25 + r() * 0.5})`; ctx.fillRect(x + Math.cos(a) * d, y + Math.sin(a) * d * 0.8, 2, 2); }
      }
    }
    return canvasTex(c);
  }
  // land mask for ocean glint
  const mc = document.createElement('canvas'); mc.width = 2048; mc.height = 1024; const mx = mc.getContext('2d');
  mx.fillStyle = '#000'; mx.fillRect(0, 0, 2048, 1024); mx.beginPath(); for (const f of land.features) polyPath(mx, f.geometry, 2048, 1024); mx.fillStyle = '#fff'; mx.fill();
  const mask = new THREE.CanvasTexture(mc);
  return { day: draw(true), night: draw(false), mask };
}
const ET = makeEarthTextures();
const globeMat = new THREE.ShaderMaterial({
  uniforms: { dayTex: { value: ET.day }, nightTex: { value: ET.night }, maskTex: { value: ET.mask }, sunDir: { value: new THREE.Vector3(1, 0, 0) }, camPos: { value: new THREE.Vector3() } },
  vertexShader: `varying vec2 vUv; varying vec3 vN; varying vec3 vW;
    void main(){ vUv = uv; vN = normalize(position); vec4 w = modelMatrix*vec4(position,1.0); vW = w.xyz; gl_Position = projectionMatrix*viewMatrix*w; }`,
  fragmentShader: `uniform sampler2D dayTex; uniform sampler2D nightTex; uniform sampler2D maskTex; uniform vec3 sunDir; uniform vec3 camPos;
    varying vec2 vUv; varying vec3 vN; varying vec3 vW;
    void main(){
      vec3 n = normalize(vN);
      vec3 day = texture2D(dayTex, vUv).rgb; vec3 night = texture2D(nightTex, vUv).rgb; float land = texture2D(maskTex, vUv).r;
      float d = dot(n, sunDir);
      float k = smoothstep(-0.14, 0.18, d);
      vec3 col = mix(night*1.25, day*(0.60 + 0.60*max(d,0.0)), k);
      col += vec3(1.0,0.48,0.25) * exp(-pow(d/0.075,2.0)) * 0.16;              // sunset band along the terminator
      vec3 V = normalize(camPos - vW);
      vec3 Rf = reflect(-sunDir, n);
      col += vec3(1.0,0.92,0.78) * pow(max(dot(Rf, V), 0.0), 48.0) * (1.0 - land) * 0.30 * k;   // ocean glint
      float fres = pow(1.0 - max(dot(n,V),0.0), 2.6);
      col += mix(vec3(0.12,0.20,0.45), vec3(0.32,0.55,1.0), k) * fres * (0.28 + 0.30*k);
      gl_FragColor = vec4(col, 1.0);
    }`,
});
const globe = new THREE.Mesh(new THREE.SphereGeometry(1, 192, 128), globeMat);
sceneG.add(globe);
const atmoMat = new THREE.ShaderMaterial({
  uniforms: { sunDir: { value: new THREE.Vector3(1, 0, 0) } },
  vertexShader: `varying vec3 vN; varying vec3 vWN; void main(){ vN = normalize(normalMatrix*normal); vWN = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `uniform vec3 sunDir; varying vec3 vN; varying vec3 vWN;
    void main(){ float i = pow(clamp(0.74 - dot(vN, vec3(0.0,0.0,1.0)), 0.0, 1.0), 3.6);
      float d = dot(vWN, sunDir);
      float lit = clamp(d*0.9 + 0.55, 0.22, 1.15);
      vec3 col = mix(vec3(0.32,0.52,1.0), vec3(1.0,0.55,0.32), exp(-pow(d/0.22,2.0))*0.55);
      gl_FragColor = vec4(col*i*0.95*lit, 1.0); }`,
  side: THREE.BackSide, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false,
});
sceneG.add(new THREE.Mesh(new THREE.SphereGeometry(1.045, 96, 64), atmoMat));
{
  const r = rng(11), n = 1800, g = pointsGeo(n);
  for (let i = 0; i < n; i++) {
    const u = r() * 2 - 1, a = r() * 6.283, s = Math.sqrt(1 - u * u);
    g.attributes.position.setXYZ(i, s * Math.cos(a) * 60, u * 60, s * Math.sin(a) * 60);
    const c = 0.7 + r() * 0.3; g.attributes.acol.setXYZ(i, c * 0.85, c * 0.9, c);
    g.attributes.size.setX(i, 2 + r() * 3.5); g.attributes.alpha.setX(i, 0.10 + Math.pow(r(), 3) * 0.6);
  }
  sceneG.add(new THREE.Points(g, glowMat(true)));
}

// routes + flights
const RT = ROUTES.map(r => { const v = llv(r.lat, r.lon); const ang = LV.angleTo(v); return { ...r, v, ang, hgt: 0.10 * ang + 0.004, L: Math.min(0.85, 0.30 / ang) }; });
function arcPt(rt, s, out = new THREE.Vector3()) {
  const om = rt.ang, so = Math.sin(om); const a = Math.sin((1 - s) * om) / so, b = Math.sin(s * om) / so;
  out.set(LV.x * a + rt.v.x * b, LV.y * a + rt.v.y * b, LV.z * a + rt.v.z * b);
  return out.multiplyScalar(1.003 + rt.hgt * Math.sin(Math.PI * s));
}
const GF = [];
for (const f of FL) GF.push({ type: f.type, t: f.t, r: f.r, wide: WIDE.has(f.ac) });
for (const g of S.ghosts) GF.push({ type: g.type, t: g.t, r: g.r, wide: false, ghost: 1 });
for (const g of GF) { const d = ROUTES[g.r].dur; g.start = g.type === 'D' ? g.t : g.t - d; g.end = g.start + d; g.drain = g.end + RT[g.r].L * d; }
// busiest routes (by daily movements)
const routeCount = ROUTES.map((_, i) => FL.filter(f => f.r === i).length);
const BUSY = routeCount.map((c, i) => [i, c]).sort((a, b) => b[1] - a[1]).slice(0, 8).map(x => x[0]);
const BUSYSET = new Set(BUSY);

const mkLine = w => { const m = new LineMaterial({ vertexColors: true, linewidth: w, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, worldUnits: false }); m.resolution.set(W, H); return m; };
const matTrail = mkLine(2.4), matNet = mkLine(1.1), matBusy = mkLine(3.0);
const lineObjs = {};
function setLines(key, mat, pos, col) {
  if (lineObjs[key]) { sceneG.remove(lineObjs[key]); lineObjs[key].geometry.dispose(); lineObjs[key] = null; }
  if (!pos.length) return;
  const g = new LineSegmentsGeometry(); g.setPositions(pos); g.setColors(col);
  const o = new LineSegments2(g, mat); o.frustumCulled = false; sceneG.add(o); lineObjs[key] = o;
}
const glyphGeo = pointsGeo(1400, ['ang']); const glyphs = new THREE.Points(glyphGeo, glyphMat); glyphs.frustumCulled = false; glyphs.renderOrder = 5; sceneG.add(glyphs);
const destGeo = pointsGeo(RT.length + 3); const dests = new THREE.Points(destGeo, glowMat(true)); dests.frustumCulled = false; dests.renderOrder = 4; sceneG.add(dests);
RT.forEach((rt, i) => { destGeo.attributes.position.setXYZ(i, rt.v.x * 1.004, rt.v.y * 1.004, rt.v.z * 1.004); });
for (let k = 0; k < 3; k++) destGeo.attributes.position.setXYZ(RT.length + k, LV.x * 1.004, LV.y * 1.004, LV.z * 1.004);
const ringGeo = pointsGeo(500); const rings = new THREE.Points(ringGeo, ringMat); rings.frustumCulled = false; rings.renderOrder = 3; sceneG.add(rings);

// labels: world cities (wide views), European cities (close view), badges for the busiest routes
const NAMES = AP.globe.names || {};
const nameOf = i => NAMES[ROUTES[i].code] || ROUTES[i].city;
const WORLD_LAB = AP.globe.worldLabels;
const EURO_LAB = AP.globe.regionLabels;
const labelEls = [];
for (const [set, kind] of [[WORLD_LAB, 'w'], [EURO_LAB, 'e']]) for (const code of set) {
  const i = ROUTES.findIndex(r => r.code === code); if (i < 0 || BUSYSET.has(i)) continue;
  const el = document.createElement('div'); el.className = 'clab'; el.textContent = nameOf(i); el.style.color = CATS[ROUTES[i].cat];
  $('labels').appendChild(el); labelEls.push({ el, i, kind });
}
const busyEls = BUSY.slice(0, 6).map(i => {
  const el = document.createElement('div'); el.className = 'busy';
  el.innerHTML = `<span class="d" style="background:${CATS[ROUTES[i].cat]};box-shadow:0 0 10px ${CATS[ROUTES[i].cat]}"></span><span>${nameOf(i)}</span><span class="n"></span>`;
  el.style.borderColor = CATS[ROUTES[i].cat] + '99';
  $('labels').appendChild(el); return { el, i };
});
const lhrLabel = document.createElement('div'); lhrLabel.className = 'clab'; lhrLabel.style.color = '#fff'; lhrLabel.style.fontSize = '16px'; lhrLabel.textContent = AP.city + ' (' + AP.code + ')'; $('labels').appendChild(lhrLabel);

// counting helpers
const routeTimes = ROUTES.map(() => []);
for (const f of FL) routeTimes[f.r].push(f.t);
routeTimes.forEach(a => a.sort((x, y) => x - y));
const ub = (a, x) => { let lo = 0, hi = a.length; while (lo < hi) { const m = (lo + hi) >> 1; if (a[m] <= x) lo = m + 1; else hi = m; } return lo; };
const depT = FL.filter(f => f.type === 'D').map(f => f.t), arrT = FL.filter(f => f.type === 'A').map(f => f.t);
const allT = FL.map(f => f.t); const paxCum = []; { let s = 0; for (const f of FL) { s += f.pax; paxCum.push(s); } }
function paxAt(m) {
  const i = ub(allT, m); if (i === 0) return 0;
  if (i >= FL.length) return paxCum[FL.length - 1];
  const t0 = allT[i - 1], t1 = allT[i];
  return paxCum[i - 1] + FL[i].pax * clamp((m - t0) / Math.max(0.01, t1 - t0), 0, 1);
}
function contCount(arr, m) { // continuous count: rolls up to the next integer just before each event
  const i = ub(arr, m); if (i >= arr.length) return arr.length;
  const t0 = i > 0 ? arr[i - 1] : arr[0] - 30, t1 = arr[i];
  return i + clamp((m - t0) / Math.max(0.01, t1 - t0), 0, 1) * 0.9999;
}
const hourRate = m => ub(allT, m + 30) - ub(allT, m - 30);

const _q = new THREE.Vector3(), _q2 = new THREE.Vector3();
function updateGlobe(t, m, fin) {
  const tp = [], tc = [], np = [], nc = [], bp = [], bc = [];
  const act = new Array(RT.length).fill(0);
  const ga = glyphGeo.attributes; let ng = 0;
  const ra = ringGeo.attributes; let nr = 0;
  const pulse = new Array(RT.length).fill(0);
  for (const g of GF) {
    // endpoint pulses at the far airport (arrival there / departure from there)
    const far = g.type === 'D' ? g.end : g.start;
    const age = m - far;
    if (age >= 0 && age < 45) pulse[g.r] = Math.max(pulse[g.r], 1 - age / 45);
    if (age >= 0 && age < 30 && nr < 500) {
      const rt = RT[g.r]; const c = g.type === 'D' ? DEPC : ARRC;
      ra.position.setXYZ(nr, rt.v.x * 1.004, rt.v.y * 1.004, rt.v.z * 1.004); ra.acol.setXYZ(nr, c.r, c.g, c.b);
      ra.size.setX(nr, 8 + age * 1.0); ra.alpha.setX(nr, (1 - age / 30) * 0.9); nr++;
    }
    if (m < g.start || m > g.drain) continue;
    const rt = RT[g.r]; const dur = ROUTES[g.r].dur;
    const f = (m - g.start) / dur;
    act[g.r]++;
    const head = Math.min(f, 1), tail = clamp(f - rt.L, 0, 1);
    if (tail >= 1) continue;
    const c = g.type === 'D' ? DEPC : ARRC;
    const s0 = g.type === 'D' ? tail : 1 - tail, s1 = g.type === 'D' ? head : 1 - head;
    const N = 20; let prev = arcPt(rt, s0);
    for (let k = 1; k <= N; k++) {
      const u = k / N; const p = arcPt(rt, lerp(s0, s1, u));
      const b0 = Math.pow((k - 1) / N, 1.6) * 0.95, b1 = Math.pow(u, 1.6) * 0.95;
      tp.push(prev.x, prev.y, prev.z, p.x, p.y, p.z);
      tc.push(c.r * b0, c.g * b0, c.b * b0, c.r * b1, c.g * b1, c.b * b1);
      prev = p;
    }
    if (f <= 1 && ng < 1400) {
      const s = g.type === 'D' ? f : 1 - f, s2 = clamp(s + (g.type === 'D' ? 0.01 : -0.01), 0, 1);
      arcPt(rt, s, _q); arcPt(rt, s2, _q2);
      ga.position.setXYZ(ng, _q.x, _q.y, _q.z);
      const a = _q.clone().project(camG), b = _q2.clone().project(camG);
      let ang = Math.atan2((b.y - a.y) * H, (b.x - a.x) * W); if (g.type === 'D' ? s2 < s : s2 > s) ang += Math.PI;
      ga.ang.setX(ng, ang);
      ga.acol.setXYZ(ng, c.r, c.g, c.b);
      ga.size.setX(ng, g.wide ? 23 : 18);
      ga.alpha.setX(ng, smooth(0, 0.02, f) * (1 - smooth(0.98, 1, f)));
      ng++;
    }
  }
  glyphGeo.setDrawRange(0, ng); for (const k of ['position', 'acol', 'size', 'alpha', 'ang']) ga[k].needsUpdate = true;
  ringGeo.setDrawRange(0, nr); for (const k of ['position', 'acol', 'size', 'alpha']) ra[k].needsUpdate = true;
  // network arcs: coloured by flight time, busiest routes thick + bright
  for (let i = 0; i < RT.length; i++) {
    const served = ub(routeTimes[i], m) > 0 || act[i] > 0;
    if (!served && !fin) continue;
    const rt = RT[i]; const c = CATC[rt.cat]; const busy = BUSYSET.has(i);
    let b = (busy ? 0.42 + 0.10 * Math.sin(t * 3 + i) : 0.13 + 0.06 * Math.min(act[i], 3)) * (1 + fin * 1.4);
    const N = Math.max(8, Math.round(rt.ang * 44)); let prev = arcPt(rt, 0);
    for (let k = 1; k <= N; k++) {
      const p = arcPt(rt, k / N);
      (busy ? bp : np).push(prev.x, prev.y, prev.z, p.x, p.y, p.z);
      (busy ? bc : nc).push(c.r * b, c.g * b, c.b * b, c.r * b, c.g * b, c.b * b);
      prev = p;
    }
  }
  setLines('net', matNet, np, nc); setLines('busy', matBusy, bp, bc); setLines('trail', matTrail, tp, tc);
  // airports
  const da = destGeo.attributes;
  for (let i = 0; i < RT.length; i++) {
    const served = ub(routeTimes[i], m) > 0 || act[i] > 0; const c = CATC[RT[i].cat];
    const w = served ? 0.35 + 0.65 * pulse[i] : 0.12;
    da.acol.setXYZ(i, lerp(c.r, 1, pulse[i] * 0.5), lerp(c.g, 1, pulse[i] * 0.5), lerp(c.b, 1, pulse[i] * 0.5));
    da.alpha.setX(i, w * (1 + fin)); da.size.setX(i, (served ? 9 + 11 * pulse[i] + (BUSYSET.has(i) ? 5 : 0) : 6));
  }
  const rate = hourRate(m); const pp = 0.5 + 0.5 * Math.sin(t * 6.0);
  da.acol.setXYZ(RT.length, 1, 0.95, 0.98); da.size.setX(RT.length, 18 + rate * 0.06); da.alpha.setX(RT.length, 1);
  da.acol.setXYZ(RT.length + 1, 0.70, 0.50, 1.0); da.size.setX(RT.length + 1, 46 + rate * 0.25 + pp * 10); da.alpha.setX(RT.length + 1, 0.55);
  da.acol.setXYZ(RT.length + 2, 0.35, 0.55, 1.0); da.size.setX(RT.length + 2, 90 + rate * 0.4); da.alpha.setX(RT.length + 2, 0.22);
  for (const k of ['alpha', 'size', 'acol']) da[k].needsUpdate = true;
  return { act, pulse, inAir: GF.filter(g => m >= g.start && m <= g.end).length };
}

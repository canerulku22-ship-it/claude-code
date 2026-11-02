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

const S = await (await fetch('schedule.json')).json();
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
const LHR = { lat: 51.47, lon: -0.4543 };
const LV = llv(LHR.lat, LHR.lon);
function sunECEF(min) { return llv(-14.35, -((min + 16.4) / 60 - 12) * 15); }
const _east = new THREE.Vector3(-Math.sin(LHR.lon * D2R), 0, -Math.cos(LHR.lon * D2R));
const _north = new THREE.Vector3(-Math.sin(LHR.lat * D2R) * Math.cos(LHR.lon * D2R), Math.cos(LHR.lat * D2R), Math.sin(LHR.lat * D2R) * Math.sin(LHR.lon * D2R));
function sunLocal(min) { const s = sunECEF(min); return new THREE.Vector3(s.dot(_east), s.dot(LV), -s.dot(_north)).normalize(); }
const mod1440 = m => ((m % 1440) + 1440) % 1440;

// ------------------------------------------------------------------ weather
//        min  dir  kt gust temp cloud rain mist
const WX = [
  [0, 215, 6, 0, 8.5, 0.15, 0, 0.0],
  [240, 220, 5, 0, 7.0, 0.10, 0, 0.15],
  [360, 225, 6, 0, 6.0, 0.20, 0, 0.50],
  [450, 230, 7, 0, 6.5, 0.30, 0, 0.55],
  [540, 235, 10, 0, 9.0, 0.40, 0, 0.12],
  [660, 240, 13, 21, 11.5, 0.55, 0, 0],
  [760, 250, 16, 26, 12.5, 0.82, 0.25, 0],
  [810, 255, 18, 29, 12.0, 0.92, 0.75, 0],
  [930, 262, 19, 31, 11.5, 0.92, 0.65, 0],
  [1000, 270, 16, 26, 11.0, 0.70, 0.2, 0],
  [1060, 280, 14, 22, 10.5, 0.45, 0, 0],
  [1200, 290, 10, 0, 9.0, 0.25, 0, 0],
  [1440, 300, 7, 0, 8.0, 0.15, 0, 0],
];
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
  if (w.mist > 0.35) return 'MIST';
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
function setGlobeCenterY(gy) { const FH = 2 * Math.max(H - gy, gy); camG.aspect = W / FH; camG.setViewOffset(W, FH, 0, FH / 2 - gy, W, H); }

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
const matTrail = mkLine(3.0), matNet = mkLine(1.3), matBusy = mkLine(3.6);
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
const NAMES = { JFK: 'NEW YORK', LAX: 'LOS ANGELES', GRU: 'SÃO PAULO', HND: 'TOKYO', KEF: 'REYKJAVIK', CDG: 'PARIS', MXP: 'MILAN', FCO: 'ROME', ARN: 'STOCKHOLM' };
const nameOf = i => NAMES[ROUTES[i].code] || ROUTES[i].city;
const WORLD_LAB = ['LAX', 'YYZ', 'MIA', 'GRU', 'DEL', 'SIN', 'HKG', 'HND', 'JNB', 'LOS', 'NBO', 'IST', 'KEF', 'CAI', 'DOH'];
const EURO_LAB = ['CDG', 'ZRH', 'CPH', 'ARN', 'MUC', 'LIS', 'BER', 'VIE', 'OSL', 'FCO', 'GLA', 'MXP', 'GVA', 'BCN'];
const labelEls = [];
for (const [set, kind] of [[WORLD_LAB, 'w'], [EURO_LAB, 'e']]) for (const code of set) {
  const i = ROUTES.findIndex(r => r.code === code); if (i < 0 || BUSYSET.has(i)) continue;
  const el = document.createElement('div'); el.className = 'clab'; el.textContent = nameOf(i); el.style.color = CATS[ROUTES[i].cat];
  $('labels').appendChild(el); labelEls.push({ el, i, kind });
}
const busyEls = BUSY.slice(0, 7).map(i => {
  const el = document.createElement('div'); el.className = 'busy';
  el.innerHTML = `<span class="d" style="background:${CATS[ROUTES[i].cat]};box-shadow:0 0 10px ${CATS[ROUTES[i].cat]}"></span><span>${nameOf(i)}</span><span class="n"></span>`;
  el.style.borderColor = CATS[ROUTES[i].cat] + '99';
  $('labels').appendChild(el); return { el, i };
});
const lhrLabel = document.createElement('div'); lhrLabel.className = 'clab'; lhrLabel.style.color = '#fff'; lhrLabel.style.fontSize = '22px'; lhrLabel.textContent = 'LONDON HEATHROW'; $('labels').appendChild(lhrLabel);

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
      ra.size.setX(nr, 10 + age * 1.4); ra.alpha.setX(nr, (1 - age / 30) * 0.9); nr++;
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
      ga.size.setX(ng, g.wide ? 30 : 24);
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
    da.alpha.setX(i, w * (1 + fin)); da.size.setX(i, (served ? 11 + 14 * pulse[i] + (BUSYSET.has(i) ? 6 : 0) : 7));
  }
  const rate = hourRate(m); const pp = 0.5 + 0.5 * Math.sin(t * 6.0);
  da.acol.setXYZ(RT.length, 1, 0.95, 0.98); da.size.setX(RT.length, 22 + rate * 0.10); da.alpha.setX(RT.length, 1);
  da.acol.setXYZ(RT.length + 1, 0.70, 0.50, 1.0); da.size.setX(RT.length + 1, 60 + rate * 0.4 + pp * 14); da.alpha.setX(RT.length + 1, 0.55);
  da.acol.setXYZ(RT.length + 2, 0.35, 0.55, 1.0); da.size.setX(RT.length + 2, 120 + rate * 0.6); da.alpha.setX(RT.length + 2, 0.22);
  for (const k of ['alpha', 'size', 'acol']) da[k].needsUpdate = true;
  return { act, pulse, inAir: GF.filter(g => m >= g.start && m <= g.end).length };
}
// ================================================================== AIRPORT
const sceneA = new THREE.Scene();
const camA = new THREE.PerspectiveCamera(30, 1032 / 372, 5, 45000);
const GS = 20000;
const RW = { '27R': { z: -845, e: 1610, w: -2290, len: 3900 }, '27L': { z: 575, e: 1650, w: -2010, len: 3660 } };
const APRONS = [[-2230, -560, -760, 300], [-520, -560, 1160, 310], [240, 820, 1280, 1110], [-2020, 820, -1080, 1260], [1260, 840, 1920, 1160]];
const TAXI = [ // polylines x,z
  [[-2350, -650], [1700, -650]], [[-2100, 385], [1720, 385]], [[-2250, -1030], [1640, -1030]], [[-2050, 780], [1740, 780]],
  [[-2350, -1030], [-2350, -650]], [[1700, -1030], [1700, -650]], [[-2100, 385], [-2100, 780]], [[1720, 385], [1720, 780]],
  [[-700, -650], [-700, 385]], [[-300, -650], [-300, 385]], [[1240, -650], [1240, 385]], [[-2350, -650], [-2350, -560]],
  [[600, -845], [380, -650]], [[-200, -845], [-420, -650]], [[-1000, -845], [-1220, -650]], [[700, 575], [480, 385]], [[-200, 575], [-420, 385]], [[-1000, 575], [-1220, 385]],
  [[-1400, -1030], [-1400, -845]], [[300, -1030], [300, -845]], [[1000, -1030], [1000, -845]], [[-1400, 780], [-1400, 575]], [[300, 780], [300, 575]], [[1000, 780], [1000, 575]],
];
function density(x, z) {
  if (x > -2800 && x < 2150 && z > -1300 && z < 1380) return 0;
  const n = 0.6 + 0.4 * Math.sin(x * 0.0011 + Math.sin(z * 0.0007) * 2) * Math.cos(z * 0.0013 - x * 0.0004);
  let d;
  if (x > 2300) d = 0.95;
  else if (z < -1500) d = x < -3700 ? 0.3 : 0.8;
  else if (z > 1550) d = x < -1800 ? 0.35 : 0.75;
  else if (x < -3600) d = 0.25;
  else d = 0.55;
  // reservoirs
  for (const r of RES) if (Math.abs(x - r[0]) < r[2] / 2 + 60 && Math.abs(z - r[1]) < r[3] / 2 + 60) return 0;
  if (Math.abs(x + 3450) < 60) return 0;
  return d * n;
}
const RES = [[-1700, 2350, 950, 720], [-2550, 3050, 1250, 520], [-5200, 900, 1300, 700], [-6500, -1100, 1150, 950], [-4400, -350, 500, 260], [-4900, 2300, 700, 400]];

const STREET = [], MWAY = [];
function makeGround() {
  const GT = 4096, GE = 2048;
  const c = document.createElement('canvas'); c.width = c.height = GT; const g = c.getContext('2d');
  const e = document.createElement('canvas'); e.width = e.height = GE; const ge = e.getContext('2d');
  const P = v => (v + GS / 2) / GS * GT, PE = v => (v + GS / 2) / GS * GE, M = v => v / GS * GT, ME = v => v / GS * GE;
  const r = rng(42);
  g.fillStyle = '#3c4a3b'; g.fillRect(0, 0, GT, GT);
  ge.fillStyle = '#000'; ge.fillRect(0, 0, GE, GE);
  // fields
  for (let i = 0; i < 1400; i++) {
    const x = (r() - 0.5) * GS, z = (r() - 0.5) * GS; const w = 150 + r() * 500, h = 120 + r() * 400;
    const d = density(x, z); if (d > 0.5 && r() < 0.8) continue;
    g.fillStyle = ['#4a6340', '#556d45', '#5d7348', '#475b3d', '#62754c'][r() * 5 | 0];
    g.save(); g.translate(P(x), P(z)); g.rotate((r() - 0.5) * 0.5); g.fillRect(-M(w) / 2, -M(h) / 2, M(w), M(h)); g.restore();
  }
  // suburban street grids
  for (let tx = -GS / 2; tx < GS / 2; tx += 900) for (let tz = -GS / 2; tz < GS / 2; tz += 900) {
    const d = density(tx + 450, tz + 450); if (d < 0.2) continue;
    const ang = (r() - 0.5) * 0.9, sp = 110 + r() * 80;
    g.save(); g.translate(P(tx + 450), P(tz + 450)); g.rotate(ang);
    ge.save(); ge.translate(PE(tx + 450), PE(tz + 450)); ge.rotate(ang);
    // houses
    const nh = Math.round(d * 260);
    for (let k = 0; k < nh; k++) {
      const hx = (r() - 0.5) * 900, hz = (r() - 0.5) * 900;
      if (density(tx + 450 + hx, tz + 450 + hz) < 0.15) continue;
      g.fillStyle = ['#5d5f60', '#6c6158', '#575a55', '#74695f', '#4f5a4b', '#646a6d'][r() * 6 | 0];
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
  // motorways & roads
  const road = (pts, wd, lightA) => {
    g.strokeStyle = '#7a7e81'; g.lineWidth = M(wd); g.lineCap = 'round';
    g.beginPath(); pts.forEach(([x, z], i) => i ? g.lineTo(P(x), P(z)) : g.moveTo(P(x), P(z))); g.stroke();
    ge.strokeStyle = `rgba(255,178,90,${lightA})`; ge.lineWidth = Math.max(1.2, ME(wd) * 0.7);
    ge.beginPath(); pts.forEach(([x, z], i) => i ? ge.lineTo(PE(x), PE(z)) : ge.moveTo(PE(x), PE(z))); ge.stroke();
    for (let i = 1; i < pts.length; i++) { const [x0, z0] = pts[i - 1], [x1, z1] = pts[i]; const L = Math.hypot(x1 - x0, z1 - z0); for (let d = 0; d < L; d += 45) { const u = d / L; MWAY.push(lerp(x0, x1, u), lerp(z0, z1, u)); } }
  };
  road([[-3450, -10000], [-3450, -2600], [-3480, 1200], [-3300, 3600], [-3700, 10000]], 40, 0.95);   // M25
  road([[-10000, -3000], [-3450, -3050], [2000, -3150], [10000, -3400]], 36, 0.9);                   // M4
  road([[-6000, -1460], [2600, -1460], [6000, -1500]], 22, 0.8);                                     // A4 Bath Road
  road([[-6000, 2150], [-3450, 2200], [-200, 1700], [2500, 1650], [10000, 2600]], 22, 0.8);           // A30 / A315
  road([[2600, -10000], [2600, -1460], [2650, 1650], [2700, 10000]], 18, 0.7);                       // A312
  road([[-2800, -1300], [2150, -1300], [2150, 1380], [-2800, 1380], [-2800, -1300]], 12, 0.6);       // perimeter
  // airport grass
  g.fillStyle = '#4f6b44'; g.fillRect(P(-2780), P(-1280), M(4910), M(2640));
  for (let i = 0; i < 300; i++) { g.fillStyle = `rgba(${70 + r() * 30},${100 + r() * 30},${60 + r() * 20},0.25)`; g.fillRect(P(-2780 + r() * 4900), P(-1280 + r() * 2640), M(60 + r() * 300), M(40 + r() * 200)); }
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
{ const pg = new THREE.RingGeometry(GS * 0.7, 60000, 64, 1); pg.rotateX(-Math.PI / 2); const m = new THREE.Mesh(pg, new THREE.MeshLambertMaterial({ color: 0x39463a, emissive: 0x3a2a18, emissiveIntensity: 0 })); m.position.y = -2; sceneA.add(m); sceneA.userData.far = m; }

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
for (const [k, lw] of [['27R', '09L'], ['27L', '09R']]) {
  const R = RW[k]; const pg = new THREE.PlaneGeometry(R.len, 60); pg.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(pg, new THREE.MeshLambertMaterial({ map: runwayTex(R.len, k, lw) }));
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
      addL(x, 4 + d * 0.01, R.z, WH, 26, 3); // sequenced flasher
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
building(-1900, -130, 176, 40, 396, 0xb7c3cf); building(-1450, -130, 52, 20, 442, 0xaab6c1); building(-1050, -130, 52, 20, 442, 0xaab6c1);
building(-2420, -130, 120, 24, 260, 0x8c8f93); building(-1900, 250, 120, 18, 60, 0x9aa0a6);
building(130, -60, 230, 28, 150, 0xa4acb4); building(380, -220, 320, 15, 40, 0xb2b8be); building(700, 60, 210, 26, 160, 0x9ea6ae);
building(860, -260, 40, 14, 300, 0xb2b8be); building(1010, 200, 260, 14, 40, 0xb2b8be); building(-150, 180, 180, 16, 60, 0x9aa0a6);
building(650, 1180, 520, 22, 90, 0xa7afb7); building(700, 990, 600, 12, 30, 0xb2b8be);
building(-1500, 1180, 400, 18, 120, 0x8f969c); building(-1000, 1200, 300, 18, 100, 0x8f969c);
building(1440, 1010, 170, 32, 120, 0xc0c5ca); building(1700, 1010, 170, 32, 120, 0xc0c5ca);
{ const r = rng(77); for (let x = -2300; x < 2300; x += 220 + r() * 160) building(x, -1400 - r() * 60, 50 + r() * 40, 24 + r() * 30, 30 + r() * 20, 0x9a9590); }
// control tower
{ const s = new THREE.Mesh(new THREE.CylinderGeometry(5, 7, 80, 16), new THREE.MeshLambertMaterial({ color: 0xc9ced3 })); s.position.set(300, 40, 70); sceneA.add(s);
  const cab = new THREE.Mesh(new THREE.CylinderGeometry(15, 11, 11, 20), new THREE.MeshLambertMaterial({ color: 0x5c6f80, emissive: 0x9fd0ff, emissiveIntensity: 0 })); cab.position.set(300, 84, 70); sceneA.add(cab); sceneA.userData.cab = cab;
  addL(300, 95, 70, RD, 14, 4); }
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
  const stands = [];
  for (const [x, w] of [[-1450, 52], [-1050, 52]]) for (let z = -310; z <= 50; z += 72) { stands.push([x - w / 2 - 30, z, 0, 1]); stands.push([x + w / 2 + 30, z, Math.PI, 1]); }
  for (let z = -300; z <= 40; z += 80) stands.push([-1900 + 88 + 34, z, Math.PI, 1]);
  for (let x = 260; x <= 520; x += 52) { stands.push([x, -220 - 20 - 22, Math.PI / 2, 0]); stands.push([x, -220 + 20 + 22, -Math.PI / 2, 0]); }
  for (let z = -380; z <= -150; z += 70) { stands.push([860 - 20 - 34, z, 0, 1]); stands.push([860 + 20 + 34, z, Math.PI, 1]); }
  for (let x = 450; x <= 960; x += 75) stands.push([x, 990 - 15 - 34, -Math.PI / 2, 1]);
  for (let x = -1650; x <= -1350; x += 80) stands.push([x, 1100, -Math.PI / 2, 1]);
  const r = rng(5);
  const tailCols = ['#1d3c78', '#c8102e', '#0b6e4f', '#5a2d82', '#e2e6ea', '#0d2b56', '#9b1b30', '#f2a900'];
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

const TAN3 = Math.tan(3 * D2R);
function arrPose(tau, rw) {
  const R = RW[rw]; const xtd = R.e - 400; const side = R.z < 0 ? 1 : -1;
  let x, y = 0, z = R.z, hd = Math.PI, pitch = 0, alpha = 1, land = 0;
  if (tau < 0) { const d = -tau * 3250; x = xtd + d; y = d > 250 ? d * TAN3 + 12 : 25.1 * Math.pow(d / 250, 1.6); pitch = 3 * D2R; alpha = smooth(-2.15, -1.85, tau); land = 1; }
  else if (tau < 0.93) { const a = 2849.5; const d = 3250 * tau - 0.5 * a * tau * tau; x = xtd - d; pitch = 3 * D2R * (1 - smooth(0, 0.15, tau)); land = 1 - smooth(0.3, 0.6, tau); }
  else { const u = tau - 0.93; const th = smooth(0, 0.3, u) * 38 * D2R; x = xtd - 1790 - 520 * u * Math.cos(th * 0.5); z = R.z + side * 520 * u * Math.sin(th * 0.6); hd = Math.PI + side * th; alpha = 1 - smooth(0.2, 0.5, u); }
  return { x, y, z, hd, pitch, alpha, land };
}
function depPose(tau, rw, seed) {
  const R = RW[rw]; const x0 = R.e - 60; const side = R.z < 0 ? 1 : -1;
  let x, y = 0, z = R.z, hd = Math.PI, pitch = 0, alpha = 1, land = 0;
  if (tau < 0) { const u = smooth(-0.36, 0, tau); const ang = u * Math.PI / 2; x = x0 + 110 * Math.sin(Math.PI / 2 - ang) * 0 + 110 * (1 - Math.sin(ang)); z = R.z + side * 120 * (1 - Math.sin(ang + 0.0)) * (1 - u * 0.0); hd = Math.PI / 2 * side * -1 * (1 - u) + Math.PI * u; if (side < 0) hd = -Math.PI / 2 * (1 - u) + Math.PI * u; else hd = Math.PI / 2 * (1 - u) + Math.PI * u; alpha = smooth(-0.46, -0.32, tau); land = 0.6; }
  else if (tau < 0.81) { const d = 0.5 * 5487 * tau * tau; x = x0 - d; land = 1; pitch = 0; if (tau > 0.72) pitch = smooth(0.72, 0.81, tau) * 7 * D2R; }
  else {
    const u = tau - 0.81; const d = 1800 + 4444 * u + 300 * u * u; x = x0 - d; y = 560 * Math.pow(u, 1.15); pitch = (7 + 3 * smooth(0, 0.2, u)) * D2R; land = 1 - smooth(0.5, 0.9, u);
    const turn = (seed < 0.5 ? -1 : 1) * smooth(0.9, 1.9, u) * 28 * D2R; hd = Math.PI + turn;
    z = R.z + (seed < 0.5 ? 1 : -1) * 2200 * Math.pow(smooth(0.9, 2.2, u), 1.6);
    alpha = 1 - smooth(1.9, 2.5, u);
  }
  return { x, y, z, hd, pitch, alpha, land };
}


// ================================================================== AIRPORT MOVEMENTS
function pickInset() {
  const ev = [];
  for (const type of ['A', 'D']) for (let h = 0; h < 24; h++) {
    const fs = FL.filter(f => f.type === type && Math.floor(f.t / 60) === h);
    if (!fs.length) continue;
    const len = vidT((h + 1) * 60) - vidT(h * 60);
    const k = Math.min(fs.length, Math.max(1, Math.floor(len * 2.3)));
    for (let i = 0; i < k; i++) { const f = fs[Math.min(fs.length - 1, Math.floor((i + 0.5) * fs.length / k))]; ev.push({ type, t: vidT(f.t), rw: f.rw, cat: ROUTES[f.r].cat, wide: WIDE.has(f.ac), seed: (f.t * 13.7) % 1 }); }
  }
  return ev.sort((a, b) => a.t - b.t);
}
const INSET = pickInset();
const INTRO_EV = [
  { type: 'A', t: 3.7, rw: '27R', cat: 3, wide: true, seed: 0.3, intro: true },
  { type: 'A', t: 6.5, rw: '27R', cat: 0, wide: false, seed: 0.7, intro: true },
];
const ALL_EV = INTRO_EV.concat(INSET);

// camera shots for the live airport panel (cuts are hidden by a quick dip to black)
const SHOTS = [
  { t0: 9.0, t1: 17.0, name: 'CAM 1 · AERIAL', p0: [2600, 1050, 2700], p1: [2150, 900, 2200], q0: [-520, 0, -260], q1: [-650, 0, -300], fov: 34, sc: 2.4, sf: 1.0, near: 0.6 },
  { t0: 17.0, t1: 24.0, name: 'CAM 2 · APPROACH 27R', p0: [860, 34, -640], p1: [960, 36, -650], q0: [5200, 230, -870], q1: [5200, 210, -870], fov: 40, sc: 1.35, sf: 0.4, near: 1.25 },
  { t0: 24.0, t1: 31.0, name: 'CAM 3 · RUNWAY 27L', p0: [-40, 26, 860], p1: [-150, 26, 850], q0: [-760, 95, 560], q1: [-880, 95, 560], fov: 38, sc: 2.1, sf: 0.45, near: 1.2 },
  { t0: 31.0, t1: 38.0, name: 'CAM 4 · TOWER VIEW', p0: [470, 185, 130], p1: [420, 185, 100], q0: [-1700, 20, -170], q1: [-1700, 20, -120], fov: 46, sc: 1.5, sf: 0.75, near: 0.9 },
  { t0: 38.0, t1: 45.0, name: 'CAM 5 · TERMINAL 5', p0: [-1330, 120, 230], p1: [-1200, 112, 205], q0: [-560, 20, -845], q1: [-730, 20, -845], fov: 42, sc: 1.35, sf: 0.55, near: 1.1 },
  { t0: 45.0, t1: 60.0, name: 'CAM 6 · AERIAL', orbit: true, fov: 36, sc: 2.5, sf: 1.0, near: 0.6 },
];
const CUTS = SHOTS.slice(1).map(s => s.t0);
const V3 = a => new THREE.Vector3(a[0], a[1], a[2]);
function airportCam(t) {
  if (t < 8.6) {
    const P0 = V3([4500, 500, -520]), P1 = V3([3850, 415, -580]), Q0 = V3([-700, 0, -720]), Q1 = V3([-900, 0, -740]);
    if (t <= T_RISE) { const u = smooth(0, 1, t / T_RISE) * 0.6 + (t / T_RISE) * 0.4; return { p: P0.lerp(P1, u), q: Q0.lerp(Q1, u), fov: 44, sc: 2.0, sf: 0.5 }; }
    const k = ease((t - T_RISE) / 2.0);
    return { p: new THREE.Vector3(lerp(P1.x, 500, k), P1.y * Math.pow(13, k), lerp(P1.z, 140, k)), q: new THREE.Vector3(lerp(Q1.x, -380, k), 0, lerp(Q1.z, -130, k)), fov: 44, sc: 2.0, sf: 0.5 };
  }
  let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (t < x.t1) { s = x; break; }
  const u = clamp((t - s.t0) / (s.t1 - s.t0), 0, 1);
  if (s.orbit) { const a = lerp(0.55, 1.35, (t - s.t0) / 15); const c = V3([-350, 0, -130]); return { ...s, p: new THREE.Vector3(c.x + 3600 * Math.cos(a), 1300, c.z + 3600 * Math.sin(a)), q: c }; }
  return { ...s, p: V3(s.p0).lerp(V3(s.p1), u), q: V3(s.q0).lerp(V3(s.q1), u) };
}

function updateAirport(t, night, cam) {
  let pi = 0; const la = acLtGeo.attributes; let nl = 0; const v = new THREE.Vector3();
  for (const e of ALL_EV) {
    const tau = t - e.t; const sf = e.intro ? 0.5 : cam.sf; const te = tau * sf;
    let p = null;
    if (e.type === 'A') { if (te > -2.2 && te < 1.5) p = arrPose(te, e.rw); }
    else if (te > -0.5 && te < 3.4) p = depPose(te, e.rw, e.seed);
    if (!p || p.alpha <= 0.001 || pi >= POOL.length) continue;
    const o = POOL[pi++]; const g = o.g; g.visible = true;
    const sc = (e.wide ? 1.85 : 1.0) * (e.intro ? 2.0 : cam.sc);
    g.scale.setScalar(sc); g.position.set(p.x, p.y + 2.6 * sc, p.z); g.rotation.set(0, p.hd, p.pitch, 'YZX');
    o.bm.opacity = o.tm.opacity = p.alpha; o.bm.depthWrite = o.tm.depthWrite = p.alpha > 0.95;
    o.tm.color.copy(CATC[e.cat]); o.tm.emissive.copy(CATC[e.cat]); o.tm.emissiveIntensity = 0.25 + 0.45 * night;
    o.bm.emissiveIntensity = 0.35 * night;
    g.updateMatrixWorld(true);
    for (const L of AC_LIGHTS) {
      let a = 1;
      if (L[5] === 1) a = (((t * 1.3 + e.seed) % 1) < 0.08) ? 1.4 : 0;
      else if (L[5] === 2) a = (((t * 1.0 + e.seed * 0.7) % 1) < 0.25) ? 1 : 0.1;
      else if (L[5] === 3) a = p.land * (0.3 + 0.9 * night);
      a *= p.alpha * (0.45 + 0.7 * night);
      if (a <= 0.01 || nl >= POOL.length * 8) continue;
      v.set(L[0], L[1], L[2]).applyMatrix4(g.matrixWorld);
      la.position.setXYZ(nl, v.x, v.y, v.z); la.acol.setXYZ(nl, ...L[3]); la.size.setX(nl, L[4] * (L[5] === 3 ? 1 : 1.6)); la.alpha.setX(nl, a); nl++;
    }
  }
  for (; pi < POOL.length; pi++) POOL[pi].g.visible = false;
  acLtGeo.setDrawRange(0, nl); for (const k of ['position', 'acol', 'size', 'alpha']) la[k].needsUpdate = true;
  const lt = ltGeo.attributes;
  for (let i = 0; i < LT.length; i++) {
    const L = LT[i]; let a = 0.35 + 0.85 * night;
    if (L.kind === 1) a = 0.15 + 0.95 * night;
    if (L.kind === 3) { const d = Math.abs(L.x - (L.x > 0 ? 1630 : -2150)); const ph = ((t * 2.0) % 1); a = Math.abs(1 - d / 900 - ph) < 0.035 ? 1.6 * (0.3 + night) : 0; }
    if (L.kind === 4) a = ((t % 1.2) < 0.6 ? 1 : 0.2) * (0.5 + night);
    lt.alpha.setX(i, a);
  }
  lt.alpha.needsUpdate = true;
}

let aMode = '';
function setAMode(mode) {
  if (mode === aMode) return; aMode = mode; const c = $('glA');
  if (mode === 'full') { rA.setSize(W, H, false); Object.assign(c.style, { left: '0px', top: '0px', width: W + 'px', height: H + 'px', borderRadius: '0px' }); }
  else { rA.setSize(1000, 390, false); Object.assign(c.style, { left: '40px', top: '1494px', width: '1000px', height: '390px', borderRadius: '24px' }); }
}

function lightAirport(t, vm, cam, rcw, rch) {
  const m = clamp(vm, 0, 1440);
  const wx = wxAt(m);
  const sl = sunLocal(mod1440(vm)); const el = Math.asin(clamp(sl.y, -1, 1)) / D2R;
  const day = smooth(-5, 7, el), night = 1 - smooth(-7, 3, el);
  camA.position.copy(cam.p); camA.lookAt(cam.q); camA.fov = cam.fov; camA.aspect = rcw / rch; camA.updateProjectionMatrix();
  sky.position.copy(camA.position);
  const cl = wx.cloud, rn = wx.rain, mist = wx.mist;
  const zNight = new THREE.Color('#070d24'), hNight = new THREE.Color('#2a2a52').lerp(new THREE.Color('#4a3048'), 0.35);
  const zDay = new THREE.Color('#3f7fd0').lerp(new THREE.Color('#5f6a77'), cl), hDay = new THREE.Color('#a9cbe8').lerp(new THREE.Color('#9aa3ab'), cl);
  const zen = zNight.clone().lerp(zDay, day), hor = hNight.clone().lerp(hDay, day);
  const twi = Math.exp(-Math.pow((el - 0.5) / 6.0, 2)) * (1 - cl * 0.5);
  const warm = mod1440(vm) < 720 ? new THREE.Color('#f39a5e') : new THREE.Color('#f06a42');
  hor.lerp(warm, twi * 0.8); zen.lerp(new THREE.Color('#33407e'), twi * 0.45);
  hor.lerp(new THREE.Color('#b8bfc8'), mist * 0.6 * day + mist * 0.2);
  skyMat.uniforms.zen.value.copy(zen); skyMat.uniforms.hor.value.copy(hor);
  skyMat.uniforms.sunDir.value.copy(sl); skyMat.uniforms.sunCol.value.set(el < 8 ? '#ffa860' : '#fff2d8'); skyMat.uniforms.sunAmt.value = smooth(-4, 2, el) * (1 - cl * 0.8);
  skyMat.uniforms.stars.value = night * (1 - cl);
  sceneA.fog.color.copy(hor);
  sceneA.fog.near = lerp(2500, 600, mist) * (1 - rn * 0.3); sceneA.fog.far = lerp(26000, 9000, mist) * (1 - rn * 0.35);
  sunL.position.copy(sl).multiplyScalar(5000); sunL.target.position.set(0, 0, 0);
  sunL.intensity = day * (1 - cl * 0.65) * 2.4; sunL.color.set(el < 10 ? '#ffc58a' : '#fff4e2');
  hemi.intensity = 0.32 + 1.15 * day * (1 - cl * 0.2); hemi.color.copy(zen.clone().lerp(new THREE.Color('#ffffff'), 0.5)); hemi.groundColor.set(day > 0.5 ? '#5a5a48' : '#1c2030');
  groundMat.emissiveIntensity = Math.pow(night, 1.2) * 0.6;
  const us = rch / (2 * Math.tan(camA.fov * D2R / 2));
  streetMat.uniforms.uInt.value = Math.pow(night, 1.3) * (rch > 1000 ? 1.5 : 1.1); streetMat.uniforms.uScale.value = us; streetMat.uniforms.uFog.value = sceneA.fog.far * 0.45; streetMat.uniforms.uMin.value = 1.3;
  sceneA.userData.far.material.emissiveIntensity = night * 0.6;
  for (const k2 in bMats) bMats[k2].emissiveIntensity = 0.12 + night * 0.95;
  sceneA.userData.cab.material.emissiveIntensity = 0.2 + night * 0.9;
  for (const hz of HAZE) hz.material.opacity = night * 0.55;
  bodyMatShared.emissiveIntensity = 0.30 * night; sceneA.userData.parkedTail.material.emissiveIntensity = 0.25 * night;
  ltMat.uniforms.uScale.value = us * (rch > 1000 ? 1.25 : 1); ltMat.uniforms.uFog.value = sceneA.fog.far * 0.55; ltMat.uniforms.uMin.value = rch > 1000 ? 2.2 : 1.6;
  acLt.material.uniforms.uScale.value = us; acLt.material.uniforms.uFog.value = sceneA.fog.far * 0.6; acLt.material.uniforms.uMin.value = 1.8;
  const wdir = (wx.dir + 180) * D2R; const wvx = Math.sin(wdir), wvz = -Math.cos(wdir);
  const cc = new THREE.Color('#ffffff').lerp(new THREE.Color('#6d7682'), rn).lerp(new THREE.Color('#1a2138'), night);
  CLOUDS.forEach(s => { const u = s.userData; const span = 26000; let x = u.x + wvx * vm * 9, z = u.z + wvz * vm * 9; x = ((x + span / 2) % span + span) % span - span / 2; z = ((z + span / 2) % span + span) % span - span / 2; s.position.set(x, u.y, z); s.material.opacity = clamp(cl * 1.3 - u.ph * 0.6, 0, 1) * 0.9; s.material.color.copy(cc).lerp(warm, twi * 0.5); });
  const rp = rainGeo.attributes.position; const fwd = new THREE.Vector3().subVectors(cam.q, cam.p).setY(0).normalize(); const rc0 = cam.p.clone().addScaledVector(fwd, 1200);
  for (let i = 0; i < RAIN_N; i++) {
    const s = rainSeed[i]; const x = rc0.x + (s[0] - 0.5) * 2400, z = rc0.z + (s[1] - 0.5) * 2400; const y = cam.p.y - 300 + ((s[2] * 900 - t * 2600) % 900 + 900) % 900;
    rp.setXYZ(i * 2, x + wvx * 14, y + 40, z + wvz * 14); rp.setXYZ(i * 2 + 1, x, y, z);
  }
  rp.needsUpdate = true; rainMat.opacity = rn * 0.34;
  if (windObj) { sceneA.remove(windObj); windObj.geometry.dispose(); windObj = null; }
  { const pos = [], col = []; const sp = 260 + wx.kt * 60; const wa = clamp((wx.kt - 3) / 14, 0.25, 1) * (0.45 + 0.55 * day) * 0.26 * smooth(8.8, 9.8, t);
    if (wa > 0.002) {
      for (let i = 0; i < WS_N; i++) {
        const s = windSeed[i]; const span = 9000; const L = 260 + s[2] * 380;
        const a = (s[0] * span + t * sp) % span - span / 2; const b = (s[1] - 0.5) * span;
        const cx = -300 + wvx * a - wvz * b, cz = 200 + wvz * a + wvx * b; const y = 50 + s[3] * 260;
        const life = Math.sin(Math.PI * ((s[0] * span + t * sp) % span) / span);
        for (let j = 0; j < WS_SEG; j++) {
          const u0 = j / WS_SEG, u1 = (j + 1) / WS_SEG; const w0 = Math.sin(Math.PI * u0) * wa * life, w1 = Math.sin(Math.PI * u1) * wa * life;
          const wob = Math.sin((t * 2 + s[1] * 9 + u0 * 4)) * 10;
          pos.push(cx + wvx * L * (u0 - 0.5) - wvz * wob, y, cz + wvz * L * (u0 - 0.5) + wvx * wob, cx + wvx * L * (u1 - 0.5) - wvz * wob, y, cz + wvz * L * (u1 - 0.5) + wvx * wob);
          col.push(w0 * 0.85, w0 * 0.95, w0 * 1.1, w1 * 0.85, w1 * 0.95, w1 * 1.1);
        }
      }
      const g = new LineSegmentsGeometry(); g.setPositions(pos); g.setColors(col); windMat.resolution.set(rcw, rch); windObj = new LineSegments2(g, windMat); windObj.frustumCulled = false; sceneA.add(windObj);
    } }
  return { wx, el, night, day };
}

// ================================================================== GLOBE CAMERA PATH
//       t     lat    lon   dist   centreY
const GK = [
  [7.0, 51.47, -0.45, 1.08, 960],
  [10.2, 24, 2, 9.4, 650],
  [19.0, 22, -4, 9.4, 650],
  [21.5, 36, -32, 6.4, 650],
  [27.5, 38, -27, 6.2, 650],
  [30.0, 48, 6, 3.7, 650],
  [35.5, 49, 9, 3.6, 650],
  [38.0, 31, 45, 6.6, 650],
  [43.5, 29, 52, 6.4, 650],
  [46.0, 23, 4, 9.4, 650],
  [52.0, 22, 8, 9.4, 650],
  [54.6, 22, -16, 7.3, 975],
  [60.0, 20, -36, 7.2, 975],
];
const VIEWS = [[10.2, 'WORLDWIDE'], [21.5, 'ACROSS THE ATLANTIC'], [30.0, 'EUROPE'], [38.0, 'MIDDLE EAST & ASIA'], [46.0, 'WORLDWIDE']];
function globeCam(t) {
  if (t <= GK[0][0]) return GK[0].slice(1);
  for (let i = 0; i < GK.length - 1; i++) if (t < GK[i + 1][0]) {
    const a = GK[i], b = GK[i + 1]; const k = ease((t - a[0]) / (b[0] - a[0]));
    return [lerp(a[1], b[1], k), lerp(a[2], b[2], k), Math.exp(lerp(Math.log(a[3]), Math.log(b[3]), k)), lerp(a[4], b[4], k)];
  }
  return GK[GK.length - 1].slice(1);
}

// ================================================================== HUD
function odoPos(v, i) { const q = Math.pow(10, i); const fl = Math.floor(v / q); return (fl % 10) + smooth(q - 0.4, q, v - fl * q); }
class Odo {
  constructor(el, nd, fs, cw, commas, grad) {
    el.classList.remove('grad', 'gradPax');
    this.lh = Math.round(fs * 1.12); this.cw = cw; this.grad = grad; this.items = [];
    el.style.fontSize = fs + 'px'; el.style.height = this.lh + 'px'; el.style.lineHeight = this.lh + 'px';
    for (let i = nd - 1; i >= 0; i--) {
      const c = document.createElement('div'); c.className = 'col'; c.style.width = cw + 'px'; c.style.height = this.lh + 'px';
      const s = document.createElement('div'); s.className = 'strip';
      s.innerHTML = Array.from({ length: 11 }, (_, d) => `<div style="height:${this.lh}px">${d % 10}</div>`).join('');
      c.appendChild(s); el.appendChild(c); this.items.push({ i, c, s, w: cw, digit: true });
      if (commas && i > 0 && i % 3 === 0) { const sp = document.createElement('div'); sp.className = 'sepc'; sp.textContent = ','; sp.style.width = (cw * 0.42) + 'px'; sp.style.height = this.lh + 'px'; el.appendChild(sp); this.items.push({ i: i - 0.5, c: sp, s: sp, w: cw * 0.42, digit: false }); }
    }
  }
  set(v) {
    v = Math.max(0, v); const n = Math.max(1, String(Math.floor(v + 0.4)).length);
    let x = 0; const vis = this.items.filter(it => it.digit ? it.i < n : it.i < n - 1);
    const tot = vis.reduce((s, it) => s + it.w, 0);
    for (const it of this.items) {
      const on = vis.includes(it); it.c.style.display = on ? 'block' : 'none'; if (!on) continue;
      if (it.digit) it.s.style.transform = `translateY(${-odoPos(v, it.i) * this.lh}px)`;
      if (this.grad) { const t = it.s; t.style.backgroundImage = this.grad; t.style.backgroundSize = `${tot}px 100%`; t.style.backgroundPosition = `${-x}px 0`; t.style.webkitBackgroundClip = 'text'; t.style.backgroundClip = 'text'; t.style.color = 'transparent'; }
      x += it.w;
    }
  }
}
const GRAD_PAX = 'linear-gradient(90deg, #FFD27A 0%, #FF9E5E 45%, #FF6FB5 100%)';
const GRAD_ALL = 'linear-gradient(90deg, #5AA9FF 0%, #A06BFF 50%, #FF6FB5 100%)';
const oPax = new Odo($('oPax'), 6, 98, 61, true, GRAD_PAX);
const oDep = new Odo($('oDep'), 3, 92, 57, false, null);
const oArr = new Odo($('oArr'), 3, 92, 57, false, null);
const oT1 = new Odo($('oT1'), 3, 84, 52, false, null); $('oT1').style.color = 'var(--arr)';
const oT2 = new Odo($('oT2'), 3, 84, 52, false, null); $('oT2').style.color = 'var(--dep)';
const oT3 = new Odo($('oT3'), 6, 84, 52, true, GRAD_PAX);
const oT4 = new Odo($('oT4'), 4, 84, 52, true, GRAD_ALL);

const hoursEl = $('hours'); const hourBars = [];
for (let h = 0; h < 24; h++) { const b = document.createElement('div'); b.className = 'b'; b.style.left = (h * 41 + 4) + 'px'; b.style.height = '0px'; b.style.background = 'linear-gradient(180deg,#A06BFF,#5AA9FF)'; hoursEl.appendChild(b); hourBars.push(b); }
const HMAX = Math.max(...S.stats.hourly);
const ICONS = {
  SUNNY: `<circle cx="24" cy="24" r="9" fill="#FFD166"/><g stroke="#FFD166" stroke-width="3" stroke-linecap="round">${[0, 45, 90, 135, 180, 225, 270, 315].map(a => `<line x1="${24 + Math.cos(a * D2R) * 14}" y1="${24 + Math.sin(a * D2R) * 14}" x2="${24 + Math.cos(a * D2R) * 19}" y2="${24 + Math.sin(a * D2R) * 19}"/>`).join('')}</g>`,
  CLEAR: `<path d="M30 8 A16 16 0 1 0 40 32 A13 13 0 1 1 30 8 Z" fill="#d8e2ff"/>`,
  CLOUD: `<path d="M14 36 H36 A8 8 0 0 0 35 20 A11 11 0 0 0 14 22 A7 7 0 0 0 14 36 Z" fill="#c9d3e6"/>`,
  RAIN: `<path d="M14 30 H36 A8 8 0 0 0 35 14 A11 11 0 0 0 14 16 A7 7 0 0 0 14 30 Z" fill="#9fb0cc"/><g stroke="#5AA9FF" stroke-width="3" stroke-linecap="round"><line x1="17" y1="35" x2="14" y2="43"/><line x1="25" y1="35" x2="22" y2="43"/><line x1="33" y1="35" x2="30" y2="43"/></g>`,
  MIST: `<g stroke="#c9d3e6" stroke-width="3.4" stroke-linecap="round"><line x1="8" y1="16" x2="40" y2="16"/><line x1="12" y1="24" x2="36" y2="24"/><line x1="8" y1="32" x2="40" y2="32"/></g>`,
};
ICONS.PART_D = `<g transform="translate(-6,-6) scale(0.8)">${ICONS.SUNNY}</g><g transform="translate(4,4) scale(0.9)">${ICONS.CLOUD}</g>`;
ICONS.PART_N = `<g transform="translate(-4,-6) scale(0.8)">${ICONS.CLEAR}</g><g transform="translate(4,4) scale(0.9)">${ICONS.CLOUD}</g>`;
let lastIcon = '';

const firstArr = FL.find(f => f.type === 'A' && f.t > 240), firstDep = FL.find(f => f.type === 'D');
const lastDep = [...FL].reverse().find(f => f.type === 'D');
const pax200 = (() => { let s = 0; for (const f of FL) { s += f.pax; if (s >= 200000) return f.t; } return 1200; })();
const TOASTS = [
  { m: firstArr.t, tm: hhmm(firstArr.t), a: 'FIRST LONG-HAUL ARRIVAL', b: `${firstArr.fn} from ${ROUTES[firstArr.r].city}` },
  { m: firstDep.t, tm: hhmm(firstDep.t), a: 'FIRST DEPARTURE', b: `${firstDep.fn} to ${ROUTES[firstDep.r].city}` },
  { m: 420, tm: '06:55', a: 'SUNRISE', b: 'the morning arrival rush begins' },
  { m: S.stats.busiest * 60 + 20, tm: pad2(S.stats.busiest) + ':00', a: 'BUSIEST HOUR', b: `${S.stats.hourly[S.stats.busiest]} take-offs and landings in 60 minutes` },
  { m: 815, tm: '13:35', a: 'SHOWERS ROLL IN', b: 'wind veering west, gusts near 30 kt' },
  { m: 900, tm: '15:00', a: 'RUNWAY SWITCH', b: 'arrivals move to 27L · departures to 27R' },
  { m: 996, tm: '16:36', a: 'SUNSET', b: 'the evening wave of long-haul departures' },
  { m: pax200, tm: hhmm(pax200), a: '200,000 PASSENGERS', b: 'and counting' },
  { m: lastDep.t, tm: hhmm(lastDep.t), a: 'LAST DEPARTURE', b: `${lastDep.fn} to ${ROUTES[lastDep.r].city}` },
];
TOASTS.forEach(x => x.t = vidT(x.m));
let lastToast = -1;

// z-order: globe < airport canvas < vignette < HUD < intro < finale
$('glG').style.zIndex = 0; $('glA').style.zIndex = 1; $('vignette').style.zIndex = 2; $('hud').style.zIndex = 3; $('introLayer').style.zIndex = 4; $('finale').style.zIndex = 5;
const fade = (id, a, dy = 0) => { const e = $(id); e.style.opacity = a; if (dy) e.style.transform = `translateY(${(1 - a) * dy}px)`; };

// ================================================================== FRAME
function renderFrame(t) {
  const m = dayMin(t), vm = visMin(t);
  const fin = smooth(52.0, 54.0, t);
  // ---- globe
  const [glat, glon, gd, gy] = globeCam(t);
  setGlobeCenterY(gy);
  camG.position.copy(llv(glat, glon + Math.sin(t * 0.13) * 1.2, gd)); camG.up.set(0, 1, 0); camG.lookAt(0, 0, 0);
  camG.near = Math.max(0.01, gd - 1.25); camG.far = 120; camG.updateProjectionMatrix();
  const sunG = sunECEF(mod1440(vm));
  globeMat.uniforms.sunDir.value.copy(sunG); globeMat.uniforms.camPos.value.copy(camG.position); atmoMat.uniforms.sunDir.value.copy(sunG);
  const gs = updateGlobe(t, vm, fin);
  rG.render(sceneG, camG);

  // ---- airport
  const fullMode = t < 8.6;
  const aOp = fullMode ? 1 - smooth(7.2, 8.4, t) : smooth(9.0, 9.6, t) * (1 - smooth(52.0, 52.7, t));
  setAMode(fullMode ? 'full' : 'inset');
  $('glA').style.opacity = aOp;
  const cam = airportCam(t);
  const lit = lightAirport(t, fullMode ? 0 : vm, cam, fullMode ? W : 1000, fullMode ? H : 390);
  if (aOp > 0.001) { updateAirport(t, lit.night, cam); rA.render(sceneA, camA); }

  // ---- intro titles
  const io = 1 - smooth(5.8, 6.5, t);
  $('introLayer').style.opacity = io; $('introLayer').style.display = io > 0.001 ? 'block' : 'none';
  if (io > 0.001) {
    const h = $('tHeathrow'); const k1 = easeOut((t - 0.6) / 1.5);
    h.style.opacity = smooth(0.6, 1.4, t); h.style.letterSpacing = lerp(48, 4, k1) + 'px'; h.style.transform = `scale(${lerp(1.08, 1, k1)})`;
    h.style.filter = `blur(${lerp(14, 0, smooth(0.6, 1.6, t))}px) drop-shadow(0 0 28px rgba(140,120,255,${0.55 * smooth(1.2, 2.0, t)}))`;
    fade('tSky', smooth(1.6, 2.3, t), 24); $('tSky').style.letterSpacing = lerp(22, 10, easeOut((t - 1.6) / 1.2)) + 'px';
    const rw = 400 * easeOut((t - 2.0) / 0.9); $('tRule').style.width = rw + 'px'; $('tRule').style.left = (540 - rw / 2) + 'px';
    for (const [id, t0] of [['s1', 3.0], ['s2', 3.5], ['s3', 4.0]]) { const a = smooth(t0, t0 + 0.4, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateY(${(1 - a) * 16}px)`; }
    $('intro').style.transform = `translateY(${-smooth(5.8, 6.5, t) * 30}px)`;
  }

  // ---- HUD visibility
  const hudOut = 1 - smooth(52.0, 52.8, t);
  fade('hdr', smooth(8.6, 9.4, t) * hudOut, -20);
  for (const id of ['inair', 'view', 'legend']) fade(id, smooth(8.9, 9.7, t) * hudOut);
  $('labels').style.opacity = smooth(8.9, 9.7, t) * (1 - fin);
  fade('stats', smooth(9.0, 9.9, t) * hudOut, 40);
  const camA_ = smooth(9.0, 9.6, t) * hudOut;
  for (const id of ['camEdge', 'camLabel', 'wchip', 'rwy']) $(id).style.opacity = camA_ * (fullMode ? 0 : 1);
  let dip = 0; for (const c of CUTS) dip = Math.max(dip, 1 - smooth(0, 0.24, Math.abs(t - c)));
  $('camDip').style.opacity = fullMode ? 0 : dip * hudOut;

  // header
  $('clock').textContent = hhmm(t >= TE ? 1439.99 : m);
  $('clocksub').textContent = t >= TE ? 'END OF DAY · GMT' : 'LOCAL TIME · GMT';
  const frac = clamp(m / 1440, 0, 1);
  $('fill').style.width = (frac * 984) + 'px'; $('marker').style.left = (frac * 984) + 'px';
  const isDay = lit.el > -0.8;
  $('marker').style.background = isDay ? 'radial-gradient(circle, #fff6c8 0%, #FFD166 55%, rgba(255,209,102,0) 72%)' : 'radial-gradient(circle, #ffffff 0%, #c9d6ff 50%, rgba(201,214,255,0) 72%)';
  $('marker').style.boxShadow = isDay ? '0 0 18px 6px rgba(255,200,90,0.55)' : '0 0 16px 5px rgba(170,190,255,0.5)';
  for (let h = 0; h < 24; h++) {
    const n = ub(allT, Math.min(m, (h + 1) * 60)) - ub(allT, h * 60);
    hourBars[h].style.height = (Math.max(0, n) / HMAX * 36) + 'px';
    hourBars[h].style.opacity = (m >= h * 60 && m < (h + 1) * 60) ? 1 : 0.5;
  }
  $('inairN').textContent = fmt(gs.inAir);
  let vn = ''; for (const [vt, name] of VIEWS) if (t >= vt - 1.2) vn = name; $('view').textContent = vn ? 'VIEW · ' + vn : '';

  // counters
  oPax.set(paxAt(m)); oDep.set(contCount(depT, m)); oArr.set(contCount(arrT, m));
  const lastH = (arr) => ub(arr, m) - ub(arr, m - 60);
  $('sPax').textContent = m > 30 ? `+${fmt(paxAt(m) - paxAt(m - 60))} in the last hour` : '';
  $('sDep').textContent = m > 30 ? `+${lastH(depT)} last hour` : '';
  $('sArr').textContent = m > 30 ? `+${lastH(arrT)} last hour` : '';

  // labels on the globe
  const camDir = camG.position.clone().normalize();
  const wA = smooth(5.0, 6.2, gd), eA = 1 - smooth(4.4, 5.6, gd);
  const proj = v => { const p = v.clone().project(camG); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H]; };
  const lhrS = proj(LV.clone().multiplyScalar(1.01));
  for (const L of labelEls) {
    const rt = RT[L.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    const served = ub(routeTimes[L.i], vm) > 0 || gs.act[L.i] > 0;
    L.el.style.left = x + 'px'; L.el.style.top = y + 'px';
    L.el.style.opacity = vis * (L.kind === 'w' ? wA : eA) * (served ? 0.55 + 0.45 * Math.min(1, gs.act[L.i] / 2) : 0.3) * (y > 250 && y < 1040 ? 1 : 0);
  }
  for (const B of busyEls) {
    const rt = RT[B.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    const dist = Math.hypot(x - lhrS[0], y - lhrS[1]);
    B.el.style.left = x + 'px'; B.el.style.top = y + 'px';
    B.el.style.opacity = vis * smooth(70, 120, dist) * (y > 250 && y < 1030 ? 1 : 0) * (ub(routeTimes[B.i], vm) > 0 ? 1 : 0.0) * (1 - fin);
    B.el.querySelector('.n').textContent = '× ' + ub(routeTimes[B.i], Math.min(vm, 1440));
  }
  lhrLabel.style.left = (lhrS[0] - 18) + 'px'; lhrLabel.style.top = (lhrS[1] + 14) + 'px'; lhrLabel.style.transform = 'translate(-100%, 0)';
  lhrLabel.style.opacity = smooth(0.12, 0.3, LV.dot(camDir)) * (1 - fin);

  // time cards
  let tA = 0, tI = -1;
  TOASTS.forEach((x, i) => { const a = smooth(x.t - 0.05, x.t + 0.25, t) * (1 - smooth(x.t + 1.75, x.t + 2.05, t)); if (a > tA) { tA = a; tI = i; } });
  const toast = $('toast'); toast.style.opacity = tA * hudOut; toast.style.transform = `translateX(-50%) translateY(${(1 - tA) * -12}px)`;
  if (tI >= 0 && tI !== lastToast) { const x = TOASTS[tI]; toast.querySelector('.tm').textContent = x.tm; toast.querySelector('.tx').textContent = x.a; toast.querySelector('.t2').textContent = x.b; lastToast = tI; }

  // live cam overlays
  $('camName').textContent = cam.name || '';
  $('rwy').innerHTML = m < 900 ? 'RWY 27R <b style="color:var(--arr)">ARRIVALS</b> · 27L <b style="color:var(--dep)">DEPARTURES</b>' : 'RWY 27L <b style="color:var(--arr)">ARRIVALS</b> · 27R <b style="color:var(--dep)">DEPARTURES</b>';
  const wx = lit.wx;
  $('needle').setAttribute('transform', `rotate(${wx.dir + 180})`);
  $('wA').textContent = `${Math.round(wx.kt)} kt ${compassPt(wx.dir)}`;
  $('wB').textContent = wx.gust > wx.kt + 6 ? `GUSTS ${Math.round(wx.gust)} KT` : `${Math.round(wx.dir)}° WIND`;
  $('wT').textContent = Math.round(wx.temp) + '°C';
  const cond = condOf(wx, lit.el); $('wC').textContent = cond;
  const icon = cond === 'SHOWERS' || cond === 'LIGHT RAIN' ? 'RAIN' : cond === 'MIST' ? 'MIST' : cond === 'CLOUDY' ? 'CLOUD' : cond === 'PARTLY CLOUDY' ? (lit.el > 0 ? 'PART_D' : 'PART_N') : (lit.el > 0 ? 'SUNNY' : 'CLEAR');
  if (icon !== lastIcon) { $('wicon').innerHTML = ICONS[icon]; lastIcon = icon; }

  // ---- finale
  const fo = smooth(52.2, 53.0, t); $('finale').style.opacity = fo; $('finale').style.display = fo > 0.001 ? 'block' : 'none';
  if (fo > 0.001) {
    $('fShade').style.opacity = fo;
    for (const [id, t0] of [['f1', 52.5], ['f2', 53.5], ['f3', 54.5]]) { const a = smooth(t0, t0 + 0.45, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateY(${(1 - a) * 26}px)`; e.style.letterSpacing = lerp(16, 3, easeOut((t - t0) / 0.7)) + 'px'; }
    const tots = [[oT1, S.stats.arr, 'r1', 55.3], [oT2, S.stats.dep, 'r2', 55.8], [oT3, S.stats.pax, 'r3', 56.3], [oT4, S.stats.dep + S.stats.arr, 'r4', 56.8]];
    for (const [o, val, id, t0] of tots) { const a = smooth(t0, t0 + 0.4, t); const e = $(id); e.style.opacity = a; e.style.transform = `translateX(${(1 - a) * 60}px)`; o.set(val * easeOut((t - t0 - 0.1) / 1.5)); }
    $('fFoot').style.opacity = smooth(58.0, 58.6, t);
  }
  return true;
}
window.renderFrame = renderFrame;

window.getAudioEvents = () => {
  const samples = [];
  for (let t = 0; t <= 60.001; t += 0.05) {
    const m = dayMin(t); const w = wxAt(m); const el = Math.asin(clamp(sunLocal(mod1440(visMin(t))).y, -1, 1)) / D2R;
    samples.push({ t: +t.toFixed(3), kt: w.kt, gust: w.gust, rain: w.rain, rate: (t >= T0 && t < TE) ? hourRate(m) : 0, night: 1 - smooth(-7, 3, el) });
  }
  const milestones = [50000, 100000, 150000, 200000].map(p => { let s = 0; for (const f of FL) { s += f.pax; if (s >= p) return vidT(f.t); } return null; });
  const shotNear = t => { if (t < 8.6) return 0.8; let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (t < x.t1) { s = x; break; } return s.near; };
  return {
    inset: ALL_EV.map(e => ({ t: e.t, type: e.type, wide: e.wide, rw: e.rw, intro: !!e.intro, near: shotNear(e.t), sf: e.intro ? 0.5 : (() => { let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (e.t < x.t1) { s = x; break; } return s.sf; })() })),
    toasts: TOASTS.map(x => x.t), hours: [...Array(25)].map((_, h) => vidT(h * 60)), samples, milestones, cuts: CUTS,
    T_RISE, T0, TN, TE, switchT: vidT(900), sunrise: vidT(414.6), sunset: vidT(996),
    title: 0.7, sky: 1.6, subs: [3.0, 3.5, 4.0], tag: [52.5, 53.5, 54.5], totals: [55.3, 55.8, 56.3, 56.8],
  };
};
window.READY = true;

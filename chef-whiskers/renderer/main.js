// Chef Whiskers: an original 3D cat chef, his kitchen and the food, as deterministic Three.js scenes.
// Every frame is a pure function of (scene, t, duration), so frames can be rendered in any order
// and in parallel processes. render.js drives window.renderFrame and window.getAudioEvents.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const W = 1080, H = 1920;

// ------------------------------------------------------------------ helpers
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const easeOut = t => 1 - Math.pow(1 - clamp(t), 3);
const easeIn = t => Math.pow(clamp(t), 3);
const easeInOut = t => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const backOut = t => { t = clamp(t); const c = 1.9; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const vlerp = (a, b, t) => a.clone().lerp(b, t);
function mulberry32(a) {
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
function hash1(n) { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); }
function noise1(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash1(i), hash1(i + 1), u); }
function std(color, o = {}) { return new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0, ...o }); }
function phys(color, o = {}) { return new THREE.MeshPhysicalMaterial({ color, roughness: 0.5, metalness: 0, ...o }); }

// ------------------------------------------------------------------ renderer
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.localClippingEnabled = true;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2a1d14);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
const camera = new THREE.PerspectiveCamera(34, W / H, 0.01, 30);

const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(W, H, { samples: 4, type: THREE.HalfFloatType }));
composer.addPass(new RenderPass(scene, camera));
const bokeh = new BokehPass(scene, camera, { focus: 1, aperture: 0.01, maxblur: 0.01 });
composer.addPass(bokeh);
composer.addPass(new OutputPass());
// Things that must not write into the depth-of-field depth pass: fur shells and soft sprites.
const noDepth = [];
const bokehRender = bokeh.render.bind(bokeh);
bokeh.render = (...a) => {
  const was = noDepth.map(o => o.visible);
  noDepth.forEach(o => { o.visible = false; });
  bokehRender(...a);
  noDepth.forEach((o, i) => { o.visible = was[i]; });
};

// ------------------------------------------------------------------ textures (seeded, so every process draws the same ones)
function canvasTex(w, h, draw, { repeat = [1, 1], srgb = true, seed = 1 } = {}) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  draw(g, w, h, mulberry32(seed));
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  t.anisotropy = 8;
  return t;
}
const woodTex = (base, dark, seed) => canvasTex(1024, 1024, (g, w, h, r) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 260; i++) {
    const y0 = r() * h, amp = 4 + r() * 14, f = 0.002 + r() * 0.006, ph = r() * 6;
    g.strokeStyle = dark; g.globalAlpha = 0.05 + r() * 0.18; g.lineWidth = 0.6 + r() * 2.6;
    g.beginPath();
    for (let x = 0; x <= w; x += 8) { const y = y0 + Math.sin(x * f + ph) * amp + Math.sin(x * f * 3.1 + ph) * amp * 0.25; x ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke();
  }
  g.globalAlpha = 1;
}, { seed });
const counterWood = woodTex('#b98352', '#6e4224', 11);
const boardWood = woodTex('#d8a873', '#8d5a33', 12);
const shelfWood = woodTex('#a8703f', '#5c3519', 13);

const tileTex = canvasTex(1024, 1024, (g, w, h, r) => {
  g.fillStyle = '#d8d0c4'; g.fillRect(0, 0, w, h);
  const tw = 128, th = 64;
  for (let row = 0; row < h / th; row++) for (let col = -1; col < w / tw + 1; col++) {
    const x = col * tw + (row % 2 ? tw / 2 : 0), y = row * th, v = 238 + Math.floor(r() * 12);
    const grd = g.createLinearGradient(x, y, x, y + th);
    grd.addColorStop(0, `rgb(${v},${v - 3},${v - 9})`); grd.addColorStop(1, `rgb(${v - 10},${v - 13},${v - 19})`);
    g.fillStyle = grd; g.fillRect(x + 3, y + 3, tw - 6, th - 6);
  }
}, { repeat: [4, 2], seed: 21 });
const plasterTex = canvasTex(512, 512, (g, w, h, r) => {
  g.fillStyle = '#efe3cf'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 2500; i++) { g.fillStyle = `rgba(150,120,90,${r() * 0.05})`; g.fillRect(r() * w, r() * h, 2 + r() * 6, 2 + r() * 6); }
}, { repeat: [3, 2], seed: 22 });
const speckle = (base, cols, n, seed, sz = 6) => canvasTex(512, 512, (g, w, h, r) => {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  for (let i = 0; i < n; i++) {
    g.fillStyle = cols[Math.floor(r() * cols.length)]; g.globalAlpha = 0.25 + r() * 0.7;
    g.beginPath(); g.ellipse(r() * w, r() * h, 1 + r() * sz, 1 + r() * sz, r() * 3, 0, 7); g.fill();
  }
  g.globalAlpha = 1;
}, { seed });
const crustTex = canvasTex(512, 512, (g, w, h, r) => {
  g.fillStyle = '#5a2a10'; g.fillRect(0, 0, w, h);
  const cols = ['#7a3d16', '#3d1a08', '#8f4f1e', '#2c1205', '#6a3010'];
  for (let i = 0; i < 700; i++) {
    const x = r() * w, y = r() * h, rad = 8 + r() * 40, grd = g.createRadialGradient(x, y, 0, x, y, rad);
    grd.addColorStop(0, cols[Math.floor(r() * cols.length)]); grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.globalAlpha = 0.25 + r() * 0.4; g.fillStyle = grd; g.beginPath(); g.arc(x, y, rad, 0, 7); g.fill();
  }
  for (let i = 0; i < 3500; i++) { g.globalAlpha = 0.3 + r() * 0.5; g.fillStyle = r() < 0.6 ? '#2a1004' : '#b0703a'; g.fillRect(r() * w, r() * h, 1 + r() * 3, 1 + r() * 3); }
  g.globalAlpha = 1;
}, { seed: 31 });
const rawTex = canvasTex(512, 512, (g, w, h, r) => {
  g.fillStyle = '#b13a44'; g.fillRect(0, 0, w, h); g.lineCap = 'round';
  const cols = ['#d0626b', '#8b2230', '#c24d58', '#e7a3a0', '#9c2c39'];
  for (let i = 0; i < 2600; i++) {
    const x = r() * w, y = r() * h, a = r() * 6.28, l = 4 + r() * 12;
    g.strokeStyle = cols[Math.floor(r() * cols.length)]; g.globalAlpha = 0.5 + r() * 0.5; g.lineWidth = 2 + r() * 3;
    g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a + 1) * l * 0.6, y + Math.sin(a + 1) * l * 0.6, x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  for (let i = 0; i < 500; i++) { g.globalAlpha = 0.7; g.fillStyle = '#f2d6cf'; g.beginPath(); g.arc(r() * w, r() * h, 0.8 + r() * 1.8, 0, 7); g.fill(); }
  g.globalAlpha = 1;
}, { seed: 32 });
const onionSkinTex = canvasTex(512, 256, (g, w, h, r) => {
  const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, '#ebe1bf'); grd.addColorStop(0.5, '#faf5e6'); grd.addColorStop(1, '#ebe1bf');
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 46; i++) {
    const x0 = i / 46 * w + r() * 6; g.strokeStyle = r() < 0.5 ? 'rgba(196,186,130,0.55)' : 'rgba(222,212,165,0.6)'; g.lineWidth = 1 + r() * 2;
    g.beginPath(); for (let y = 0; y <= h; y += 8) { const x = x0 + Math.sin(y * 0.03 + i) * 3; y ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke();
  }
}, { seed: 37 });
const crumbTex = speckle('#d79a4c', ['#b06a28', '#e9be7a', '#8a4f1c', '#f0cf93'], 3000, 33, 3);
const onionCutTex = canvasTex(512, 512, (g, w, h, r) => {
  g.fillStyle = '#f4efe0'; g.fillRect(0, 0, w, h);
  for (let k = 1; k < 12; k++) {
    g.strokeStyle = k % 2 ? 'rgba(205,200,170,0.9)' : 'rgba(235,230,205,0.9)'; g.lineWidth = 3 + r() * 3;
    g.beginPath(); g.arc(w / 2, h / 2, k * 21, 0, Math.PI * 2); g.stroke();
  }
}, { seed: 34 });
const pickleTex = canvasTex(256, 256, (g, w, h, r) => {
  const grd = g.createRadialGradient(128, 128, 10, 128, 128, 128);
  grd.addColorStop(0, '#c9cf7a'); grd.addColorStop(0.6, '#9aa84a'); grd.addColorStop(0.85, '#6f8a2c'); grd.addColorStop(1, '#3f5a17');
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2; g.fillStyle = '#e7e6b8'; g.beginPath(); g.ellipse(128 + Math.cos(a) * 52, 128 + Math.sin(a) * 52, 9, 5, a, 0, 7); g.fill(); }
}, { seed: 35 });
const irisTex = canvasTex(256, 256, (g, w, h, r) => {
  const grd = g.createRadialGradient(128, 128, 20, 128, 128, 128);
  grd.addColorStop(0, '#5a2a05'); grd.addColorStop(0.25, '#c06a12'); grd.addColorStop(0.6, '#f0a52a'); grd.addColorStop(0.86, '#f8c45a'); grd.addColorStop(0.95, '#6a3608'); grd.addColorStop(1, '#3a1d04');
  g.fillStyle = grd; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 140; i++) {
    const a = r() * Math.PI * 2, r0 = 40 + r() * 20, r1 = 90 + r() * 30;
    g.strokeStyle = r() < 0.5 ? 'rgba(255,220,140,0.35)' : 'rgba(120,55,8,0.35)'; g.lineWidth = 1 + r() * 2;
    g.beginPath(); g.moveTo(128 + Math.cos(a) * r0, 128 + Math.sin(a) * r0); g.lineTo(128 + Math.cos(a) * r1, 128 + Math.sin(a) * r1); g.stroke();
  }
}, { seed: 36 });
const softDot = canvasTex(128, 128, g => {
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.4, 'rgba(255,255,255,0.5)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
});
const starTex = canvasTex(128, 128, g => {
  g.translate(64, 64); g.fillStyle = '#fff';
  g.beginPath();
  for (let i = 0; i < 8; i++) { const rr = i % 2 ? 9 : 62, a = i / 8 * Math.PI * 2; g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr); }
  g.fill();
  const grd = g.createRadialGradient(0, 0, 0, 0, 0, 30); grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.beginPath(); g.arc(0, 0, 30, 0, 7); g.fill();
});
const heartTex = canvasTex(128, 128, g => {
  g.fillStyle = '#ff6f91'; g.translate(64, 70); g.beginPath();
  g.moveTo(0, 40); g.bezierCurveTo(-70, -5, -35, -60, 0, -22); g.bezierCurveTo(35, -60, 70, -5, 0, 40); g.fill();
  g.fillStyle = 'rgba(255,255,255,0.6)'; g.beginPath(); g.ellipse(-22, -18, 10, 6, -0.6, 0, 7); g.fill();
});
const windowTex = canvasTex(256, 512, g => {
  const grd = g.createLinearGradient(0, 0, 0, 512);
  grd.addColorStop(0, '#fff6e2'); grd.addColorStop(0.55, '#ffe3b0'); grd.addColorStop(1, '#ffd08a');
  g.fillStyle = grd; g.fillRect(0, 0, 256, 512);
  g.fillStyle = 'rgba(120,170,90,0.35)';
  for (let i = 0; i < 18; i++) { g.beginPath(); g.arc(20 + i * 14, 470 - (i % 3) * 20, 40, 0, 7); g.fill(); }
}, { repeat: [1, 1] });

// ------------------------------------------------------------------ fur (shell texturing) and the tabby coat
const COAT_GLSL = /* glsl */`
varying vec3 vObj; varying vec2 vUv2; varying vec3 vNrm;
uniform float uShell, uDensity, uStripeFreq, uStripeAmt, uStripeMinY, uCreamSoft, uMode, uApron, uDark;
uniform vec3 uBase, uStripe, uCream, uStripeDir; uniform vec4 uCreamPlane;
float h3(vec3 p){ p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vn(vec3 x){ vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(h3(i), h3(i + vec3(1,0,0)), f.x), mix(h3(i + vec3(0,1,0)), h3(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(h3(i + vec3(0,0,1)), h3(i + vec3(1,0,1)), f.x), mix(h3(i + vec3(0,1,1)), h3(i + vec3(1,1,1)), f.x), f.y), f.z); }
float apronMask(vec3 p){
  if (p.z < -0.005) return 0.0;
  float top = 0.045, bot = -0.108;
  if (p.y > top || p.y < bot) return 0.0;
  float t = (top - p.y) / (top - bot);
  float hw = mix(0.046, 0.09, smoothstep(0.0, 0.55, t));
  return 1.0 - smoothstep(hw - 0.003, hw, abs(p.x));
}
vec3 coat(vec3 p, vec2 uv){
  float n = vn(p * 24.0) * 0.7 + vn(p * 70.0) * 0.3;
  float s = uMode < 0.5 ? sin(dot(p, uStripeDir) * uStripeFreq + n * 2.6) : sin(uv.x * uStripeFreq + n * 1.6);
  float stripe = smoothstep(0.15, 0.8, s) * uStripeAmt;
  if (uMode < 0.5) stripe *= smoothstep(uStripeMinY - 0.015, uStripeMinY + 0.02, p.y);
  vec3 c = mix(uBase, uStripe, stripe);
  c *= 0.9 + 0.2 * vn(p * 160.0);
  float cm = uMode < 0.5
    ? smoothstep(-uCreamSoft, uCreamSoft, dot(p, uCreamPlane.xyz) - uCreamPlane.w + (n - 0.5) * 0.03)
    : smoothstep(uCreamPlane.w - 0.03, uCreamPlane.w + 0.03, uv.x + (n - 0.5) * 0.04);
  return mix(c, uCream, cm);
}`;
const ORANGE = new THREE.Color('#e5873a'), STRIPE = new THREE.Color('#a9501b'), CREAM = new THREE.Color('#fff8ee');
function coatUniforms(o = {}) {
  const u = {
    uBase: { value: (o.base || ORANGE).clone() }, uStripe: { value: (o.stripe || STRIPE).clone() }, uCream: { value: (o.cream || CREAM).clone() },
    uStripeDir: { value: (o.stripeDir || V(0, 1, 0)).clone().normalize() }, uStripeFreq: { value: o.freq ?? 70 }, uStripeAmt: { value: o.amt ?? 0.85 },
    uStripeMinY: { value: o.minY ?? -10 }, uCreamPlane: { value: o.creamPlane || new THREE.Vector4(0, 0, 1, 10) }, uCreamSoft: { value: o.creamSoft ?? 0.012 },
    uMode: { value: o.mode ?? 0 }, uApron: { value: o.apron ? 1 : 0 },
  };
  return u;
}
// A furry mesh: one solid base plus `shells` offset layers that keep only the strand cells.
function fur(geo, coat, { shells = 10, len = 0.007, density = 850, comb = V(0, -0.5, 0.15) } = {}) {
  const group = new THREE.Group();
  const uni = coatUniforms(coat);
  for (let i = 0; i <= shells; i++) {
    const mat = new THREE.MeshLambertMaterial();
    const sv = i / shells;
    mat.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, uni, { uShell: { value: sv }, uFurLen: { value: len }, uDensity: { value: density }, uComb: { value: comb } });
      sh.vertexShader = 'varying vec3 vObj; varying vec2 vUv2; varying vec3 vNrm; uniform float uShell, uFurLen; uniform vec3 uComb;\n' +
        sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
          vObj = position; vUv2 = uv; vNrm = objectNormal;
          transformed += (normalize(objectNormal) + uComb * uShell) * uShell * uFurLen;`);
      sh.fragmentShader = COAT_GLSL + '\n' + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
          if (uShell > 0.0) {
            vec3 an = abs(vNrm);
            float ax = an.x > an.y && an.x > an.z ? 0.0 : (an.y > an.z ? 1.0 : 2.0);
            vec2 q = ax < 0.5 ? vObj.yz : (ax < 1.5 ? vObj.xz : vObj.xy);
            vec2 cell = q * uDensity + (vec2(vn(vObj * 31.0), vn(vObj * 29.0 + 7.0)) - 0.5) * 1.6;
            vec2 fc = fract(cell) - 0.5;
            float strand = h3(vec3(floor(cell), ax * 17.0));
            float reach = 0.35 + 0.65 * strand;
            if (uShell > reach || length(fc) > 0.62 * (1.0 - uShell / reach) + 0.08) discard;
            if (uApron > 0.5 && apronMask(vObj) > 0.5) discard;
          }
          vec3 cc = coat(vObj, vUv2);
          diffuseColor.rgb = cc * mix(0.62, 1.04, pow(uShell, 0.7));
          totalEmissiveRadiance += cc * 0.1 * uShell; // light scattering through the fur tips`);
    };
    mat.customProgramCacheKey = () => 'fur-v3';
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = i === 0;
    m.receiveShadow = i === 0;
    if (i > 0) noDepth.push(m);
    group.add(m);
  }
  group.userData.coat = uni;
  return group;
}
const ell = (rx, ry, rz, ws = 48, hs = 36) => new THREE.SphereGeometry(1, ws, hs).scale(rx, ry, rz);

// ------------------------------------------------------------------ Chef Whiskers
function makeCat() {
  const root = new THREE.Group();
  const body = new THREE.Group(); body.position.y = 0.17; root.add(body);

  // body + apron (the fur under the apron is hidden by the shader's apron mask)
  body.add(fur(ell(0.105, 0.13, 0.095), { creamPlane: new THREE.Vector4(0.0, -0.35, 1, 0.075), stripeDir: V(0.15, 1, -0.2), freq: 95, apron: true }, { shells: 10, len: 0.009, density: 760 }));
  const apronMat = std('#c62a2f', { roughness: 0.82 });
  apronMat.onBeforeCompile = sh => {
    sh.vertexShader = 'varying vec3 vObj; varying vec2 vUv2; varying vec3 vNrm;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vObj = position; vUv2 = uv;');
    sh.fragmentShader = COAT_GLSL + '\n' + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
      vec3 p = vObj / vec3(1.05, 1.04, 1.075);
      if (apronMask(p) < 0.5) discard;
      vec2 q = vec2(p.x, p.y + 0.072);
      float pocket = step(abs(q.x), 0.032) * step(abs(q.y), 0.026);
      float inner = step(abs(q.x), 0.0285) * step(abs(q.y), 0.0225);
      float pad = 1.0 - smoothstep(0.0085, 0.0098, length((q - vec2(0.0, -0.006)) * vec2(1.0, 1.3)));
      float toes = 0.0;
      toes = max(toes, 1.0 - smoothstep(0.0036, 0.0046, length(q - vec2(-0.0115, 0.0065))));
      toes = max(toes, 1.0 - smoothstep(0.0036, 0.0046, length(q - vec2(-0.004, 0.0118))));
      toes = max(toes, 1.0 - smoothstep(0.0036, 0.0046, length(q - vec2(0.004, 0.0118))));
      toes = max(toes, 1.0 - smoothstep(0.0036, 0.0046, length(q - vec2(0.0115, 0.0065))));
      vec3 red = diffuseColor.rgb * (0.93 + 0.07 * vn(p * 300.0)) * (0.96 + 0.04 * sin(p.x * 2600.0) * sin(p.y * 2600.0));
      float tt = (0.045 - p.y) / (0.045 + 0.108);
      float hw = mix(0.046, 0.09, smoothstep(0.0, 0.55, tt));
      float edge = min(min(hw - abs(p.x), 0.045 - p.y), p.y + 0.108);
      red = mix(red, red * 0.72, 1.0 - smoothstep(0.003, 0.0045, edge));
      red = mix(red, vec3(0.98, 0.9, 0.86), (1.0 - smoothstep(0.0012, 0.002, abs(edge - 0.0062))) * step(0.5, fract(p.x * 260.0 + p.y * 260.0)) * 0.7);
      red = mix(red, red * 0.62, pocket * (1.0 - inner));
      diffuseColor.rgb = mix(red, vec3(0.97, 0.95, 0.9), max(pad, toes) * inner);`);
  };
  apronMat.customProgramCacheKey = () => 'apron-v1';
  const apron = new THREE.Mesh(ell(0.105 * 1.05, 0.13 * 1.04, 0.095 * 1.075), apronMat);
  apron.castShadow = true; body.add(apron);
  const strapMat = std('#b8252a', { roughness: 0.8 });
  const tie = new THREE.Mesh(new THREE.TorusGeometry(1, 0.055, 10, 64, Math.PI * 1.05), strapMat);
  tie.scale.set(0.106, 0.1, 0.098); tie.rotation.set(-Math.PI / 2, 0, -0.025 * Math.PI); tie.position.y = -0.005; body.add(tie);
  const bow = new THREE.Group(); bow.position.set(0, -0.005, -0.1); body.add(bow);
  for (const s of [-1, 1]) { const l = new THREE.Mesh(ell(0.022, 0.012, 0.008), strapMat); l.position.x = s * 0.018; l.rotation.z = s * 0.4; bow.add(l); }
  const neck = new THREE.Mesh(new THREE.TorusGeometry(0.058, 0.0055, 10, 48), strapMat); neck.rotation.x = Math.PI / 2 - 0.35; neck.position.set(0, 0.105, 0.012); body.add(neck);

  // legs + feet
  for (const s of [-1, 1]) {
    const leg = fur(new THREE.CapsuleGeometry(0.036, 0.04, 6, 20), { creamPlane: new THREE.Vector4(0, -1, 0, 0.0) }, { shells: 8, len: 0.007 });
    leg.position.set(s * 0.052, -0.1, 0.0); body.add(leg);
    const foot = fur(ell(0.04, 0.024, 0.055), { creamPlane: new THREE.Vector4(0, 0, 0, -1) }, { shells: 7, len: 0.006 });
    foot.position.set(s * 0.055, -0.148, 0.025); body.add(foot);
  }

  // arms: shoulder -> elbow -> paw, posed by 2-bone IK
  const arms = {};
  for (const s of [-1, 1]) {
    const shoulder = new THREE.Group(); shoulder.position.set(s * 0.086, 0.065, 0.012); body.add(shoulder);
    const upper = fur(new THREE.CapsuleGeometry(0.03, 0.05, 6, 20).translate(0, -0.035, 0), { stripeDir: V(0, 1, 0), freq: 110 }, { shells: 9, len: 0.008, comb: V(0, -0.6, 0) });
    shoulder.add(upper);
    const elbow = new THREE.Group(); elbow.position.y = -0.07; shoulder.add(elbow);
    const fore = fur(new THREE.CapsuleGeometry(0.027, 0.045, 6, 20).translate(0, -0.03, 0), { stripeDir: V(0, 1, 0), freq: 110, creamPlane: new THREE.Vector4(0, -1, 0, 0.045) }, { shells: 9, len: 0.007, comb: V(0, -0.6, 0) });
    elbow.add(fore);
    const paw = fur(ell(0.031, 0.028, 0.034).translate(0, -0.068, 0.004), { creamPlane: new THREE.Vector4(0, 0, 0, -1) }, { shells: 7, len: 0.006 });
    elbow.add(paw);
    arms[s < 0 ? 'R' : 'L'] = { shoulder, elbow, side: s, a: 0.07, b: 0.07 };
  }

  // tail: a tapered tube rebuilt each frame from a few control points
  const NR = 44, NS = 16;
  const tailGeo = new THREE.BufferGeometry();
  const tPos = new Float32Array((NR + 1) * (NS + 1) * 3), tUv = new Float32Array((NR + 1) * (NS + 1) * 2), idx = [];
  for (let i = 0; i <= NR; i++) for (let j = 0; j <= NS; j++) {
    tUv[(i * (NS + 1) + j) * 2] = i / NR; tUv[(i * (NS + 1) + j) * 2 + 1] = j / NS;
    if (i < NR && j < NS) { const a = i * (NS + 1) + j, b = a + NS + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  }
  tailGeo.setAttribute('position', new THREE.BufferAttribute(tPos, 3));
  tailGeo.setAttribute('uv', new THREE.BufferAttribute(tUv, 2));
  tailGeo.setIndex(idx);
  const tail = fur(tailGeo, { mode: 1, freq: 38, creamPlane: new THREE.Vector4(0, 0, 0, 0.87) }, { shells: 9, len: 0.011, density: 720, comb: V(0, 0, 0) });
  body.add(tail);
  tail.frustumCulled = false; tail.children.forEach(c => { c.frustumCulled = false; });
  function setTail(sway, lift = 0) {
    const pts = [V(0, -0.085, -0.075), V(0.02 * sway, -0.115, -0.15), V(0.08 + 0.05 * sway, -0.09, -0.2),
      V(0.13 + 0.07 * sway, -0.005 + lift * 0.3, -0.2), V(0.15 + 0.1 * sway, 0.09 + lift * 0.6, -0.16), V(0.12 + 0.14 * sway, 0.16 + lift, -0.11)];
    const curve = new THREE.CatmullRomCurve3(pts);
    const fr = curve.computeFrenetFrames(NR, false);
    for (let i = 0; i <= NR; i++) {
      const s = i / NR, P = curve.getPointAt(s);
      const r = 0.024 * (1 - 0.3 * s) * Math.sqrt(Math.max(0, 1 - Math.pow(seg(s, 0.88, 1), 2))) + 0.0005;
      for (let j = 0; j <= NS; j++) {
        const a = j / NS * Math.PI * 2, n = fr.normals[i].clone().multiplyScalar(Math.cos(a)).add(fr.binormals[i].clone().multiplyScalar(Math.sin(a)));
        const k = (i * (NS + 1) + j) * 3;
        tPos[k] = P.x + n.x * r; tPos[k + 1] = P.y + n.y * r; tPos[k + 2] = P.z + n.z * r;
      }
    }
    tailGeo.attributes.position.needsUpdate = true;
    tailGeo.computeVertexNormals();
  }

  // head
  const neckPivot = new THREE.Group(); neckPivot.position.set(0, 0.115, 0.0); body.add(neckPivot);
  const head = new THREE.Group(); head.position.set(0, 0.095, 0.012); neckPivot.add(head);
  head.add(fur(ell(0.126, 0.11, 0.115), { stripeDir: V(1, 0, 0), freq: 150, minY: 0.045, amt: 0.9, creamPlane: new THREE.Vector4(0, -0.75, 0.65, 0.066), creamSoft: 0.016 }, { shells: 10, len: 0.0065, density: 950, comb: V(0, 0.15, -0.6) }));
  for (const s of [-1, 1]) { // cheek fluff
    const ch = fur(ell(0.052, 0.045, 0.05), { stripeDir: V(0, 1, 0.5), freq: 160, amt: 0.6, creamPlane: new THREE.Vector4(0, -1, 0.3, 0.0) }, { shells: 9, len: 0.008, density: 950, comb: V(s * 0.8, -0.4, 0) });
    ch.position.set(s * 0.088, -0.035, 0.035); head.add(ch);
  }
  for (const s of [-1, 1]) { // whisker pads
    const wp = fur(ell(0.026, 0.021, 0.022), { creamPlane: new THREE.Vector4(0, 0, 0, -1) }, { shells: 6, len: 0.004, density: 1000 });
    wp.position.set(s * 0.02, -0.048, 0.098); head.add(wp);
  }
  const chin = fur(ell(0.022, 0.016, 0.018), { creamPlane: new THREE.Vector4(0, 0, 0, -1) }, { shells: 5, len: 0.004, density: 1000 });
  chin.position.set(0, -0.07, 0.09); head.add(chin);
  const earGroups = [];
  for (const s of [-1, 1]) { // ears
    const eg = new THREE.Group(); eg.position.set(s * 0.068, 0.07, -0.012); eg.rotation.set(-0.12, 0, -s * 0.42); head.add(eg);
    eg.add(fur(new THREE.ConeGeometry(0.047, 0.078, 28, 1).scale(1, 1, 0.45).translate(0, 0.03, 0), { amt: 0.4, stripeDir: V(0, 1, 0), freq: 120 }, { shells: 5, len: 0.004, density: 1000 }));
    const inner = new THREE.Mesh(new THREE.ConeGeometry(0.031, 0.056, 24, 1).scale(1, 1, 0.3).translate(0, 0.022, 0.012), std('#efa9a6', { roughness: 0.75 }));
    eg.add(inner); earGroups.push(eg);
  }
  // eyes
  const eyes = [];
  const scleraMat = phys('#fffdf8', { roughness: 0.12, clearcoat: 1, clearcoatRoughness: 0.04 });
  const irisMat = phys('#ffffff', { map: irisTex, roughness: 0.15, clearcoat: 1, clearcoatRoughness: 0.03 });
  const pupilMat = phys('#090604', { roughness: 0.1, clearcoat: 1 });
  const glintMat = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
  for (const s of [-1, 1]) {
    const socket = new THREE.Group(); socket.position.set(s * 0.05, 0.005, 0.094); socket.rotation.set(0.04, s * 0.38, 0); head.add(socket);
    const eye = new THREE.Group(); socket.add(eye);
    const sclera = new THREE.Mesh(new THREE.SphereGeometry(0.035, 40, 30), scleraMat); sclera.scale.set(1, 1.1, 0.6); eye.add(sclera);
    const look = new THREE.Group(); eye.add(look);
    const iris = new THREE.Mesh(new THREE.SphereGeometry(0.0275, 40, 24, 0, Math.PI * 2, 0, Math.PI * 0.42), irisMat);
    iris.rotation.x = Math.PI / 2; iris.scale.set(1, 0.55, 1.08); iris.position.z = 0.0078; look.add(iris);
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.0148, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.42), pupilMat);
    pupil.rotation.x = Math.PI / 2; pupil.scale.set(0.82, 0.55, 1.12); pupil.position.z = 0.0086; look.add(pupil);
    const g1 = new THREE.Mesh(new THREE.CircleGeometry(0.0072, 24), glintMat); g1.position.set(-s * 0.002 - 0.006, 0.0105, 0.0228); look.add(g1);
    const g2 = new THREE.Mesh(new THREE.CircleGeometry(0.0034, 20), glintMat); g2.position.set(0.0075, -0.0085, 0.0226); look.add(g2);
    const lidMat = std('#d97b31', { roughness: 0.9 });
    const lid = new THREE.Mesh(new THREE.SphereGeometry(0.0372, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), lidMat);
    lid.scale.set(1.03, 1.11, 0.615); eye.add(lid);
    const happy = new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.0042, 10, 32, Math.PI), std('#2b160b', { roughness: 0.6 }));
    happy.position.set(0, -0.004, 0.018); socket.add(happy);
    eyes.push({ socket, eye, look, lid, happy, pupil, glints: [g1, g2] });
  }
  // nose, mouth, tongue, whiskers
  const nose = new THREE.Mesh(ell(0.013, 0.0085, 0.009), phys('#e48795', { roughness: 0.3, clearcoat: 0.6 }));
  nose.position.set(0, -0.026, 0.115); head.add(nose);
  const lipMat = std('#4a2414', { roughness: 0.6 });
  for (const s of [-1, 1]) {
    const lip = new THREE.Mesh(new THREE.TorusGeometry(0.0105, 0.0019, 8, 20, Math.PI), lipMat);
    lip.position.set(s * 0.0105, -0.058, 0.118); lip.rotation.set(0.25, 0, Math.PI); head.add(lip);
  }
  const mouth = new THREE.Mesh(ell(0.018, 0.014, 0.008), std('#5a1e1e', { roughness: 0.7 }));
  mouth.position.set(0, -0.069, 0.112); head.add(mouth);
  const tongue = new THREE.Mesh(ell(0.011, 0.007, 0.012), phys('#f07f8f', { roughness: 0.35, clearcoat: 0.5 }));
  tongue.position.set(0, -0.072, 0.115); head.add(tongue);
  const whiskerMat = std('#fffaf0', { roughness: 0.4 });
  for (const s of [-1, 1]) for (let k = 0; k < 3; k++) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(0.0009, 0.0006, 0.11, 6).translate(0, 0.055, 0), whiskerMat);
    w.position.set(s * 0.03, -0.047 + k * 0.006, 0.1); w.rotation.set(0.3 - k * 0.05, s * 0.15, -s * (1.25 + k * 0.17)); head.add(w);
  }
  // tear, crumb
  const tear = new THREE.Mesh(ell(0.0065, 0.0095, 0.005), phys('#dff3ff', { roughness: 0.02, clearcoat: 1, transparent: true, opacity: 0.9 }));
  head.add(tear);
  const crumb = new THREE.Mesh(new RoundedBoxGeometry(0.006, 0.005, 0.005, 2, 0.0015), phys('#d8973f', { roughness: 0.6 }));
  crumb.position.set(0.034, -0.06, 0.112); head.add(crumb);

  // chef hat, small and tilted
  const hat = new THREE.Group(); hat.position.set(0.012, 0.092, -0.01); hat.rotation.set(-0.12, 0.1, -0.26); head.add(hat);
  const cloth = phys('#fbfbf7', { roughness: 0.9, sheen: 0.4, sheenRoughness: 0.8, sheenColor: new THREE.Color('#ffffff') });
  const band = new THREE.Mesh(new THREE.CylinderGeometry(0.058, 0.062, 0.036, 40), cloth); band.position.y = 0.012; hat.add(band);
  for (let k = 0; k < 6; k++) {
    const a = k / 6 * Math.PI * 2, puff = new THREE.Mesh(new THREE.SphereGeometry(0.036, 28, 20), cloth);
    puff.position.set(Math.cos(a) * 0.036, 0.055, Math.sin(a) * 0.036); hat.add(puff);
  }
  const top = new THREE.Mesh(new THREE.SphereGeometry(0.046, 32, 24), cloth); top.position.y = 0.07; hat.add(top);
  hat.traverse(o => { if (o.isMesh) o.castShadow = true; });

  // ---------- posing
  const base = { lean: 0, side: 0, turn: 0, headX: 0, headY: 0, headZ: 0, look: [0, 0], open: 1, squint: 0, happy: 0,
    sparkle: 0, mouth: 0, tongue: 0, tail: 0, tailLift: 0, ears: 0, chew: 0, tearT: -1, crumb: 0, glow: 0, bob: 0 };
  function pose(o) {
    const p = { ...base, ...o };
    body.position.y = 0.17 + p.bob;
    body.rotation.set(p.lean, p.turn, p.side);
    neckPivot.rotation.set(p.headX, p.headY, p.headZ);
    for (const [i, e] of eyes.entries()) {
      const open = p.happy > 0.5 ? 0 : clamp(p.open * (1 - p.squint * 0.78));
      e.eye.visible = p.happy <= 0.5;
      e.happy.visible = p.happy > 0.5;
      e.lid.rotation.x = lerp(-Math.PI / 2 - 0.2, Math.PI / 2, 1 - open);
      e.look.position.set(p.look[0] * 0.006, p.look[1] * 0.005, 0);
      const ps = 1 + p.sparkle * 0.25;
      e.pupil.scale.set(0.82 * ps, 0.55, 1.12 * ps);
      e.glints[0].scale.setScalar(1 + p.sparkle * 0.5 + p.glow * 0.3);
      e.glints[1].scale.setScalar(1 + p.sparkle * 0.8);
      e.glints.forEach(g => g.material.color.setRGB(1, 1 - p.glow * 0.25, 1 - p.glow * 0.55));
      e.socket.scale.setScalar(1 + p.sparkle * 0.06);
      void i;
    }
    mouth.scale.set(1, 0.15 + p.mouth * 1.6 + p.chew * 0.35, 1);
    mouth.visible = p.mouth > 0.02 || p.chew > 0.02;
    tongue.visible = p.tongue > 0.02;
    tongue.position.set(0.004 * Math.sin(p.tongue * 9), -0.07 - p.tongue * 0.006, 0.112 + p.tongue * 0.01);
    for (const [i, eg] of earGroups.entries()) eg.rotation.z = (i ? -1 : 1) * 0.42 + (i ? 1 : -1) * p.ears * 0.15;
    tear.visible = p.tearT >= 0;
    if (p.tearT >= 0) tear.position.set(-0.062, -0.025 - p.tearT * 0.05, 0.1 - p.tearT * 0.01);
    crumb.visible = p.crumb > 0.5;
    setTail(p.tail, p.tailLift);
    root.updateMatrixWorld(true);
  }
  // Point the paw of arm 'R' or 'L' at a world position (2-bone IK in body space).
  function reach(which, target, pole = null) {
    const arm = arms[which];
    root.updateMatrixWorld(true);
    const T = body.worldToLocal(target.clone());
    const S = arm.shoulder.position.clone();
    const a = arm.a, b = arm.b + 0.004;
    const D = T.clone().sub(S); const d = clamp(D.length(), 0.02, a + b - 0.002); const dir = D.normalize();
    const A = Math.acos(clamp((a * a + d * d - b * b) / (2 * a * d), -1, 1));
    const pv = (pole || V(arm.side * 0.9, -0.4, -0.5)).clone();
    const P = pv.sub(dir.clone().multiplyScalar(pv.dot(dir))).normalize();
    const u = dir.clone().multiplyScalar(Math.cos(A)).add(P.clone().multiplyScalar(Math.sin(A)));
    const E = S.clone().add(u.clone().multiplyScalar(a));
    const f = S.clone().add(dir.clone().multiplyScalar(d)).sub(E).normalize();
    const qS = new THREE.Quaternion().setFromUnitVectors(V(0, -1, 0), u);
    const qF = new THREE.Quaternion().setFromUnitVectors(V(0, -1, 0), f);
    arm.shoulder.quaternion.copy(qS);
    arm.elbow.quaternion.copy(qS.clone().invert().multiply(qF));
    root.updateMatrixWorld(true);
  }
  function relax(which, swing = 0) {
    const arm = arms[which];
    arm.shoulder.quaternion.setFromEuler(new THREE.Euler(0.15 + swing, 0, arm.side * 0.12));
    arm.elbow.quaternion.setFromEuler(new THREE.Euler(-0.25, 0, 0));
  }
  function headWorld(local) { root.updateMatrixWorld(true); return head.localToWorld(local.clone()); }
  pose({});
  return { root, body, head, pose, reach, relax, headWorld };
}

// ------------------------------------------------------------------ kitchen
const props = [];
function prop(obj) { props.push(obj); scene.add(obj); obj.visible = false; return obj; }
function shadowy(o, cast = true, recv = true) { o.traverse(m => { if (m.isMesh) { m.castShadow = cast; m.receiveShadow = recv; } }); return o; }

const kitchen = new THREE.Group(); scene.add(kitchen);
{
  const island = new THREE.Mesh(new RoundedBoxGeometry(2.6, 0.06, 0.8, 4, 0.012), std('#ffffff', { map: counterWood, roughness: 0.42 }));
  island.position.set(0, -0.03, 0.16); island.receiveShadow = true; kitchen.add(island);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(2.56, 0.9, 0.74), std('#8da48a', { roughness: 0.7 }));
  cab.position.set(0, -0.51, 0.15); kitchen.add(cab);
  const back = new THREE.Mesh(new THREE.PlaneGeometry(4, 1.0), std('#ffffff', { map: tileTex, roughness: 0.18 }));
  back.position.set(0, 0.35, -1.25); back.receiveShadow = true; kitchen.add(back);
  const upperWall = new THREE.Mesh(new THREE.PlaneGeometry(4, 1.6), std('#ffffff', { map: plasterTex, roughness: 0.95 }));
  upperWall.position.set(0, 1.65, -1.25); kitchen.add(upperWall);
  const bCounter = new THREE.Mesh(new RoundedBoxGeometry(4, 0.05, 0.6, 3, 0.01), std('#ffffff', { map: counterWood, roughness: 0.45 }));
  bCounter.position.set(0, -0.12, -0.95); bCounter.receiveShadow = true; kitchen.add(bCounter);
  const bCab = new THREE.Mesh(new THREE.BoxGeometry(4, 0.9, 0.58), std('#8da48a', { roughness: 0.7 })); bCab.position.set(0, -0.6, -0.95); kitchen.add(bCab);
  // window with warm daylight
  const win = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.78), new THREE.MeshBasicMaterial({ map: windowTex, toneMapped: true, color: new THREE.Color(2.2, 2.0, 1.7) }));
  win.position.set(-0.62, 0.48, -1.24); kitchen.add(win);
  const frameMat = std('#f4efe6', { roughness: 0.6 });
  for (const [w, h, x, y] of [[0.68, 0.04, -0.62, 0.89], [0.68, 0.04, -0.62, 0.07], [0.04, 0.82, -0.94, 0.48], [0.04, 0.82, -0.3, 0.48], [0.025, 0.78, -0.62, 0.48], [0.62, 0.025, -0.62, 0.5]]) {
    const f = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.03), frameMat); f.position.set(x, y, -1.225); kitchen.add(f);
  }
  // floating shelf with jars and plants
  const shelf = new THREE.Mesh(new RoundedBoxGeometry(1.1, 0.035, 0.2, 2, 0.006), std('#ffffff', { map: shelfWood, roughness: 0.5 }));
  shelf.position.set(0.55, 0.62, -1.14); kitchen.add(shelf);
  const rnd = mulberry32(77);
  const jarCols = ['#e9d8b8', '#c2502e', '#f2c14e', '#7a8f4a', '#d9cbb0'];
  for (let k = 0; k < 6; k++) {
    const h = 0.09 + rnd() * 0.08, r = 0.035 + rnd() * 0.02;
    const jar = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 24), phys(jarCols[k % jarCols.length], { roughness: 0.25, clearcoat: 0.8 }));
    jar.position.set(0.1 + k * 0.16, 0.64 + h / 2, -1.13); kitchen.add(jar);
    const lidm = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.05, r * 1.05, 0.015, 24), std('#b8893c', { metalness: 1, roughness: 0.35 }));
    lidm.position.set(0.1 + k * 0.16, 0.64 + h + 0.007, -1.13); kitchen.add(lidm);
  }
  const leafMat = std('#5d8a3a', { roughness: 0.6 }), potMat = std('#c46a3d', { roughness: 0.8 });
  function plant(x, y, z, s = 1) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.scale.setScalar(s);
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.045, 0.1, 24), potMat); pot.position.y = 0.05; g.add(pot);
    for (let k = 0; k < 22; k++) {
      const a = rnd() * Math.PI * 2, rr = rnd() * 0.06, leaf = new THREE.Mesh(ell(0.024, 0.006, 0.014, 12, 8), leafMat);
      leaf.position.set(Math.cos(a) * rr, 0.11 + rnd() * 0.12, Math.sin(a) * rr); leaf.rotation.set(rnd() - 0.5, a, rnd() - 0.5); g.add(leaf);
    }
    kitchen.add(g); return g;
  }
  plant(0.42, -0.095, -1.0, 1.2); plant(0.62, -0.095, -1.05, 0.9); plant(-0.25, 0.64, -1.13, 0.8); plant(1.0, 0.64, -1.13, 0.9);
  // copper kettle and a bowl of lemons on the back counter
  const bowl = new THREE.Mesh(new THREE.SphereGeometry(0.1, 32, 16, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), std('#f1ece2', { roughness: 0.4, side: THREE.DoubleSide }));
  bowl.position.set(0.95, -0.0, -0.95); kitchen.add(bowl);
  for (let k = 0; k < 5; k++) { const l = new THREE.Mesh(ell(0.035, 0.03, 0.03), std('#f3cf3a', { roughness: 0.5 })); l.position.set(0.95 + (k - 2) * 0.03, 0.01 + (k % 2) * 0.02, -0.95 + (k % 3 - 1) * 0.03); kitchen.add(l); }
  // brass rail with utensils
  const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 1.0, 12), std('#c9a14a', { metalness: 1, roughness: 0.3 }));
  rail.rotation.z = Math.PI / 2; rail.position.set(0.5, 0.3, -1.22); kitchen.add(rail);
  for (let k = 0; k < 5; k++) {
    const u = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.2, 8), std('#bfc3c8', { metalness: 1, roughness: 0.3 })); u.position.set(0.15 + k * 0.17, 0.2, -1.21); kitchen.add(u);
    const h = new THREE.Mesh(ell(0.03, 0.04, 0.01), std('#bfc3c8', { metalness: 1, roughness: 0.3 })); h.position.set(0.15 + k * 0.17, 0.09, -1.21); kitchen.add(h);
  }
  // warm under-shelf glow and pendant bulbs (they become soft bokeh balls)
  const glow = new THREE.Mesh(new THREE.BoxGeometry(1.05, 0.008, 0.01), new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 2.2, 1.2) }));
  glow.position.set(0.55, 0.598, -1.1); kitchen.add(glow);
  for (const x of [-0.45, 0.45]) {
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 12), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 2.6, 1.3) }));
    bulb.position.set(x, 0.95, -0.6); kitchen.add(bulb);
    const shade = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.08, 24, 1, true), std('#2d3a33', { roughness: 0.5, side: THREE.DoubleSide }));
    shade.position.set(x, 0.99, -0.6); kitchen.add(shade);
  }
}

// lights
scene.add(new THREE.HemisphereLight(0xfff2e2, 0xb48c68, 1.1));
const key = new THREE.DirectionalLight(0xffdcb0, 3.0);
key.position.set(-0.7, 1.3, 1.0); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.003;
Object.assign(key.shadow.camera, { left: -0.6, right: 0.6, top: 0.6, bottom: -0.6, near: 0.3, far: 4 });
scene.add(key); scene.add(key.target);
const rim = new THREE.DirectionalLight(0xffb36b, 2.6); rim.position.set(-0.5, 0.8, -1.6); scene.add(rim); scene.add(rim.target);
const fill = new THREE.DirectionalLight(0xf2f0ff, 1.3); fill.position.set(0.9, 0.35, 1.4); scene.add(fill);

// ------------------------------------------------------------------ food and tools
const board = prop(shadowy(new THREE.Mesh(new RoundedBoxGeometry(0.4, 0.022, 0.26, 3, 0.008), std('#ffffff', { map: boardWood, roughness: 0.5 }))));

const BUN_GOLD = new THREE.Color('#b8621c'), BUN_LIGHT = new THREE.Color('#e3a24c'), BUN_PALE = new THREE.Color('#f2d394');
function lathe(profile, colorAt) {
  const pts = new THREE.SplineCurve(profile.map(p => new THREE.Vector2(p[0], p[1]))).getPoints(40);
  const geo = new THREE.LatheGeometry(pts, 72);
  const pos = geo.attributes.position, cols = new Float32Array(pos.count * 3), c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    colorAt(pos.getX(i), pos.getY(i), pos.getZ(i), c);
    const j = 0.94 + 0.12 * noise1(Math.atan2(pos.getZ(i), pos.getX(i)) * 7 + pos.getY(i) * 90);
    cols[i * 3] = c.r * j; cols[i * 3 + 1] = c.g * j; cols[i * 3 + 2] = c.b * j;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(cols, 3));
  return geo;
}
const bunMat = phys('#ffffff', { vertexColors: true, roughness: 0.42, clearcoat: 0.7, clearcoatRoughness: 0.32, side: THREE.DoubleSide });
const crumbMat = std('#ffffff', { map: crumbTex, roughness: 0.85 });
function makeTopBun() {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(lathe([[0.0015, 0.064], [0.03, 0.062], [0.058, 0.053], [0.078, 0.038], [0.09, 0.02], [0.093, 0.008], [0.089, 0.0]],
    (x, y, z, c) => c.copy(BUN_PALE).lerp(BUN_LIGHT, smooth(y / 0.02)).lerp(BUN_GOLD, smooth((y - 0.02) / 0.04))), bunMat));
  const cut = new THREE.Mesh(new THREE.CircleGeometry(0.089, 64).rotateX(Math.PI / 2), crumbMat); cut.position.y = 0.0005; g.add(cut);
  return shadowy(g);
}
function makeBottomBun() {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(lathe([[0.086, 0.028], [0.09, 0.022], [0.091, 0.012], [0.087, 0.003], [0.075, 0.0], [0.0015, 0.0]],
    (x, y, z, c) => c.copy(BUN_PALE).lerp(BUN_LIGHT, 0.55 - y * 8)), bunMat));
  const cut = new THREE.Mesh(new THREE.CircleGeometry(0.087, 64).rotateX(-Math.PI / 2), crumbMat); cut.position.y = 0.028; g.add(cut);
  return shadowy(g);
}
function makeSauce(r = 0.058) {
  const shape = new THREE.Shape();
  for (let k = 0; k <= 64; k++) { const a = k / 64 * Math.PI * 2, rr = r * (0.9 + 0.12 * noise1(a * 3 + 5)); k ? shape.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : shape.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
  const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.002, bevelEnabled: true, bevelThickness: 0.0015, bevelSize: 0.003, bevelSegments: 3 }).rotateX(-Math.PI / 2);
  return new THREE.Mesh(geo, phys('#f2a477', { roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.1 }));
}

// Patty: one mesh that morphs from a raw beef ball (influence 0) to a thin, lacy smashed patty (1).
function makePatty(seed = 1, R = 0.083) {
  const NRg = 30, NSg = 96, ball = 0.043, th = 0.012;
  const pos = [], pat = [], uv = [], rimA = [], idx = [];
  const rimR = a => R * (1 + 0.05 * (noise1(a * 2.2 + seed * 9) - 0.5) * 2 + 0.07 * (noise1(a * 9 + seed * 3) - 0.5) + 0.06 * Math.pow(noise1(a * 23 + seed), 3));
  for (let i = 0; i <= NRg; i++) for (let j = 0; j < NSg; j++) {
    const v = i / NRg, a = j / NSg * Math.PI * 2, phi = v * Math.PI;
    pos.push(ball * Math.sin(phi) * Math.cos(a), ball + ball * Math.cos(phi), ball * Math.sin(phi) * Math.sin(a));
    let x, y, z, rr;
    if (v <= 0.5) { const u = v / 0.5; rr = u; const rad = u * rimR(a); x = rad * Math.cos(a); z = rad * Math.sin(a); y = th * (0.22 + 0.78 * Math.pow(1 - u * u, 0.7)) + 0.0016 * noise1(x * 140 + z * 90 + seed); }
    else { const u = (1 - v) / 0.5; rr = u; const rad = u * rimR(a) * 0.985; x = rad * Math.cos(a); z = rad * Math.sin(a); y = 0.0004 * (1 - u); }
    pat.push(x, y, z);
    uv.push(0.5 + x / 0.2, 0.5 + z / 0.2);
    rimA.push(rr);
  }
  for (let i = 0; i < NRg; i++) for (let j = 0; j < NSg; j++) {
    const a = i * NSg + j, b = i * NSg + (j + 1) % NSg, c = (i + 1) * NSg + j, d = (i + 1) * NSg + (j + 1) % NSg;
    idx.push(a, c, b, b, c, d);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setAttribute('rim', new THREE.Float32BufferAttribute(rimA, 1));
  geo.setIndex(idx); geo.computeVertexNormals();
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.Float32BufferAttribute(pat, 3)); pg.setIndex(idx); pg.computeVertexNormals();
  geo.morphAttributes.position = [pg.attributes.position];
  geo.morphAttributes.normal = [pg.attributes.normal];
  const mat = phys('#ffffff', { map: rawTex, bumpMap: crustTex, bumpScale: 2.5, roughness: 0.55, clearcoat: 0.35, clearcoatRoughness: 0.45 });
  const uCook = { value: 0 };
  mat.onBeforeCompile = sh => {
    sh.uniforms.uCook = uCook; sh.uniforms.uCrust = { value: crustTex };
    sh.vertexShader = 'attribute float rim; varying float vRim;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vRim = rim;');
    sh.fragmentShader = 'uniform float uCook; uniform sampler2D uCrust; varying float vRim;\n' + sh.fragmentShader.replace('#include <map_fragment>', `
      vec4 rawC = texture2D(map, vMapUv);
      vec4 crust = texture2D(uCrust, vMapUv * 1.3);
      float ck = clamp(uCook * 1.7 - (1.0 - vRim) * 0.7 + (crust.r - 0.3) * 0.6, 0.0, 1.0);
      vec3 col = mix(rawC.rgb, crust.rgb, ck);
      col *= mix(1.0, 0.55, smoothstep(0.82, 1.0, vRim) * uCook);
      diffuseColor.rgb *= col;`);
  };
  mat.customProgramCacheKey = () => 'patty-v1';
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = mesh.receiveShadow = true;
  mesh.morphTargetInfluences = [1];
  mesh.userData.cook = uCook;
  return mesh;
}

// Cheese slice that drapes and melts over a patty of radius R.
function makeCheese(R = 0.08, seed = 2) {
  const S = 0.118, N = 44, th = 0.012;
  const geo = new THREE.PlaneGeometry(S, S, N, N).rotateX(-Math.PI / 2).rotateY(Math.PI / 4 + seed * 0.3);
  const orig = geo.attributes.position.array.slice();
  let base = orig.slice();
  const mat = phys('#f4a11c', { roughness: 0.35, clearcoat: 0.7, clearcoatRoughness: 0.18, side: THREE.DoubleSide, emissive: new THREE.Color('#3a1600') });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = mesh.receiveShadow = true;
  const dome = u => th * (0.22 + 0.78 * Math.pow(Math.max(0, 1 - u * u), 0.7));
  let lastM = 0;
  mesh.userData.melt = m => {
    lastM = m;
    const p = geo.attributes.position.array;
    for (let i = 0; i < p.length; i += 3) {
      const x = base[i], z = base[i + 2], rho = Math.hypot(x, z) + 1e-9, a = Math.atan2(z, x);
      const edge = R * (0.97 + 0.05 * (noise1(a * 4 + seed) - 0.5));
      const pull = 1 - 0.1 * m * smooth((rho - R * 0.6) / (R * 0.5));
      const r2 = rho * pull, u = Math.min(r2 / edge, 1);
      const slump = (dome(u) - dome(0)) * m;
      const over = Math.max(0, r2 - edge);
      const drip = over * (0.6 + 2.2 * m) * (0.6 + 0.9 * noise1(a * 6 + seed * 7)) + over * over * 60 * m;
      p[i] = x * pull; p[i + 2] = z * pull;
      p[i + 1] = 0.0012 + slump - Math.min(0.02, drip) + 0.0006 * m * (noise1(x * 260 + z * 170 + seed) - 0.5);
    }
    geo.attributes.position.needsUpdate = true; geo.computeVertexNormals();
    mat.roughness = lerp(0.4, 0.2, m);
  };
  mesh.userData.warp = f => {
    base = orig.slice();
    if (f) for (let i = 0; i < base.length; i += 3) { const k = f(base[i], base[i + 2]); base[i] *= k; base[i + 2] *= k; }
    mesh.userData.melt(lastM);
  };
  mesh.userData.melt(0);
  return mesh;
}
// A bite: a scalloped dent in the outline around angle theta0 (radians, in the burger's own x/z plane).
function biteWarp(theta0, depth = 0.034, width = 0.55, Rb = 0.09) {
  return (x, z) => {
    let d = Math.atan2(z, x) - theta0; d = Math.atan2(Math.sin(d), Math.cos(d));
    const u = d / width, rho = Math.hypot(x, z) + 1e-9;
    if (Math.abs(u) >= 1) return 1;
    const cut = depth * Math.pow(1 - u * u, 1.5) * (1 + 0.15 * Math.cos(u * Math.PI * 4)) * smooth((rho - 0.3 * Rb) / (0.7 * Rb));
    return Math.max(0.05, rho - cut) / rho;
  };
}
function warpGeo(geo, f) {
  const g = geo.clone();
  const warp = attr => { for (let i = 0; i < attr.count; i++) { const x = attr.getX(i), z = attr.getZ(i), k = f(x, z); attr.setXYZ(i, x * k, attr.getY(i), z * k); } };
  warp(g.attributes.position);
  if (g.morphAttributes.position) {
    g.morphAttributes.position = g.morphAttributes.position.map(a => { const b = a.clone(); warp(b); return b; });
    const tmp = new THREE.BufferGeometry(); tmp.setAttribute('position', g.morphAttributes.position[0]); tmp.setIndex(g.index); tmp.computeVertexNormals();
    g.morphAttributes.normal = [tmp.attributes.normal];
  }
  g.computeVertexNormals();
  return g;
}
const diceMat = phys('#f5f1e4', { roughness: 0.2, clearcoat: 0.9, clearcoatRoughness: 0.1, emissive: new THREE.Color('#1a1810') });
function makeDice(count, seed, spread, sz = 0.0065) {
  const geo = new RoundedBoxGeometry(sz, sz * 0.8, sz, 1, sz * 0.2);
  const inst = new THREE.InstancedMesh(geo, diceMat, count);
  const r = mulberry32(seed), m = new THREE.Matrix4(), q = new THREE.Quaternion();
  const items = [];
  for (let k = 0; k < count; k++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r()) * spread;
    items.push({ x: Math.cos(a) * d, z: Math.sin(a) * d, y: r() * 0.004, rot: new THREE.Euler(r() * 3, r() * 3, r() * 3), s: 0.7 + r() * 0.6 });
  }
  inst.userData.items = items;
  inst.userData.layout = (n, yLift = 0) => {
    for (let k = 0; k < count; k++) {
      const it = items[k]; q.setFromEuler(it.rot);
      m.compose(V(it.x, it.y + yLift, it.z), q, V(1, 1, 1).multiplyScalar(k < n ? it.s : 0.0001));
      inst.setMatrixAt(k, m);
    }
    inst.instanceMatrix.needsUpdate = true;
  };
  inst.userData.layout(count);
  inst.castShadow = true;
  return inst;
}
const pickleMats = [phys('#4f6b22', { roughness: 0.35, clearcoat: 0.8 }), phys('#ffffff', { map: pickleTex, roughness: 0.3, clearcoat: 0.9 }), phys('#ffffff', { map: pickleTex, roughness: 0.3, clearcoat: 0.9 })];
function makePickles(n, seed) {
  const g = new THREE.Group(), r = mulberry32(seed);
  for (let k = 0; k < n; k++) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.0035, 28), pickleMats);
    const a = k / n * Math.PI * 2 + r(); p.position.set(Math.cos(a) * 0.035, 0.002 + k * 0.0012, Math.sin(a) * 0.035); p.rotation.set((r() - 0.5) * 0.15, 0, (r() - 0.5) * 0.15);
    g.add(p);
  }
  return shadowy(g);
}
// a full burger whose layers can be animated in from above (stack(t) with 0..1 per layer)
function makeBurger(seed, biteable = false) {
  const g = new THREE.Group();
  const L = {
    bottom: makeBottomBun(), sauce: makeSauce(), p1: makePatty(seed), c1: makeCheese(0.08, seed), p2: makePatty(seed + 5), c2: makeCheese(0.08, seed + 3),
    onion: makeDice(40, seed + 11, 0.05), pickles: makePickles(3, seed + 13), top: makeTopBun(),
  };
  for (const o of Object.values(L)) g.add(o);
  if (biteable) {
    const f = biteWarp(-1.27);
    const swaps = [];
    for (const k of ['bottom', 'sauce', 'p1', 'p2', 'top']) L[k].traverse(o => { if (o.isMesh) swaps.push([o, o.geometry, warpGeo(o.geometry, f)]); });
    g.userData.bite = on => {
      swaps.forEach(([o, a, b]) => { o.geometry = on ? b : a; });
      L.c1.userData.warp(on ? f : null); L.c2.userData.warp(on ? f : null);
    };
  }
  L.p1.userData.cook.value = 1; L.p2.userData.cook.value = 1;
  L.c1.userData.melt(0.85); L.c2.userData.melt(1);
  const rest = { bottom: 0, sauce: 0.0285, p1: 0.031, c1: 0.0425, p2: 0.045, c2: 0.0565, onion: 0.06, pickles: 0.064, top: 0.069 };
  g.userData.layers = L; g.userData.rest = rest;
  g.userData.stack = (prog = {}) => {
    for (const [k, o] of Object.entries(L)) {
      const p = prog[k] ?? 1;
      o.visible = p > 0;
      o.position.y = rest[k] + (1 - easeOut(p)) * 0.055;
    }
  };
  g.userData.stack();
  return g;
}
const heroBurger = prop(makeBurger(3));
const stackBurger = prop(makeBurger(7, true));

// chopping rig: onion half, knife and diced pile, turned so the camera sees the side of the blade.
// In rig space the onion is cut along x (kept part: x > c) and the knife blade runs along z.
const chopRig = prop(new THREE.Group());
const onion = new THREE.Group(); chopRig.add(onion);
const onionClip = new THREE.Plane(V(1, 0, 0), 0);
{
  const geo = new THREE.SphereGeometry(0.047, 56, 28, 0, Math.PI * 2, 0, Math.PI / 2);
  const pp = geo.attributes.position, uvs = geo.attributes.uv;
  for (let i = 0; i < pp.count; i++) uvs.setXY(i, Math.atan2(pp.getZ(i), Math.max(pp.getY(i), 1e-6)) / Math.PI + 0.5, pp.getX(i) / 0.094 + 0.5);
  const outer = new THREE.Mesh(geo, phys('#ffffff', { map: onionSkinTex, roughness: 0.22, clearcoat: 0.7, clippingPlanes: [onionClip], side: THREE.DoubleSide }));
  outer.scale.set(1, 0.92, 1); outer.castShadow = true; onion.add(outer);
  const cap = new THREE.Mesh(new THREE.CircleGeometry(1, 48, 0, Math.PI), std('#ffffff', { map: onionCutTex, roughness: 0.3, side: THREE.DoubleSide }));
  onion.add(cap);
  const rootMat = std('#8a6a44', { roughness: 0.9 });
  for (let k = 0; k < 7; k++) {
    const f = new THREE.Mesh(new THREE.CylinderGeometry(0.0007, 0.0004, 0.012, 5).translate(0, 0.006, 0), rootMat);
    f.position.set(0.046, 0.006, 0); f.rotation.set((k - 3) * 0.25, 0, -1.3 + (k % 2) * 0.2); onion.add(f);
  }
  onion.userData.cut = c => {
    const r = Math.sqrt(Math.max(0, 0.047 * 0.047 - c * c));
    cap.scale.set(r, r * 0.92, 1); cap.position.set(c, 0, 0); cap.rotation.set(0, -Math.PI / 2, 0); cap.visible = r > 0.002;
  };
}
const choppedPile = makeDice(70, 5, 0.028, 0.0062); chopRig.add(choppedPile);
const knife = new THREE.Group(); chopRig.add(knife);
{
  const s = new THREE.Shape();
  s.moveTo(0, 0); s.lineTo(0.13, 0.0); s.quadraticCurveTo(0.165, 0.004, 0.178, 0.02); s.lineTo(0.12, 0.034); s.lineTo(0, 0.036); s.lineTo(0, 0);
  const blade = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.0016, bevelEnabled: true, bevelThickness: 0.0005, bevelSize: 0.0007, bevelSegments: 2 }).translate(0, 0, -0.0008),
    std('#eef1f4', { metalness: 0.75, roughness: 0.3 }));
  knife.add(blade);
  const handle = new THREE.Mesh(new RoundedBoxGeometry(0.085, 0.022, 0.016, 3, 0.006), std('#1d1a18', { roughness: 0.35 }));
  handle.position.set(-0.042, 0.018, 0); knife.add(handle);
  for (const x of [-0.06, -0.035, -0.012]) { const rv = new THREE.Mesh(new THREE.CylinderGeometry(0.0025, 0.0025, 0.0172, 12).rotateX(Math.PI / 2), std('#d0d0d0', { metalness: 1, roughness: 0.3 })); rv.position.set(x, 0.018, 0); knife.add(rv); }
  shadowy(knife);
}
const skillet = prop(new THREE.Group());
{
  const prof = [[0, 0], [0.118, 0], [0.128, 0.006], [0.134, 0.034], [0.139, 0.042], [0.143, 0.04], [0.137, 0.003], [0.124, -0.008], [0, -0.008]];
  const pan = new THREE.Mesh(new THREE.LatheGeometry(prof.map(p => new THREE.Vector2(p[0], p[1])), 96), std('#202022', { metalness: 0.55, roughness: 0.42, side: THREE.DoubleSide }));
  skillet.add(pan);
  const handle = new THREE.Mesh(new RoundedBoxGeometry(0.16, 0.014, 0.03, 3, 0.006), std('#1c1c1e', { metalness: 0.55, roughness: 0.45 }));
  handle.position.set(0.2, 0.032, 0); handle.rotation.z = 0.12; skillet.add(handle);
  const oil = new THREE.Mesh(new THREE.CircleGeometry(0.118, 64).rotateX(-Math.PI / 2), phys('#2a2015', { roughness: 0.12, metalness: 0.2, clearcoat: 1, transparent: true, opacity: 0.5 }));
  oil.position.y = 0.0006; skillet.add(oil);
  const hob = new THREE.Mesh(new RoundedBoxGeometry(0.5, 0.012, 0.44, 3, 0.005), phys('#0d0d0f', { roughness: 0.1, clearcoat: 1 }));
  hob.position.set(0.06, -0.014, 0); skillet.add(hob);
  shadowy(skillet);
}
const spatula = prop(new THREE.Group());
{
  const blade = new THREE.Mesh(new RoundedBoxGeometry(0.09, 0.0035, 0.085, 2, 0.0015), std('#d5d9de', { metalness: 1, roughness: 0.28 }));
  spatula.add(blade);
  const neck = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.004, 0.014), std('#d5d9de', { metalness: 1, roughness: 0.28 }));
  neck.position.set(-0.062, 0.016, 0); neck.rotation.z = -0.55; spatula.add(neck);
  const handle = new THREE.Mesh(new THREE.CapsuleGeometry(0.011, 0.085, 6, 16).rotateZ(Math.PI / 2), std('#6b3b1c', { roughness: 0.45 }));
  handle.position.set(-0.13, 0.04, 0); handle.rotation.z = 0.12; spatula.add(handle);
  shadowy(spatula);
}
const panPatty = prop(makePatty(11));
const panCheese = prop(makeCheese(0.08, 9));

// soft particles: steam/smoke rising, spatter, sparkles, hearts
function emitter(tex, count, { color = 0xffffff, size = 0.04, blending = THREE.NormalBlending } = {}) {
  const g = prop(new THREE.Group());
  const r = mulberry32(count * 31 + size * 1000);
  const parts = [];
  for (let k = 0; k < count; k++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color, transparent: true, depthWrite: false, blending, opacity: 0 }));
    s.userData.r = [r(), r(), r(), r(), r()];
    g.add(s); parts.push(s); noDepth.push(s);
  }
  g.userData.parts = parts; g.userData.size = size;
  return g;
}
const steam = emitter(softDot, 26, { color: 0xffffff, size: 0.05 });
const smoke = emitter(softDot, 34, { color: 0xd8d0c8, size: 0.08 });
const spatter = emitter(softDot, 40, { color: 0xffe7a0, size: 0.006, blending: THREE.AdditiveBlending });
const sparkles = emitter(starTex, 8, { color: 0xfff1c0, size: 0.03, blending: THREE.AdditiveBlending });
const hearts = emitter(heartTex, 5, { size: 0.03 });
function rise(em, t, origin, { amount = 1, rate = 0.9, height = 0.18, spread = 0.05, life = 1.6 } = {}) {
  em.visible = amount > 0;
  for (const s of em.userData.parts) {
    const [a, b, c, d, e] = s.userData.r;
    const age = ((t * rate / life) + a) % 1;
    s.position.set(origin.x + (b - 0.5) * spread * (0.6 + age) + Math.sin(t * 1.7 + c * 9) * 0.012 * age, origin.y + age * height, origin.z + (c - 0.5) * spread * 0.6);
    s.scale.setScalar(em.userData.size * (0.5 + age * 1.6) * (0.7 + d * 0.6));
    s.material.opacity = amount * 0.3 * Math.sin(Math.PI * age) * (0.5 + e * 0.5);
    s.material.rotation = d * 6 + age;
  }
}
function burst(em, t, t0, origin, { power = 1, life = 0.7 } = {}) {
  em.visible = t >= t0 && t < t0 + life + 0.2;
  for (const s of em.userData.parts) {
    const [a, b, c, d] = s.userData.r, dt = t - t0 - a * 0.25;
    const ang = b * Math.PI * 2, sp = (0.25 + c * 0.5) * power;
    if (dt < 0 || dt > life) { s.material.opacity = 0; continue; }
    s.position.set(origin.x + Math.cos(ang) * sp * 0.4 * dt, origin.y + (0.6 + d) * sp * dt - 2.2 * dt * dt, origin.z + Math.sin(ang) * sp * 0.4 * dt);
    s.scale.setScalar(em.userData.size * (0.6 + d));
    s.material.opacity = 1 - dt / life;
  }
}
function twinkle(em, t, centers, { amount = 1, size = 1 } = {}) {
  em.visible = amount > 0;
  em.userData.parts.forEach((s, k) => {
    const [a, b, c, d] = s.userData.r, ctr = centers[k % centers.length];
    const ph = (t * (1.2 + a) + b) % 1;
    s.position.set(ctr.x + (c - 0.5) * 0.09, ctr.y + (d - 0.3) * 0.08, ctr.z + 0.02);
    s.scale.setScalar(em.userData.size * size * Math.sin(Math.PI * ph) * (0.6 + a * 0.6));
    s.material.opacity = amount * Math.sin(Math.PI * ph);
    s.material.rotation = t * 1.5 + b * 6;
  });
}

// ------------------------------------------------------------------ the cat, and shot helpers
const cat = makeCat();
scene.add(cat.root);
const shells = new Set(noDepth);
cat.root.traverse(o => { if (o.isMesh) { o.receiveShadow = !shells.has(o); o.castShadow = !shells.has(o); } });

function shoot(pos, target, { fov = 34, focus = null, aperture = 0.012, maxblur = 0.012 } = {}) {
  camera.position.copy(pos); camera.fov = fov; camera.updateProjectionMatrix(); camera.lookAt(target);
  bokeh.uniforms.focus.value = focus ?? pos.distanceTo(target);
  bokeh.uniforms.aperture.value = aperture;
  bokeh.uniforms.maxblur.value = maxblur;
  key.target.position.copy(target); rim.target.position.copy(target);
}
function blink(t, period = 2.9, offset = 0.4) { const ph = ((t + offset) % period); return ph < 0.13 ? 1 - Math.sin(ph / 0.13 * Math.PI) : 1; }
function breathe(t) { return Math.sin(t * 2.4) * 0.002; }
function behindCounter(x = 0, z = -0.3, turn = 0) { cat.root.position.set(x, -0.15, z); cat.root.rotation.set(0, turn, 0); }
function show(...objs) { objs.forEach(o => { o.visible = true; }); }

// Each scene: setup() places props once, update(t, D) sets everything that moves; events(D) lists sound cues.
const SCENES = {
  ref: {
    setup() { cat.root.position.set(0, 0, 0.0); cat.root.rotation.set(0, -0.45, 0); },
    update(t) {
      cat.pose({ headY: 0.3, headX: 0.04, headZ: -0.06, tail: 0.25, mouth: 0, look: [-0.1, 0.0] });
      cat.relax('R', 0.0); cat.relax('L', 0.0);
      shoot(V(0.02, 0.3, 1.1), V(0.0, 0.29, 0.0), { fov: 34, aperture: 0.03, maxblur: 0.012 });
    },
    events: () => [],
  },

  // The finished burger, with Chef Whiskers leaning in from behind it and licking its lips.
  burger_hero: {
    setup() { show(board, heroBurger, steam, sparkles); board.position.set(0, 0.011, 0.03); heroBurger.position.set(0, 0.022, 0.03); heroBurger.rotation.y = 0.4; },
    update(t, D) {
      const enter = easeOut(seg(t, 0.1, 1.0));
      cat.root.position.set(lerp(0.3, 0.15, enter), -0.2, -0.25); cat.root.rotation.set(0, -0.45, 0);
      const lick = seg(t, D * 0.55, D * 0.92);
      cat.pose({ lean: 0.1, side: lerp(0, 0.14, enter), headZ: 0.18 * enter, headX: 0.22, headY: 0.12, look: [-0.7, -0.8], open: blink(t, 2.4, 1.2),
        sparkle: smooth(seg(t, 0.6, 1.2)), tongue: Math.sin(lick * Math.PI), mouth: 0.3 * Math.sin(lick * Math.PI), tail: Math.sin(t * 2) * 0.3, ears: enter, bob: breathe(t) });
      cat.relax('R', 0.3); cat.relax('L', 0.5);
      rise(steam, t, V(0, 0.15, 0.03), { amount: 0.8, spread: 0.08, height: 0.18 });
      twinkle(sparkles, t, [cat.headWorld(V(-0.05, 0.03, 0.12)), cat.headWorld(V(0.05, 0.03, 0.12))], { amount: smooth(seg(t, 0.8, 1.2)), size: 0.9 });
      const push = easeInOut(seg(t, 0, D));
      shoot(V(-0.02, lerp(0.22, 0.2, push), lerp(0.74, 0.64, push)), V(0.03, 0.15, 0.0), { fov: 34, aperture: 0.025, maxblur: 0.012 });
      bokeh.uniforms.focus.value = camera.position.distanceTo(V(0, 0.07, 0.03));
    },
    events: D => [{ t: 0, type: 'room', dur: D }, { t: 0, type: 'sizzle', dur: D, level: 0.2 }, { t: 0.9, type: 'sparkle' }, { t: D * 0.62, type: 'lick' }],
  },

  // Dicing half an onion; the onion makes its eyes water.
  chop_onion: {
    setup() {
      show(board, chopRig); board.position.set(0, 0.011, -0.125);
      chopRig.position.set(0.03, 0.022, -0.15); chopRig.rotation.set(0, 1.36, 0); choppedPile.position.set(-0.075, 0, 0.0);
    },
    update(t, D) {
      behindCounter(0.0, -0.31, 0.0);
      const t0 = 0.35, t1 = D - 0.3, n = 11, chopT = seg(t, t0, t1);
      const k = Math.min(n - 1, Math.floor(chopT * n)), ph = chopT * n - k;
      const c = lerp(-0.044, 0.012, (k + smooth(ph)) / n);
      onion.userData.cut(c);
      chopRig.updateMatrixWorld(true);
      onionClip.setFromNormalAndCoplanarPoint(V(1, 0, 0).transformDirection(chopRig.matrixWorld), chopRig.localToWorld(V(c, 0, 0)));
      choppedPile.userData.layout(Math.round(70 * clamp(chopT * 1.05)));
      const lift = chopT > 0 && chopT < 1 ? Math.pow(Math.abs(Math.cos(ph * Math.PI)), 1.5) * 0.034 : 0.03;
      knife.position.set(c - 0.003, lift + 0.001, -0.075); knife.rotation.set(0, -Math.PI / 2, 0);
      const squint = smooth(seg(t, 0.9, 1.5));
      cat.pose({ lean: 0.22, headX: 0.3, headZ: -0.05 + Math.sin(t * 7) * 0.012 * squint, squint, look: [0.1, -1], tail: Math.sin(t * 1.6) * 0.4,
        tearT: t > 1.6 ? seg(t, 1.6, D) : -1, bob: breathe(t) });
      cat.reach('R', knife.localToWorld(V(-0.055, 0.02, 0)), V(-0.9, -0.2, -0.5));
      cat.reach('L', chopRig.localToWorld(V(c + 0.045, 0.045, 0.0)), V(0.9, -0.2, -0.5));
      const push = easeInOut(seg(t, 0, D));
      shoot(V(lerp(-0.04, -0.03, push), lerp(0.31, 0.29, push), lerp(0.62, 0.53, push)), V(0.0, 0.12, -0.2), { fov: 36, aperture: 0.02, maxblur: 0.01 });
      bokeh.uniforms.focus.value = camera.position.distanceTo(V(0, 0.09, -0.18));
    },
    events: D => {
      const ev = [{ t: 0, type: 'room', dur: D }], t0 = 0.35, t1 = D - 0.3, n = 11;
      for (let k = 0; k < n; k++) ev.push({ t: t0 + (k + 0.5) * (t1 - t0) / n, type: 'chop' });
      ev.push({ t: 1.6, type: 'sniff' });
      return ev;
    },
  },

  // A ball of beef goes into the hot pan and gets smashed flat with a long spatula.
  smash_patty: {
    setup() { show(skillet, spatula, panPatty, smoke, spatter); skillet.position.set(0, 0.008, -0.085); },
    update(t, D) {
      behindCounter(0.0, -0.31, 0.0);
      const P = V(0, 0.008, -0.085), tPlace = 0.95, tSmash = 1.55, tLift = 3.2;
      const hand = V(-0.085, 0.07, -0.12), toss = seg(t, 0.45, tPlace);
      const ballPos = t < 0.45 ? vlerp(V(-0.06, 0.05, -0.22), hand, easeOut(seg(t, 0, 0.45)))
        : vlerp(hand, P, easeIn(toss)).add(V(0, Math.sin(Math.PI * toss) * 0.03, 0));
      const smash = easeIn(seg(t, tSmash - 0.16, tSmash));
      panPatty.position.copy(t < tPlace ? ballPos : P); panPatty.rotation.y = 0.6;
      panPatty.morphTargetInfluences[0] = smash;
      panPatty.userData.cook.value = 0.8 * smooth(seg(t, tSmash, D + 0.5));
      const inS = easeInOut(seg(t, tPlace + 0.05, tSmash - 0.16)), out = easeInOut(seg(t, tLift, D));
      const h = t < tSmash - 0.16 ? lerp(0.15, 0.09, inS) : t < tLift ? lerp(0.09, 0.0225, smash) + Math.sin(t * 30) * 0.0005 : lerp(0.0225, 0.12, out);
      spatula.position.set(P.x, P.y + h, P.z + 0.005 - out * 0.05); spatula.rotation.set(0, -Math.PI / 2, 0);
      spatula.visible = t > tPlace - 0.15;
      const pressing = t > tSmash - 0.2 && t < tLift;
      cat.pose({ lean: 0.3, headX: 0.25, headY: 0.12, squint: pressing ? 0.4 : 0, sparkle: smooth(seg(t, tLift, tLift + 0.4)), mouth: pressing ? 0.25 : 0,
        look: [0, -0.9], tail: Math.sin(t * 2.4) * 0.5, ears: t > tSmash ? 1 : 0, bob: breathe(t) - (pressing ? 0.008 : 0) });
      if (t < tPlace - 0.15) { cat.reach('R', (t < 0.45 ? ballPos : hand).clone().add(V(-0.02, 0.07, -0.01)), V(-0.9, -0.2, -0.5)); cat.relax('L', 0.3); }
      else {
        cat.reach('R', spatula.localToWorld(V(-0.14, 0.048, 0)), V(-0.9, -0.1, -0.5));
        cat.reach('L', spatula.localToWorld(V(-0.085, 0.035, 0.0)), V(0.9, -0.1, -0.5));
      }
      rise(smoke, t, P.clone().add(V(0, 0.03, 0)), { amount: 0.5 + 0.6 * smooth(seg(t, tSmash, tSmash + 0.3)), spread: 0.22, height: 0.3, rate: 1.1, life: 2.0 });
      burst(spatter, t, tSmash, P.clone().add(V(0, 0.02, 0)), { power: 1.2, life: 0.75 });
      const push = easeInOut(seg(t, 0, D));
      shoot(V(lerp(0.3, 0.27, push), lerp(0.33, 0.31, push), lerp(0.36, 0.31, push)), V(0, 0.1, -0.15), { fov: 40, aperture: 0.022, maxblur: 0.01 });
      bokeh.uniforms.focus.value = camera.position.distanceTo(P);
    },
    events: D => [{ t: 0, type: 'room', dur: D }, { t: 0, type: 'sizzle', dur: D, level: 0.22 }, { t: 0.95, type: 'place' },
      { t: 1.55, type: 'smash' }, { t: 1.55, type: 'sizzle', dur: D - 1.55, level: 0.75, attack: 0.05 }],
  },

  // Macro: a slice of cheese drops onto the flipped patty and melts; the cat watches, out of focus.
  cheese_melt: {
    setup() { show(skillet, panPatty, panCheese, steam); skillet.position.set(0, 0.008, -0.085); },
    update(t, D) {
      behindCounter(0.0, -0.4, 0.0);
      const P = V(0, 0.008, -0.085);
      panPatty.position.copy(P); panPatty.rotation.y = 2.2; panPatty.morphTargetInfluences[0] = 1; panPatty.userData.cook.value = 1;
      const drop = easeIn(seg(t, 0.1, 0.42)), melt = smooth(seg(t, 0.45, D - 0.2));
      panCheese.position.set(P.x, P.y + 0.0128 + (1 - drop) * 0.06, P.z); panCheese.rotation.y = 0.3;
      panCheese.userData.melt(melt);
      cat.pose({ lean: 0.15, headX: 0.15, headZ: Math.sin(t * 0.9) * 0.08, sparkle: 0.8, glow: 1, open: blink(t, 2.2, 0.9), look: [0, -0.8],
        tail: Math.sin(t * 1.4) * 0.5, ears: 1, bob: breathe(t) });
      cat.relax('R', 0.5); cat.relax('L', 0.5);
      rise(steam, t, P.clone().add(V(0, 0.02, 0)), { amount: 0.4 + 0.6 * melt, spread: 0.12, height: 0.2, rate: 0.8 });
      const push = easeInOut(seg(t, 0, D));
      shoot(V(0.0, lerp(0.42, 0.38, push), lerp(0.3, 0.26, push)), V(0, 0.07, -0.15), { fov: 32, aperture: 0.09, maxblur: 0.02 });
      bokeh.uniforms.focus.value = camera.position.distanceTo(P.clone().add(V(0, 0.014, 0)));
    },
    events: D => [{ t: 0, type: 'room', dur: D }, { t: 0, type: 'sizzle', dur: D, level: 0.65 }, { t: 0.42, type: 'plop' }],
  },

  // Stack the burger, lift it, take a big happy bite.
  stack_and_bite: {
    setup() { show(board, stackBurger, hearts, sparkles); board.position.set(0, 0.011, -0.12); },
    update(t, D) {
      behindCounter(0.0, -0.31, 0.0);
      const B = V(0, 0.022, -0.12), lp = (a, b) => seg(t, a, b);
      stackBurger.userData.stack({ p1: lp(0.05, 0.35), c1: lp(0.15, 0.4), p2: lp(0.45, 0.75), c2: lp(0.55, 0.8), onion: lp(0.85, 1.05), pickles: lp(0.95, 1.15), top: lp(1.2, 1.45) });
      const press = Math.sin(Math.PI * seg(t, 1.45, 1.7));
      stackBurger.userData.layers.top.scale.set(1 + press * 0.04, 1 - press * 0.12, 1 + press * 0.04);
      const lift = easeInOut(seg(t, 1.8, 2.3)), into = easeInOut(seg(t, 2.3, 2.55)), back = easeInOut(seg(t, 2.65, 3.1));
      const mouthW = cat.headWorld(V(0, -0.07, 0.11));
      const hold = mouthW.clone().add(V(-0.01, -0.085, 0.14)), bitePos = mouthW.clone().add(V(-0.01, -0.068, 0.09));
      const show = mouthW.clone().add(V(-0.035, -0.125, 0.09));
      stackBurger.position.copy(vlerp(B, hold, lift).lerp(bitePos, into * (1 - back)).lerp(show, back));
      stackBurger.rotation.set(0.15 * lift * (1 - back) + 0.2 * back, 0.3 + 1.45 * back, 0);
      stackBurger.userData.bite(t > 2.55);
      const bite = Math.sin(Math.PI * seg(t, 2.22, 2.58)), happy = t > 2.6 ? 1 : 0;
      const chew = t > 2.8 ? Math.abs(Math.sin((t - 2.8) * 11)) : 0;
      cat.pose({ lean: 0.2 - 0.14 * lift, headX: lerp(0.32, 0.05, lift), headZ: happy * Math.sin(t * 4) * 0.06, mouth: bite, chew: chew * happy, happy, crumb: t > 2.6 ? 1 : 0,
        look: [0, lerp(-1, -0.3, lift)], open: blink(t, 2.6, 0.2), sparkle: t < 1.8 ? 0.6 : 0, tail: Math.sin(t * (happy ? 6 : 2)) * (happy ? 0.8 : 0.4), tailLift: happy * 0.04,
        ears: 1, bob: breathe(t) + happy * Math.abs(Math.sin(t * 6)) * 0.004 });
      if (t < 1.8) {
        const y = lerp(0.07, 0.15, seg(t, 0, 1.45)) + 0.018 * Math.abs(Math.sin(t * 5.2)) - press * 0.012;
        cat.reach('R', B.clone().add(V(-0.015, y, 0.0)), V(-0.9, -0.3, -0.5));
        cat.relax('L', 0.2);
      } else {
        stackBurger.updateMatrixWorld(true);
        cat.reach('R', stackBurger.localToWorld(V(-0.088, 0.035, 0.0)), V(-0.9, -0.5, -0.3));
        cat.reach('L', stackBurger.localToWorld(V(0.088, 0.035, 0.0)), V(0.9, -0.5, -0.3));
      }
      rise(hearts, t, cat.headWorld(V(0.06, 0.12, 0.05)), { amount: happy * smooth(seg(t, 2.9, 3.2)), spread: 0.16, height: 0.12, rate: 1.0, life: 1.2 });
      twinkle(sparkles, t, [cat.headWorld(V(-0.05, 0.03, 0.12)), cat.headWorld(V(0.05, 0.03, 0.12))], { amount: t < 1.6 ? 0.6 : 0, size: 0.8 });
      const push = easeInOut(seg(t, 0, D));
      shoot(V(lerp(0.12, 0.1, push), lerp(0.25, 0.24, push), lerp(0.5, 0.44, push)), V(0, lerp(0.18, 0.2, lift), -0.22), { fov: 38, aperture: 0.02, maxblur: 0.01 });
      bokeh.uniforms.focus.value = camera.position.distanceTo(V(0, 0.15, -0.24));
    },
    events: D => [{ t: 0, type: 'room', dur: D }, { t: 0.35, type: 'place' }, { t: 0.75, type: 'place' }, { t: 1.05, type: 'plop' }, { t: 1.45, type: 'place' },
      { t: 1.6, type: 'squish' }, { t: 2.5, type: 'bite' }, { t: 2.85, type: 'mrrp' }, { t: 2.9, type: 'sparkle' }],
  },
};

// ------------------------------------------------------------------ API used by render.js
let current = null;
function enter(name) {
  if (current === name) return;
  props.forEach(p => { p.visible = false; });
  SCENES[name].setup();
  current = name;
}
window.SCENES = Object.keys(SCENES);
window.renderFrame = (name, t, duration) => {
  enter(name);
  SCENES[name].update(t, duration || 4);
  scene.updateMatrixWorld(true);
  composer.render();
  return true;
};
window.getAudioEvents = (name, duration) => ({ duration, events: SCENES[name].events(duration || 4) });
window.renderFrame('ref', 0, 3);
window.READY = true;

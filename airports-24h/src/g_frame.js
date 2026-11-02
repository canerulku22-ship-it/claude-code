
// ================================================================== HUD SETUP
const GRAD_PAX = 'linear-gradient(90deg, #FFD27A 0%, #FF9E5E 45%, #FF6FB5 100%)';
const GRAD_ALL = 'linear-gradient(90deg, #5AA9FF 0%, #A06BFF 50%, #FF6FB5 100%)';
const nd = n => String(n).length;
const oPax = new Odo($('oPax'), Math.max(5, nd(S.stats.pax)), 56, 35, true, GRAD_PAX);
const oDep = new Odo($('oDep'), 3, 52, 32, false, null);
const oArr = new Odo($('oArr'), 3, 52, 32, false, null);
const oT1 = new Odo($('oT1'), 3, 64, 40, false, null); $('oT1').style.color = 'var(--arr)';
const oT2 = new Odo($('oT2'), 3, 64, 40, false, null); $('oT2').style.color = 'var(--dep)';
const oT3 = new Odo($('oT3'), Math.max(5, nd(S.stats.pax)), 64, 40, true, GRAD_PAX);
const oT4 = new Odo($('oT4'), Math.max(3, nd(S.stats.dep + S.stats.arr)), 64, 40, true, GRAD_ALL);
if (AP.titleSize) $('tBig').style.fontSize = AP.titleSize + 'px';
const elAt = mm => Math.asin(clamp(sunLocal(mm).y, -1, 1)) / D2R;
let SUNRISE = 0, SUNSET = 0; for (let mm = 1; mm < 1440; mm++) { if (elAt(mm - 1) < -0.83 && elAt(mm) >= -0.83) SUNRISE = mm; if (elAt(mm - 1) >= -0.83 && elAt(mm) < -0.83) SUNSET = mm; }
{ const p = mm => (mm / 1440 * 100).toFixed(1) + '%';
  const gstr = `linear-gradient(90deg, #0d1838 0%, #18265a ${p(SUNRISE - 40)}, #f2955c ${p(SUNRISE)}, #64aef7 ${p(SUNRISE + 60)}, #6fb6ff 50%, #64aef7 ${p(SUNSET - 60)}, #f0784a ${p(SUNSET)}, #2b2f6c ${p(SUNSET + 50)}, #0d1838 100%)`;
  $('track').style.background = gstr; $('fill').style.background = gstr; $('fill').style.backgroundSize = '860px 8px'; }

const TOASTS = AP.toasts(FL, ROUTES, S, hhmm, pad2).map(x => {
  let m = x.m; if (typeof m === 'string' && m.startsWith('pax')) { const thr = parseInt(m.slice(3)) * 1000; let s = 0; m = 1200; for (const f of FL) { s += f.pax; if (s >= thr) { m = f.t; break; } } }
  return { ...x, m, tm: x.tm || hhmm(m) };
});
for (const g of GA_EV) TOASTS.push({ m: g.m, tm: hhmm(g.m), a: 'GO-AROUND', b: `${g.cs} climbs away from runway ${g.rw}` });
TOASTS.sort((a, b) => a.m - b.m); TOASTS.forEach(x => x.t = vidT(x.m));

// milestones: counters pulse and a chip pops up
const niceStep = (tot, n, c) => c.find(s => tot / s <= n) || c[c.length - 1];
const MS = [];
{ const sD = niceStep(S.stats.dep, 5, [10, 20, 25, 50, 100, 200, 250, 500]), sA = niceStep(S.stats.arr, 5, [10, 20, 25, 50, 100, 200, 250, 500]);
  for (let k = sD; k <= depT.length; k += sD) MS.push({ card: 'cDep', chip: 'chipDep', t: vidT(depT[k - 1]), text: `${k}TH DEPARTURE`, col: '#38C8FF' });
  for (let k = sA; k <= arrT.length; k += sA) MS.push({ card: 'cArr', chip: 'chipArr', t: vidT(arrT[k - 1]), text: `${k}TH ARRIVAL`, col: '#3DF5A0' });
  const sP = niceStep(S.stats.pax, 6, [1000, 2000, 2500, 5000, 10000, 20000, 25000, 50000]); let s = 0, next = sP;
  for (const f of FL) { s += f.pax; while (s >= next) { MS.push({ card: 'cPax', chip: 'chipPax', t: vidT(f.t), text: `${fmt(next)} PASSENGERS`, col: '#FFB84D' }); next += sP; } } }
MS.forEach(x => x.text = x.text.replace(/(\d)TH /, (m0, d) => d + 'TH ').replace(/1TH /, '1ST ').replace(/2TH /, '2ND ').replace(/3TH /, '3RD ').replace(/(1[123])(ST|ND|RD) /, '$1TH '));

$('glG').style.zIndex = 0; $('glA').style.zIndex = 1; $('vignette').style.zIndex = 2; $('hud').style.zIndex = 3; $('introLayer').style.zIndex = 4; $('finale').style.zIndex = 5;
const FULL_END = T_RISE + 1.7;
const SUBTITLE = 'Every flight. Every arrival. Every departure.';
// prominent word pops (for the soundtrack)
{ const n = AP.titleBig.length; WORD_TICKS.push(0.12);
  ['24', 'HOURS', 'IN', 'THE', 'SKY'].forEach((_, i) => WORD_TICKS.push(0.5 + i * 0.07));
  SUBTITLE.split(' ').forEach((_, i) => WORD_TICKS.push(1.05 + i * 0.11));
  for (const x of TOASTS) WORD_TICKS.push(x.t + 0.02);
  WORD_TICKS.push(52.45, 52.6, 53.25, 53.4, 54.05, 54.14, 54.23); }

// ================================================================== FRAME
function renderFrame(t) {
  const m = dayMin(t), vm = visMin(t);
  const fin = smooth(52.0, 54.0, t);
  // ---- globe
  const [glat, glon, gd, gy] = globeCam(t);
  setGlobeCenter(500, gy);
  camG.position.copy(llv(glat, glon + Math.sin(t * 0.13) * 1.2, gd)); camG.up.set(0, 1, 0); camG.lookAt(0, 0, 0);
  camG.near = Math.max(0.01, gd - 1.25); camG.far = 120; camG.updateProjectionMatrix();
  const sunG = sunECEF(mod1440(vm));
  globeMat.uniforms.sunDir.value.copy(sunG); globeMat.uniforms.camPos.value.copy(camG.position); atmoMat.uniforms.sunDir.value.copy(sunG);
  const gs = updateGlobe(t, vm, fin);
  rG.render(sceneG, camG);

  // ---- airport
  const fullMode = t < FULL_END;
  const aOp = fullMode ? 1 - smooth(T_RISE + 0.6, T_RISE + 1.5, t) : smooth(T0, T0 + 0.5, t) * (1 - smooth(52.0, 52.6, t));
  setAMode(fullMode ? 'full' : 'inset');
  $('glA').style.opacity = aOp;
  const cam = airportCam(t);
  const lit = lightAirport(t, fullMode ? 0 : vm, cam, fullMode ? W : CAMR.w, fullMode ? H : CAMR.h);
  if (aOp > 0.001) { updateAirport(t, lit.night, cam); rA.render(sceneA, camA); }

  // ---- intro (quick): title letters, tagline words, subtitle words — all animate in and out
  const showIntro = t < T_RISE + 0.45;
  $('introLayer').style.display = showIntro ? 'block' : 'none';
  if (showIntro) {
    $('introShade').style.opacity = 1 - smooth(2.6, 3.2, t);
    kin($('tBig'), AP.titleBig, 0.12, 2.5, t, { mode: 'char', stagger: 0.035, dIn: 0.38, s0: 0.2, y0: 40, blur: 10, r0: -12, outStagger: 0.015 });
    $('tBig').style.filter = `drop-shadow(0 0 26px rgba(140,120,255,${0.55 * smooth(0.5, 1.0, t) * (1 - smooth(2.5, 2.8, t))}))`;
    kin($('tSky'), '24 HOURS IN THE SKY', 0.5, 2.58, t, { stagger: 0.07 });
    const rw = 320 * easeOut((t - 0.75) / 0.4) * (1 - smooth(2.6, 2.85, t)); $('tRule').style.width = rw + 'px'; $('tRule').style.left = (500 - rw / 2) + 'px';
    kin($('tSub'), SUBTITLE, 1.05, 2.64, t, { stagger: 0.11, outStagger: 0.03 });
  }

  // ---- HUD (every label pops in word by word at the start of the day and closes at 24:00)
  const OUT = 52.0;
  $('hdrShade').style.opacity = smooth(T0 - 0.5, T0, t) * (1 - smooth(OUT, OUT + 0.6, t));
  kin($('hTitle'), AP.header, T0 - 0.45, OUT, t, { stagger: 0.08 });
  kin($('hSub'), '24 HOURS IN THE SKY', T0 - 0.3, OUT + 0.05, t, { stagger: 0.05 });
  pop($('clock'), T0 - 0.4, OUT, t, { s0: 0.4 });
  kin($('clocksub'), (t >= TE ? 'END OF DAY · ' : 'LOCAL TIME · ') + AP.tz, T0 - 0.2, OUT + 0.1, t, { stagger: 0.05 });
  $('daybar').style.opacity = smooth(T0 - 0.3, T0 + 0.1, t) * (1 - smooth(OUT, OUT + 0.5, t));
  kin($('inairL'), 'IN THE AIR NOW', T0 - 0.1, OUT, t, { stagger: 0.06 });
  pop($('inairN'), T0, OUT + 0.1, t, { s0: 0.3 });
  [...$('legend').children].forEach((p, i) => pop(p, T0 + 0.1 + i * 0.15, OUT + i * 0.08, t));
  $('legend').style.opacity = 1;
  $('labels').style.opacity = smooth(T0 - 0.2, T0 + 0.6, t) * (1 - fin);
  // stats cards + labels + milestone pulses/chips
  const pulse = { cPax: 0, cDep: 0, cArr: 0 }, chipOn = {};
  for (const x of MS) { const d = t - x.t; if (d >= 0 && d < 0.7) pulse[x.card] = Math.max(pulse[x.card], Math.exp(-d / 0.18)); if (d >= -0.05 && d < 1.5) chipOn[x.chip] = x; }
  for (const [id, lab, k, i] of [['cPax', 'PASSENGERS', 'kPax', 0], ['cDep', 'DEPARTURES', 'kDep', 1], ['cArr', 'ARRIVALS', 'kArr', 2]]) {
    const e = $(id); const a = pop(e, T0 - 0.1 + i * 0.14, OUT + i * 0.06, t, { s0: 0.85, pre: `scale(${(1 + 0.05 * pulse[id]).toFixed(3)})` });
    e.style.boxShadow = `0 10px 36px rgba(0,0,0,0.45), 0 0 ${(34 * pulse[id]).toFixed(0)}px ${['#FFB84D', '#38C8FF', '#3DF5A0'][i]}`;
    kin($(k), lab, T0 + 0.05 + i * 0.14, OUT, t, { stagger: 0.05 });
  }
  for (const id of ['chipPax', 'chipDep', 'chipArr']) { const x = chipOn[id], e = $(id);
    if (!x || t > OUT) { e.style.opacity = 0; continue; }
    pop(e, x.t, x.t + 1.2, t, { s0: 0.4 }); kin(e, x.text, x.t + 0.04, x.t + 1.1, t, { stagger: 0.05, blur: 4, y0: 12 }); }
  // live cam + radar row
  const rowA = smooth(T0, T0 + 0.6, t) * (1 - smooth(OUT, OUT + 0.6, t)) * (fullMode ? 0 : 1);
  for (const id of ['camEdge', 'radar', 'radarEdge', 'camLabel']) $(id).style.opacity = rowA;
  pop($('wchip'), T0 + 0.4, OUT, t, { s0: 0.6 });
  let dip = 0; for (const c of CUTS) dip = Math.max(dip, 1 - smooth(0, 0.24, Math.abs(t - c)));
  $('camDip').style.opacity = fullMode ? 0 : dip * (1 - smooth(OUT, OUT + 0.6, t));
  if (rowA > 0.001) drawRadar(t, m);
  { let si = 0; for (let i = 0; i < SHOTS.length; i++) if (t >= SHOTS[i].t0) si = i; const s = SHOTS[si];
    kin($('camName'), s.name, Math.max(s.t0 + 0.08, T0 + 0.2), si < SHOTS.length - 1 ? s.t1 - 0.3 : OUT, t, { stagger: 0.06, blur: 5 }); }
  // view label
  { let vi = -1; for (let i = 0; i < VIEWS.length; i++) if (t >= VIEWS[i][0] - 1.2) vi = i;
    if (vi >= 0) kin($('view'), 'VIEW · ' + VIEWS[vi][1], Math.max(VIEWS[vi][0] - 1.2, T0), vi < VIEWS.length - 1 ? VIEWS[vi + 1][0] - 1.45 : OUT, t, { stagger: 0.06, blur: 4 }); }

  // clock, day bar, counters
  $('clock').textContent = hhmm(t >= TE ? 1439.99 : m);
  const frac = clamp(m / 1440, 0, 1);
  $('fill').style.width = (frac * 860) + 'px'; $('marker').style.left = (frac * 860) + 'px';
  const isDay = lit.el > -0.8;
  $('marker').style.background = isDay ? 'radial-gradient(circle, #fff6c8 0%, #FFD166 55%, rgba(255,209,102,0) 72%)' : 'radial-gradient(circle, #ffffff 0%, #c9d6ff 50%, rgba(201,214,255,0) 72%)';
  $('marker').style.boxShadow = isDay ? '0 0 14px 5px rgba(255,200,90,0.55)' : '0 0 12px 4px rgba(170,190,255,0.5)';
  for (let h = 0; h < 24; h++) {
    const n = ub(allT, Math.min(m, (h + 1) * 60)) - ub(allT, h * 60);
    hourBars[h].style.height = (Math.max(0, n) / HMAX * 24) + 'px'; hourBars[h].style.width = '29px';
    hourBars[h].style.opacity = (m >= h * 60 && m < (h + 1) * 60) ? 1 : 0.5;
  }
  $('inairN').textContent = fmt(gs.inAir);
  oPax.set(paxAt(m)); oDep.set(contCount(depT, m)); oArr.set(contCount(arrT, m));
  const lastH = arr => ub(arr, m) - ub(arr, m - 60);
  $('sPax').textContent = m > 30 ? `+${fmt(paxAt(m) - paxAt(m - 60))} last hour` : '';
  $('sDep').textContent = m > 30 ? `+${lastH(depT)} last hour` : '';
  $('sArr').textContent = m > 30 ? `+${lastH(arrT)} last hour` : '';

  // globe labels
  const camDir = camG.position.clone().normalize();
  const wA = smooth(7.0, 8.5, gd), eA = 1 - smooth(6.6, 8.0, gd);
  const proj = v => { const p = v.clone().project(camG); return [(p.x + 1) / 2 * W, (1 - p.y) / 2 * H]; };
  const inBox = (x, y) => x > 80 && x < 920 && y > 345 && y < 895 ? 1 : 0;
  const hubS = proj(LV.clone().multiplyScalar(1.01));
  for (const L of labelEls) {
    const rt = RT[L.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    const served = ub(routeTimes[L.i], vm) > 0 || gs.act[L.i] > 0;
    L.el.style.left = x + 'px'; L.el.style.top = y + 'px';
    L.el.style.opacity = vis * (L.kind === 'w' ? wA : eA) * (served ? 0.55 + 0.45 * Math.min(1, gs.act[L.i] / 2) : 0.3) * inBox(x, y) * smooth(50, 80, Math.hypot(x - hubS[0], y - hubS[1]));
  }
  for (const B of busyEls) {
    const rt = RT[B.i]; const vis = smooth(0.12, 0.35, rt.v.dot(camDir));
    const [x, y] = proj(rt.v.clone().multiplyScalar(1.01));
    B.el.style.left = x + 'px'; B.el.style.top = y + 'px';
    B.el.style.opacity = vis * smooth(55, 90, Math.hypot(x - hubS[0], y - hubS[1])) * inBox(x, y) * (ub(routeTimes[B.i], vm) > 0 ? 1 : 0) * (1 - fin);
    B.el.querySelector('.n').textContent = '× ' + ub(routeTimes[B.i], Math.min(vm, 1440));
  }
  lhrLabel.style.left = (hubS[0] - 14) + 'px'; lhrLabel.style.top = (hubS[1] + 10) + 'px'; lhrLabel.style.transform = 'translate(-100%, 0)';
  lhrLabel.style.opacity = smooth(0.12, 0.3, LV.dot(camDir)) * (1 - fin) * inBox(hubS[0], hubS[1]);

  // time cards: box pops, words fly in, then close
  let cur = null; for (const x of TOASTS) if (t >= x.t - 0.1 && t < x.t + 2.25) cur = x;
  const toast = $('toast');
  if (cur && t < OUT) {
    pop(toast, cur.t - 0.05, cur.t + 1.98, t, { s0: 0.5, pre: 'translateX(-50%)' });
    kin($('toastT1'), `${cur.tm} ${cur.a}`, cur.t + 0.02, cur.t + 1.72, t, { stagger: 0.055, color0: '#FFD27A' });
    kin($('toastT2'), cur.b, cur.t + 0.16, cur.t + 1.76, t, { stagger: 0.03, blur: 4, y0: 14 });
  } else toast.style.opacity = 0;

  // weather chip
  const wx = lit.wx;
  $('needle').setAttribute('transform', `rotate(${wx.dir + 180})`);
  $('wA').textContent = `${compassPt(wx.dir)} ${Math.round(wx.kt)} kt`;
  $('wB').textContent = wx.gust > wx.kt + 6 ? `GUSTS ${Math.round(wx.gust)} KT` : `${Math.round(wx.dir)}° WIND`;
  $('wT').textContent = Math.round(wx.temp) + '°C';
  const cond = condOf(wx, lit.el); $('wC').textContent = cond;
  const icon = cond === 'SHOWERS' || cond === 'LIGHT RAIN' ? 'RAIN' : cond === (AP.mistName || 'MIST') ? 'MIST' : cond === 'CLOUDY' ? 'CLOUD' : cond === 'PARTLY CLOUDY' ? (lit.el > 0 ? 'PART_D' : 'PART_N') : (lit.el > 0 ? 'SUNNY' : 'CLEAR');
  if (icon !== lastIcon) { $('wicon').innerHTML = ICONS[icon]; lastIcon = icon; }

  // ---- finale: slam-in words, rows pop, numbers roll, then everything closes
  const fo = smooth(52.2, 52.9, t); $('finale').style.display = fo > 0.001 ? 'block' : 'none';
  if (fo > 0.001) {
    $('fShade').style.opacity = fo;
    const slam = { s0: 1.9, y0: -6, blur: 10, r0: 0, dIn: 0.3 };
    kin($('f1'), '24 HOURS.', 52.45, 59.25, t, { ...slam, stagger: 0.15 });
    kin($('f2'), 'ONE AIRPORT.', 53.25, 59.3, t, { ...slam, stagger: 0.15 });
    kin($('f3'), 'THOUSANDS OF JOURNEYS.', 54.05, 59.35, t, { ...slam, stagger: 0.09 });
    const tots = [[oT1, S.stats.arr, 'r1', 'k1', 'TOTAL ARRIVALS', 55.0], [oT2, S.stats.dep, 'r2', 'k2', 'TOTAL DEPARTURES', 55.45], [oT3, S.stats.pax, 'r3', 'k3', 'TOTAL PASSENGERS', 55.9], [oT4, S.stats.dep + S.stats.arr, 'r4', 'k4', 'TOTAL FLIGHTS', 56.35]];
    tots.forEach(([o, val, id, kid, lab, t0], i) => {
      pop($(id), t0, 59.32 + i * 0.06, t, { s0: 0.7, y0: 30 });
      kin($(kid), lab, t0 + 0.06, 59.3 + i * 0.06, t, { stagger: 0.08 });
      o.set(val * easeOut((t - t0 - 0.1) / 1.3));
    });
    kin($('fFoot'), "Representative day modelled on the airport's route network · local time", 57.6, 59.2, t, { stagger: 0.02, blur: 3, y0: 8 });
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
  const shotOf = t => { let s = SHOTS[SHOTS.length - 1]; for (const x of SHOTS) if (t < x.t1) { s = x; break; } return s; };
  return {
    inset: ALL_EV.map(e => ({ t: e.t, type: e.type === 'G' ? 'D' : e.type, ga: e.type === 'G', wide: e.wide, rw: e.rw, intro: !!e.intro, near: e.intro || e.t < FULL_END ? 0.8 : shotOf(e.t).near, sf: e.intro ? 0.5 : shotOf(e.t).sf })),
    toasts: TOASTS.map(x => x.t), hours: [...Array(25)].map((_, h) => vidT(h * 60)), samples, milestones: MS.map(x => x.t), cuts: CUTS, ga: GA_EV.map(g => g.t),
    words: WORD_TICKS, T_RISE, T0, TN, TE, switchT: -1, sunrise: vidT(SUNRISE), sunset: vidT(SUNSET),
    title: 0.12, sky: 0.5, subs: [1.05, 1.38, 1.6], tag: [52.45, 53.25, 54.05], totals: [55.0, 55.45, 55.9, 56.35],
  };
};
window.READY = true;

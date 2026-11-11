// Scene choreography. Every time comes from the voiceover word timings (w = word start, we = word end).

// ---------- shared builders ----------
function figure(parent, x, floorY, h, o = {}) {
  const hw = h * 0.3, bw = h * 0.46, bh = h * 0.62;
  const fg = div('floor-glow', parent);
  fg.style.cssText += `left:${x - h * 0.75}px;top:${floorY - h * 0.075}px;width:${h * 1.5}px;height:${h * 0.15}px;`;
  if (o.ring) fg.style.background = `radial-gradient(closest-side, rgba(255,209,92,.75), rgba(255,209,92,.12) 70%, rgba(255,209,92,0))`;
  const wrap = div('fig-wrap reflect', parent);
  wrap.style.cssText += `left:${x - bw / 2}px;top:${floorY - h}px;width:${bw}px;height:${h}px;`;
  const head = div('', wrap); head.style.cssText = `position:absolute;left:${(bw - hw) / 2}px;top:0;width:${hw}px;height:${hw}px;border-radius:50%;background:radial-gradient(circle at 40% 32%,#fff 0%,#eef2fa 55%,#b8c1d6 100%)`;
  const body = div('', wrap); body.style.cssText = `position:absolute;left:0;top:${h - bh}px;width:${bw}px;height:${bh}px;border-radius:${bw / 2}px ${bw / 2}px ${bw * 0.14}px ${bw * 0.14}px;background:radial-gradient(ellipse at 40% 18%,#fff 0%,#e8edf7 50%,#a9b3c9 100%)`;
  return { wrap, fg, all: [wrap, fg] };
}
function lbl(parent, text, cls = '', x, y, size) { const e = div('lbl ' + cls, parent, text); if (size) e.style.fontSize = size + 'px'; at(e, x, y); return e; }
function strike(parent, color = C.red) { const s = div('', parent); s.style.cssText = `position:absolute;left:-4%;width:108%;top:50%;height:6px;margin-top:-3px;background:${color};border-radius:3px;box-shadow:0 0 12px ${color};transform-origin:left center;transform:scaleX(0)`; return s; }
function pathHead(p, t0, dur, easeName, fn) {
  const len = p.getTotalLength(), f = ease(easeName);
  dyn(t => { const k = f(clamp01((t - t0) / dur)), pt = p.getPointAtLength(len * k); fn(pt.x, pt.y, k, t); });
}
function samplePath(p, n = 160) { const len = p.getTotalLength(); return Array.from({ length: n + 1 }, (_, i) => { const q = p.getPointAtLength(len * i / n); return [q.x, q.y]; }); }
function cursor(parent) { const c = div('', parent, icon('mouse-pointer-click', 92, '#fff', 1.6)); c.style.filter = 'drop-shadow(0 6px 10px rgba(0,0,0,.6)) drop-shadow(0 0 14px rgba(255,255,255,.35))'; return c; }
function ripple(parent, x, y, t, color = '#fff') { const r = div('', parent); r.style.cssText += `width:160px;height:160px;border-radius:50%;border:5px solid ${color};`; at(r, x, y, { autoAlpha: 0 }); tl.fromTo(r, { scale: 0.4, autoAlpha: 0.9 }, { scale: 2.2, autoAlpha: 0, duration: 0.6, ease: 'power2.out', immediateRender: false }, t); return r; }

// =====================================================================
// S01  HOOK — a live counter that's visibly draining
// =====================================================================
(() => {
  const t1 = w('s02', 'quick') + 0.04, sc = scene('hook', 0, t1);
  tint(0, 'red', 0.13, 0.01);
  envTo(0, { spot: 1, grid: 0.08 }, 0.01);
  music(0, 0.7);

  const tag = div('row lbl w', sc, `<span class="dot" style="display:inline-block;width:16px;height:16px;border-radius:50%;background:${C.red};box-shadow:0 0 14px ${C.red};margin-right:16px"></span>LIVE&nbsp;&nbsp;·&nbsp;&nbsp;Your savings&nbsp;&nbsp;·&nbsp;&nbsp;Real value`);
  at(tag, 540, 330);
  const dot = tag.querySelector('.dot');
  dyn(t => { dot.style.opacity = 0.35 + 0.65 * (Math.sin(t * 7) > 0 ? 1 : 0.2); });

  const num = div('num glow-w', sc); num.style.fontSize = '190px'; at(num, 540, 485);
  const loss = div('mono', sc); loss.style.cssText += `font-size:36px;font-weight:800;color:${C.red};letter-spacing:.04em;`; at(loss, 540, 635);
  dyn(t => {
    const v = 1000 - 9.5 * Math.pow(Math.max(0, t - 0.15), 1.55), [i, d] = money(v, 2).split('.');
    num.innerHTML = `<span style="font-size:.55em;vertical-align:.62em;margin-right:6px">$</span>${i}<span style="font-size:.42em;color:#FF6B80">.${d}</span>`;
    loss.innerHTML = `▼ LOST SO FAR&nbsp;&nbsp;$${money(1000 - v, 2)}`;
  });
  emitter({ t0: 0.35, t1: t1, rate: 16, x: r => lerp(280, 800, r()), y: r => 548 + r() * 16, vy: [0, 80], g: 1300, life: 0.95, size: [3, 5.5], color: RGB.red, seed: 3 });

  const you = figure(sc, 540, 1080, 330, { ring: true });
  lbl(sc, 'You', 'gold', 540, 1128, 24);

  const tS = w('s01', 'shrinking');
  tl.fromTo(num, { color: '#FF4560' }, { color: '#F2F5FF', duration: 0.7, immediateRender: false }, tS);
  shake(tS, 0.45, 0.4); punch(tS, 0.035);
  sfx('hit', tS, 0.7);

  // "...and you can't even SEE it" — the money goes invisible
  const tSee = w('s01', 'see');
  tl.to(num, { opacity: 0.1, filter: 'blur(18px)', duration: 0.5, ease: 'power2.out' }, tSee - 0.05);
  tl.to(loss, { opacity: 0.12, filter: 'blur(8px)', duration: 0.5 }, tSee - 0.05);
  const eye = div('', sc, icon('eye-off', 150, '#F2F5FF', 1.3)); eye.style.filter = 'drop-shadow(0 0 22px rgba(255,255,255,.6))'; at(eye, 540, 480);
  popIn(eye, tSee, { from: 0.3, sfx: 'shimmer', gain: 0.7 });
  const inv = lbl(sc, 'Invisible', 'red', 540, 600, 26); fadeIn(inv, tSee + 0.15, 0.3, { y: 14 });

  // camera: open tight on the number, pull back to reveal "you"
  camSet(0, 540, 520, 1.22);
  focus(0.7, 540, 720, 1.0, 1.4);
  sfx('boom', 0.02, 0.85);
  for (let t = 0.2; t < 3.2; t += 0.09) sfx('tick', t, 0.16);
  sfx('riser', S('s02') - 1.0, 0.5, { dur: 1.0 });
  glitch(S('s02') - 0.08, 0.3);
})();

// =====================================================================
// S02 + S03  QUIZ — guess in the comments, then the reveal
// =====================================================================
(() => {
  const t0 = S('s02') - 0.02, t1 = S('s04') + 0.12, sc = scene('quiz', t0, t1);
  tint(t0, 'gold', 0.13, 0.4);
  camSet(t0, 540, 760, 1);
  music(t0, 0.6);

  const tQ = w('s02', 'quick');
  const stamp = div('stamp glow-g', sc, 'Quick test'); stamp.style.cssText += `font-size:116px;color:${C.gold};`; at(stamp, 540, 560);
  slam(stamp, tQ, { rot: -5, from: 2.6, shake: 1 });
  flash(tQ + 0.02, 0.22, 0.25, C.gold);
  tl.to(stamp, { top: 228, scale: 0.4, rotation: 0, duration: 0.5, ease: 'power3.inOut' }, L('s02', 1).start - 0.2);

  // savings card
  const card = div('card gold row', sc); card.style.cssText += 'width:690px;height:178px;padding:0 40px;gap:32px;';
  card.innerHTML = `<div>${icon('wallet', 90, C.gold, 1.5)}</div>
    <div class="col" style="gap:12px;flex:1"><div class="lbl gold cl">Your savings</div><div class="num cv" style="font-size:96px">$0</div></div>
    <div class="chip cy" style="color:#F2F5FF;font-size:32px">${icon('calendar', 30, '#F2F5FF', 2)}<span>2020</span></div>`;
  at(card, 540, 418);
  popIn(card, w('s02', 'saved') - 0.05, { from: 0.7, y: 40 });
  const cv = card.querySelector('.cv'), cl = card.querySelector('.cl'), cy = card.querySelector('.cy');
  popIn(cy, w('s02', 'twenty'), { from: 0.2, sfx: 'click', rot: -20 });
  const tA = w('s02', 'a'), dA = we('s02', 'dollars') - tA, tB = w('s03', 'eight'), dB = we('s03', 'worth') - tB;
  dyn(t => {
    let v, red = 0;
    if (t < tB) v = lerp(0, 1000, E_OUT(clamp01((t - tA) / dA)));
    else { const k = E_INOUT(clamp01((t - tB) / dB)); v = lerp(1000, 800, k); red = k; }
    cv.textContent = '$' + money(v);
    cv.style.color = `rgb(${mixRGB(RGB.white, RGB.red, red)})`;
    cl.textContent = t < tB ? 'Your savings' : 'Buys today';
  });

  const q = lbl(sc, 'What does it buy today?', 'w', 540, 572, 24);
  fadeIn(q, w('s02', 'what') - 0.05, 0.4, { y: 20 });

  const opts = [['A', '$1,000'], ['B', '$900'], ['C', '$800']].map(([k, v], i) => {
    const o = div('card pill', sc); o.style.cssText += 'width:640px;height:92px;border-width:2.5px;';
    o.innerHTML = `<div style="width:56px;height:56px;border-radius:50%;border:2.5px solid #F2F5FF;display:flex;align-items:center;justify-content:center;font:800 28px Inter">${k}</div>
      <div class="num" style="font-size:52px;flex:1">${v}<span style="font:700 22px Inter;color:#8A93A8;margin-left:16px;letter-spacing:.2em">WORTH</span></div>
      <div class="mark" style="width:60px;height:60px"></div>`;
    at(o, 540, 682 + i * 112);
    const ti = w('s02', 'buy') + i * 0.12 - 0.1;
    tl.fromTo(o, { autoAlpha: 0, x: 280 }, { autoAlpha: 1, x: 0, duration: 0.45, ease: 'back.out(1.6)' }, ti);
    sfx('pop', ti + 0.05, 0.5);
    o._strike = strike(o);
    return o;
  });

  // countdown + comment prompt
  const tc0 = w('s02', 'lock'), tc1 = S('s03'), dc = tc1 - tc0;
  const cp = div('row', sc); cp.style.gap = '20px';
  cp.innerHTML = `<svg width="68" height="68" viewBox="0 0 68 68" style="overflow:visible"><circle cx="34" cy="34" r="29" stroke="rgba(255,255,255,.15)" stroke-width="6" fill="none"/>
    <circle class="ring" cx="34" cy="34" r="29" stroke="${C.gold}" stroke-width="6" fill="none" stroke-linecap="round" transform="rotate(-90 34 34)" stroke-dasharray="182.2 182.2"/>
    <text class="cd" x="34" y="46" text-anchor="middle" font-family="Inter Display" font-weight="900" font-size="34" fill="#fff">3</text></svg>
    <div class="lbl w" style="font-size:24px;letter-spacing:.24em">Comment A, B or C</div>${icon('message-circle', 42, C.gold, 2)}`;
  at(cp, 540, 1012);
  popIn(cp, tc0 - 0.1, { from: 0.8, sfx: false });
  const ring = cp.querySelector('.ring'), cd = cp.querySelector('.cd');
  dyn(t => { const k = clamp01((t - tc0) / dc); ring.style.strokeDashoffset = 182.2 * k; cd.textContent = Math.max(1, 3 - Math.floor(k * 3)); });
  for (let i = 0; i < 3; i++) { sfx('clock', tc0 + i * dc / 3, 0.9); tl.fromTo(cd, { scale: 1.5, transformOrigin: '34px 34px' }, { scale: 1, duration: 0.25, immediateRender: false }, tc0 + i * dc / 3); }
  tl.to(opts, { scale: 1.02, duration: dc / 6, yoyo: true, repeat: 5, ease: 'sine.inOut', stagger: 0.08 }, tc0);

  // reveal
  const tr = S('s03');
  opts.slice(0, 2).forEach((o, i) => { tl.to(o, { opacity: 0.3, duration: 0.3 }, tr); tl.to(o._strike, { scaleX: 1, duration: 0.3, ease: 'power2.out' }, tr + i * 0.06); });
  tl.to(opts[2], { borderColor: C.mint, boxShadow: '0 0 44px rgba(61,255,176,.6)', scale: 1.07, duration: 0.35, ease: 'back.out(3)' }, tr);
  const mark = opts[2].querySelector('.mark'); mark.innerHTML = icon('check', 60, C.mint, 3);
  popIn(mark, tr + 0.05, { from: 0, sfx: 'ding', gain: 0.9 });
  flash(tr, 0.18, 0.3, C.mint); shake(tr, 0.4, 0.3);
  out(cp, tr, 0.25);
  tl.to(card, { borderColor: C.red, boxShadow: '0 0 34px rgba(255,69,96,.5)', duration: 0.4 }, tB + dB * 0.6);
  sfx('down', tB, 0.6, { dur: dB });

  // the missing $200 breaks off
  const tX = we('s03', 'worth') + 0.02;
  tl.to(opts, { autoAlpha: 0, y: 60, stagger: 0.05, duration: 0.3, ease: 'power2.in' }, tX);
  out(q, tX, 0.25);
  const blocks = div('row', sc); blocks.style.gap = '10px'; at(blocks, 540, 742);
  const bl = [...Array(10)].map((_, i) => {
    const b = div('', blocks), red = i >= 8, c = red ? C.red : C.mint, rgb = red ? '255,69,96' : '61,255,176';
    b.style.cssText = `position:relative;width:58px;height:92px;border-radius:12px;border:3px solid ${c};background:rgba(${rgb},.2);box-shadow:0 0 18px rgba(${rgb},.45)`;
    return b;
  });
  tl.fromTo(bl, { autoAlpha: 0, scale: 0.2 }, { autoAlpha: 1, scale: 1, stagger: 0.03, duration: 0.3, ease: 'back.out(2)' }, tX + 0.08);
  sfx('swoosh', tX + 0.08, 0.5);
  const each = lbl(sc, 'Each block = $100 of stuff', '', 540, 832, 20); fadeIn(each, tX + 0.3, 0.3);
  const tG = w('s03', 'two');
  tl.to(bl[9], { y: 520, x: 90, rotation: 55, autoAlpha: 0, duration: 1.1, ease: 'power2.in' }, tG);
  tl.to(bl[8], { y: 540, x: -20, rotation: -38, autoAlpha: 0, duration: 1.15, ease: 'power2.in' }, tG + 0.05);
  emitter({ t0: tG, t1: tG + 0.12, rate: 260, x: r => lerp(770, 850, r()), y: r => lerp(700, 790, r()), vx: [-380, 380], vy: [-650, -150], g: 1500, life: 0.8, size: [2.5, 5], color: RGB.red, seed: 21, shape: 'dot' });
  const minus = div('num glow-r', sc, '−$200'); minus.style.fontSize = '150px'; at(minus, 540, 958);
  slam(minus, tG + 0.06, { from: 1.9, shake: 1.1, sfx: 'boom' });
  tint(tG, 'red', 0.2, 0.3);
  const tGone = w('s03', 'gone');
  tl.to(minus, { opacity: 0, scale: 1.3, filter: 'blur(16px)', duration: 0.45, ease: 'power2.in' }, tGone + 0.05);
  glitch(tGone, 0.22, 0.7);

  // "...without spending a cent" — a receipt for $0.00
  const tW = w('s03', 'without');
  const rc = div('', sc); rc.style.cssText += `width:440px;padding:30px 34px;background:linear-gradient(#F4F5F8,#DADDE5);color:#151821;border-radius:6px;box-shadow:0 30px 70px rgba(0,0,0,.7);font-family:'JetBrains Mono',monospace;font-size:25px;line-height:1.75;`;
  rc.innerHTML = `<div style="text-align:center;font-weight:800;letter-spacing:.3em">RECEIPT</div><div style="border-top:3px dashed #9aa0ad;margin:10px 0"></div>
    <div style="display:flex;justify-content:space-between"><span>ITEMS</span><span>0</span></div>
    <div style="display:flex;justify-content:space-between"><span>SPENT</span><b>$0.00</b></div><div style="border-top:3px dashed #9aa0ad;margin:10px 0"></div>
    <div style="text-align:center;font-size:20px;color:#5b6170">THANK YOU</div>`;
  at(rc, 540, 960);
  tl.fromTo(rc, { autoAlpha: 0, y: 500, rotation: 6 }, { autoAlpha: 1, y: 0, rotation: -3, duration: 0.5, ease: 'power3.out' }, tW - 0.1);
  sfx('swoosh', tW - 0.1, 0.6);
  const st2 = div('stamp', sc, 'Still −$200'); st2.style.cssText += `font-size:54px;color:${C.red};background:rgba(255,69,96,.08);`; at(st2, 560, 975);
  slam(st2, w('s03', 'cent'), { rot: -14, from: 2.2, shake: 0.8 });
  whip(t1 - 0.1);
})();

// =====================================================================
// S04  INFLATION — prices climb, year after year
// =====================================================================
(() => {
  const t0 = S('s04') - 0.08, t1 = S('s05') + 0.12, sc = scene('inflation', t0, t1);
  camSet(t0, 540, 760, 1);
  music(t0, 0.8);
  const ti = w('s04', 'inflation');
  const glow = div('', sc); glow.style.cssText += 'width:1000px;height:420px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,69,96,.35),rgba(255,69,96,0));'; at(glow, 540, 560);
  tl.fromTo(glow, { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.6 }, ti);
  const title = div('big-title reflect glow-w', sc); title.style.cssText += 'font-size:138px;letter-spacing:.04em;';
  title.innerHTML = 'INFLATION'.split('').map(c => `<span style="display:inline-block">${c}</span>`).join('');
  at(title, 540, 560);
  tl.fromTo(title.children, { y: -280, autoAlpha: 0, rotationX: -80 }, { y: 0, autoAlpha: 1, rotationX: 0, duration: 0.55, ease: 'back.out(1.8)', stagger: 0.035 }, ti - 0.15);
  sfx('boom', ti, 0.9); punch(ti + 0.15, 0.05); shake(ti + 0.2, 0.5, 0.4); tint(ti, 'red', 0.22);

  const tg = w('s04', 'groceries');
  tl.to(title, { top: 248, scale: 0.42, duration: 0.5, ease: 'power3.inOut' }, tg - 0.25);
  tl.to(glow, { autoAlpha: 0, duration: 0.4 }, tg - 0.25);

  const cats = [['groceries', 'shopping-cart', 'Groceries'], ['rent', 'house', 'Rent'], ['gas', 'fuel', 'Gas'], ['insurance', 'shield', 'Insurance']];
  const pos = [[315, 575], [765, 575], [315, 865], [765, 865]];
  const ups = [];
  cats.forEach(([word, ic, name], i) => {
    const c = div('card', sc); c.style.cssText += 'width:400px;height:250px;';
    c.innerHTML = `<div style="position:absolute;left:30px;top:30px">${icon(ic, 78, '#F2F5FF', 1.4)}</div>
      <div class="lbl w" style="position:absolute;left:30px;bottom:30px;font-size:24px">${name}</div>
      <div class="up" style="position:absolute;right:26px;bottom:24px;color:${C.red};font:900 30px Inter;display:flex;align-items:center;gap:2px">${icon('arrow-up', 32, C.red, 3)}<span>UP</span></div>
      <svg width="400" height="250" style="position:absolute;left:0;top:0;overflow:visible"><path class="spark" d="M160 185 L200 172 L232 180 L268 146 L300 140 L334 100 L370 60" fill="none" stroke="${C.red}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" style="filter:drop-shadow(0 0 8px rgba(255,69,96,.8))"/></svg>`;
    at(c, ...pos[i]);
    const tw = w('s04', word);
    popIn(c, tw - 0.08, { from: 0.5, y: 30, sfx: 'pop', gain: 0.7 });
    drawPath(c.querySelector('.spark'), tw + 0.02, 0.6);
    sfx('tick', tw + 0.15, 0.35);
    ups.push(c.querySelector('.up'));
  });

  // year ticker
  const yc = div('chip', sc); yc.style.cssText += `color:${C.gold};font-size:34px;`; at(yc, 540, 352);
  popIn(yc, w('s04', 'prices') - 0.1, { from: 0.4, sfx: false });
  const te = w('s04', 'every'), tyEnd = we('s04', 'year') + 0.1, dy = tyEnd - te;
  dyn(t => { const y = 2020 + Math.min(6, Math.floor(clamp01((t - te) / dy) * 6.999)); yc.innerHTML = `${icon('calendar', 30, C.gold, 2)}<span class="mono">${y}</span>`; });
  for (let k = 1; k <= 6; k++) {
    const tk = te + (k / 6.999) * dy;
    sfx('tick', tk, 0.55);
    tl.fromTo(ups, { scale: 1.35 }, { scale: 1, duration: 0.22, immediateRender: false }, tk);
  }
  punch(w('s04', 'climb'), 0.03);
  whip(t1 - 0.1);
})();

// =====================================================================
// S05  SAVINGS — the account pays ~nothing; buying power drains
// =====================================================================
(() => {
  const t0 = S('s05') - 0.08, t1 = S('s06'), sc = scene('savings', t0, t1);
  tint(t0, 'navy', 0.2, 0.5);
  camSet(t0, 540, 760, 1);
  const pan = div('card', sc); pan.style.cssText += 'width:780px;height:390px;padding:40px 46px;';
  const bar = (cls, color, rgb, wpct, val, glowCls) => `<div class="row" style="gap:22px;margin-top:14px"><div style="flex:1;height:26px;border-radius:13px;background:rgba(255,255,255,.08);position:relative">
      <div class="${cls}" style="position:absolute;left:0;top:0;bottom:0;width:${wpct}%;border-radius:13px;background:${color};box-shadow:0 0 18px rgba(${rgb},.75);transform-origin:left center;transform:scaleX(0)"></div></div>
      <div class="num ${glowCls}" style="font-size:46px;width:130px;text-align:right">${val}</div></div>`;
  pan.innerHTML = `<div class="row" style="justify-content:space-between"><div class="lbl w" style="font-size:26px">Savings account</div><div class="lbl" style="font-size:17px">US average</div></div>
    <div class="lbl" style="margin-top:46px">Prices / year</div>${bar('b1', C.red, '255,69,96', 82, '~3%', 'glow-r')}
    <div class="lbl" style="margin-top:36px">Your interest</div>${bar('b2', C.mint, '61,255,176', 11, '~0.4%', 'glow-m')}`;
  at(pan, 540, 565, { transformPerspective: 1400 });
  tl.fromTo(pan, { autoAlpha: 0, rotationY: 75, rotationX: 6, x: 320 }, { autoAlpha: 1, rotationY: -12, rotationX: 6, x: 0, duration: 0.7, ease: 'power3.out' }, S('s05') - 0.05);
  sfx('whoosh', S('s05') - 0.1, 0.5);
  tl.to(pan.querySelector('.b1'), { scaleX: 1, duration: 0.6, ease: 'power3.out' }, w('s05', 'savings'));
  sfx('swoosh', w('s05', 'savings'), 0.4);
  tl.to(pan.querySelector('.b2'), { scaleX: 1, duration: 0.5, ease: 'power3.out' }, w('s05', 'pays'));
  const tn = w('s05', 'nothing');
  tl.fromTo(pan.querySelector('.b2'), { opacity: 1 }, { opacity: 0.2, duration: 0.07, repeat: 5, yoyo: true, immediateRender: false }, tn);
  const note = div('card pill', sc, `${icon('banknote', 44, C.mint, 1.6)}<span style="font:700 34px Inter">$1,000 earns&nbsp;<b class="glow-m">≈ $4 a year</b></span>`); note.style.height = '96px'; at(note, 540, 840);
  popIn(note, tn + 0.05, { from: 0.6, sfx: 'buzz', gain: 0.5 });

  // balance looks the same...
  const tb = L('s05', 1).start;
  tl.to([pan, note], { autoAlpha: 0, y: -220, duration: 0.4, ease: 'power2.in', stagger: 0.04 }, tb - 0.25);
  const bal = div('col', sc); bal.style.alignItems = 'center';
  bal.innerHTML = `<div class="lbl w" style="font-size:24px">Balance</div><div class="row" style="gap:18px;margin-top:6px"><div class="num glow-w" style="font-size:130px">$1,000</div>
    <svg width="90" height="90" viewBox="0 0 24 24" style="overflow:visible"><path class="ck" d="M4 12.5l5 5L20 6.5" fill="none" stroke="${C.mint}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="filter:drop-shadow(0 0 6px ${C.mint})"/></svg></div>`;
  at(bal, 540, 395);
  fadeIn(bal, tb, 0.45, { y: 40, scale: 0.9 });
  drawPath(bal.querySelector('.ck'), w('s05', 'same') - 0.1, 0.35);
  sfx('ding', w('s05', 'same'), 0.6);

  // ...but the cart keeps shrinking
  const items = ['milk', 'egg', 'apple', 'croissant', 'beef', 'carrot', 'coffee', 'cookie', 'fish', 'sandwich'];
  const tBuy = w('s05', 'buys') - 0.15;
  const shelf = items.map((n, i) => { const e = div('', sc, icon(n, 88, '#F2F5FF', 1.4)); e.style.filter = 'drop-shadow(0 0 10px rgba(255,255,255,.35))'; at(e, 540 + (i % 5 - 2) * 150, i < 5 ? 600 : 760); return e; });
  [672, 832].forEach(y => { const s = div('', sc); s.style.cssText += 'width:780px;height:3px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.6),transparent);'; at(s, 540, y); fadeIn(s, tBuy, 0.4); });
  tl.fromTo(shelf, { autoAlpha: 0, y: 40, scale: 0.6 }, { autoAlpha: 1, y: 0, scale: 1, stagger: 0.035, duration: 0.35, ease: 'back.out(2)' }, tBuy);
  sfx('swoosh', tBuy, 0.5);
  const bpL = div('lbl w', sc); bpL.style.fontSize = '22px'; at(bpL, 380, 915);
  const bpV = div('num', sc); bpV.style.fontSize = '50px'; at(bpV, 840, 912);
  const track = div('', sc); track.style.cssText += 'width:760px;height:24px;border-radius:12px;background:rgba(255,255,255,.08);'; at(track, 540, 968);
  const fill = div('', track); fill.style.cssText = 'position:absolute;left:0;top:0;bottom:0;border-radius:12px;';
  fadeIn([bpL, bpV, track], tBuy + 0.2, 0.4, { y: 20 });
  const tl0 = w('s05', 'less'), tl1 = we('s05', 'year') + 0.15, dl = tl1 - tl0;
  dyn(t => {
    const k = E_INOUT(clamp01((t - tl0) / dl)), p = 100 - 20 * k, c = mixRGB(RGB.mint, RGB.red, k);
    fill.style.width = p + '%'; fill.style.background = `rgb(${c})`; fill.style.boxShadow = `0 0 18px rgba(${c},.7)`;
    bpV.textContent = p.toFixed(0) + '%'; bpV.style.color = `rgb(${c})`;
    bpL.textContent = 'Buying power · ' + (2020 + Math.round(6 * k));
  });
  [9, 8].forEach((idx, k) => { const tk = tl0 + 0.15 + k * 0.5; tl.to(shelf[idx], { y: 80, autoAlpha: 0, scale: 0.5, rotation: 25, duration: 0.45, ease: 'power2.in' }, tk); sfx('pop', tk, 0.45, { pitch: 0.7 }); });
  sfx('down', tl0, 0.5, { dur: dl });
})();

// =====================================================================
// S06  TWIST — "what they don't teach you in school"
// =====================================================================
(() => {
  const t0 = S('s06') - 0.02, t1 = S('s07') + 0.1, sc = scene('twist', t0, t1);
  envTo(t0, { dim: 0.3, spot: 1.5, grid: 0.03 }, 0.25); tint(t0, 'red', 0.1, 0.25);
  music(t0, 0.12, { filter: 1 });
  sfx('hit', t0, 0.7);
  sfx('riser', t0 + 0.2, 0.8, { dur: S('s07') - t0 - 0.2 });
  const doc = div('card red', sc); doc.style.cssText += 'width:720px;height:540px;padding:48px 54px;';
  doc.innerHTML = `<div class="lbl red" style="font-size:20px">File · ECON-101</div>
    <div class="lbl w" style="font-size:28px;margin-top:18px;letter-spacing:.2em">What school teaches you</div>
    <div style="border-top:2px solid rgba(255,69,96,.4);margin:26px 0 28px"></div>
    <div class="mono l1" style="font-size:36px;height:56px"></div><div class="mono l2" style="font-size:36px;height:56px"></div>
    <div class="red-bars"></div>`;
  at(doc, 540, 610);
  tl.fromTo(doc, { autoAlpha: 0, y: 60, scale: 0.94 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.4, ease: 'power3.out' }, t0);
  typeText(doc.querySelector('.l1'), '01  Save your money ✓', t0 + 0.2, 40);
  typeText(doc.querySelector('.l2'), '02  Work hard ✓', t0 + 0.75, 40);
  for (let k = 0; k < 10; k++) sfx('type', t0 + 0.2 + k * 0.1, 0.35);
  const rb = doc.querySelector('.red-bars'); rb.style.cssText = 'display:flex;flex-direction:column;gap:16px;margin-top:10px';
  const bars = [430, 560, 360].map(wd => { const b = div('', rb); b.style.cssText = `position:relative;width:${wd}px;height:34px;background:#C9D0DE;border-radius:4px;transform-origin:left center`; return b; });
  tl.fromTo(bars, { scaleX: 0 }, { scaleX: 1, stagger: 0.12, duration: 0.3, ease: 'power2.out' }, w('s06', 'dont') - 0.1);
  const cl = div('stamp', sc, 'Classified'); cl.style.cssText += `font-size:96px;color:${C.red};background:rgba(255,69,96,.07);`; at(cl, 560, 700);
  slam(cl, w('s06', 'school'), { rot: -13, from: 2.5, shake: 1, sfx: 'stamp', gain: 1 });
  camSet(t0, 540, 680, 1.0);
  focus(t0 + 0.05, 540, 660, 1.08, S('s07') - t0, 'power1.in');
  // bars rip off into the next scene
  const tc = S('s07');
  tl.to(bars, { x: 700, rotation: 18, autoAlpha: 0, stagger: 0.04, duration: 0.3, ease: 'power2.in' }, tc - 0.28);
  tl.to(cl, { autoAlpha: 0, scale: 1.4, duration: 0.25 }, tc - 0.2);
  glitch(tc - 0.06, 0.32);
  flash(tc, 0.45, 0.35, C.mint);
})();

// =====================================================================
// S07 + S08  FLOW — who gets new money first (the Cantillon cascade)
// =====================================================================
(() => {
  const t0 = S('s07') - 0.05, t1 = S('s09') + 0.05, sc = scene('flow', t0, t1);
  const hs = scene('flowHud', t0, t1, hud);
  envTo(t0, { dim: 0, spot: 0.6, grid: 0.1 }, 0.3); tint(t0, 'mint', 0.15, 0.4);
  music(S('s07'), 1.0, { drop: 1 });
  sfx('drop', S('s07'), 1);

  const SRC = [540, 290], N1 = [280, 505], N2 = [800, 505], N3 = [540, 705];
  const svg = svgLayer(sc);
  const mk = (d, cls) => svgEl('path', { d, fill: 'none', stroke: C.mint, 'stroke-width': 5, 'stroke-linecap': 'round', class: cls, style: 'filter:drop-shadow(0 0 8px rgba(61,255,176,.85))' }, svg);
  const D = [
    `M540 365 C540 430, 280 400, 280 441`, `M540 365 C540 430, 800 400, 800 441`,
    `M280 569 C280 640, 540 600, 540 641`, `M800 569 C800 640, 540 600, 540 641`,
    `M540 769 C620 790, 460 815, 540 848`];
  const ghosts = D.map(d => { const g = svgEl('path', { d, fill: 'none', stroke: 'rgba(240,244,255,.25)', 'stroke-width': 3, 'stroke-dasharray': '3 12', 'stroke-linecap': 'round' }, svg); return g; });
  const P = D.map(d => mk(d, 'flow'));
  tl.fromTo(ghosts, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.5, stagger: 0.1 }, w('s07', 'reach') - 0.2);

  // source: freshly printed money
  const src = div('', sc); src.style.cssText += 'width:150px;height:150px;border-radius:50%;border:4px solid #3DFFB0;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle,rgba(61,255,176,.4),rgba(61,255,176,.05) 70%);box-shadow:0 0 60px rgba(61,255,176,.65),inset 0 0 30px rgba(61,255,176,.4)';
  src.innerHTML = `<div class="num glow-m" style="font-size:88px;margin-top:-6px">$</div>`;
  at(src, ...SRC);
  const rays = svgLayer(sc);
  for (let i = 0; i < 16; i++) { const a = i / 16 * Math.PI * 2; svgEl('line', { x1: SRC[0] + Math.cos(a) * 100, y1: SRC[1] + Math.sin(a) * 100, x2: SRC[0] + Math.cos(a) * (i % 2 ? 125 : 145), y2: SRC[1] + Math.sin(a) * (i % 2 ? 125 : 145), stroke: C.mint, 'stroke-width': 4, 'stroke-linecap': 'round', opacity: 0.7 }, rays); }
  rays.style.transformOrigin = `${SRC[0]}px ${SRC[1]}px`;
  dyn(t => { rays.style.transform = `rotate(${t * 40}deg)`; });
  const srcL = lbl(sc, 'New money', 'mint', 540, 178, 24);
  const tN = w('s07', 'new');
  popIn(src, tN - 0.1, { from: 0, sfx: 'boom', gain: 0.6 });
  tl.fromTo(rays, { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, tN);
  fadeIn(srcL, tN + 0.1, 0.3, { y: 14 });
  emitter({ t0: tN, t1: t1 - 1.4, rate: 10, x: r => SRC[0] + lerp(-60, 60, r()), y: SRC[1] - 30, vx: [-90, 90], vy: [-260, -120], g: 260, life: 1.1, size: [5, 7], color: RGB.mint, seed: 9, shape: 'text', glow: 14 });

  // tiers
  const node = (p, ic, name, lx, ly) => {
    const n = div('', sc); n.style.cssText += 'width:128px;height:128px;border-radius:50%;border:3px solid rgba(240,244,255,.45);display:flex;align-items:center;justify-content:center;background:rgba(10,14,24,.92);color:#F2F5FF';
    n.innerHTML = icon(ic, 62, 'currentColor', 1.5); at(n, ...p);
    const l = lbl(sc, name, 'w', lx, ly, 22);
    return { n, l };
  };
  const n1 = node(N1, 'landmark', 'Banks', N1[0], N1[1] + 96);
  const n2 = node(N2, 'chart-candlestick', 'Wall Street', N2[0], N2[1] + 96);
  const n3 = node(N3, 'house', 'Asset owners', N3[0] + 250, N3[1]);
  const tR = w('s07', 'reach');
  [n1, n2, n3].forEach((n, i) => { tl.fromTo([n.n, n.l], { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 0.55, scale: 1, duration: 0.4, ease: 'back.out(2)' }, tR + i * 0.12); sfx('pop', tR + i * 0.12, 0.35); });
  const you = figure(sc, 540, 1080, 230, { ring: true });
  const youL = lbl(sc, 'You', 'gold', 540, 1122, 24);
  tl.fromTo([...you.all, youL], { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.5 }, tR + 0.4);

  const light = (n, t, badge, color = C.mint, rgb = '61,255,176') => {
    tl.to([n.n, n.l], { autoAlpha: 1, duration: 0.2 }, t);
    tl.to(n.n, { borderColor: color, color, boxShadow: `0 0 44px rgba(${rgb},.65), inset 0 0 20px rgba(${rgb},.25)`, scale: 1.12, duration: 0.3, ease: 'back.out(3)' }, t);
    const b = div('chip', sc, badge); b.style.cssText += `color:${color};font-size:22px;padding:6px 14px;`;
    at(b, parseFloat(n.n.style.left) + 78, parseFloat(n.n.style.top) - 64);
    popIn(b, t + 0.05, { from: 0.3, sfx: 'ding', gain: 0.55 });
    return b;
  };
  // money streams along each path
  const streams = [];
  const flow = (i, ts, tt, gap, seed) => {
    drawPath(P[i], ts, tt, 'none');
    streams.push({ pts: samplePath(P[i]), ts, tt, gap, seed });
  };
  const tB = w('s07', 'banks'), tW = w('s07', 'wall'), tT = w('s07', 'then'), tA = w('s07', 'assets');
  flow(0, tB - 0.35, 0.55, 0.075, 1); light(n1, tB + 0.2, '1st');
  flow(1, tW - 0.3, 0.55, 0.075, 2); light(n2, tW + 0.25, '1st');
  flow(2, tT - 0.05, 0.8, 0.12, 3); flow(3, tT - 0.05, 0.8, 0.12, 4); light(n3, tA, '2nd');
  sfx('whoosh', tB - 0.35, 0.45); sfx('whoosh', tW - 0.3, 0.45); sfx('whoosh', tT - 0.05, 0.45);
  const tRe = w('s08', 'reaches'), tPay = w('s08', 'paycheck');
  flow(4, tRe - 0.35, 1.1, 0.34, 5);
  fx((c, t) => {
    if (t < t0 || t > t1) return;
    c.globalCompositeOperation = 'lighter'; c.font = '800 26px Inter'; c.textAlign = 'center'; c.textBaseline = 'middle';
    c.shadowColor = C.mint; c.shadowBlur = 14;
    for (const s of streams) {
      if (t < s.ts) continue;
      const n = Math.floor((t - s.ts) / s.gap);
      for (let j = Math.max(0, n - 40); j <= n; j++) {
        const u = (t - (s.ts + j * s.gap)) / s.tt; if (u < 0 || u > 1) continue;
        const f = u * (s.pts.length - 1), a = Math.floor(f), b = Math.min(a + 1, s.pts.length - 1), q = f - a;
        const x = lerp(s.pts[a][0], s.pts[b][0], q) + Math.sin(j * 12.9 + s.seed) * 6, y = lerp(s.pts[a][1], s.pts[b][1], q);
        c.fillStyle = `rgba(61,255,176,${0.95 * Math.min(1, (1 - u) * 6)})`; c.fillText('$', x, y);
      }
    }
  });

  // they buy before prices move
  const tS = w('s07', 'spend');
  [[160, 420], [920, 420], [370, 640]].forEach(([x, y], i) => {
    const b = div('', sc, `${icon('shopping-bag', 54, C.mint, 1.7)}<div style="position:absolute;right:-12px;bottom:-8px;background:${C.mint};border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center">${icon('check', 20, '#06120d', 3.4)}</div>`);
    b.style.filter = 'drop-shadow(0 0 10px rgba(61,255,176,.6))'; at(b, x, y);
    popIn(b, tS + i * 0.14, { from: 0.2, sfx: 'cash', gain: 0.4 });
  });

  // price meter (screen-space HUD)
  const meter = div('col', hs); meter.style.cssText += 'align-items:center;gap:16px;';
  meter.innerHTML = `<div class="lbl w" style="font-size:18px;letter-spacing:.2em">Prices</div>
    <div style="width:22px;height:470px;border-radius:11px;background:rgba(255,255,255,.1);position:relative"><div class="mf" style="position:absolute;left:0;right:0;bottom:0;border-radius:11px"></div></div>
    <div class="num mv" style="font-size:40px">100</div>`;
  at(meter, 78, 640);
  tl.fromTo(meter, { autoAlpha: 0, x: -40 }, { autoAlpha: 1, x: 0, duration: 0.4 }, tR);
  const mf = meter.querySelector('.mf'), mv = meter.querySelector('.mv');
  const tBe = w('s07', 'before'), tMo = w('s08', 'more'), fM = ease('power1.in');
  dyn(t => {
    const k = fM(clamp01((t - tBe) / (tMo - tBe))), v = 100 + 10 * k, c = mixRGB(RGB.mint, RGB.red, clamp01(k * 1.3));
    mf.style.height = (30 + 70 * k) + '%'; mf.style.background = `rgb(${c})`; mf.style.boxShadow = `0 0 16px rgba(${c},.8)`;
    mv.textContent = v.toFixed(0); mv.style.color = `rgb(${c})`;
  });
  sfx('riser', tBe, 0.5, { dur: tMo - tBe });

  // by the time it reaches YOUR paycheck...
  const last = div('chip', sc, 'Last'); last.style.cssText += `color:${C.red};font-size:22px;padding:6px 14px;`; at(last, 650, 862);
  popIn(last, tPay - 0.1, { from: 0.3, sfx: 'pop', gain: 0.5 });
  const pay = div('card mint col', sc); pay.style.cssText += 'width:300px;height:150px;align-items:center;justify-content:center;gap:8px;';
  pay.innerHTML = `<div class="lbl mint" style="font-size:18px">Your paycheck</div><div class="num glow-m pv" style="font-size:64px">+$100</div><div class="lbl red pb" style="font-size:18px;opacity:0">Buys $91 worth</div>`;
  at(pay, 345, 880);
  popIn(pay, tPay, { from: 0.5, y: 30, sfx: 'cash', gain: 0.7 });
  const tEv = w('s08', 'everything'), tAl = w('s08', 'already'), tCo = w('s08', 'costs');
  [[tEv, 'Rent', 790, 800], [tAl, 'Food', 805, 885], [tCo, 'Gas', 790, 970]].forEach(([t, name, x, y]) => {
    const g = div('chip', sc, `${name} ${icon('arrow-up', 26, C.red, 3)}`); g.style.cssText += `color:${C.red};font-size:26px;`; at(g, x, y);
    popIn(g, t - 0.05, { from: 0.3, sfx: 'pop', gain: 0.55, rot: 12 });
  });
  tl.to(pay, { borderColor: C.red, boxShadow: '0 0 34px rgba(255,69,96,.5)', duration: 0.3 }, tMo);
  tl.to(pay.querySelector('.pv'), { color: '#8A93A8', textShadow: 'none', duration: 0.3 }, tMo);
  tl.to(pay.querySelector('.pb'), { opacity: 1, duration: 0.3 }, tMo + 0.05);
  shake(tMo, 0.9, 0.5); flash(tMo, 0.2, 0.3, C.red); tint(tMo, 'red', 0.2, 0.4); sfx('boom', tMo, 0.8);

  // camera choreography
  camSet(t0, 540, 330, 1.35);
  focus(tR - 0.3, 540, 640, 1.0, 1.0);
  focus(tB - 0.3, 410, 520, 1.12, 0.7);
  focus(tW - 0.25, 670, 520, 1.12, 0.6);
  focus(tT - 0.1, 540, 640, 1.06, 0.8);
  focus(tS - 0.2, 540, 620, 0.98, 0.8);
  focus(S('s08') + 0.1, 540, 900, 1.18, 1.0);
  focus(tMo + 0.15, 540, 720, 1.0, 0.8);
})();

// =====================================================================
// S09  NAME — "The Cantillon Effect" + save prompt
// =====================================================================
(() => {
  const t0 = S('s09') - 0.02, t1 = S('s10') + 0.12, sc = scene('name', t0, t1);
  envTo(t0, { dim: 0.5, spot: 1.3, grid: 0.03 }, 0.3); tint(t0, 'gold', 0.08, 0.3);
  camSet(t0, 540, 760, 1);
  focus(t0, 540, 700, 1.06, w('s09', 'the') - t0, 'power1.inOut');
  music(t0, 0.0);
  const pre = lbl(sc, 'This has a name', 'w', 540, 640, 28); pre.style.letterSpacing = '.5em';
  fadeIn(pre, t0 + 0.05, 0.6, { scale: 0.92 });
  sfx('shimmer', t0 + 0.05, 0.4);
  const tThe = w('s09', 'the'), tc = w('s09', 'cantillon'), te = w('s09', 'effect');
  out(pre, tThe - 0.1, 0.2);

  const blk = div('col', sc); blk.style.cssText += 'align-items:center;';
  const goldSpan = c => `<span style="display:inline-block;background:linear-gradient(180deg,#FFF3C9 0%,#FFD15C 45%,#E8901A 100%);-webkit-background-clip:text;background-clip:text;color:transparent">${c}</span>`;
  blk.innerHTML = `<div class="lbl gold the" style="font-size:36px;letter-spacing:.6em;margin-left:.6em">The</div>
    <div class="big-title cant" style="font-size:146px;letter-spacing:-.01em;margin-top:18px;filter:drop-shadow(0 0 26px rgba(255,190,60,.55))">${'CANTILLON'.split('').map(goldSpan).join('')}</div>
    <div class="big-title eff glow-w" style="font-size:116px;letter-spacing:.12em;margin-top:6px">${'EFFECT'.split('').map(c => `<span style="display:inline-block">${c}</span>`).join('')}</div>`;
  at(blk, 540, 590);
  gsap.set(blk, { transformPerspective: 900 });
  fadeIn(blk.querySelector('.the'), tThe, 0.3, { y: 20 });
  tl.fromTo(blk.querySelector('.cant').children, { rotationX: -100, autoAlpha: 0, y: 50, transformPerspective: 700 }, { rotationX: 0, autoAlpha: 1, y: 0, stagger: 0.035, duration: 0.5, ease: 'back.out(1.6)' }, tc - 0.1);
  tl.fromTo(blk.querySelector('.eff').children, { rotationX: -100, autoAlpha: 0, y: 50, transformPerspective: 700 }, { rotationX: 0, autoAlpha: 1, y: 0, stagger: 0.035, duration: 0.45, ease: 'back.out(1.6)' }, te - 0.08);
  [0, 0.09].forEach(d => { const r = div('', sc); r.style.cssText += `width:220px;height:220px;border-radius:50%;border:6px solid ${C.gold};box-shadow:0 0 30px ${C.gold}`; at(r, 540, 590, { autoAlpha: 0 }); tl.fromTo(r, { scale: 0.2, autoAlpha: 1 }, { scale: 6, autoAlpha: 0, duration: 0.9, ease: 'power2.out', immediateRender: false }, tc + d); });
  flash(tc, 0.5, 0.45, C.gold); shake(tc, 1.2, 0.6); punch(tc, 0.08, 0.7);
  sfx('boom', tc, 1); sfx('shimmer', tc + 0.12, 0.6);
  music(tc, 0.9, { hit: 1 });
  envTo(tc, { dim: 0.15 }, 0.3); tint(tc, 'gold', 0.2, 0.3);
  const sweep = div('', sc); sweep.style.cssText += 'width:150px;height:420px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);mix-blend-mode:overlay;transform:skewX(-18deg)'; at(sweep, 540, 600);
  gsap.set(sweep, { autoAlpha: 0 });
  tl.fromTo(sweep, { x: -620, autoAlpha: 1 }, { x: 620, duration: 0.8, ease: 'power2.inOut', immediateRender: false }, tc + 0.45);
  tl.set(sweep, { autoAlpha: 0 }, tc + 1.3);
  const sub = lbl(sc, 'Whoever gets new money first, wins', 'mint', 540, 800, 23); fadeIn(sub, te + 0.3, 0.4, { y: 16 });
  const cred = div('', sc, 'Named after economist Richard Cantillon (1680–1734)'); cred.style.cssText += 'font:500 22px Inter;color:#8A93A8;white-space:nowrap;font-style:italic'; at(cred, 540, 846);
  fadeIn(cred, te + 0.45, 0.4);

  // save prompt
  const ts = w('s09', 'save');
  const btn = div('', sc); btn.style.cssText += 'width:150px;height:150px;border-radius:50%;border:3px solid rgba(255,255,255,.85);background:rgba(10,14,24,.9);box-shadow:0 0 30px rgba(255,255,255,.2)';
  btn.innerHTML = `<div style="position:absolute;left:39px;top:39px">${icon('bookmark', 72, '#F2F5FF', 1.6)}</div><div class="bf" style="position:absolute;left:39px;top:39px;opacity:0">${icon('bookmark', 72, C.gold, 1.6, C.gold)}</div>`;
  at(btn, 540, 985);
  popIn(btn, ts - 0.2, { from: 0.3, sfx: 'pop' });
  const cur = cursor(sc); at(cur, 0, 0);
  const tap = ts + 0.35;
  tl.fromTo(cur, { left: 820, top: 1240, autoAlpha: 0 }, { left: 585, top: 1030, autoAlpha: 1, duration: 0.45, ease: 'power3.out' }, ts - 0.1);
  tl.to(cur, { scale: 0.85, duration: 0.08, yoyo: true, repeat: 1 }, tap - 0.04);
  ripple(sc, 540, 985, tap, C.gold);
  tl.to(btn.querySelector('.bf'), { opacity: 1, duration: 0.15 }, tap);
  tl.to(btn, { borderColor: C.gold, boxShadow: '0 0 44px rgba(255,209,92,.6)', duration: 0.2 }, tap);
  tl.fromTo(btn, { scale: 1.18 }, { scale: 1, duration: 0.35, ease: 'back.out(3)', immediateRender: false }, tap);
  sfx('click', tap, 0.8); sfx('ding', tap + 0.03, 0.7);
  const saved = div('chip', sc, `${icon('check', 24, C.gold, 3)} Saved`); saved.style.cssText += `color:${C.gold};font-size:24px;`; at(saved, 700, 920);
  popIn(saved, tap + 0.08, { from: 0.3, sfx: false });
  whip(t1 - 0.1);
})();

// =====================================================================
// S10  DIVERGE — assets vs. salary
// =====================================================================
(() => {
  const t0 = S('s10') - 0.08, t1 = S('s11') + 0.1, sc = scene('diverge', t0, t1);
  envTo(t0, { dim: 0, spot: 0.45, grid: 0.06 }, 0.3); tint(t0, 'mint', 0.13, 0.4);
  music(t0, 0.85);
  const title = lbl(sc, 'Who gets richer?', 'w', 540, 262, 30); fadeIn(title, t0 + 0.05, 0.4, { y: 16 });
  const svg = svgLayer(sc);
  for (let y = 400; y <= 1000; y += 120) svgEl('line', { x1: 140, x2: 940, y1: y, y2: y, stroke: 'rgba(255,255,255,.07)', 'stroke-width': 2 }, svg);
  svgEl('line', { x1: 140, x2: 940, y1: 1000, y2: 1000, stroke: 'rgba(255,255,255,.35)', 'stroke-width': 2 }, svg);
  for (let i = 0; i <= 6; i++) { const tx = svgEl('text', { x: 140 + i * 800 / 6, y: 1040, fill: '#8A93A8', 'font-family': 'JetBrains Mono', 'font-size': 22, 'text-anchor': 'middle' }, svg); tx.textContent = 2020 + i; }
  const dA = 'M140 880 C 380 862, 610 700, 940 405', dS = 'M140 880 C 400 876, 700 862, 940 842';
  const gap = svgEl('path', { d: `${dA} L940 842 C 700 862, 400 876, 140 880 Z`, fill: 'url(#gapGrad)', opacity: 0 }, svg);
  const defs = svgEl('defs', {}, svg); const lg = svgEl('linearGradient', { id: 'gapGrad', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  svgEl('stop', { offset: 0, 'stop-color': C.red, 'stop-opacity': 0.5 }, lg); svgEl('stop', { offset: 1, 'stop-color': C.red, 'stop-opacity': 0.08 }, lg);
  const pa = svgEl('path', { d: dA, fill: 'none', stroke: C.mint, 'stroke-width': 7, 'stroke-linecap': 'round', style: 'filter:drop-shadow(0 0 10px rgba(61,255,176,.9))' }, svg);
  const ps = svgEl('path', { d: dS, fill: 'none', stroke: '#F2F5FF', 'stroke-width': 7, 'stroke-linecap': 'round', style: 'filter:drop-shadow(0 0 8px rgba(255,255,255,.7))' }, svg);
  tl.fromTo(svg, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, t0);
  const tH = w('s10', 'homes') - 0.1, dAd = we('s10', 'inflation') - tH, tWh = w('s10', 'while'), dSd = we('s10', 'behind') - tWh;
  drawPath(pa, tH, dAd, 'power1.in'); drawPath(ps, tWh, dSd, 'power1.inOut');
  sfx('riser', tH, 0.45, { dur: dAd });
  const mkDot = (color) => { const d = div('', sc); d.style.cssText += `width:26px;height:26px;border-radius:50%;background:${color};box-shadow:0 0 22px ${color},0 0 50px ${color}`; return d; };
  const dotA = mkDot(C.mint), dotS = mkDot('#F2F5FF');
  const chipA = div('chip', sc, `${icon('house', 26, C.mint, 2)}${icon('trending-up', 26, C.mint, 2)} Homes & stocks`); chipA.style.cssText += `color:${C.mint};font-size:22px;`;
  const chipS = div('chip', sc, `${icon('briefcase', 26, '#F2F5FF', 2)} Salary`); chipS.style.cssText += 'color:#F2F5FF;font-size:22px;';
  [dotA, chipA].forEach(e => tl.fromTo(e, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25 }, tH));
  [dotS, chipS].forEach(e => tl.fromTo(e, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.25 }, tWh));
  pathHead(pa, tH, dAd, 'power1.in', (x, y) => { at(dotA, x, y); at(chipA, Math.min(800, Math.max(260, x - 40)), y - 62); });
  pathHead(ps, tWh, dSd, 'power1.inOut', (x, y) => { at(dotS, x, y); at(chipS, Math.min(840, Math.max(220, x - 20)), y + 60); });
  const rich = div('chip', sc, `${icon('arrow-up', 24, C.mint, 3)} Richer`); rich.style.cssText += `color:${C.mint};font-size:24px;background:rgba(61,255,176,.12)`; at(rich, 500, 410);
  popIn(rich, w('s10', 'richer'), { from: 0.3, sfx: 'cash', gain: 0.7 });
  const tF = w('s10', 'fall');
  tl.to(gap, { opacity: 1, duration: 0.6 }, tF);
  const behind = div('chip', sc, `${icon('arrow-down', 24, C.red, 3)} Falling behind`); behind.style.cssText += `color:${C.red};font-size:24px;background:rgba(255,69,96,.12)`; at(behind, 720, 960);
  popIn(behind, tF, { from: 0.3, sfx: 'down', gain: 0.6 });
  const arr = svgLayer(sc);
  svgEl('line', { x1: 975, x2: 975, y1: 425, y2: 822, stroke: C.red, 'stroke-width': 4, 'stroke-dasharray': '10 8' }, arr);
  svgEl('path', { d: 'M963 440 L975 422 L987 440 M963 807 L975 825 L987 807', fill: 'none', stroke: C.red, 'stroke-width': 4, 'stroke-linecap': 'round' }, arr);
  const gapL = div('big-title glow-r', sc, 'THE GAP'); gapL.style.fontSize = '64px'; at(gapL, 760, 640);
  const tBh = w('s10', 'behind');
  tl.fromTo(arr, { autoAlpha: 0, scaleY: 0, transformOrigin: '975px 624px' }, { autoAlpha: 1, scaleY: 1, duration: 0.4, ease: 'power3.out' }, tBh);
  slam(gapL, tBh + 0.05, { from: 1.8, shake: 0.6, sfx: 'hit' });
  tint(tF, 'red', 0.15, 0.6);
  camSet(t0, 420, 740, 1.1);
  focus(tH, 640, 660, 1.04, dAd + 0.3, 'power2.inOut');
  focus(tF, 560, 680, 0.98, 1.0);
})();

// =====================================================================
// S11  DESIGN — not effort: cash is built to lose ~2% a year
// =====================================================================
(() => {
  const t0 = S('s11') - 0.05, t1 = S('s12') + 0.1, sc = scene('design', t0, t1);
  envTo(t0, { dim: 0, spot: 1, grid: 0.08 }, 0.2); tint(t0, 'navy', 0.18, 0.3);
  camSet(t0, 540, 760, 1);
  glitch(S('s11') - 0.05, 0.25, 0.8);
  music(t0, 0.75);
  // A — work harder?
  const tBc = L('s11', 1).start;
  const you = figure(sc, 540, 1080, 290);
  const clk = svgLayer(sc); const CX = 540, CY = 545;
  svgEl('circle', { cx: CX, cy: CY, r: 120, fill: 'rgba(10,14,24,.9)', stroke: '#F2F5FF', 'stroke-width': 5, style: 'filter:drop-shadow(0 0 14px rgba(255,255,255,.4))' }, clk);
  for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; svgEl('line', { x1: CX + Math.cos(a) * 98, y1: CY + Math.sin(a) * 98, x2: CX + Math.cos(a) * 110, y2: CY + Math.sin(a) * 110, stroke: '#F2F5FF', 'stroke-width': 4 }, clk); }
  const hm = svgEl('line', { x1: CX, y1: CY, x2: CX, y2: CY - 88, stroke: C.gold, 'stroke-width': 6, 'stroke-linecap': 'round' }, clk);
  const hh = svgEl('line', { x1: CX, y1: CY, x2: CX, y2: CY - 58, stroke: '#F2F5FF', 'stroke-width': 8, 'stroke-linecap': 'round' }, clk);
  dyn(t => { const a = Math.max(0, t - t0) * 1300; hm.setAttribute('transform', `rotate(${a} ${CX} ${CY})`); hh.setAttribute('transform', `rotate(${a / 12} ${CX} ${CY})`); });
  const hrs = lbl(sc, '40+ hrs / week', 'w', 540, 378, 26);
  const days = div('row', sc); days.style.gap = '12px';
  const dEls = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map(d => { const e = div('chip', days, d); e.style.cssText += 'color:#8A93A8;font-size:20px;position:relative;'; return e; });
  at(days, 540, 735);
  const partA = [...you.all, clk, hrs, days];
  tl.fromTo(partA, { autoAlpha: 0, y: 40 }, { autoAlpha: 1, y: 0, duration: 0.35, stagger: 0.04 }, t0);
  dEls.forEach((e, i) => { const tk = t0 + 0.3 + i * 0.2; tl.to(e, { color: C.mint, borderColor: C.mint, duration: 0.12 }, tk); sfx('tick', tk, 0.5); });
  tl.to(partA, { autoAlpha: 0, y: 80, duration: 0.25, ease: 'power2.in' }, tBc - 0.2);
  whip(tBc);

  // B — a blueprint: the dollar is *designed*
  const bp = div('', sc); bp.style.cssText += 'width:860px;height:470px;';
  const bs = svgEl('svg', { width: 860, height: 470, viewBox: '0 0 860 470' }, bp); bs.style.overflow = 'visible';
  for (let x = 0; x <= 860; x += 43) svgEl('line', { x1: x, x2: x, y1: 0, y2: 470, stroke: 'rgba(124,196,255,.10)', 'stroke-width': 1.5 }, bs);
  for (let y = 0; y <= 470; y += 43) svgEl('line', { x1: 0, x2: 860, y1: y, y2: y, stroke: 'rgba(124,196,255,.10)', 'stroke-width': 1.5 }, bs);
  const B = { stroke: C.blue, fill: 'none', 'stroke-width': 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', style: 'filter:drop-shadow(0 0 6px rgba(124,196,255,.8))' };
  const strokes = [
    svgEl('rect', Object.assign({ x: 50, y: 95, width: 760, height: 322, rx: 18 }, B), bs),
    svgEl('rect', Object.assign({ x: 80, y: 122, width: 700, height: 268, rx: 10 }, B, { 'stroke-width': 2.5 }), bs),
    svgEl('circle', Object.assign({ cx: 430, cy: 256, r: 96 }, B), bs),
    svgEl('path', Object.assign({ d: 'M50 60 L810 60 M50 48 L50 72 M810 48 L810 72' }, B, { 'stroke-width': 2.5 }), bs),
    svgEl('path', Object.assign({ d: 'M840 95 L840 417 M828 95 L852 95 M828 417 L852 417' }, B, { 'stroke-width': 2.5 }), bs),
  ];
  const txt = (x, y, s, size, extra = {}) => { const e = svgEl('text', Object.assign({ x, y, fill: C.blue, 'font-family': 'JetBrains Mono', 'font-size': size, 'text-anchor': 'middle', 'font-weight': 700 }, extra), bs); e.textContent = s; return e; };
  const texts = [txt(430, 292, '$', 110, { 'font-family': 'Inter Display', 'font-weight': 900 }), txt(120, 175, '1', 46), txt(740, 370, '1', 46), txt(430, 44, '156 mm', 22), txt(870, 262, '66 mm', 22, { transform: 'rotate(90 870 262)' })];
  at(bp, 540, 590);
  const tCash = w('s11', 'cash');
  tl.fromTo(bp, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, tBc);
  strokes.forEach((s, i) => { s.style.strokeDasharray = 4000; drawPath(s, tCash - 0.15 + i * 0.12, 0.7, 'power2.inOut'); });
  tl.fromTo(texts, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3, stagger: 0.08 }, tCash + 0.3);
  sfx('swoosh', tCash - 0.1, 0.5);
  const specL = lbl(sc, 'Design spec · US dollar', '', 340, 340, 20); specL.style.color = C.blue; fadeIn(specL, tCash, 0.3);
  const purp = div('mono', sc); purp.style.cssText += 'font-size:40px;font-weight:800;white-space:nowrap'; at(purp, 540, 870);
  const tLose = w('s11', 'lose');
  const pt = 'PURPOSE: LOSE VALUE ▼';
  dyn(t => { const n = Math.floor(clamp01((t - tLose + 0.1) * 30 / pt.length) * pt.length), s = pt.slice(0, n); purp.innerHTML = s.length > 9 ? `<span style="color:#8A93A8">${s.slice(0, 9)}</span><span class="glow-r">${s.slice(9)}</span>` : `<span style="color:#8A93A8">${s}</span>`; });
  for (let k = 0; k < 8; k++) sfx('type', tLose - 0.1 + k * 0.08, 0.35);

  // C — the Fed's 2% target
  const tFed = w('s11', 'fed'), tTwo = w('s11', 'two');
  tl.to(bp, { top: 330, scale: 0.5, duration: 0.5, ease: 'power3.inOut' }, tFed - 0.3);
  tl.to([specL, purp], { autoAlpha: 0, duration: 0.25 }, tFed - 0.3);
  const tg = svgLayer(sc); const TX = 540, TY = 790;
  [170, 128, 86, 44].forEach((r, i) => svgEl('circle', { cx: TX, cy: TY, r, fill: i % 2 ? 'rgba(255,69,96,.12)' : 'rgba(10,14,24,.85)', stroke: i % 2 ? C.red : '#F2F5FF', 'stroke-width': 5, style: `filter:drop-shadow(0 0 10px ${i % 2 ? 'rgba(255,69,96,.7)' : 'rgba(255,255,255,.4)'})` }, tg));
  tg.style.transformOrigin = `${TX}px ${TY}px`;
  tl.fromTo(tg, { autoAlpha: 0, scale: 0, rotation: -90 }, { autoAlpha: 1, scale: 1, rotation: 0, duration: 0.5, ease: 'back.out(1.8)' }, tFed - 0.1);
  sfx('swoosh', tFed - 0.1, 0.5);
  const fedL = lbl(sc, 'Federal Reserve target', 'w', 540, 580, 24); fadeIn(fedL, tFed, 0.3, { y: 12 });
  const dart = div('', sc, `<svg width="260" height="40" viewBox="0 0 260 40" style="overflow:visible"><line x1="0" y1="20" x2="210" y2="20" stroke="#F2F5FF" stroke-width="6" stroke-linecap="round"/><path d="M0 20 L-26 8 L-26 32 Z" fill="#F2F5FF"/><path d="M200 20 L250 2 M200 20 L250 38 M215 20 L262 6 M215 20 L262 34" stroke="${C.gold}" stroke-width="5" stroke-linecap="round"/></svg>`);
  at(dart, TX + 150, TY - 30, { rotation: -22, transformOrigin: '0% 50%' });
  tl.fromTo(dart, { x: 700, y: -260, autoAlpha: 0 }, { x: 0, y: 0, autoAlpha: 1, duration: 0.24, ease: 'power2.in' }, tTwo - 0.24);
  sfx('whoosh', tTwo - 0.28, 0.6); sfx('thunk', tTwo, 0.9);
  shake(tTwo, 0.6, 0.35);
  const two = div('num glow-g', sc, '2%'); two.style.fontSize = '84px'; at(two, TX, TY);
  popIn(two, tTwo + 0.02, { from: 0.2, sfx: false });
  tl.fromTo(tg, { scale: 1.08 }, { scale: 1, duration: 0.4, ease: 'elastic.out(1,0.4)', immediateRender: false }, tTwo);
  const per = lbl(sc, 'Inflation · per year', 'gold', 540, 1000, 22); fadeIn(per, w('s11', 'inflation') - 0.05, 0.3);

  // D — every. single. year.
  const tE = w('s11', 'every'), tSi = w('s11', 'single'), tY = w('s11', 'year');
  tl.to([tg, fedL, dart, two, per], { autoAlpha: 0, scale: 0.8, duration: 0.2 }, tE - 0.22);
  tl.to(bp, { top: 600, scale: 0.95, duration: 0.25, ease: 'power3.out' }, tE - 0.22);
  const val = div('num glow-w', sc); val.style.fontSize = '110px'; at(val, 540, 905);
  const yr = div('chip', sc); yr.style.cssText += `color:${C.red};font-size:28px;`; at(yr, 540, 330);
  tl.fromTo([val, yr], { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.15 }, tE - 0.1);
  const steps = [[tE, '$0.98', 'Year 1', 0.84], [tSi, '$0.96', 'Year 2', 0.74], [tY, '$0.94', 'Year 3', 0.64]];
  dyn(t => { let v = '$1.00', y = 'Year 0'; for (const [ts, vv, yy] of steps) if (t >= ts) { v = vv; y = yy; } val.textContent = v; yr.textContent = y; });
  steps.forEach(([ts, , , s]) => {
    tl.to(bp, { scale: s, duration: 0.25, ease: 'back.out(2.5)' }, ts);
    punch(ts, 0.05, 0.4); flash(ts, 0.12, 0.2, C.red); sfx('hit', ts, 0.9);
    tl.fromTo(val, { scale: 1.25, color: C.red }, { scale: 1, color: '#F2F5FF', duration: 0.35, immediateRender: false }, ts);
  });
  tl.to(strokes, { stroke: C.red, duration: 0.8 }, tE);
  const ten = div('chip', sc, `10 years ${icon('arrow-down', 24, C.red, 3)} $0.82`); ten.style.cssText += `color:${C.red};font-size:30px;background:rgba(255,69,96,.12)`; at(ten, 540, 1010);
  popIn(ten, we('s11', 'year') + 0.05, { from: 0.4, sfx: 'pop', gain: 0.6 });
  tint(tE, 'red', 0.16, 0.5);
})();

// =====================================================================
// S12  CLOSE — not safe; it's melting; follow for part 2
// =====================================================================
(() => {
  const t0 = S('s12') - 0.05, t1 = DUR + 1, sc = scene('close', t0, t1);
  envTo(t0, { dim: 0, spot: 1, grid: 0.08 }, 0.2); tint(t0, 'navy', 0.18, 0.3);
  camSet(t0, 540, 760, 1);
  whip(S('s12'));
  music(t0, 0.8);
  // A — sitting still next to a "safe"
  const tM = L('s12', 1).start;
  const you = figure(sc, 320, 1080, 300);
  const sit = lbl(sc, 'Sitting still', 'w', 320, 715, 22);
  const vault = div('card col', sc); vault.style.cssText += 'width:270px;height:300px;align-items:center;justify-content:center;gap:16px;';
  vault.innerHTML = `${icon('vault', 150, '#F2F5FF', 1.3)}<div class="num glow-m" style="font-size:46px">$1,000</div>`;
  at(vault, 745, 925);
  vault.classList.add('reflect');
  const safe = div('chip', sc, `${icon('shield-check', 28, C.mint, 2)} Safe`); safe.style.cssText += `color:${C.mint};font-size:28px;position:absolute;`; at(safe, 745, 728);
  const sk = strike(safe);
  tl.fromTo([...you.all, vault], { autoAlpha: 0, y: 40 }, { autoAlpha: 1, y: 0, duration: 0.4, stagger: 0.06 }, t0);
  fadeIn(sit, w('s12', 'sitting') - 0.05, 0.3, { y: 14 });
  popIn(safe, w('s12', 'still'), { from: 0.4, sfx: 'pop', gain: 0.5 });
  const tNot = w('s12', 'not');
  tl.to(sk, { scaleX: 1, duration: 0.2 }, tNot);
  tl.to(safe, { color: '#8A93A8', duration: 0.2 }, tNot);
  const ns = div('stamp', sc, 'Not safe'); ns.style.cssText += `font-size:64px;color:${C.red};background:rgba(255,69,96,.08);`; at(ns, 745, 625);
  slam(ns, tNot + 0.05, { rot: -7, from: 2.2, shake: 0.9, sfx: 'stamp' });
  tl.to(vault, { borderColor: C.red, boxShadow: '0 0 34px rgba(255,69,96,.5)', duration: 0.2 }, tNot);
  envTo(tNot, { alarm: 1 }, 0.15); envTo(tM - 0.2, { alarm: 0 }, 0.2);
  sfx('alarm', tNot, 0.55);
  tl.to([...you.all, sit, vault, safe, ns], { autoAlpha: 0, scale: 0.9, duration: 0.2 }, tM - 0.18);

  // B — "It's melting."
  const tMelt = w('s12', 'melting') - 0.2;
  const mw = div('', sc); mw.style.cssText += 'width:820px;height:300px;filter:url(#goo);color:#F2F5FF;';
  at(mw, 540, 590);
  const N = 26, R = mulberry32(77), strips = [];
  for (let i = 0; i < N; i++) {
    const s = div('num', mw, '$1,000'); s.style.cssText += `position:absolute;left:0;top:0;width:820px;text-align:center;font-size:250px;color:inherit;clip-path:inset(0 ${(100 - (i + 1) * 100 / N).toFixed(2)}% 0 ${(i * 100 / N).toFixed(2)}%);transform-origin:50% 0%;`;
    strips.push(s);
  }
  tl.fromTo(mw, { autoAlpha: 0, scale: 1.3 }, { autoAlpha: 1, scale: 1, duration: 0.25, ease: 'expo.out' }, tM - 0.12);
  sfx('hit', tM - 0.1, 0.7);
  strips.forEach(s => { const d = 80 + R() * 420, dl = R() * 0.25; tl.to(s, { y: d * 0.6, scaleY: 1 + d / 220, duration: 1.15, ease: 'power1.in' }, tMelt + dl); });
  tl.to(mw, { color: C.red, duration: 0.7 }, tMelt);
  tl.to(mw, { autoAlpha: 0, duration: 0.3 }, L('s12', 2).start - 0.2);
  emitter({ t0: tMelt + 0.2, t1: L('s12', 2).start - 0.2, rate: 30, x: r => lerp(180, 900, r()), y: r => 690 + r() * 60, vy: [50, 200], g: 1500, life: 0.9, size: [4, 7], color: RGB.red, seed: 31 });
  sfx('melt', tMelt, 0.9);
  focus(tM - 0.1, 540, 640, 1.08, 1.4, 'power1.inOut');
  music(tMelt, 0.35);

  // C — end card: follow for part 2
  const tF = w('s12', 'follow'), tP = w('s12', 'part'), tPr = w('s12', 'protect');
  camSet(L('s12', 2).start - 0.2, 540, 760, 1);
  tint(tF - 0.2, 'mint', 0.2, 0.4);
  music(tF - 0.2, 0.9);
  const next = lbl(sc, 'Next episode', 'mint', 540, 392, 24);
  const p2 = div('big-title', sc); p2.style.cssText += 'font-size:220px;letter-spacing:-.02em;background:linear-gradient(180deg,#FFFFFF 10%,#3DFFB0 100%);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 30px rgba(61,255,176,.5));padding:0 10px';
  p2.textContent = 'PART 2'; at(p2, 540, 545);
  const how = div('', sc, 'How to protect your money'); how.style.cssText += 'font:800 46px Inter Display;white-space:nowrap;'; at(how, 540, 712);
  const sh = div('', sc, icon('shield-check', 96, C.mint, 1.5)); sh.style.filter = 'drop-shadow(0 0 16px rgba(61,255,176,.8))'; at(sh, 540, 830);
  const fb = div('pill', sc); fb.style.cssText += `height:112px;width:430px;justify-content:center;background:${C.gold};color:#120d02;font:900 46px Inter;letter-spacing:.06em;box-shadow:0 0 40px rgba(255,209,92,.55)`;
  fb.innerHTML = `<span class="f1" style="position:absolute">+ FOLLOW</span><span class="f2" style="position:absolute;opacity:0;color:#F2F5FF">✓ FOLLOWING</span>`;
  at(fb, 540, 1000);
  popIn(fb, tF - 0.12, { from: 0.4, sfx: 'pop' });
  const cur = cursor(sc); at(cur, 0, 0);
  const tap = tF + 0.42;
  tl.fromTo(cur, { left: 840, top: 1250, autoAlpha: 0 }, { left: 600, top: 1045, autoAlpha: 1, duration: 0.4, ease: 'power3.out' }, tF);
  tl.to(cur, { scale: 0.85, duration: 0.08, yoyo: true, repeat: 1 }, tap - 0.04);
  ripple(sc, 540, 1000, tap, C.gold);
  tl.to(fb, { backgroundColor: 'rgba(255,255,255,.1)', boxShadow: '0 0 0 3px rgba(255,255,255,.7) inset', duration: 0.2 }, tap);
  tl.to(fb.querySelector('.f1'), { opacity: 0, duration: 0.12 }, tap);
  tl.to(fb.querySelector('.f2'), { opacity: 1, duration: 0.15 }, tap + 0.05);
  tl.fromTo(fb, { scale: 1.12 }, { scale: 1, duration: 0.35, ease: 'back.out(3)', immediateRender: false }, tap);
  tl.to(cur, { autoAlpha: 0, left: 760, top: 1200, duration: 0.4, ease: 'power2.in' }, tap + 0.35);
  sfx('click', tap, 0.8); sfx('ding', tap + 0.04, 0.6);
  fadeIn(next, tP - 0.25, 0.3, { y: 14 });
  slam(p2, tP, { from: 1.8, shake: 0.8, sfx: 'boom', gain: 0.8 });
  flash(tP, 0.3, 0.35, C.mint);
  fadeIn(how, w('s12', 'how') - 0.05, 0.4, { y: 24 });
  popIn(sh, tPr, { from: 0.3, sfx: 'shimmer', gain: 0.6 });
  emitter({ t0: tP, t1: DUR, rate: 14, x: r => lerp(80, 1000, r()), y: r => 1150 + r() * 200, vy: [-260, -120], g: -40, life: 2.4, size: [2, 4], color: RGB.mint, seed: 41, shape: 'dot' });
  // after the voice ends: comment prompt where captions live
  const cm = div('row', hud); cm.style.cssText += `position:absolute;gap:18px;font:800 54px Inter Display;color:${C.gold};text-shadow:0 5px 0 rgba(0,0,0,.55),0 0 28px rgba(255,209,92,.5);white-space:nowrap`;
  cm.innerHTML = `${icon('message-circle', 58, C.gold, 2.2)}<span>Comment “PART 2”</span>`;
  at(cm, 540, 1320);
  const tCm = L('s12', 2).end + 0.65;
  gsap.set(cm, { autoAlpha: 0 });
  popIn(cm, tCm, { from: 0.5, sfx: 'pop', gain: 0.6 });
  tl.to(cm, { y: -10, duration: 0.4, yoyo: true, repeat: 3, ease: 'sine.inOut' }, tCm + 0.45);
  music(DUR - 1.2, 0.9); music(DUR, 0);
  tl.set({}, {}, DUR); // timeline spans the whole video
})();

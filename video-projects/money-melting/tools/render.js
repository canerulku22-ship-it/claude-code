// Frame-accurate renderer: drives web/index.html in headless Chromium via window.seek(t).
//   node tools/render.js cues                      -> audio/cues.json (sfx + music cues)
//   node tools/render.js stills <t> [t...]         -> out/stills/t_<t>.jpg
//   node tools/render.js frames <from> <to> <dir>  -> <dir>/f_00000.jpg ... (frame indices, 30 fps)
//   node tools/render.js all [workers]             -> out/frames/*.jpg using N parallel browsers
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs'), { spawn } = require('child_process');
const ROOT = path.resolve(__dirname, '..'), FPS = 30;
const [mode, ...args] = process.argv.slice(2);

async function open() {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files', '--font-render-hinting=none', '--disable-lcd-text'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('[pageerror]', e.message); process.exitCode = 1; });
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  await page.goto('file://' + path.join(ROOT, 'web', 'index.html'));
  await page.evaluate(async () => { await document.fonts.ready; window.seek(0); });
  await page.waitForTimeout(400);
  return { browser, page };
}
const shot = (page, file) => page.screenshot({ path: file, type: 'jpeg', quality: 93 });

(async () => {
  if (mode === 'cues') {
    const { browser, page } = await open();
    const cues = await page.evaluate(() => window.getCues());
    fs.writeFileSync(path.join(ROOT, 'audio', 'cues.json'), JSON.stringify(cues, null, 1));
    console.log(`cues: ${cues.sfx.length} sfx, ${cues.music.length} music, duration ${cues.duration}`);
    await browser.close();
  } else if (mode === 'stills') {
    const dir = path.join(ROOT, 'out', 'stills'); fs.mkdirSync(dir, { recursive: true });
    const { browser, page } = await open();
    for (const a of args) {
      const t = parseFloat(a);
      await page.evaluate(t => window.seek(t), t);
      await shot(page, path.join(dir, `t_${t.toFixed(2).padStart(6, '0')}.jpg`));
    }
    await browser.close();
  } else if (mode === 'frames') {
    const [from, to, dir] = [parseInt(args[0]), parseInt(args[1]), args[2]];
    fs.mkdirSync(dir, { recursive: true });
    const { browser, page } = await open();
    const t0 = Date.now();
    for (let f = from; f < to; f++) {
      await page.evaluate(t => window.seek(t), f / FPS);
      await shot(page, path.join(dir, `f_${String(f).padStart(5, '0')}.jpg`));
      if ((f - from) % 150 === 0) console.log(`[${from}-${to}] frame ${f} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
    await browser.close();
  } else if (mode === 'all') {
    const workers = parseInt(args[0] || '4');
    const dur = JSON.parse(fs.readFileSync(path.join(ROOT, 'audio', 'timing.json'))).duration;
    const total = Math.ceil(dur * FPS), per = Math.ceil(total / workers), dir = path.join(ROOT, 'out', 'frames');
    fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const t0 = Date.now();
    await Promise.all([...Array(workers)].map((_, i) => new Promise((res, rej) => {
      const p = spawn(process.execPath, [__filename, 'frames', i * per, Math.min(total, (i + 1) * per), dir], { stdio: 'inherit' });
      p.on('exit', c => c === 0 ? res() : rej(new Error('worker ' + i + ' failed')));
    })));
    console.log(`rendered ${total} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  } else {
    console.log('usage: node tools/render.js cues | stills <t...> | frames <from> <to> <dir> | all [workers]');
  }
})().catch(e => { console.error(e); process.exit(1); });

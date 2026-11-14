// Frame-accurate renderer for the WebGL page: serves the project over HTTP (ES modules), drives window.seek(t).
//   node tools/render.js cues | stills <t...> | frames <from> <to> <dir> | all [workers]
const { chromium } = require('playwright');
const http = require('http'), path = require('path'), fs = require('fs'), { spawn } = require('child_process');
const ROOT = path.resolve(__dirname, '..'), FPS = 30;
const [mode, ...args] = process.argv.slice(2);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm' };

function serve() {
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(rsp);
    }).listen(0, '127.0.0.1', () => res(srv));
  });
}
async function open(port) {
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('[pageerror]', e.message); process.exitCode = 1; });
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/web/index.html`);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 120000 });
  await page.evaluate(() => window.seek(0));
  return { browser, page };
}
const shot = (page, file) => page.screenshot({ path: file, type: 'jpeg', quality: 94 });

(async () => {
  const srv = await serve(), port = srv.address().port;
  try {
    if (mode === 'cues') {
      const { browser, page } = await open(port);
      const cues = await page.evaluate(() => window.getCues());
      fs.writeFileSync(path.join(ROOT, 'audio', 'cues.json'), JSON.stringify(cues, null, 1));
      console.log(`cues: ${cues.sfx.length} sfx, ${cues.music.length} music, duration ${cues.duration}`);
      await browser.close();
    } else if (mode === 'stills') {
      const dir = path.join(ROOT, 'out', 'stills'); fs.mkdirSync(dir, { recursive: true });
      const { browser, page } = await open(port);
      for (const a of args) { const t = parseFloat(a); const t1 = Date.now(); await page.evaluate(t => window.seek(t), t); await shot(page, path.join(dir, `t_${t.toFixed(2).padStart(6, '0')}.jpg`)); console.log(`t=${t} ${Date.now() - t1}ms`); }
      await browser.close();
    } else if (mode === 'frames') {
      const [from, to, dir] = [parseInt(args[0]), parseInt(args[1]), args[2]];
      fs.mkdirSync(dir, { recursive: true });
      const { browser, page } = await open(port);
      const t0 = Date.now();
      for (let f = from; f < to; f++) {
        await page.evaluate(t => window.seek(t), f / FPS);
        await shot(page, path.join(dir, `f_${String(f).padStart(5, '0')}.jpg`));
        if ((f - from) % 60 === 0) console.log(`[${from}-${to}] frame ${f} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
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
        p.on('exit', c => (c === 0 ? res() : rej(new Error('worker ' + i + ' failed'))));
      })));
      console.log(`rendered ${total} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    } else console.log('usage: node tools/render.js cues | stills <t...> | frames <from> <to> <dir> | all [workers]');
  } finally { srv.close(); }
})().catch(e => { console.error(e); process.exit(1); });

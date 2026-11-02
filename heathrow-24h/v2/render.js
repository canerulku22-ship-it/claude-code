// usage: node render.js still <outdir> t1 t2 ...
//        node render.js chunk <f0> <f1> <out.mp4>   (frames [f0,f1) at 60 fps)
//        node render.js events <out.json>
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const { spawn } = require('child_process');
const ROOT = __dirname, FPS = 60;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };

function serve() {
  return new Promise(res => {
    const s = http.createServer((q, r) => {
      const p = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]));
      fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); r.end(d); });
    });
    s.listen(0, '127.0.0.1', () => res(s));
  });
}

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const srv = await serve();
  const url = `http://127.0.0.1:${srv.address().port}/index.html`;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-vsync', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(url);
  await page.waitForFunction('window.READY === true', null, { timeout: 180000 });
  const frame = async t => { await page.evaluate(t => window.renderFrame(t), t); };
  page.setDefaultTimeout(300000);
  await frame(0.1); await page.screenshot({ type: 'jpeg', quality: 50, timeout: 300000 });

  if (mode === 'events') {
    fs.writeFileSync(args[0], JSON.stringify(await page.evaluate(() => window.getAudioEvents())));
  } else if (mode === 'still') {
    const out = args[0]; fs.mkdirSync(out, { recursive: true });
    for (const ts of args.slice(1)) {
      const t = parseFloat(ts); const t0 = Date.now();
      await frame(t);
      await page.screenshot({ path: path.join(out, `f_${ts}.png`) });
      console.log(ts, 'rendered in', ((Date.now() - t0) / 1000).toFixed(2), 's');
    }
  } else if (mode === 'chunk') {
    const f0 = parseInt(args[0]), f1 = parseInt(args[1]), out = args[2];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let f = f0; f < f1; f++) {
      await frame(f / FPS);
      const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - f0) % 60 === 0) console.log(`frame ${f} (${f - f0}/${f1 - f0}) ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('CHUNKDONE', out, ((Date.now() - t0) / 1000).toFixed(0), 's');
  }
  await browser.close(); srv.close();
})().catch(e => { console.error(e); process.exit(1); });

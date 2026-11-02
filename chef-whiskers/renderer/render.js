// Renders Chef Whiskers scenes frame by frame in headless Chromium (software WebGL).
//
// usage: node render.js scenes                                   print the scene names as JSON
//        node render.js still  <scene> <t> <duration> <out.png>   one frame
//        node render.js stills <scene> <duration> <outdir> t1 t2 ... frames for checking
//        node render.js clip   <scene> <duration> <fps> <f0> <f1> <out.mp4>   frames [f0, f1)
//        node render.js events <scene> <duration> <out.json>     sound cues for audio.py
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const { spawn } = require('child_process');

const ROOT = __dirname;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };

function serve() {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      const file = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
      if (!file.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }
      fs.readFile(file, (err, data) => {
        if (err) { res.writeHead(404); res.end(); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  if (!mode) throw new Error('usage: node render.js <scenes|still|stills|clip|events> ...');
  const server = await serve();
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
           '--disable-gpu-vsync', '--font-render-hinting=none'],
  });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.setDefaultTimeout(300000);
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction('window.READY === true', null, { timeout: 180000 });

  const scenes = await page.evaluate(() => window.SCENES);
  const checkScene = name => {
    if (!scenes.includes(name)) throw new Error(`unknown scene "${name}". Available: ${scenes.join(', ')}`);
  };
  const frame = (scene, t, duration) => page.evaluate(([s, t, d]) => window.renderFrame(s, t, d), [scene, t, duration]);

  if (mode === 'scenes') {
    process.stdout.write(JSON.stringify(scenes) + '\n');
  } else if (mode === 'still') {
    const [scene, t, duration, out] = args;
    checkScene(scene);
    await frame(scene, parseFloat(t), parseFloat(duration));
    await page.screenshot({ path: out });
  } else if (mode === 'stills') {
    const [scene, duration, outdir, ...times] = args;
    checkScene(scene);
    fs.mkdirSync(outdir, { recursive: true });
    for (const ts of times) {
      const t0 = Date.now();
      await frame(scene, parseFloat(ts), parseFloat(duration));
      await page.screenshot({ path: path.join(outdir, `${scene}_${ts}.png`) });
      console.log(scene, ts, 'rendered in', ((Date.now() - t0) / 1000).toFixed(2), 's');
    }
  } else if (mode === 'clip') {
    const [scene, duration, fpsArg, f0Arg, f1Arg, out] = args;
    checkScene(scene);
    const fps = parseInt(fpsArg), f0 = parseInt(f0Arg), f1 = parseInt(f1Arg);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(fps), out],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let f = f0; f < f1; f++) {
      await frame(scene, f / fps, parseFloat(duration));
      const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - f0) % 30 === 0) console.error(`  ${scene} frame ${f} (${f - f0 + 1}/${f1 - f0}) ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end();
    const code = await new Promise(r => ff.on('close', r));
    if (code !== 0) throw new Error(`ffmpeg exited with ${code}`);
  } else if (mode === 'events') {
    const [scene, duration, out] = args;
    checkScene(scene);
    fs.writeFileSync(out, JSON.stringify(await page.evaluate(([s, d]) => window.getAudioEvents(s, d), [scene, parseFloat(duration)])));
  } else {
    throw new Error(`unknown mode "${mode}"`);
  }
  await browser.close();
  server.close();
})().catch(e => { console.error(e.message || e); process.exit(1); });

// Renders film.html frame by frame with headless Chromium and encodes with ffmpeg.
// The page is served over a local HTTP server (ES modules and three.js don't load
// from file://), and WebGL runs on SwiftShader, Chromium's CPU renderer.
//
//   node render.mjs stills out/stills 1.2 7.5 20     -> PNG stills at the given times
//   node render.mjs video out/video.mp4 [workers]    -> silent H.264 video, all frames
//
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, rmSync, readFile } from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.png': 'image/png', '.wav': 'audio/wav' };
const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = path.join(here, path.normalize(rel));
  if (!file.startsWith(here + path.sep)) { res.writeHead(403); res.end(); return; }
  readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); res.end(data);
  });
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const url = `http://127.0.0.1:${server.address().port}/film.html#render`;

let SIZE = { width: 1920, height: 1080 };   // replaced by the film's FRAME_W x FRAME_H once the page has loaded
async function openPage(browser) {
  const page = await browser.newPage({ viewport: SIZE, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => window.ready, null, { timeout: 120000 });
  await page.evaluate(() => window.ready); // photos decoded and 3D stage built before the first frame
  const [width, height] = await page.evaluate(() => [window.FRAME_W || 1920, window.FRAME_H || 1080]);
  if (width !== SIZE.width || height !== SIZE.height) { SIZE = { width, height }; await page.setViewportSize(SIZE); }
  return page;
}

async function grab(page, t, type = 'png') {
  await page.evaluate(t => window.drawFrame(t), t);
  const clip = { x: 0, y: 0, ...SIZE };
  // JPEG q95 capture is ~15x faster than PNG and visually lossless before the final x264 pass.
  return page.screenshot(type === 'png' ? { type, clip } : { type, quality: 95, clip });
}

const run = (cmd, args, opts = {}) => new Promise((res, rej) => {
  const p = spawn(cmd, args, { stdio: ['pipe', 'inherit', 'inherit'], ...opts });
  p.on('exit', c => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`))));
  p.on('error', rej);
});

async function renderSegment(browser, f0, f1, out) {
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-pix_fmt', 'yuv420p', out],
  { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('exit', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  for (let f = f0; f < f1; f++) {
    const buf = await grab(page, f / FPS, 'jpeg');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 0) console.log(`  [${path.basename(out)}] frame ${f - f0}/${f1 - f0}`);
  }
  ff.stdin.end();
  await done;
  await page.close();
}

const [mode, out, ...rest] = process.argv.slice(2);
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
if (mode === 'stills') {
  mkdirSync(out, { recursive: true });
  const page = await openPage(browser);
  for (const t of rest.map(Number)) {
    writeFileSync(path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`), await grab(page, t));
  }
} else if (mode === 'video') {
  const page = await openPage(browser);
  const duration = await page.evaluate(() => window.DURATION);
  await page.close();
  const total = Math.round(duration * FPS);
  const workers = Number(rest[0] || 4);
  const tmp = path.join(path.dirname(out), 'segments');
  rmSync(tmp, { recursive: true, force: true }); mkdirSync(tmp, { recursive: true });
  const per = Math.ceil(total / workers);
  const segs = [];
  await Promise.all(Array.from({ length: workers }, (_, i) => {
    const f0 = i * per, f1 = Math.min(total, f0 + per);
    const seg = path.join(tmp, `seg${i}.mp4`); segs.push(seg);
    return renderSegment(browser, f0, f1, seg);
  }));
  writeFileSync(path.join(tmp, 'list.txt'), segs.map(s => `file '${path.resolve(s)}'`).join('\n'));
  await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'), '-c', 'copy', out], { stdio: 'inherit' });
  console.log(`wrote ${out} (${total} frames)`);
}
await browser.close();
server.close();

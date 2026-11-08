#!/usr/bin/env node
// Renders scene.html frame by frame in headless Chromium and pipes the frames to ffmpeg.
//   node render.js                      -> out/level-up.mp4 (video + build/mix_master.wav)
//   node render.js --stills 1.2,24,47   -> build/still_<t>.png for quick checks
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const HERE = __dirname;
const FPS = 30;
const timeline = JSON.parse(fs.readFileSync(path.join(HERE, 'build/timeline.json'), 'utf8'));

async function open() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => { console.error('page error:', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.join(HERE, 'scene.html'));
  await page.evaluate(tl => window.setTimeline(tl), timeline);
  return { browser, page };
}

async function stills(times) {
  const { browser, page } = await open();
  for (const t of times) {
    const b64 = await page.evaluate(t => window.still(t), t);
    const f = path.join(HERE, 'build', `still_${t.toFixed(2)}.png`);
    fs.writeFileSync(f, Buffer.from(b64, 'base64'));
    console.log(f);
  }
  await browser.close();
}

async function video() {
  const out = path.join(HERE, 'out');
  fs.mkdirSync(out, { recursive: true });
  const audio = path.join(HERE, 'build/mix_master.wav');
  const dst = path.join(out, 'level-up.mp4');
  const n = Math.ceil(timeline.duration * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', audio,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-maxrate', '9M', '-bufsize', '18M', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', dst], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const { browser, page } = await open();
  const t0 = Date.now();
  for (let f = 0; f < n; f++) {
    const b64 = await page.evaluate(t => window.frame(t), f / FPS);
    if (!ff.stdin.write(Buffer.from(b64, 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 150 === 0) console.log(`frame ${f}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await done;
  await browser.close();
  console.log('wrote', dst);
}

const i = process.argv.indexOf('--stills');
(i > 0 ? stills(process.argv[i + 1].split(',').map(Number)) : video()).catch(e => { console.error(e); process.exit(1); });

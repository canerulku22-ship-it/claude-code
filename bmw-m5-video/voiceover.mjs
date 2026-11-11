// Synthesises the voiceover, one WAV per line, with Kokoro-82M (Apache-2.0),
// run locally through kokoro-js. Writes out/vo/<id>.wav and out/vo/durations.json.
//
//   node voiceover.mjs [voice]        default voice: bf_emma (British English)
import { KokoroTTS } from 'kokoro-js';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
// timeline.js sets window.TIMELINE; strip the assignment to read it as JSON.
const src = readFileSync(path.join(here, 'timeline.js'), 'utf8');
const TL = JSON.parse(src.slice(src.indexOf('{'), src.lastIndexOf('}') + 1));
const voice = process.argv[2] || TL.voice;
const outDir = path.join(here, 'out', 'vo_ref'); // Kokoro lines: Chatterbox's reference voice, or a fallback narration
mkdirSync(outDir, { recursive: true });

const tts = await KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX', { dtype: 'fp32', device: 'cpu' });
const durations = {};
for (const line of TL.vo) {
  const audio = await tts.generate(line.say || line.text, { voice, speed: line.speed || TL.speed || 1 });
  const file = path.join(outDir, `${line.id}.wav`);
  audio.save(file);
  // speech onset/offset inside the file, from short-term energy (10 ms windows)
  const x = audio.audio, sr = audio.sampling_rate, win = Math.round(sr / 100);
  let on = -1, off = 0;
  for (let i = 0; i + win < x.length; i += win) {
    let e = 0;
    for (let j = 0; j < win; j++) e += x[i + j] * x[i + j];
    if (Math.sqrt(e / win) > 0.01) { if (on < 0) on = i; off = i + win; }
  }
  durations[line.id] = { dur: x.length / sr, on: Math.max(0, on) / sr, off: off / sr };
  console.log(`${line.id}  ${durations[line.id].dur.toFixed(2)}s  speech ${(on / sr).toFixed(2)}-${(off / sr).toFixed(2)}  ${line.text}`);
}
writeFileSync(path.join(outDir, 'durations.json'), JSON.stringify(durations, null, 2));
// film.html loads this with a <script> tag so captions follow the real speech timing.
writeFileSync(path.join(outDir, 'timing.js'), `window.VO_TIMING = ${JSON.stringify(durations)};\n`);

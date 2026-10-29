// Masters every audio file of a folder with one preset, one after the other.
//
//   node mastering-batch.mjs <input_dir> [--out out] [--preset builtin:balanced | --settings settings.json] [--format wav-pcm16|wav-pcm24|wav-f32]
//
// Files are sent one at a time (the API keeps one active job and three waiting per account). A file whose
// <name>-master.wav is already in the output folder is skipped, so the script can be run again after an
// interruption. On a 429 it waits the Retry-After the server gives (5 minutes at most), then retries the
// same file once with the same Idempotency-Key. On a 403 (tier or scope) or a long 429 it stops: the next
// files would fail the same way. Needs JAM_JAM_API_KEY with mastering:read and mastering:write.
import { existsSync } from 'node:fs';
import { readdir, stat } from 'node:fs/promises';
import { extname, join, parse } from 'node:path';
import { parseArgs } from 'node:util';
import { ApiError, idempotencyKey } from './lib.mjs';
import { describeReport, downloadMaster, explain, loadSettings, needKey, runMastering, startRender, waitForRender } from './mastering-lib.mjs';

const AUDIO_EXTENSIONS = new Set(['.wav', '.mp3', '.flac', '.ogg', '.oga', '.opus', '.aac', '.m4a']);
const MAX_BYTES = 200 * 1024 * 1024;
const MAX_WAIT_S = 300; // a longer Retry-After means a spent quota (a day, a week), not a busy moment
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function masterOne(path, out, options) {
  const key = idempotencyKey();
  let job;
  for (const attempt of [1, 2]) {
    try {
      job = await startRender(path, { ...options, key });
      break;
    } catch (err) {
      if (err instanceof ApiError && err.status === 429 && attempt === 1 && err.retryAfter && err.retryAfter <= MAX_WAIT_S) {
        console.error(`  429, waiting ${err.retryAfter} s`);
        await sleep(err.retryAfter * 1000);
        continue;
      }
      throw err;
    }
  }
  job = await waitForRender(job.id);
  if (job.status !== 'done') return { ok: false, text: `failed (${job.status} ${job.error?.code ?? ''})` };
  const saved = await downloadMaster(job.id, out);
  return { ok: true, text: `${saved} (${describeReport(job)})` };
}

await runMastering(async () => {
  const { positionals, values } = parseArgs({
    allowPositionals: true,
    options: { out: { type: 'string', default: 'out' }, preset: { type: 'string' }, settings: { type: 'string' }, format: { type: 'string', default: 'wav-pcm16' } },
  });
  const [dir] = positionals;
  if (!dir) throw new Error('usage: node mastering-batch.mjs <input_dir> [--out out] [--preset id | --settings file] [--format wav-f32]');
  if (values.preset && values.settings) throw new Error('give --preset or --settings, not both');
  needKey();

  const settings = values.settings ? await loadSettings(values.settings) : undefined;
  const options = { settings, preset: settings ? undefined : (values.preset ?? 'builtin:balanced'), format: values.format };
  const files = (await readdir(dir)).filter((f) => AUDIO_EXTENSIONS.has(extname(f).toLowerCase())).sort();
  if (!files.length) throw new Error(`no audio file in ${dir}`);

  let done = 0, skipped = 0, failed = 0;
  for (const file of files) {
    const path = join(dir, file);
    if (existsSync(join(values.out, `${parse(file).name}-master.wav`))) {
      console.log(`skip ${file} (already mastered)`);
      skipped++;
    } else if ((await stat(path)).size > MAX_BYTES) {
      console.log(`skip ${file} (over 200 MB)`);
      failed++;
    } else {
      console.log(`master ${file}`);
      try {
        const result = await masterOne(path, values.out, options);
        console.log('  ', result.text);
        if (result.ok) done++; else failed++;
      } catch (err) {
        if (!(err instanceof ApiError)) throw err;
        console.error(explain(err));
        if ([401, 403].includes(err.status) || (err.status === 429 && (err.retryAfter ?? 0) > MAX_WAIT_S)) {
          throw new Error('stopping: the next files would be refused the same way (rerun later, finished files are skipped).');
        }
        failed++;
      }
    }
  }
  console.log(`done ${done}, skipped ${skipped}, failed ${failed}`);
  if (failed) process.exitCode = 1;
});

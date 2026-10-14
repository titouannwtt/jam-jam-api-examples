// Converts text, a file or a web page, waits for the job, saves the result and prints the songbook.
//
//   node convert.mjs text [file.cho]            ChordPro text (default: the sample song)
//   node convert.mjs file <path> [--input id]   file upload (multipart/form-data)
//   node convert.mjs url <https://...>          a web page you have the right to convert
//
// Options: --output <id> (default pdf-chords), --input <id> (default chordpro for text).
// Valid ids come from GET /formats (served: true). Run list-formats.mjs.
import { readFile } from 'node:fs/promises';
import { basename } from 'node:path';
import { parseArgs } from 'node:util';
import { createJob, downloadResult, json, run, waitForJob } from './lib.mjs';

const SAMPLE = new URL('../samples/amazing-grace.cho', import.meta.url);

await run(async () => {
  const { positionals, values } = parseArgs({
    allowPositionals: true,
    options: { output: { type: 'string', default: 'pdf-chords' }, input: { type: 'string' } },
  });
  const [mode, source] = positionals;
  const { output, input } = values;

  let body;
  if (mode === 'text') {
    body = { text: await readFile(source ?? SAMPLE, 'utf8'), inputFormat: input ?? 'chordpro', output };
  } else if (mode === 'url' && source) {
    body = { url: source, output, ...(input && { inputFormat: input }) };
  } else if (mode === 'file' && source) {
    body = new FormData();
    body.append('file', new Blob([await readFile(source)]), basename(source));
    body.append('output', output);
    if (input) body.append('inputFormat', input);
  } else {
    throw new Error('usage: node convert.mjs text [file] | file <path> | url <https://...>  [--output id] [--input id]');
  }

  let job = await createJob(body);
  console.log('job:', job.id, `(${job.inputFormat} -> ${job.outputFormat}), expires ${job.expiresAt}`);
  job = await waitForJob(job.id);

  if (job.phase !== 'done') {
    console.error('not done:', job.phase, job.problem ? `${job.problem.code}: ${job.problem.detail ?? job.problem.title}` : '');
    process.exitCode = 1;
    return;
  }
  console.log('artifacts:', job.artifacts.map((a) => `${a.filename} (${a.mediaType}, ${a.bytes} bytes)`).join(', '));
  console.log('saved:', await downloadResult(job.id));

  // The canonical songbook JSON is available after any successful job, whatever the output.
  const songbook = await json(`/jobs/${job.id}/result/songbook`);
  const song = songbook.songs[0];
  console.log(`songbook: "${song.title}", ${song.sections?.length ?? 0} sections`);
});

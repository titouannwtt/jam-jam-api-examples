// Masters one audio file on the Jam Jam server and saves the result in ./out.
//
//   node mastering.mjs capabilities                       limits, ranges, built-in presets (no key needed)
//   node mastering.mjs presets                            your presets and the built-in ids
//   node mastering.mjs create-preset "My preset" [settings.json]
//   node mastering.mjs master <audio> [--preset builtin:warm | --settings settings.json] [--format wav-f32]
//   node mastering.mjs delete job|preset <id>
//
// Input: WAV, MP3, FLAC, Ogg, AAC, M4A... 200 MB and 10 minutes at most. Output: a 48 kHz WAV.
// `master` without --preset or --settings uses builtin:balanced. Needs JAM_JAM_API_KEY except for capabilities.
// Whether your tier may render is shown by `capabilities` (renderAllowed) and the 403 explained below.
import { parseArgs } from 'node:util';
import { json, request } from './lib.mjs';
import { createPreset, describeReport, downloadMaster, loadSettings, needKey, runMastering, startRender, waitForRender } from './mastering-lib.mjs';

const SAMPLE_SETTINGS = new URL('../samples/mastering-settings.json', import.meta.url);

await runMastering(async () => {
  const { positionals, values } = parseArgs({
    allowPositionals: true,
    options: { preset: { type: 'string' }, settings: { type: 'string' }, format: { type: 'string', default: 'wav-pcm16' } },
  });
  const [command, a, b] = positionals;

  if (command === 'capabilities') {
    const caps = await json('/mastering/capabilities');
    console.log(`engine ${caps.engineVersion}, ${caps.sampleRate} Hz, ${caps.maxUploadBytes / 2 ** 20} MB, ${caps.maxDurationSeconds} s, formats ${caps.formats.join(', ')}`);
    console.log('built-in presets:', caps.builtinPresets.map((p) => p.id).join(', '));
    console.log('targets:', caps.targets.map((t) => `${t.id} (${t.lufs} LUFS)`).join(', '));
    for (const m of caps.modules) console.log(`  ${m.id}: ${m.min}..${m.max} step ${m.step} (${m.unit})`);
    console.log('renderAllowed:', caps.renderAllowed, '| quota:', JSON.stringify(caps.quota));
    return;
  }

  needKey();
  if (command === 'presets') {
    const listing = await json('/mastering/presets');
    console.log('built-in:', listing.builtin.join(', '));
    for (const p of listing.presets) console.log(`${p.id}  ${p.name}`);
  } else if (command === 'create-preset' && a) {
    const preset = await createPreset(a, await loadSettings(b ?? SAMPLE_SETTINGS));
    console.log('preset id:', preset.id);
  } else if (command === 'delete' && ['job', 'preset'].includes(a) && b) {
    await request(`/mastering/${a === 'job' ? 'jobs' : 'presets'}/${b}`, { method: 'DELETE' });
    console.log('deleted', a, b);
  } else if (command === 'master' && a) {
    if (values.preset && values.settings) throw new Error('give --preset or --settings, not both');
    const settings = values.settings ? await loadSettings(values.settings) : undefined;
    const preset = settings ? undefined : (values.preset ?? 'builtin:balanced');
    let job = await startRender(a, { preset, settings, format: values.format });
    console.log('job:', job.id, 'expires', job.expiresAt);
    job = await waitForRender(job.id);
    if (job.status !== 'done') throw new Error(`not done: ${job.status} ${job.error?.code ?? ''} ${job.error?.detail ?? ''}`.trim());
    console.log(describeReport(job));
    console.log('saved:', await downloadMaster(job.id));
  } else {
    throw new Error('usage: node mastering.mjs capabilities | presets | create-preset <name> [settings.json] | master <audio> [--preset id | --settings file] [--format wav-f32] | delete job|preset <id>');
  }
});

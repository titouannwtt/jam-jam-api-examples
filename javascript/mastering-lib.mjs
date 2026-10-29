// Helpers for the Mastering examples. Builds on lib.mjs (same key, same error type). Node 20+.
import { openAsBlob } from 'node:fs';
import { mkdir, readFile } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { basename, join } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { ApiError, idempotencyKey, request } from './lib.mjs';

const DEVELOPERS = 'https://jam-jam.org/app/developers';
export const FINAL_STATUSES = ['done', 'failed', 'cancelled', 'expired'];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// A readable message for the errors a Mastering call can answer. `code` is the stable value to test.
export function explain(err) {
  const code = err.problem?.code ?? '';
  let hint = '';
  if (err.status === 401) hint = 'The key is missing or invalid. Check JAM_JAM_API_KEY.';
  else if (err.status === 403 && code === 'insufficient-scope') hint = 'This key lacks a scope: mastering:read to follow and download, mastering:write to create, render and delete.';
  else if (err.status === 403) hint = `Not allowed for your key or tier. Depending on your tier, see ${DEVELOPERS}`;
  else if (err.status === 409 && code === 'not-ready') hint = 'The render is not finished yet.';
  else if (err.status === 410) hint = 'The result expired: files are kept 24 hours.';
  else if (err.status === 413) hint = 'File too large: 200 MB at most.';
  else if (err.status === 429 && code === 'quota-exhausted') hint = `Render quota spent: 3 per ISO week on a free account (resets Monday 00:00 UTC, same counter as the web tool), unlimited with Premium. Wait ${err.retryAfter ?? 'a little'} s.`;
  else if (err.status === 429) hint = `Too many requests or quota spent. Wait ${err.retryAfter ?? 'a little'} s before trying again.`;
  const lines = [err.message];
  if (hint) lines.push(hint);
  // 422 invalid-settings: one entry per refused value.
  for (const issue of err.problem?.errors ?? []) lines.push(`  ${issue.pointer}: ${issue.code} ${issue.message ?? ''}`.trimEnd());
  return lines.join('\n');
}

export function needKey() {
  if (!process.env.JAM_JAM_API_KEY) throw new Error('JAM_JAM_API_KEY is not set (see .env.example).');
}

export const loadSettings = async (path) => JSON.parse(await readFile(path, 'utf8'));

// POST /mastering/presets (mastering:write). Idempotency-Key is required.
export async function createPreset(name, settings) {
  const res = await request('/mastering/presets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey() },
    body: JSON.stringify({ name, settings }),
  });
  return res.json();
}

// POST /mastering/jobs (mastering:write). Exactly one of `preset` ("builtin:<id>" or the uuid of one of
// your presets) and `settings`. `key` lets a caller replay the same Idempotency-Key after a network error.
export async function startRender(path, { preset, settings, format = 'wav-pcm16', key = idempotencyKey() } = {}) {
  if ((preset === undefined) === (settings === undefined)) throw new Error('give exactly one of preset and settings');
  const body = new FormData();
  body.append('file', await openAsBlob(path), basename(path)); // streamed from disk, not read in memory
  if (preset !== undefined) body.append('preset', preset);
  else body.append('settings', JSON.stringify(settings));
  body.append('format', format);
  const res = await request('/mastering/jobs', { method: 'POST', headers: { 'Idempotency-Key': key }, body });
  const remaining = res.headers.get('x-mastering-quota-remaining');
  if (remaining !== null) console.error(`mastering quota remaining: ${remaining}`);
  return res.json();
}

// Polls GET /mastering/jobs/{id} (mastering:read), waiting as long as the server asks (Retry-After, seconds).
export async function waitForRender(id) {
  for (;;) {
    const res = await request(`/mastering/jobs/${id}`);
    const job = await res.json();
    console.error(`${job.status} ${Math.round((job.progress ?? 0) * 100)}%`);
    if (FINAL_STATUSES.includes(job.status)) return job;
    await sleep((Number(res.headers.get('retry-after')) || 2) * 1000);
  }
}

// Saves the mastered WAV as <name>-master.wav. Kept 24 h (then 410); downloading again is free.
export async function downloadMaster(id, dir = 'out') {
  const res = await request(`/mastering/jobs/${id}/result`);
  const disposition = res.headers.get('content-disposition') ?? '';
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
  const name = basename(decodeURIComponent(match?.[1] ?? match?.[2] ?? `${id}-master.wav`));
  await mkdir(dir, { recursive: true });
  const path = join(dir, name);
  await pipeline(Readable.fromWeb(res.body), createWriteStream(path));
  return path;
}

// One line with the integrated loudness and true peak before and after (null = silence).
export function describeReport(job) {
  if (!job.report) return 'no report';
  const { before, after } = job.report;
  return `integrated LUFS ${before.integratedLufs} -> ${after.integratedLufs}, true peak dBTP ${before.truePeakDbtp} -> ${after.truePeakDbtp}`;
}

// Runs a script's main function and prints Mastering errors readably.
export async function runMastering(main) {
  try {
    await main();
  } catch (err) {
    console.error(err instanceof ApiError ? explain(err) : err instanceof Error ? err.message : err);
    process.exitCode = 1;
  }
}

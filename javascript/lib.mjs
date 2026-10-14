// Shared helpers for the examples. Node 20+, no dependency.
import { mkdir, writeFile } from 'node:fs/promises';
import { basename, join } from 'node:path';

export const API = 'https://jam-jam.org/api/v1';

// Anonymous mode: the Authorization header is only sent when JAM_JAM_API_KEY is set.
const key = process.env.JAM_JAM_API_KEY;
const authHeaders = key ? { Authorization: `Bearer ${key}` } : {};

export class ApiError extends Error {
  constructor(status, problem, retryAfter) {
    const code = problem?.code ? ` ${problem.code}` : '';
    const detail = problem?.detail ?? problem?.title ?? 'not a Jam Jam error response (the anti-bot protection may block calls without an API key)';
    super(`HTTP ${status}${code}: ${detail}`);
    this.status = status;
    this.problem = problem;
    this.retryAfter = retryAfter;
  }
}

// Every API error is application/problem+json (RFC 9457): `code` is the stable value to test.
async function toApiError(res) {
  let problem = null;
  if ((res.headers.get('content-type') ?? '').includes('json')) {
    problem = await res.json().catch(() => null);
  }
  const retryAfter = Number(res.headers.get('retry-after')) || undefined;
  return new ApiError(res.status, problem, retryAfter);
}

export async function request(path, init = {}) {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...authHeaders, ...init.headers },
  });
  if (!res.ok) throw await toApiError(res);
  return res;
}

export const json = async (path, init) => (await request(path, init)).json();

// A fresh Idempotency-Key per write: replaying the same key returns the same result, no duplicate.
export const idempotencyKey = () => crypto.randomUUID();

export async function createJob(body) {
  const isForm = body instanceof FormData;
  const res = await request('/jobs', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey(), ...(isForm ? {} : { 'Content-Type': 'application/json' }) },
    body: isForm ? body : JSON.stringify(body),
  });
  console.log(`quota remaining: ${res.headers.get('x-quota-remaining') ?? 'n/a'} (window ${res.headers.get('x-quota-window') ?? 'n/a'})`);
  return res.json();
}

const FINAL_PHASES = ['done', 'failed', 'cancelled'];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Polls GET /jobs/{id}, waiting as long as the server asks (Retry-After, in seconds).
export async function waitForJob(id) {
  for (;;) {
    const res = await request(`/jobs/${id}`);
    const job = await res.json();
    console.log(`${job.phase} ${job.percent}%`);
    if (FINAL_PHASES.includes(job.phase)) return job;
    await sleep((Number(res.headers.get('retry-after')) || 2) * 1000);
  }
}

// Saves the main result file in ./out. Results are kept 24 h after the job was created (then 410).
export async function downloadResult(id, dir = 'out') {
  const res = await request(`/jobs/${id}/result`);
  const disposition = res.headers.get('content-disposition') ?? '';
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(disposition);
  const name = basename(decodeURIComponent(match?.[1] ?? match?.[2] ?? `${id}.bin`));
  await mkdir(dir, { recursive: true });
  const path = join(dir, name);
  await writeFile(path, Buffer.from(await res.arrayBuffer()));
  return path;
}

// Runs a script's main function and prints API errors readably.
export async function run(main) {
  try {
    await main();
  } catch (err) {
    console.error(err instanceof Error ? err.message : err);
    if (err.retryAfter) console.error(`Retry after ${err.retryAfter} s.`);
    process.exitCode = 1;
  }
}

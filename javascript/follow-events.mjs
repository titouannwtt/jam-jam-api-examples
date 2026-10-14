// Follows a job with Server-Sent Events instead of polling.
// Events: state (job snapshot), done (final job), error (problem), ping (keep-alive).
// Usage: node follow-events.mjs <job_id>
import { request, run } from './lib.mjs';

await run(async () => {
  const id = process.argv[2];
  if (!id) throw new Error('usage: node follow-events.mjs <job_id>');

  const res = await request(`/jobs/${id}/events`, { headers: { Accept: 'text/event-stream' } });
  const decoder = new TextDecoder();
  let buffer = '';
  let event = 'message';
  let data = [];

  for await (const chunk of res.body) {
    buffer += decoder.decode(chunk, { stream: true });
    let newline;
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newline).replace(/\r$/, '');
      buffer = buffer.slice(newline + 1);
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
      else if (line === '') {
        const payload = data.length ? JSON.parse(data.join('\n')) : null;
        if (event === 'state') console.log(`${payload.phase} ${payload.percent}%`);
        if (event === 'done') return console.log('done:', payload.id, payload.artifacts.map((a) => a.filename).join(', '));
        if (event === 'error') {
          console.error('error:', payload.code, payload.detail ?? payload.title);
          process.exitCode = 1;
          return;
        }
        event = 'message';
        data = [];
      }
    }
  }
});

// Shows your quota balances and the scopes of your API key. Needs JAM_JAM_API_KEY.
import { json, run } from './lib.mjs';

await run(async () => {
  const usage = await json('/me/usage');
  console.log('owner:', usage.ownerKind, '| scopes:', usage.scopes.join(', ') || '(none)');
  for (const name of ['conversion', 'read', 'write', 'stems']) {
    const bucket = usage[name];
    if (bucket) {
      console.log(`${name}: ${bucket.used} / ${bucket.limit ?? 'unlimited'} (${bucket.window}, resets ${bucket.resetsAt})`);
    }
  }
});

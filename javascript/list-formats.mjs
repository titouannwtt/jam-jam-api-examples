// Lists the input and output formats this server serves. No API key needed.
// Usage: node list-formats.mjs [inputFormat]
import { json, run } from './lib.mjs';

await run(async () => {
  const input = process.argv[2];
  const formats = await json(input ? `/formats?input=${encodeURIComponent(input)}` : '/formats');

  if (input) {
    for (const o of formats.possibleOutputs) {
      console.log(`${o.id.padEnd(18)} ${o.allowed ? 'allowed' : `not allowed (${o.reason})`}`);
    }
    return;
  }
  console.log('Inputs:');
  for (const f of formats.inputs.filter((f) => f.served)) {
    console.log(`  ${f.id.padEnd(20)} ${f.extensions.join(',')}${f.requiresAccount ? '  [account]' : ''}`);
  }
  console.log('Outputs:');
  for (const f of formats.outputs.filter((f) => f.served)) {
    console.log(`  ${f.id.padEnd(20)} tier=${f.tier}${f.requiresAccount ? '  [account]' : ''}`);
  }
});

// Reads and writes your private notebook (the carnet).
//   node notebook.mjs list     needs scope carnet:read  (draws on the read quota)
//   node notebook.mjs add      needs scope carnet:write (draws on the write quota)
import { idempotencyKey, json, run } from './lib.mjs';

await run(async () => {
  const [action] = process.argv.slice(2);

  if (action === 'list') {
    // Cursor pagination: replay nextCursor until it is null.
    const page = await json('/me/songs?limit=10');
    for (const s of page.items) console.log(`${s.id}  ${s.title}${s.artist ? ` - ${s.artist}` : ''}  (key ${s.key ?? '?'})`);
    console.log(page.nextCursor ? `more: cursor=${page.nextCursor}` : 'end of list');
  } else if (action === 'add') {
    // A public domain song. The id is derived (artist-title slug): posting it twice replaces it.
    const song = {
      title: 'Amazing Grace',
      artist: 'John Newton (1779), traditional melody',
      sections: [{ label: 'Verse 1', lines: [{ lyrics: 'Amazing grace! how sweet the sound', chords: [{ offset: 0, chord: 'G' }] }] }],
    };
    const ack = await json('/me/songs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey() },
      body: JSON.stringify({ song }),
    });
    console.log('saved:', ack.id, ack.updatedAt);
  } else {
    throw new Error('usage: node notebook.mjs list|add');
  }
});

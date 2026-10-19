import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

let implementation;
try {
  implementation = await import('./capture-evidence.mjs');
} catch (error) {
  if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
}

// Signature fixtures exercise byte preservation, not image decoding.
const jpeg = Uint8Array.from([255, 216, 255, 224, 1, 2, 3, 255, 217]);
const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
  'base64',
);
const session = { channel: 'Device Hub / CUA', target: 'test phone / OS', app: 'test app / build' };

async function fixture(t, screenshots = [jpeg]) {
  assert.equal(typeof implementation?.createEvidenceRecorder, 'function', 'Evidence recorder is not implemented');
  const directory = await mkdtemp(join(tmpdir(), 'iphone-evidence-test-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const calls = [];
  const target = {
    async getScreenshot(options) {
      calls.push(options);
      return screenshots.shift();
    },
  };
  const recorder = await implementation.createEvidenceRecorder({ directory, target, session });
  return { recorder, directory, target, calls };
}

test('preserves JPEG bytes and records neutral ID, actual observation and UTC metadata', async (t) => {
  const { recorder, directory, calls } = await fixture(t);
  const result = await recorder.capture({ state: 'transition', observation: 'List still visible; answer has not appeared' });
  assert.equal(result.entry.id, 'capture-0001');
  assert.equal(result.entry.file, 'capture-0001.jpg');
  assert.equal(result.entry.mimeType, 'image/jpeg');
  assert.equal(result.entry.state, 'transition');
  assert.equal(result.entry.publication, 'raw-private');
  assert.equal(result.entry.observation, 'List still visible; answer has not appeared');
  assert.equal(new Date(result.entry.observedAt).toISOString(), result.entry.observedAt);
  assert.equal(new Date(result.entry.savedAt).toISOString(), result.entry.savedAt);
  assert.deepEqual(await readFile(result.path), Buffer.from(jpeg));
  assert.deepEqual(result.bytes, Buffer.from(jpeg));
  assert.deepEqual(calls, [{ emit: false }]);
  const manifest = JSON.parse(await readFile(join(directory, 'screenshots.json'), 'utf8'));
  assert.deepEqual(manifest.session, session);
  assert.deepEqual(manifest.screenshots, [result.entry]);
});

test('resumes a matching session and preserves previous files while detecting PNG', async (t) => {
  const { recorder, directory } = await fixture(t);
  const first = await recorder.capture({ state: 'stable', observation: 'Initial screen' });
  const resumed = await implementation.createEvidenceRecorder({
    directory, session, target: { getScreenshot: async () => png },
  });
  const second = await resumed.capture({ state: 'stable', observation: 'Second screen', publication: 'reviewed' });
  assert.equal(second.entry.file, 'capture-0002.png');
  assert.equal(second.entry.mimeType, 'image/png');
  assert.deepEqual(await readFile(first.path), Buffer.from(jpeg));
  assert.deepEqual(await readFile(second.path), png);
  assert.equal(JSON.parse(await readFile(join(directory, 'screenshots.json'))).screenshots.length, 2);
});

test('rejects premature labels and unknown/truncated bytes without publishing artifacts', async (t) => {
  const { recorder, directory, calls } = await fixture(t, [Buffer.from('unknown'), jpeg.subarray(0, 5)]);
  await assert.rejects(() => recorder.capture({ observation: 'No state' }), /state/);
  assert.equal(calls.length, 0);
  await assert.rejects(() => recorder.capture({ state: 'stable' }), /format|truncated/i);
  await assert.rejects(() => recorder.capture({ state: 'stable' }), /format|truncated/i);
  assert.deepEqual(await readdir(directory), []);
});

test('refuses a different session and a colliding filename without overwriting evidence', async (t) => {
  const { recorder, directory } = await fixture(t, [jpeg, jpeg]);
  await recorder.capture({ state: 'stable' });
  const manifestBefore = await readFile(join(directory, 'screenshots.json'));
  await assert.rejects(() => implementation.createEvidenceRecorder({
    directory, session: { ...session, target: 'other phone' }, target: { getScreenshot() {} },
  }), /session/i);
  const collision = join(directory, 'capture-0002.jpg');
  await writeFile(collision, 'existing evidence');
  await assert.rejects(() => recorder.capture({ state: 'stable' }), { code: 'EEXIST' });
  assert.equal(await readFile(collision, 'utf8'), 'existing evidence');
  assert.deepEqual(await readFile(join(directory, 'screenshots.json')), manifestBefore);
});

test('serializes concurrent requests through one recorder', async (t) => {
  const { recorder, directory } = await fixture(t, [jpeg, png]);
  const results = await Promise.all([
    recorder.capture({ state: 'stable', observation: 'First' }),
    recorder.capture({ state: 'transition', observation: 'Second' }),
  ]);
  assert.deepEqual(results.map((r) => r.entry.id), ['capture-0001', 'capture-0002']);
  assert.deepEqual(JSON.parse(await readFile(join(directory, 'screenshots.json'))).screenshots, results.map((r) => r.entry));
});

test('accepts screenshot byte views from a separate REPL realm', async (t) => {
  const foreignBytes = runInNewContext('new Uint8Array([255,216,255,224,1,2,3,255,217])');
  assert.equal(foreignBytes instanceof Uint8Array, false);
  const { recorder } = await fixture(t, [foreignBytes]);
  const result = await recorder.capture({ state: 'stable' });
  assert.deepEqual(await readFile(result.path), Buffer.from(jpeg));
});

test('captures unreviewed bytes before annotation, preserving image identity and timestamps', async (t) => {
  const { recorder, directory } = await fixture(t);
  const saved = await recorder.capture();
  assert.equal(saved.entry.state, 'unreviewed');
  assert.equal(saved.entry.observation, '');
  assert.equal(saved.entry.publication, 'raw-private');
  const annotated = await recorder.annotate(saved.entry.id, {
    state: 'transition', observation: 'Saved bytes show the last card, not a blank carousel',
  });
  assert.equal(annotated.entry.observation, 'Saved bytes show the last card, not a blank carousel');
  assert.equal(annotated.entry.state, 'transition');
  assert.equal(new Date(annotated.entry.annotatedAt).toISOString(), annotated.entry.annotatedAt);
  for (const key of ['id', 'file', 'mimeType', 'bytes', 'sha256', 'observedAt', 'savedAt']) {
    assert.equal(annotated.entry[key], saved.entry[key]);
  }
  assert.deepEqual(await readFile(saved.path), Buffer.from(jpeg));
  assert.deepEqual(JSON.parse(await readFile(join(directory, 'screenshots.json'))).screenshots, [annotated.entry]);
});

test('keeps annotations across queued captures and a resumed recorder', async (t) => {
  const { recorder, directory } = await fixture(t, [jpeg, png]);
  const first = await recorder.capture();
  const [annotated] = await Promise.all([
    recorder.annotate(first.entry.id, { state: 'stable', observation: 'First card and next card overlap' }),
    recorder.capture(),
  ]);
  const resumed = await implementation.createEvidenceRecorder({
    directory, session, target: { getScreenshot: async () => jpeg },
  });
  await resumed.capture();
  const entries = JSON.parse(await readFile(join(directory, 'screenshots.json'))).screenshots;
  assert.deepEqual(entries[0], annotated.entry);
  assert.equal(entries.length, 3);
});

test('rejects invalid annotations without changing evidence and accepts a later correction', async (t) => {
  const { recorder, directory } = await fixture(t);
  const first = await recorder.capture({ state: 'stable', observation: 'Old label' });
  const before = await readFile(join(directory, 'screenshots.json'));
  for (const [id, options] of [
    ['capture-9999', { state: 'stable', observation: 'Missing' }],
    [first.entry.id, { state: 'unreviewed', observation: 'Invalid state' }],
    [first.entry.id, { state: 'stable', observation: '' }],
    [first.entry.id, { state: 'stable', observation: 'Valid', publication: 'public' }],
    [first.entry.id, { state: 'stable', observation: 'Valid', sha256: 'replace' }],
  ]) {
    await assert.rejects(() => recorder.annotate(id, options));
    assert.deepEqual(await readFile(join(directory, 'screenshots.json')), before);
  }
  const corrected = await recorder.annotate(first.entry.id, { state: 'transition', observation: 'Corrected after inspecting saved bytes' });
  assert.equal(corrected.entry.observation, 'Corrected after inspecting saved bytes');
  assert.deepEqual(await readFile(first.path), Buffer.from(jpeg));
});

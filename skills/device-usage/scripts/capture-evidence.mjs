import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { isAbsolute, join } from 'node:path';
import { types } from 'node:util';

const pngHeader = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const pngEnd = Buffer.from([0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]);

function imageFormat(bytes) {
  if (bytes.length >= 5 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255
      && bytes.at(-2) === 255 && bytes.at(-1) === 217) {
    return { extension: 'jpg', mimeType: 'image/jpeg' };
  }
  if (bytes.length >= 33 && bytes.subarray(0, 8).equals(pngHeader)
      && bytes.subarray(-12).equals(pngEnd)) {
    return { extension: 'png', mimeType: 'image/png' };
  }
  throw new Error('Unknown screenshot format or truncated bytes; nothing was saved');
}

/** One recorder/writer per evidence directory. The caller judges visual stability. */
export async function createEvidenceRecorder({ directory, target, session }) {
  if (!isAbsolute(directory)) throw new Error('Evidence directory must be absolute');
  if (typeof target?.getScreenshot !== 'function') throw new Error('A CUA screenshot target is required');
  const context = { channel: session?.channel, target: session?.target, app: session?.app };
  if (Object.values(context).some((value) => typeof value !== 'string' || !value.trim())) {
    throw new Error('Session requires channel, target and app labels');
  }
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const manifestPath = join(directory, 'screenshots.json');
  let manifest;
  try {
    manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
    if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.screenshots)
        || Object.keys(context).some((key) => manifest.session?.[key] !== context[key])
        || manifest.screenshots.some((entry, index) => entry.id !== `capture-${String(index + 1).padStart(4, '0')}`)) {
      throw new Error('Existing manifest has an incompatible schema or session; choose another directory');
    }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    manifest = { schemaVersion: 1, session: context, screenshots: [] };
  }

  async function saveManifest(next) {
    const temporaryPath = join(directory, '.screenshots.json.tmp');
    await writeFile(temporaryPath, `${JSON.stringify(next, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
    await rename(temporaryPath, manifestPath);
    manifest = next;
  }

  async function captureOne({ state = 'unreviewed', observation = '', publication = 'raw-private' } = {}) {
    if (!['unreviewed', 'stable', 'transition'].includes(state)) throw new Error('Unknown capture state');
    if (typeof observation !== 'string') throw new Error('Observation must be text');
    if (!['raw-private', 'reviewed'].includes(publication)) throw new Error('Unknown publication classification');
    if (state === 'unreviewed' && (observation !== '' || publication !== 'raw-private')) {
      throw new Error('Inspect saved bytes before assigning state, observation or publication');
    }
    const raw = await target.getScreenshot({ emit: false });
    const observedAt = new Date().toISOString();
    if (!types.isUint8Array(raw)) throw new Error('Expected CUA screenshot bytes');
    const bytes = Buffer.from(raw);
    const format = imageFormat(bytes);
    const id = `capture-${String(manifest.screenshots.length + 1).padStart(4, '0')}`;
    const file = `${id}.${format.extension}`;
    const path = join(directory, file);
    await writeFile(path, bytes, { flag: 'wx', mode: 0o600 });
    const entry = {
      id, file, mimeType: format.mimeType, observedAt,
      savedAt: new Date().toISOString(), state, observation, publication,
      bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'),
    };
    const next = { ...manifest, screenshots: [...manifest.screenshots, entry] };
    await saveManifest(next);
    return { entry: { ...entry }, bytes, path };
  }

  async function annotateOne(id, options = {}) {
    const { state, observation, publication } = options;
    if (Object.keys(options).some((key) => !['state', 'observation', 'publication'].includes(key))) {
      throw new Error('Annotation may change only state, observation and publication');
    }
    if (!['stable', 'transition'].includes(state)) throw new Error('Annotation state must be stable or transition');
    if (typeof observation !== 'string' || !observation.trim()) throw new Error('Annotation requires an observed description');
    if (publication !== undefined && !['raw-private', 'reviewed'].includes(publication)) {
      throw new Error('Unknown publication classification');
    }
    const index = manifest.screenshots.findIndex((entry) => entry.id === id);
    if (index < 0) throw new Error('Unknown capture ID');
    const previous = manifest.screenshots[index];
    const entry = {
      ...previous, state, observation, publication: publication ?? previous.publication,
      annotatedAt: new Date().toISOString(),
    };
    const screenshots = manifest.screenshots.map((item, position) => position === index ? entry : item);
    await saveManifest({ ...manifest, screenshots });
    return { entry: { ...entry }, path: join(directory, entry.file) };
  }

  let pending = Promise.resolve();
  function enqueue(operation) {
    const result = pending.then(operation);
    pending = result.catch(() => {});
    return result;
  }
  return {
    capture(options) {
      return enqueue(() => captureOne(options));
    },
    annotate(id, options) {
      return enqueue(() => annotateOne(id, options));
    },
  };
}

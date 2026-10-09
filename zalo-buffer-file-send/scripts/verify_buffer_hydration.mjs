import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const bundle = process.argv[2];
assert.ok(bundle, 'Pass the normalization bundle path');
const { c: hydrateAttachmentParamsForAction, p: resolveAttachmentMediaPolicy } = await import(pathToFileURL(bundle).href);
assert.equal(typeof hydrateAttachmentParamsForAction, 'function');
assert.equal(typeof resolveAttachmentMediaPolicy, 'function');
const outbound = '/root/.openclaw/media/outbound';
await fs.mkdir(outbound, {recursive: true});
const directory = await fs.mkdtemp(path.join(outbound, 'hydration-check-'));
const fixture = path.join(directory, 'attachment.txt');
const bytes = Buffer.from(`Bounded Zalo attachment check ${crypto.randomUUID()}`);
await fs.writeFile(fixture, bytes);
const cfg = {agents: {defaults: {mediaMaxMb: 1}}};
const mediaPolicy = resolveAttachmentMediaPolicy({mediaLocalRoots: [directory]});
const hydrate = (args, overrides = {}) => hydrateAttachmentParamsForAction({
  cfg, channel: 'zalouser', accountId: 'default', action: 'send',
  args, dryRun: false, mediaPolicy, ...overrides,
});
const checks = [];
try {
  const args = {media: fixture, asDocument: true};
  let commitChecks = 0;
  await hydrate(args, {assertClientUploadAllowed: () => {commitChecks += 1;}});
  assert.deepEqual(Buffer.from(args.buffer, 'base64'), bytes);
  assert.notEqual(args.media, fixture);
  assert.deepEqual(await fs.readFile(args.media), bytes);
  assert.equal(args.filename, 'attachment.txt');
  assert.equal(args.mediaUrl, args.media);
  assert.deepEqual(args.mediaUrls, [args.media]);
  assert.ok(commitChecks > 0);
  checks.push('local-file-buffer-staging-and-upload-authority');

  const fileArgs = {filePath: fixture, filename: 'specified-name.txt'};
  await hydrate(fileArgs);
  assert.equal(fileArgs.filename, 'specified-name.txt');
  assert.deepEqual(Buffer.from(fileArgs.buffer, 'base64'), bytes);
  checks.push('file-path-alias-and-explicit-filename');

  const dryArgs = {media: path.join(directory, 'does-not-exist.txt')};
  await hydrate(dryArgs, {dryRun: true});
  assert.equal(dryArgs.buffer, undefined);
  checks.push('dry-run-does-not-read-or-stage');

  await assert.rejects(hydrate({media: '/etc/hostname'}));
  checks.push('local-root-denial-preserved');
  await assert.rejects(hydrate({media: fixture}, {cfg: {agents: {defaults: {mediaMaxMb: 0.000001}}}}));
  checks.push('media-size-limit-preserved');
  await assert.rejects(hydrate({media: fixture}, {
    assertClientUploadAllowed: () => {throw new Error('fixture-commit-denied');},
  }), /fixture-commit-denied/);
  checks.push('upload-authority-denial-preserved');

  const telegram = {media: fixture};
  await hydrate(telegram, {channel: 'telegram'});
  assert.equal(telegram.media, fixture);
  assert.equal(telegram.buffer, undefined);
  checks.push('telegram-local-send-unchanged');

  const bufferArgs = {buffer: bytes.toString('base64'), filename: 'buffer.txt'};
  await hydrate(bufferArgs);
  assert.equal(bufferArgs.buffer, undefined);
  assert.deepEqual(await fs.readFile(bufferArgs.media), bytes);
  checks.push('native-buffer-only-send-unchanged');

  const attachment = {media: fixture};
  await hydrate(attachment, {action: 'sendAttachment'});
  assert.deepEqual(Buffer.from(attachment.buffer, 'base64'), bytes);
  checks.push('native-sendAttachment-unchanged');

  if (process.argv[3]) {
    const source = path.resolve(process.argv[3]);
    const actualArgs = {media: source, asDocument: true};
    await hydrate(actualArgs, {mediaPolicy: resolveAttachmentMediaPolicy({mediaLocalRoots: [path.dirname(source)]})});
    assert.deepEqual(Buffer.from(actualArgs.buffer, 'base64'), await fs.readFile(source));
    assert.deepEqual(await fs.readFile(actualArgs.media), await fs.readFile(source));
    assert.equal(actualArgs.filename, path.basename(source));
    checks.push('existing-requested-docx-bytes-preserved');
  }
  console.log(JSON.stringify({ok: true, platformCalls: 0, deliveryAttempted: false, checks}));
} finally {
  await fs.rm(directory, {recursive: true, force: true});
}
process.exit(0);

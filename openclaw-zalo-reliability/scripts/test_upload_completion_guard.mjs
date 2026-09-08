import assert from 'node:assert/strict';
import { dispatchUploadCompletion, waitForUploadCompletion } from './upload-completion-guard.js';

const context = () => ({ uploadCallbacks: new Map() });
const result = (data) => ({ fileId: data.fileId, fileUrl: data.fileUrl });

// Normal callback: resolves and removes the callback.
{
  const ctx = context();
  const p = waitForUploadCompletion(ctx, 'normal', async (d) => result(d), 1000);
  assert.equal(dispatchUploadCompletion(ctx, { fileId: 'normal', fileUrl: 'ok' }), true);
  assert.deepEqual(await p, { fileId: 'normal', fileUrl: 'ok' });
  assert.equal(ctx.uploadCallbacks.size, 0);
}

// Early file_done: buffered briefly, then consumed by the waiter.
{
  const ctx = context();
  assert.equal(dispatchUploadCompletion(ctx, { fileId: 'early', fileUrl: 'early-ok' }), false);
  const p = waitForUploadCompletion(ctx, 'early', async (d) => result(d), 1000);
  assert.deepEqual(await p, { fileId: 'early', fileUrl: 'early-ok' });
}

// Missing callback: typed timeout and callback cleanup.
{
  const ctx = context();
  let keepTimer = setTimeout(() => {}, 150);
  const p = waitForUploadCompletion(ctx, 'timeout', async (d) => result(d), 25);
  await assert.rejects(p, (e) => e.code === 'ZALO_UPLOAD_ACK_TIMEOUT' && e.deliveryUncertain === true);
  clearTimeout(keepTimer);
  assert.equal(ctx.uploadCallbacks.size, 0);
}

// Late callback after timeout cannot settle or create a future waiter.
{
  const ctx = context();
  let keepTimer = setTimeout(() => {}, 150);
  const p = waitForUploadCompletion(ctx, 'late', async (d) => result(d), 25);
  await assert.rejects(p, (e) => e.code === 'ZALO_UPLOAD_ACK_TIMEOUT');
  clearTimeout(keepTimer);
  assert.equal(dispatchUploadCompletion(ctx, { fileId: 'late', fileUrl: 'late' }), false);
  await assert.rejects(waitForUploadCompletion(ctx, 'late', async (d) => result(d), 25),
    (e) => e.code === 'ZALO_UPLOAD_ACK_ALREADY_SETTLED');
}

// Checksum/read callback failure rejects and cleans up.
{
  const ctx = context();
  const p = waitForUploadCompletion(ctx, 'exception', async () => { throw new Error('checksum failed'); }, 1000);
  dispatchUploadCompletion(ctx, { fileId: 'exception' });
  await assert.rejects(p, (e) => e.code === 'ZALO_UPLOAD_ACK_PROCESSING_FAILED' && e.cause?.message === 'checksum failed');
  assert.equal(ctx.uploadCallbacks.size, 0);
}

console.log('upload completion guard tests: PASS');

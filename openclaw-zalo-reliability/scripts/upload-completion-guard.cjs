'use strict';

const UPLOAD_ACK_TIMEOUT_MS = 60000;
const EARLY_EVENT_TTL_MS = 15000;
const CLOSED_EVENT_TTL_MS = 5 * 60 * 1000;
const MAX_EARLY_EVENTS = 128;
const MAX_CLOSED_EVENTS = 2048;
const states = new WeakMap();

function stateFor(ctx) {
  let state = states.get(ctx);
  if (!state) {
    state = { early: new Map(), closed: new Map() };
    states.set(ctx, state);
  }
  return state;
}
function prune(state, now = Date.now()) {
  for (const [key, item] of state.early) {
    if (item.expiresAt <= now) {
      clearTimeout(item.timer);
      state.early.delete(key);
    }
  }
  for (const [key, expiresAt] of state.closed) {
    if (expiresAt <= now) state.closed.delete(key);
  }
}
function closeKey(state, key) {
  state.closed.delete(key);
  state.closed.set(key, Date.now() + CLOSED_EVENT_TTL_MS);
  while (state.closed.size > MAX_CLOSED_EVENTS) state.closed.delete(state.closed.keys().next().value);
  const timer = setTimeout(() => {
    if (state.closed.get(key) <= Date.now()) state.closed.delete(key);
  }, CLOSED_EVENT_TTL_MS + 1);
  timer.unref?.();
}
function takeEarly(state, key) {
  const item = state.early.get(key);
  if (!item) return undefined;
  clearTimeout(item.timer);
  state.early.delete(key);
  return item.data;
}
function rememberEarly(state, key, data) {
  const expiresAt = Date.now() + EARLY_EVENT_TTL_MS;
  const old = state.early.get(key);
  if (old) clearTimeout(old.timer);
  const timer = setTimeout(() => {
    const current = state.early.get(key);
    if (current?.expiresAt === expiresAt) state.early.delete(key);
  }, EARLY_EVENT_TTL_MS);
  timer.unref?.();
  state.early.set(key, { data, expiresAt, timer });
  while (state.early.size > MAX_EARLY_EVENTS) {
    const oldest = state.early.keys().next().value;
    const item = state.early.get(oldest);
    clearTimeout(item?.timer);
    state.early.delete(oldest);
  }
}
function uploadError(message, code, cause) {
  const error = new Error(message);
  if (cause !== undefined) error.cause = cause;
  error.name = 'ZaloUploadAcknowledgementError';
  error.code = code;
  error.deliveryUncertain = true;
  return error;
}
function waitForUploadCompletion(ctx, fileId, buildResult, timeoutMs = UPLOAD_ACK_TIMEOUT_MS) {
  const key = String(fileId);
  if (!key || key === 'undefined' || key === 'null') return Promise.reject(uploadError('Missing upload file id', 'ZALO_UPLOAD_INVALID_FILE_ID'));
  const state = stateFor(ctx);
  prune(state);
  if (state.closed.has(key)) return Promise.reject(uploadError(`Upload acknowledgement already settled for ${key}`, 'ZALO_UPLOAD_ACK_ALREADY_SETTLED'));
  if (ctx.uploadCallbacks.has(key)) return Promise.reject(uploadError(`Upload acknowledgement already waiting for ${key}`, 'ZALO_UPLOAD_ACK_DUPLICATE'));
  let settled = false;
  let running = false;
  let timer;
  let callback;
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  const finish = (error, result) => {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    if (ctx.uploadCallbacks.get(key) === callback) ctx.uploadCallbacks.delete(key);
    closeKey(state, key);
    if (error) reject(error); else resolve(result);
  };
  callback = async (wsData) => {
    if (settled || running) return;
    running = true;
    try { finish(null, await buildResult(wsData)); }
    catch (error) { finish(uploadError('Upload acknowledgement processing failed', 'ZALO_UPLOAD_ACK_PROCESSING_FAILED', error)); }
  };
  timer = setTimeout(() => finish(uploadError(`Timed out waiting for upload acknowledgement ${key}`, 'ZALO_UPLOAD_ACK_TIMEOUT')), timeoutMs);
  timer.unref?.();
  ctx.uploadCallbacks.set(key, callback);
  const early = takeEarly(state, key);
  if (early) void callback(early);
  return promise;
}
function dispatchUploadCompletion(ctx, data) {
  const key = String(data?.fileId ?? '');
  if (!key || key === 'undefined' || key === 'null') return false;
  const state = stateFor(ctx);
  prune(state);
  if (state.closed.has(key)) return false;
  const callback = ctx.uploadCallbacks.get(key);
  if (callback) {
    ctx.uploadCallbacks.delete(key);
    void callback(data);
    return true;
  }
  rememberEarly(state, key, data);
  return false;
}
module.exports = { UPLOAD_ACK_TIMEOUT_MS, waitForUploadCompletion, dispatchUploadCompletion };

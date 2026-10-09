import { createHash, randomUUID } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, renameSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

const MAX_TEXT_LENGTH = 1000;
const RETENTION_MS = 7 * 24 * 60 * 60 * 1000;
const MAX_DESTINATIONS = 256;
const digest = (value) => createHash("sha256").update(value).digest("hex");
const destinationKey = (threadId, options) => digest(JSON.stringify([options.profile ?? "default", options.isGroup === true, threadId]));

export function numericErrorCode(value) {
  return /^-?\d{1,8}$/.test(String(value ?? "")) ? Number(value) : null;
}

export function splitPlainText(text, requestedLimit = MAX_TEXT_LENGTH) {
  if (!text) return [];
  const limit = Number.isFinite(requestedLimit) ? Math.max(64, Math.min(MAX_TEXT_LENGTH, Math.floor(requestedLimit))) : MAX_TEXT_LENGTH;
  if (text.length <= limit) return [text];
  const capacity = limit - (2 * String(text.length).length + 4);
  const boundaries = new Set([0, text.length]);
  for (const segment of new Intl.Segmenter("vi", { granularity: "grapheme" }).segment(text)) boundaries.add(segment.index);
  const parts = [];
  let start = 0;
  while (start < text.length) {
    let end = Math.min(text.length, start + capacity);
    if (end < text.length) {
      const newline = text.lastIndexOf("\n", end - 1) + 1;
      if (newline > start + capacity / 2) end = newline;
      else {
        const whitespace = text.lastIndexOf(" ", end - 1) + 1;
        if (whitespace > start + capacity / 2) end = whitespace;
      }
      while (end > start && !boundaries.has(end)) end -= 1;
    }
    if (end <= start) throw new Error("Một cụm ký tự vượt giới hạn gửi Zalo.");
    parts.push(text.slice(start, end));
    start = end;
  }
  return parts.map((part, index) => `[${index + 1}/${parts.length}]\n${part}`);
}

function createFileStore(log, path = join(homedir(), ".openclaw", "state", "zalouser-text-delivery-state.json")) {
  let fallback = {};
  const load = () => {
    try {
      const parsed = JSON.parse(readFileSync(path, "utf8"));
      if (parsed.version === 1 && parsed.entries && typeof parsed.entries === "object") fallback = parsed.entries;
    } catch (error) {
      if (error.code !== "ENOENT") log({ event: "state_read_failed" });
    }
    return fallback;
  };
  return {
    read: (key) => load()[key],
    write: (key, entry) => {
      const entries = { ...load(), [key]: entry };
      fallback = Object.fromEntries(Object.entries(entries)
        .filter(([, value]) => Number.isFinite(value.current?.updatedAt) && Date.now() - value.current.updatedAt < RETENTION_MS)
        .sort((left, right) => right[1].current.updatedAt - left[1].current.updatedAt)
        .slice(0, MAX_DESTINATIONS));
      try {
        mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
        const temporary = `${path}.${randomUUID()}.tmp`;
        writeFileSync(temporary, JSON.stringify({ version: 1, entries: fallback }), { mode: 0o600 });
        renameSync(temporary, path);
      } catch {
        log({ event: "state_write_failed" });
      }
    }
  };
}

export function createTextDeliveryGuard(dependencies = {}) {
  const log = dependencies.log ?? ((metadata) => console.info(`[zalouser-text-guard] ${JSON.stringify(metadata)}`));
  const sleep = dependencies.sleep ?? ((milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)));
  const store = dependencies.store ?? createFileStore(log, dependencies.statePath);
  const lanes = new Map();

  async function deliver(params, key) {
    const { threadId, text, options, send, onDeliveryResult, createReceipt, createPartialError } = params;
    const parts = splitPlainText(text, options.textChunkLimit);
    if (parts.length === 0) throw new Error("Không có nội dung văn bản để gửi Zalo.");
    const contentHash = digest(text);
    const previous = store.read(key);
    let failure = previous?.failure;
    let confirmedParts = 0;
    const messageIds = [];
    let activePart = 1;
    let lastResult;
    const record = (status, errorCode = null) => {
      const current = { status, contentHash, confirmedParts, totalParts: parts.length, activePart, errorCode, updatedAt: Date.now() };
      if (["rejected", "unknown", "partial"].includes(status)) failure = current;
      if (status === "confirmed" && failure?.contentHash === contentHash) failure = undefined;
      store.write(key, { current, ...(failure ? { failure } : {}) });
    };
    record("sending");
    try {
      for (const [index, part] of parts.entries()) {
        activePart = index + 1;
        if (index > 0) await sleep(600);
        for (let attempt = 1; attempt <= 2; attempt += 1) {
          record("sending");
          log({ event: "send_started", part: activePart, total: parts.length, chars: part.length, attempt });
          const result = await send(threadId, part, {
            ...options,
            textMode: "plain",
            textStyles: undefined,
            textChunkLimit: MAX_TEXT_LENGTH
          });
          const receipts = result.receipt?.platformMessageIds?.filter((value) => typeof value === "string" && value.trim()) ?? [];
          if (result.ok && receipts.length > 0) {
            messageIds.push(...receipts);
            confirmedParts += 1;
            lastResult = result;
            record(confirmedParts === parts.length ? "confirmed" : "sending");
            log({ event: "part_confirmed", part: activePart, total: parts.length, attempt });
            await onDeliveryResult?.(result);
            break;
          }
          messageIds.push(...receipts);
          const errorCode = numericErrorCode(result.errorCode);
          const explicitlyRejected = !result.ok && result.errorKind === "api_rejected" && errorCode !== null && errorCode !== 0 && receipts.length === 0;
          log({ event: "send_failed", part: activePart, total: parts.length, chars: part.length, attempt, errorCode, classification: explicitlyRejected ? "api_rejected" : "unknown" });
          if (explicitlyRejected && attempt < 2) {
            await sleep(900);
            continue;
          }
          const error = new Error(`Zalo chưa xác nhận gửi phần ${activePart}/${parts.length} (${explicitlyRejected ? "api_rejected" : "unknown_after_send"}${errorCode === null ? "" : `; code=${errorCode}`}).`);
          error.zaloErrorCode = errorCode;
          error.zaloExplicitRejection = explicitlyRejected;
          throw error;
        }
      }
      return lastResult;
    } catch (error) {
      record(confirmedParts > 0 || messageIds.length > 0 ? "partial" : error.zaloExplicitRejection ? "rejected" : "unknown", numericErrorCode(error.zaloErrorCode));
      if (messageIds.length > 0) throw createPartialError(error, {
        messageIds,
        receipt: createReceipt({ threadId, kind: "text", platformMessageIds: messageIds }),
        visibleReplySent: true
      });
      throw error;
    }
  }

  return {
    send: (params) => {
      const key = destinationKey(params.threadId, params.options);
      const task = (lanes.get(key) ?? Promise.resolve()).then(() => deliver(params, key));
      const tail = task.catch(() => {});
      lanes.set(key, tail);
      void tail.then(() => { if (lanes.get(key) === tail) lanes.delete(key); });
      return task;
    },
    context: (threadId, options = {}) => {
      const entry = store.read(destinationKey(threadId, options));
      const pending = entry?.failure ?? (entry?.current?.status === "sending" ? entry.current : undefined);
      if (!pending || Date.now() - pending.updatedAt > RETENTION_MS) return "";
      const status = pending.status === "sending" ? "chưa xác nhận hoàn tất" : "gửi lỗi hoặc chưa xác định giao thành công";
      return `[Trạng thái giao văn bản Zalo do hệ thống ghi nhận lúc ${new Date(pending.updatedAt).toISOString()}: ${status}; ${pending.confirmedParts}/${pending.totalParts} phần có xác nhận API. Nội dung có trong lịch sử không có nghĩa đã gửi thành công. Khi nói về kết quả này, phải báo đúng trạng thái; không nói người dùng đã nhận và không hỏi như thể đã gửi xong. Nếu cần gửi lại, chỉ gửi khi người dùng yêu cầu; không tự phát lại phần không rõ trạng thái. Xác nhận API không chứng minh người dùng đã đọc.]`;
    }
  };
}

const guard = createTextDeliveryGuard();
export const sendGuardedText = (params) => guard.send(params);
export const getTextDeliveryContext = (threadId, options) => guard.context(threadId, options);

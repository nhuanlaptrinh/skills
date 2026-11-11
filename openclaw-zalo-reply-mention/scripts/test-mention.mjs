import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { resolve, join } from "node:path";
import { pathToFileURL } from "node:url";

const [setupPath, chunkingPath] = process.argv.slice(2);
if (!setupPath || !chunkingPath) throw new Error("Usage: node test-mention.mjs <setup-dir> <text-chunking-module>");
const { chunkTextRanges } = await import(pathToFileURL(resolve(chunkingPath)).href);
const sendSource = readFileSync(join(setupPath, "send-B24acSlE.mjs"), "utf8");
const zaloSource = readFileSync(join(setupPath, "zalo-js-Bu9ojNUf.mjs"), "utf8");
const monitorSource = readFileSync(join(setupPath, "monitor-Cc1OOIE-.mjs"), "utf8");
const channelSource = readFileSync(join(setupPath, "channel-D90hoq2j.mjs"), "utf8");
const extract = (source, start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const sliceStyles = extract(zaloSource, "function sliceTextStyles(", "function resolveMediaFileName(");
const sliceStylesFunction = sliceStyles.slice(0, sliceStyles.indexOf("\n}") + 2);
const sent = [];
const context = {
  chunkTextRanges,
  ZALO_TEXT_LIMIT: 2000,
  TextStyle: { Indent: "indent" },
  parseZalouserTextStyles: (text) => ({ text, styles: [{ start: 0, len: text.length, st: "bold" }] }),
  sendZaloTextMessage: async (thread, text, options) => {
    sent.push({ thread, text, options });
    return { ok: true, receipt: { platformMessageIds: ["1"] } };
  },
  createZalouserSendReceipt: (receipt) => ({ ...receipt, platformMessageIds: [] }),
  createChannelPartialDeliveryError: (error) => error,
  createAcceptedChannelDeliveryResult: (value) => value,
};
vm.createContext(context);
vm.runInContext(`${sliceStylesFunction}\n${extract(sendSource, "async function sendMessageZalouser(", "async function sendImageZalouser(")}\n${extract(sendSource, "function splitStyledText(", "//#endregion\nexport")}`, context);
const send = context.sendMessageZalouser;

test("group reply uses native entity for current sender and shifts styles", async () => {
  sent.length = 0;
  await send("group", "Hello", { isGroup: true, textMode: "markdown", mentionTarget: { id: "123456789", name: "Tên 😀" } });
  assert.equal(sent[0].text, "@Tên 😀 Hello");
  assert.equal(sent[0].options.mentions[0].uid, "123456789");
  assert.equal(sent[0].options.mentions[0].len, "@Tên 😀".length);
  assert.equal(sent[0].options.textStyles[0].start, "@Tên 😀 ".length);
  assert.match(monitorSource, /isGroup,\s*senderId,\s*senderName,\s*runtime/);
  assert.match(monitorSource, /mentionTarget: \{ id: params\.senderId, name: params\.senderName \}/);
});

test("private chats and unverified identities do not get a fabricated mention", async () => {
  for (const options of [
    { isGroup: false, mentionTarget: { id: "123", name: "Name" } },
    { isGroup: true, mentionTarget: { id: "bad", name: "Name" } },
    { isGroup: true, mentionTarget: { id: "123" } },
  ]) {
    sent.length = 0;
    await send("chat", "Hello", options);
    assert.equal(sent[0].text, "Hello");
    assert.equal(sent[0].options.mentions, undefined);
  }
});

test("long names and preferred splitting retain one intact UTF-16 mention", async () => {
  sent.length = 0;
  await send("group", "Hi ".repeat(30), { isGroup: true, textChunkLimit: 20, textChunkMode: "newline", mentionTarget: { id: "888", name: "😀 A A A A A A A A A A A" } });
  const mention = sent[0].options.mentions[0];
  assert.equal(mention.uid, "888");
  assert.ok(sent[0].text.length >= mention.len);
  assert.ok(sent[0].text.slice(0, mention.len).startsWith("@😀"));
  assert.ok(sent.slice(1).every((entry) => entry.options.mentions === undefined));
});

test("native API receives mention metadata for text, image and audio only in groups", async () => {
  const calls = [];
  let mediaKind;
  const api = {
    sendMessage: async (...args) => { calls.push(args); return "id"; },
    uploadAttachment: async () => [{ fileType: "others", fileUrl: "voice" }],
    sendVoice: async () => "voice-id",
  };
  const nativeContext = {
    ThreadType: { Group: "group", User: "user" },
    loadOutboundMediaFromUrl: async () => ({ kind: mediaKind, buffer: Buffer.from("x"), fileName: "file.bin" }),
    fetchMediaWithZaloSendContext: () => {},
    resolveMediaFileName: () => "file.bin",
    hasAttachmentExtension: () => true,
    truncateUtf16Safe: (text, limit) => text.slice(0, limit),
    sliceTextStyles: () => undefined,
    extractSendMessageId: (id) => id,
    createZalouserSendReceipt: (receipt) => receipt,
    resolveUploadedVoiceUrl: () => "voice",
    formatErrorMessage: String,
  };
  vm.createContext(nativeContext);
  vm.runInContext(extract(zaloSource, "async function sendZaloTextWithApi(", "\n//#endregion"), nativeContext);
  for (const kind of ["text", "image", "audio", "private"]) {
    calls.length = 0;
    mediaKind = kind;
    const options = { isGroup: kind !== "private", mentions: [{ uid: "123", pos: 0, len: 4 }], ...(kind === "image" || kind === "audio" ? { mediaUrl: "test" } : {}) };
    const result = await nativeContext.sendZaloTextWithApi(api, "thread", "@abc hello", options);
    assert.equal(result.ok, true);
    if (kind === "private") assert.equal(calls[0][0], "@abc hello");
    else {
      assert.equal(calls[0][0].mentions[0].uid, "123");
      assert.equal(calls[0][0].mentions[0].pos, 0);
      assert.equal(calls[0][0].mentions[0].len, 4);
    }
  }
});

test("durable adapter carries only the current sender for the matching group and account", async () => {
  const delivered = [];
  const channelContext = {
    loadZalouserChannelRuntime$1: async () => ({ sendMessageZalouser: async (threadId, text, options) => {
      delivered.push({ threadId, text, options });
      return { receipt: { platformMessageIds: ["1"] } };
    } }),
    resolveZalouserAccountSync: ({ accountId }) => ({ accountId, profile: accountId }),
    parseZalouserOutboundTarget: (to) => ({ threadId: to.slice(2), isGroup: to.startsWith("g:") }),
    toZalouserMessageSendResult: (value) => value,
    getZalouserRuntime: () => ({ channel: { text: { resolveChunkMode: () => "hard", resolveTextChunkLimit: () => 2000 } } }),
    ZALOUSER_TEXT_CHUNK_LIMIT: 2000,
  };
  vm.createContext(channelContext);
  vm.runInContext(extract(channelSource, "async function sendZalouserFromContext(", "function adaptZalouserOutboundProgress("), channelContext);
  assert.match(monitorSource, /identity: \{ zalouserReplyMention: \{ id: senderId, name: senderName, threadId: chatId, accountId: account\.accountId \} \}/);
  const identity = JSON.parse(JSON.stringify({ zalouserReplyMention: { id: "123", name: "Người hỏi", threadId: "group1", accountId: "default" } }));
  for (const [to, accountId, expected] of [["g:group1", "default", true], ["g:other", "default", false], ["g:group1", "other", false], ["u:group1", "default", false]]) {
    delivered.length = 0;
    await channelContext.sendZalouserFromContext({ to, accountId, identity, cfg: {}, text: "Hello" });
    assert.equal(Boolean(delivered[0].options.mentionTarget), expected);
    if (expected) assert.equal(delivered[0].options.mentionTarget.id, "123");
  }
});

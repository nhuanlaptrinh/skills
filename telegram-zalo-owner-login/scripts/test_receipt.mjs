import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

const asset = process.env.OWNER_QR_ASSET ?? new URL("../assets/index.mjs", import.meta.url);
const source = readFileSync(asset, "utf8");
const ownerId = "123456789";
const receipt = { payload: { ok: true, chatId: ownerId, messageId: "synthetic-receipt" } };
const suffix = "[state/agent-db] agent database clean-close receipt: synthetic";

function fixture(output = JSON.stringify(receipt), outcomeCode = 0) {
  const settings = { runtimeRoot: "/mock-state", runtimeHome: "/mock-home", pluginId: "telegram-zalo-owner-login",
    telegramAccount: "fixture", zaloAccount: "default", agentId: "main" };
  const files = new Map();
  files.set("/mock-state/openclaw.json", JSON.stringify({ commands: { ownerAllowFrom: [ownerId] } }));
  const events = [];
  let clock = 100000;
  let deliveries = 0;
  let deliveryTimeout;
  let finishLogin;
  const login = {
    closed: false,
    output: `Scan QR image: ${path.join(os.tmpdir(), "openclaw", "openclaw-zalouser-qr-mock.png")}`,
    done: new Promise((resolve) => { finishLogin = resolve; }),
    stop() {
      events.push(this.closed ? "stop-after-close" : "stop-before-close");
      if (!this.closed) {
        this.closed = true;
        finishLogin({ code: -1, output: "" });
      }
    },
  };
  const cliStart = source.indexOf("function cliProcess(");
  const parserStart = source.indexOf("function parseReceipt(");
  assert.ok(cliStart >= 0 && parserStart > cliStart);
  const body = (source.slice(0, cliStart) + "const cliProcess = fakeCliProcess;\n" + source.slice(parserStart))
    .replace(/^import .*;\n/gm, "")
    .replace(/^const settings = .*;$/m, "const settings = fixtureSettings;")
    .replace(/export (?=(?:async )?function)/g, "")
    .replace("export default", "const plugin =");
  const plugin = vm.runInNewContext(body + "\n({ parseReceipt, loginAndSendQr, plugin });", {
    fixtureSettings: settings, path, os, Buffer, process: { pid: 101 }, randomUUID: () => "mock-lock",
    Date: { now: () => clock },
    mkdirSync() {}, chmodSync() {}, copyFileSync() {}, rmSync() {},
    mkdtempSync: (prefix) => prefix + "mock",
    lstatSync: () => ({ isSymbolicLink: () => false }),
    statSync: () => ({ size: 40, mtimeMs: 100000 }),
    writeFileSync: (destination, value) => files.set(destination, value),
    readFileSync: (destination) => files.get(destination) ?? Buffer.concat([
      Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), Buffer.alloc(32),
    ]),
    fakeCliProcess(argumentsList, options) {
      if (argumentsList[0] === "channels") return login;
      deliveries += 1;
      deliveryTimeout = options.timeoutMs;
      events.push("delivery");
      return { done: Promise.resolve({ code: 0, output }) };
    },
    setTimeout(callback, delay) {
      clock += delay;
      events.push("wait");
      if (clock >= 101000 && !login.closed) {
        events.push("login-close");
        login.closed = true;
        finishLogin({ code: outcomeCode, output: "" });
      }
      queueMicrotask(callback);
    },
  }, { filename: String(asset), timeout: 1000 });
  return { ...plugin, events, get deliveries() { return deliveries; }, get deliveryTimeout() { return deliveryTimeout; } };
}

for (const [name, output] of [
  ["single JSON", JSON.stringify(receipt)],
  ["pretty JSON", JSON.stringify(receipt, null, 2)],
  ["leading log", "startup log\n" + JSON.stringify(receipt)],
  ["trailing clean-close log", JSON.stringify(receipt) + "\n" + suffix],
  ["pretty JSON between logs", "startup\n" + JSON.stringify(receipt, null, 2) + "\n" + suffix],
  ["CRLF logs", "startup\r\n" + JSON.stringify(receipt, null, 2).replace(/\n/g, "\r\n") + "\r\n" + suffix],
  ["unrelated JSON before receipt", "{\"level\":\"info\"}\n" + JSON.stringify(receipt) + "\n" + suffix],
  ["malformed JSON line before receipt", "{not-json}\n" + JSON.stringify(receipt) + "\n" + suffix],
  ["top-level receipt", JSON.stringify(receipt.payload) + "\n" + suffix],
  ["wrong chat followed by valid receipt", JSON.stringify({ payload: { ...receipt.payload, chatId: "987654321" } }) + "\n" + JSON.stringify(receipt)],
]) {
  test("receipt accepts " + name, () => {
    assert.equal(fixture().parseReceipt(output, ownerId), "synthetic-receipt");
  });
}

for (const [name, output] of [
  ["wrong chat", JSON.stringify({ payload: { ...receipt.payload, chatId: "987654321" } })],
  ["missing message ID", JSON.stringify({ payload: { ok: true, chatId: ownerId } })],
  ["negative ack", JSON.stringify({ payload: { ...receipt.payload, ok: false } })],
  ["truncated JSON", JSON.stringify(receipt).slice(0, -1)],
  ["logs only", suffix],
]) {
  test("receipt rejects " + name, () => {
    assert.throws(() => fixture().parseReceipt(output, ownerId), /biên nhận/);
  });
}

test("trailing logs preserve confirmed receipt, 60-second delivery timeout and one send", async () => {
  const mock = fixture(JSON.stringify(receipt) + "\n" + suffix);
  const result = await mock.loginAndSendQr(ownerId, () => {});
  assert.equal(result.status, "login_completed");
  assert.equal(result.telegramMessageId, "synthetic-receipt");
  assert.equal(mock.deliveries, 1);
  assert.equal(mock.deliveryTimeout, 60000);
  assert.ok(mock.events.includes("login-close"));
  assert.ok(!mock.events.includes("stop-before-close"));
});

for (const outcomeCode of [0, 1]) {
  test("unreadable receipt keeps login alive until exit " + outcomeCode + " without retry or delivery claim", async () => {
    const mock = fixture(suffix, outcomeCode);
    const result = await mock.loginAndSendQr(ownerId, () => {});
    assert.equal(result.status, "qr_delivery_unconfirmed");
    assert.equal(result.qrSent, null);
    assert.equal(result.loginCompleted, outcomeCode === 0);
    assert.equal(result.telegramMessageId, undefined);
    assert.equal(mock.deliveries, 1);
    assert.ok(mock.events.indexOf("wait") > mock.events.indexOf("delivery"));
    assert.ok(mock.events.indexOf("stop-after-close") > mock.events.indexOf("login-close"));
    assert.ok(!mock.events.includes("stop-before-close"));
  });
}

test("registration still exposes owner-gated tool and zaloqr command without invoking them", () => {
  const mock = fixture();
  let tool;
  let command;
  mock.plugin.register({ registerTool(value) { tool = value; }, registerCommand(value) { command = value; } });
  assert.equal(command.name, "zaloqr");
  assert.equal(command.requireAuth, true);
  assert.equal(tool.contextVersion, 2);
  assert.equal(tool.create({ senderIsOwner: false, requesterSenderId: ownerId }), null);
  assert.equal(mock.deliveries, 0);
});

const helper = process.env.OWNER_QR_HELPER ?? new URL("../../openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs", import.meta.url);
const helperSource = readFileSync(helper, "utf8");
const helperFunctions = helperSource.slice(helperSource.indexOf("function runOfficialZaloLogin("), helperSource.indexOf("function sendTelegram("));

test("fallback helper extracts receipt between noisy log lines", () => {
  const output = "startup\n" + JSON.stringify({ channel: "telegram", payload: receipt.payload }) + "\n" + suffix;
  const parsed = vm.runInNewContext(helperFunctions + "\nparseTelegramReceipt;", {})(output, ownerId);
  assert.equal(parsed.payload.messageId, "synthetic-receipt");
});

test("fallback helper does not kill CLI for unconfirmed receipt and rejects only after login closes", async () => {
  const child = new EventEmitter();
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  let kills = 0;
  child.kill = () => { kills += 1; };
  const runLogin = vm.runInNewContext(helperFunctions + "\nrunOfficialZaloLogin;", {
    spawn: () => child, process: { env: {} },
    openClawCommand: (argumentsList) => ({ executable: "mock", args: argumentsList }),
    fs: { existsSync: () => true },
    stripAnsi: (value) => value, sanitizeLoginOutput: () => "synthetic",
    setTimeout() { return 1; }, clearTimeout() {},
  });
  let settled = false;
  const error = Object.assign(new Error("unconfirmed"), { deliveryUnconfirmed: true });
  const pending = runLogin("fixture", 180, () => { throw error; });
  const observed = pending.catch((result) => { settled = true; return result; });
  child.stdout.emit("data", "Scan QR image: /offline/mock.png\nLogin successful.\n");
  await Promise.resolve();
  assert.equal(kills, 0);
  assert.equal(settled, false);
  child.emit("close", 0);
  assert.equal(await observed, error);
  assert.equal(kills, 0);
});

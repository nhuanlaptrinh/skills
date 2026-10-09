import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, statSync, rmSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { SourceTextModule, SyntheticModule, createContext, runInNewContext } from "node:vm";
import { createTextDeliveryGuard, numericErrorCode, splitPlainText } from "./guard.mjs";

let deployment;
try { deployment = JSON.parse(readFileSync(new URL("./deployment.json", import.meta.url), "utf8")); } catch (error) { if (error.code !== "ENOENT") throw error; }

const fixtureText = "Dòng kiểm thử tiếng Việt 👨‍👩‍👧‍👦: 1.250.000 đồng.\n".repeat(100);
const accepted = (number = 1) => ({ ok: true, messageId: `test-${number}`, receipt: { platformMessageIds: [`test-${number}`] } });
const rejected = () => ({ ok: false, errorKind: "api_rejected", errorCode: 123, receipt: { platformMessageIds: [] } });
const ambiguous = () => ({ ok: false, errorKind: "unknown", errorCode: null, receipt: { platformMessageIds: [] } });

function harness(overrides = {}) {
  const entries = new Map();
  const logs = [];
  const delays = [];
  const calls = [];
  const guard = createTextDeliveryGuard({
    store: { read: (key) => entries.get(key), write: (key, value) => entries.set(key, value) },
    sleep: async (milliseconds) => { delays.push(milliseconds); },
    log: (value) => logs.push(value),
    ...overrides
  });
  const params = {
    threadId: "synthetic-destination",
    text: fixtureText,
    options: { profile: "default", isGroup: false, textStyles: [{ st: "b" }] },
    send: async (threadId, text, options) => { calls.push({ threadId, text, options }); return accepted(calls.length); },
    createReceipt: (value) => ({ platformMessageIds: value.platformMessageIds, threadId: value.threadId }),
    createPartialError: (error, details) => Object.assign(new Error("Partial delivery", { cause: error }), details, { partial: true })
  };
  return { guard, params, entries, logs, delays, calls };
}

test("numbered plain chunks preserve every character and remain <= 1000 UTF-16 units", () => {
  const parts = splitPlainText(fixtureText);
  assert(parts.length > 1);
  assert(parts.every((part) => part.length <= 1000));
  assert.equal(parts.map((part) => part.replace(/^\[\d+\/\d+\]\n/, "")).join(""), fixtureText);
  const boundaries = new Set([...new Intl.Segmenter("vi", { granularity: "grapheme" }).segment(fixtureText)].map((segment) => segment.index));
  let offset = 0;
  for (const part of parts.slice(0, -1)) {
    offset += part.replace(/^\[\d+\/\d+\]\n/, "").length;
    assert(boundaries.has(offset));
  }
});

test("empty, short, unbroken and custom-limit text is handled without truncation", () => {
  assert.deepEqual(splitPlainText(""), []);
  assert.deepEqual(splitPlainText("ngắn"), ["ngắn"]);
  assert.deepEqual(splitPlainText("a".repeat(1000)), ["a".repeat(1000)]);
  for (const text of ["a".repeat(4105), "🇻🇳".repeat(1500), "é".repeat(2100)]) {
    for (const limit of [64, 500, 1000, 2000]) {
      const parts = splitPlainText(text, limit);
      assert(parts.every((part) => part.length <= Math.min(limit, 1000)));
      assert.equal(parts.map((part) => part.replace(/^\[\d+\/\d+\]\n/, "")).join(""), text);
    }
  }
});

test("unsafe API codes are never emitted as metadata", () => {
  assert.equal(numericErrorCode("123"), 123);
  assert.equal(numericErrorCode("-1"), -1);
  assert.equal(numericErrorCode("private-token"), null);
  assert.equal(numericErrorCode(null), null);
  assert.equal(numericErrorCode("123456789"), null);
});

test("all text parts are plain, acknowledged, numbered and delayed", async () => {
  const fixture = harness();
  const acknowledgements = [];
  await fixture.guard.send({ ...fixture.params, onDeliveryResult: (result) => acknowledgements.push(result.messageId) });
  assert.equal(acknowledgements.length, fixture.calls.length);
  assert(fixture.calls.every((call) => call.text.length <= 1000 && call.options.textMode === "plain" && call.options.textStyles === undefined));
  assert.equal(fixture.delays.length, fixture.calls.length - 1);
  assert(fixture.delays.every((delay) => delay === 600));
  assert.equal([...fixture.entries.values()][0].current.status, "confirmed");
  assert.equal(fixture.guard.context(fixture.params.threadId), "");
  assert(!JSON.stringify(fixture.logs).includes(fixture.params.threadId));
  assert(!JSON.stringify([...fixture.entries.values()]).includes("Dòng kiểm thử"));
});

test("only explicit server rejection is retried, at most twice", async () => {
  const fixture = harness();
  let attempts = 0;
  await fixture.guard.send({ ...fixture.params, text: "short", send: async () => ++attempts === 1 ? rejected() : accepted() });
  assert.equal(attempts, 2);
  assert.deepEqual(fixture.delays, [900]);
  attempts = 0;
  await assert.rejects(fixture.guard.send({ ...fixture.params, text: "short", send: async () => { attempts += 1; return rejected(); } }), /api_rejected; code=123/);
  assert.equal(attempts, 2);
  assert.equal([...fixture.entries.values()][0].current.status, "rejected");
});

test("unknown result, timeout and missing receipt never trigger blind retry", async () => {
  for (const behavior of [async () => ambiguous(), async () => ({ ok: true }), async () => { throw new Error("synthetic timeout"); }]) {
    const fixture = harness();
    let attempts = 0;
    await assert.rejects(fixture.guard.send({ ...fixture.params, text: "short", send: async () => { attempts += 1; return behavior(); } }));
    assert.equal(attempts, 1);
    assert.equal([...fixture.entries.values()][0].current.status, "unknown");
    assert.match(fixture.guard.context(fixture.params.threadId), /0\/1 phần/);
  }
});

test("a receipt on a failed result prevents retry and preserves partial delivery", async () => {
  const fixture = harness();
  let attempts = 0;
  const error = await fixture.guard.send({ ...fixture.params, send: async () => { attempts += 1; return { ...rejected(), receipt: { platformMessageIds: ["test-partial"] } }; } }).catch((failure) => failure);
  assert.equal(attempts, 1);
  assert.equal(error.partial, true);
  assert.deepEqual(error.messageIds, ["test-partial"]);
});

test("a later failed part stops the sequence without resending earlier parts", async () => {
  const fixture = harness();
  let attempts = 0;
  const error = await fixture.guard.send({ ...fixture.params, send: async () => ++attempts === 1 ? accepted() : ambiguous() }).catch((failure) => failure);
  assert.equal(attempts, 2);
  assert.equal(error.partial, true);
  assert.deepEqual(error.messageIds, ["test-1"]);
  const state = [...fixture.entries.values()][0].current;
  assert.equal(state.confirmedParts, 1);
  assert.equal(state.status, "partial");
});

test("the next part waits for the actual platform acknowledgement", async () => {
  const fixture = harness();
  let release;
  const first = new Promise((resolve) => { release = resolve; });
  let attempts = 0;
  const task = fixture.guard.send({ ...fixture.params, send: async () => ++attempts === 1 ? first : accepted(attempts) });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(attempts, 1);
  release(accepted());
  await task;
  assert.equal(attempts, splitPlainText(fixtureText).length);
});

test("same-destination replies serialize and failed lanes do not block later replies", async () => {
  const fixture = harness();
  const order = [];
  await Promise.all([
    fixture.guard.send({ ...fixture.params, text: "first", send: async () => { order.push("first"); throw new Error("synthetic"); } }).catch(() => {}),
    fixture.guard.send({ ...fixture.params, text: "second", send: async () => { order.push("second"); return accepted(); } })
  ]);
  assert.deepEqual(order, ["first", "second"]);
  assert.match(fixture.guard.context(fixture.params.threadId), /gửi lỗi/);
});

test("failure context stays separate for profiles and direct/group targets", async () => {
  const fixture = harness();
  await fixture.guard.send({ ...fixture.params, text: "failure", send: async () => ambiguous() }).catch(() => {});
  assert.match(fixture.guard.context(fixture.params.threadId), /không nói người dùng đã nhận/);
  assert.equal(fixture.guard.context(fixture.params.threadId, { isGroup: true }), "");
  assert.equal(fixture.guard.context(fixture.params.threadId, { profile: "other" }), "");
  assert.equal(fixture.guard.context("other-destination"), "");
  await fixture.guard.send({ ...fixture.params, text: "failure" });
  assert.equal(fixture.guard.context(fixture.params.threadId), "");
});

test("private delivery metadata persists atomically and survives a fresh guard", async () => {
  const directory = mkdtempSync(join(tmpdir(), "zalo-guard-test-"));
  try {
    const statePath = join(directory, "state.json");
    const fixture = harness({ store: undefined, statePath });
    await fixture.guard.send({ ...fixture.params, text: "synthetic-private-content", send: async () => ambiguous() }).catch(() => {});
    const raw = readFileSync(statePath, "utf8");
    assert(!raw.includes(fixture.params.threadId));
    assert(!raw.includes("synthetic-private-content"));
    assert.equal(statSync(statePath).mode & 0o777, 0o600);
    const fresh = createTextDeliveryGuard({ statePath, log: () => {} });
    assert.match(fresh.context(fixture.params.threadId), /gửi lỗi/);
    assert.equal(JSON.parse(raw).version, 1);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("active plugin integration uses plain numbered text but leaves media sends unchanged", { skip: !deployment }, async () => {
  const base = deployment.pluginSetup;
  const file = deployment.sources.send;
  const resolve = createRequire(join(base, deployment.files.send));
  const fixture = harness();
  const context = createContext({ console, Buffer });
  const module = new SourceTextModule(`${readFileSync(file, "utf8")}\nexport { preparePlainZalouserText };`, { context, identifier: pathToFileURL(file).href });
  await module.link(async (specifier) => {
    let namespace;
    if (specifier.endsWith("/zalo-text-delivery-guard/guard.mjs")) namespace = { sendGuardedText: (params) => fixture.guard.send(params) };
    else {
      const path = specifier.startsWith(".") ? join(base, specifier) : specifier.startsWith("node:") ? specifier : resolve.resolve(specifier);
      namespace = { ...await import(path.startsWith("node:") ? path : pathToFileURL(path).href) };
      if (specifier.startsWith("./zalo-js-")) namespace.v = fixture.params.send;
    }
    const names = Object.keys(namespace);
    return new SyntheticModule(names, function () { for (const name of names) this.setExport(name, namespace[name]); }, { context });
  });
  await module.evaluate();
  let originalText = `**OCR**\n${fixtureText}`;
  if (process.env.ZALO_GUARD_FIXTURE_STDIN === "1") {
    originalText = "";
    for await (const data of process.stdin) originalText += data.toString();
  }
  const expectedText = module.namespace.preparePlainZalouserText(originalText);
  await module.namespace.n("synthetic-destination", originalText, { textMode: "markdown", profile: "default" });
  assert(fixture.calls.every((call) => call.text.length <= 1000 && call.options.textStyles === undefined));
  assert(fixture.calls.map((call) => call.text.replace(/^\[\d+\/\d+\]\n/, "")).join("") === expectedText, "Every prepared character must survive chunking");
  assert(!fixture.calls.map((call) => call.text).join("").includes("**OCR**"));
  if (process.env.ZALO_GUARD_FIXTURE_STDIN === "1") console.info(`Saved reply offline regression: inputChars=${originalText.length} plainChars=${expectedText.length} parts=${fixture.calls.length} largestPart=${Math.max(...fixture.calls.map((call) => call.text.length))}`);
  const beforeMedia = fixture.calls.length;
  await module.namespace.n("synthetic-destination", "caption", { mediaUrl: "synthetic-media", textMode: "markdown" });
  assert.equal(fixture.calls.length, beforeMedia + 1);
  assert.equal(fixture.calls.at(-1).options.mediaUrl, "synthetic-media");
  assert.equal(fixture.calls.at(-1).text, "caption");
  const structural = module.namespace.preparePlainZalouserText("**OCR**\n- apple\n1. first\n2. second\n[reference](https://example.com)");
  assert(structural.includes("1. first"));
  assert(structural.includes("2. second"));
  assert(structural.includes("apple"));
  assert(structural.includes("https://example.com"));
  assert(!structural.includes("**OCR**"));
  const monitor = readFileSync(deployment.sources.monitor, "utf8");
  assert(monitor.includes('bodyForAgent: textDeliveryContext ? `${rawBody}\\n\\n${textDeliveryContext}` : rawBody'));
  const lowLevel = readFileSync(deployment.sources.low, "utf8");
  assert(lowLevel.includes("const LISTENER_WATCHDOG_MAX_GAP_MS = 180e3;"));
  assert(lowLevel.includes('error?.name === "ZcaApiError"'));
});

test("the local watchdog tolerates measured short stalls but still reconnects after 180 seconds", { skip: !deployment }, () => {
  const file = deployment.sources.low;
  const source = readFileSync(file, "utf8");
  const watchdog = source.match(/const watchdogTimer = setInterval\(\(\) => \{[\s\S]*?\}, LISTENER_WATCHDOG_INTERVAL_MS\);/)[0];
  const failures = [];
  let tick;
  let now = 0;
  runInNewContext(`let lastWatchdogTickAt = 0; const LISTENER_WATCHDOG_INTERVAL_MS = 30000; ${source.match(/const LISTENER_WATCHDOG_MAX_GAP_MS = [^;]+;/)[0]} ${watchdog}`, {
    Date: { now: () => now },
    setInterval: (callback) => { tick = callback; return {}; },
    failListener: (error) => failures.push(error)
  });
  for (const gap of [43000, 66000, 95000, 180000]) { now += gap; tick(); }
  assert.equal(failures.length, 0);
  now += 181000;
  tick();
  assert.equal(failures.length, 1);
  assert.match(failures[0].message, /forcing reconnect/);
});

test("native inbound finalization preserves the failure note without changing commands or raw text", { skip: !deployment }, async () => {
  const fixture = harness();
  await fixture.guard.send({ ...fixture.params, text: "synthetic failed reply", send: async () => ambiguous() }).catch(() => {});
  const note = fixture.guard.context(fixture.params.threadId);
  const candidates = readdirSync(deployment.coreDist).filter((name) => /^inbound-context-.*\.mjs$/.test(name) && readFileSync(join(deployment.coreDist, name), "utf8").includes("function finalizeInboundContext("));
  assert(candidates.length > 0);
  for (const candidate of candidates) {
    const file = join(deployment.coreDist, candidate);
    const alias = readFileSync(file, "utf8").match(/finalizeInboundContext as ([a-zA-Z_][\w]*)/);
    assert(alias, "Native finalizer export must be explicit");
    const namespace = await import(pathToFileURL(file).href);
    const context = namespace[alias[1]]({
      Body: "synthetic envelope",
      BodyForAgent: `synthetic user input\n\n${note}`,
      RawBody: "synthetic user input",
      CommandBody: "synthetic user input",
      BodyForCommands: "synthetic user input",
      ChatType: "direct",
      Provider: "zalouser"
    });
    assert(context.agentText.includes(note));
    assert.equal(context.rawText, "synthetic user input");
    assert.equal(context.commandText, "synthetic user input");
  }
});

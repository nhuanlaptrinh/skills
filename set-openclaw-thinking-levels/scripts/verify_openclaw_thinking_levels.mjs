#!/usr/bin/env node

import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const LEVELS = ["off", "minimal", "low", "medium", "high", "xhigh"];

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") options.help = true;
    else if (arg === "--agent" || arg === "--config") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) fail(`Missing value for ${arg}`);
      index += 1;
      options[arg === "--agent" ? "agentId" : "configPath"] = value;
    } else fail(`Unknown argument: ${arg}`);
  }
  return options;
}

function redact(value) {
  return String(value || "")
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, "sk-REDACTED")
    .replace(/(botToken|apiKey|token)\s*[:=]\s*\S+/gi, "$1=REDACTED");
}

function parseJsonOutput(stdout) {
  const firstBrace = stdout.indexOf("{");
  if (firstBrace < 0) throw new Error("OpenClaw returned no JSON object");
  return JSON.parse(stdout.slice(firstBrace));
}

const options = parseArgs(process.argv.slice(2));
if (options.help) {
  console.log(`Usage:
  node verify_openclaw_thinking_levels.mjs --agent <id> [--config <path>]

Runs isolated, non-delivered diagnostics for:
  off minimal low medium high xhigh
`);
  process.exit(0);
}
if (!options.agentId) fail("--agent is required");

const configPath = path.resolve(
  options.configPath || process.env.OPENCLAW_CONFIG_PATH || path.join(os.homedir(), ".openclaw", "openclaw.json"),
);
const runStamp = Date.now();
let failures = 0;

for (const level of LEVELS) {
  const result = spawnSync(
    "openclaw",
    [
      "agent",
      "--agent",
      options.agentId,
      "--session-key",
      `diagnostic:thinking-levels:${runStamp}:${level}`,
      "--thinking",
      level,
      "--message",
      "Reply exactly: LEVEL_OK",
      "--json",
    ],
    {
      encoding: "utf8",
      timeout: 180000,
      env: { ...process.env, OPENCLAW_CONFIG_PATH: configPath },
    },
  );

  if (result.error || result.status !== 0) {
    failures += 1;
    const details = redact(result.stderr || result.stdout || result.error?.message).trim().split("\n")[0];
    console.log(`FAIL ${level}: ${details || "unknown error"}`);
    continue;
  }

  try {
    const body = parseJsonOutput(result.stdout);
    const payloadText = Array.isArray(body?.result?.payloads)
      ? body.result.payloads.map((payload) => payload?.text || "").join(" ").trim()
      : "";
    const meta = body?.result?.meta || {};
    const provider = meta?.agentMeta?.provider || meta?.executionTrace?.winnerProvider || "unknown";
    const model = meta?.agentMeta?.model || meta?.executionTrace?.winnerModel || "unknown";
    const shapedThinking = meta?.requestShaping?.thinking || "unset";
    const ok = body?.status === "ok" && payloadText.includes("LEVEL_OK");
    if (!ok) failures += 1;
    console.log(`${ok ? "OK" : "FAIL"} ${level}: thinking=${shapedThinking} provider=${provider} model=${model}`);
  } catch (error) {
    failures += 1;
    console.log(`FAIL ${level}: ${redact(error.message)}`);
  }
}

if (failures > 0) fail(`${failures}/${LEVELS.length} thinking level checks failed`);
console.log(`ALL OK: ${LEVELS.join(", ")}`);


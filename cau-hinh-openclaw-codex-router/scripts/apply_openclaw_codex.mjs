#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function fail(message) {
  console.error(`Error: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      fail(`Unexpected argument: ${token}`);
    }
    const equalsIndex = token.indexOf("=");
    if (equalsIndex !== -1) {
      options[token.slice(2, equalsIndex)] = token.slice(equalsIndex + 1);
      continue;
    }
    const name = token.slice(2);
    if (name === "apply" || name === "dry-run") {
      options[name] = true;
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      fail(`Missing value for --${name}`);
    }
    options[name] = value;
    index += 1;
  }
  return options;
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`Cannot read valid JSON from ${filePath}: ${error.message}`);
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeBaseUrl(value) {
  return String(value).replace(/\/+$/, "");
}

function timestamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return [
    now.getUTCFullYear(),
    pad(now.getUTCMonth() + 1),
    pad(now.getUTCDate()),
  ].join("") + "-" + [
    pad(now.getUTCHours()),
    pad(now.getUTCMinutes()),
    pad(now.getUTCSeconds()),
  ].join("");
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function collectAgentCaches(config, configPath) {
  const paths = new Set();
  const configDir = path.dirname(configPath);
  const listedAgents = config?.agents?.list ?? [];
  for (const agent of listedAgents) {
    if (agent?.agentDir) {
      paths.add(path.resolve(agent.agentDir, "models.json"));
    }
  }
  const agentsDir = path.join(configDir, "agents");
  if (fs.existsSync(agentsDir)) {
    for (const entry of fs.readdirSync(agentsDir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        paths.add(path.join(agentsDir, entry.name, "agent", "models.json"));
      }
    }
  }
  return [...paths].filter((filePath) => fs.existsSync(filePath));
}

function buildModelEntry(existing, modelId, contextWindow, maxTokens) {
  return {
    ...(existing ?? {}),
    id: modelId,
    name: modelId,
    input: ["text", "image"],
    maxTokens,
    reasoning: false,
    cost: {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
    },
    contextWindow,
    api: "openai-completions",
  };
}

const options = parseArgs(process.argv.slice(2));
if (options.apply && options["dry-run"]) {
  fail("Use either --apply or --dry-run, not both");
}

const provider = String(options.provider ?? "codex-router");
if (provider === "codex") {
  fail("Provider name codex is reserved by the OpenClaw Codex plugin; use codex-router");
}

const configPath = path.resolve(
  String(options.config ?? process.env.OPENCLAW_CONFIG ?? path.join(os.homedir(), ".openclaw", "openclaw.json")),
);
if (!fs.existsSync(configPath)) {
  fail(`OpenClaw config not found: ${configPath}`);
}

const baseUrl = normalizeBaseUrl(options["base-url"] ?? "https://codex.anhlaptrinh.vn/v1");
const modelId = String(options.model ?? "GPT-6.1-sol");
const contextWindow = Number(options["context-window"] ?? 128000);
const maxTokens = Number(options["max-tokens"] ?? 4096);
if (!Number.isInteger(contextWindow) || contextWindow <= 0) {
  fail("--context-window must be a positive integer");
}
if (!Number.isInteger(maxTokens) || maxTokens <= 0) {
  fail("--max-tokens must be a positive integer");
}

const keyEnv = String(options["api-key-env"] ?? "CODEX_API_KEY");
const apiKey = process.env[keyEnv] || (keyEnv !== "OPENAI_API_KEY" ? process.env.OPENAI_API_KEY : "");
const config = readJson(configPath);
const agentCaches = collectAgentCaches(config, configPath);
const existingProvider = config?.models?.providers?.[provider] ?? {};
const existingModel = Array.isArray(existingProvider.models)
  ? existingProvider.models.find((entry) => entry?.id === modelId)
  : undefined;
const modelEntry = buildModelEntry(existingModel, modelId, contextWindow, maxTokens);
const providerSpec = {
  ...clone(existingProvider),
  baseUrl,
  apiKey: apiKey || existingProvider.apiKey || "",
  api: "openai-completions",
  models: [
    ...(Array.isArray(existingProvider.models)
      ? existingProvider.models.filter((entry) => entry?.id !== modelId)
      : []),
    modelEntry,
  ],
};
const modelRef = `${provider}/${modelId}`;

console.log(`Config: ${configPath}`);
console.log(`Provider: ${provider}`);
console.log(`Base URL: ${baseUrl}`);
console.log(`Model: ${modelRef}`);
console.log(`API key: ${apiKey || existingProvider.apiKey ? "present" : "missing"}`);
console.log(`Agent caches: ${agentCaches.length}`);

if (!options.apply) {
  console.log("Dry run only; no files changed. Use --apply after review.");
  process.exit(0);
}
if (!apiKey && !existingProvider.apiKey) {
  fail(`Missing API key in ${keyEnv}; set it in the environment before --apply`);
}

const backupDir = path.join(path.dirname(configPath), "backups", `codex-router-${timestamp()}`);
fs.mkdirSync(backupDir, { recursive: true });
fs.copyFileSync(configPath, path.join(backupDir, "openclaw.json"));
for (const cachePath of agentCaches) {
  const label = path.basename(path.dirname(path.dirname(cachePath)));
  fs.copyFileSync(cachePath, path.join(backupDir, `${label}-models.json`));
}

config.models ??= {};
config.models.providers ??= {};
config.models.providers[provider] = providerSpec;
config.agents ??= {};
config.agents.defaults ??= {};
config.agents.defaults.model ??= {};
config.agents.defaults.model.primary = modelRef;
config.agents.defaults.models ??= {};
config.agents.defaults.models[modelRef] ??= {};
writeJson(configPath, config);

for (const cachePath of agentCaches) {
  const cache = readJson(cachePath);
  cache.providers ??= {};
  cache.providers[provider] = clone(providerSpec);
  writeJson(cachePath, cache);
}

console.log(`Applied. Backup: ${backupDir}`);
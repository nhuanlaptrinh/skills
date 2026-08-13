#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const SUPPORTED_LEVELS = ["low", "medium", "high", "xhigh"];
const DEFAULT_LEVELS = new Set(["off", "minimal", ...SUPPORTED_LEVELS]);

function fail(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function printHelp() {
  console.log(`Usage:
  node set_openclaw_thinking_levels.mjs --agent <id> [options]
  node set_openclaw_thinking_levels.mjs --all-agents --provider <id> --model <id> [options]
  node set_openclaw_thinking_levels.mjs --provider <id> --model <id> [options]

Options:
  --config <path>       Active openclaw.json path
  --agent <id>          Update one agent and its local model catalog
  --all-agents          Update matching agents and their local catalogs
  --provider <id>       Provider id; use together with --model
  --model <id>          Model id; use together with --provider
  --default <level>     Set thinkingDefault: off|minimal|low|medium|high|xhigh
  --backup-dir <path>   Backup root directory
  --dry-run             Show intended changes without writing
  --no-restart          Do not restart the OpenClaw Gateway
  --help                Show this help
`);
}

function parseArgs(argv) {
  const options = {
    dryRun: false,
    restart: true,
    allAgents: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--dry-run") options.dryRun = true;
    else if (arg === "--no-restart") options.restart = false;
    else if (arg === "--all-agents") options.allAgents = true;
    else if (arg === "--help" || arg === "-h") options.help = true;
    else if (["--config", "--agent", "--provider", "--model", "--default", "--backup-dir"].includes(arg)) {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) fail(`Missing value for ${arg}`);
      index += 1;
      const key = {
        "--config": "configPath",
        "--agent": "agentId",
        "--provider": "provider",
        "--model": "model",
        "--default": "defaultLevel",
        "--backup-dir": "backupRoot",
      }[arg];
      options[key] = value;
    } else {
      fail(`Unknown argument: ${arg}`);
    }
  }
  return options;
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`Cannot parse JSON ${filePath}: ${error.message}`);
  }
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function primaryModel(modelValue) {
  if (typeof modelValue === "string") return modelValue.trim();
  if (modelValue && typeof modelValue === "object" && typeof modelValue.primary === "string") {
    return modelValue.primary.trim();
  }
  return "";
}

function splitModelRef(modelRef) {
  const separator = modelRef.indexOf("/");
  if (separator <= 0 || separator === modelRef.length - 1) {
    fail(`Model reference must be provider/model, received: ${modelRef || "<empty>"}`);
  }
  return {
    provider: modelRef.slice(0, separator),
    model: modelRef.slice(separator + 1),
  };
}

function sameValue(left, right) {
  return left.toLowerCase() === right.toLowerCase();
}

function effectiveAgentModel(config, agent) {
  return primaryModel(agent?.model) || primaryModel(config?.agents?.defaults?.model);
}

function findProvider(providers, providerId, sourcePath) {
  if (!providers || typeof providers !== "object" || Array.isArray(providers)) {
    fail(`Provider catalog is missing in ${sourcePath}`);
  }
  const providerKey = Object.keys(providers).find((key) => sameValue(key, providerId));
  if (!providerKey) fail(`Provider ${providerId} not found in ${sourcePath}`);
  return { key: providerKey, value: providers[providerKey] };
}

function updateCatalogRoot(root, providerId, modelId, sourcePath, isMainConfig) {
  const providers = isMainConfig ? root?.models?.providers : root?.providers;
  const provider = findProvider(providers, providerId, sourcePath);
  if (!Array.isArray(provider.value?.models)) {
    fail(`Provider ${provider.key} has no models array in ${sourcePath}`);
  }
  const model = provider.value.models.find(
    (candidate) => typeof candidate?.id === "string" && sameValue(candidate.id, modelId),
  );
  if (!model) fail(`Model ${modelId} not found under provider ${provider.key} in ${sourcePath}`);

  model.reasoning = true;
  const compat = model.compat && typeof model.compat === "object" && !Array.isArray(model.compat)
    ? model.compat
    : {};
  compat.supportedReasoningEfforts = [...SUPPORTED_LEVELS];
  compat.reasoningEffortMap = {
    ...(compat.reasoningEffortMap && typeof compat.reasoningEffortMap === "object"
      ? compat.reasoningEffortMap
      : {}),
    minimal: "low",
  };
  model.compat = compat;
}

function ensureAgent(config, agentId) {
  const agents = Array.isArray(config?.agents?.list) ? config.agents.list : [];
  const agent = agents.find((candidate) => candidate?.id === agentId);
  if (!agent) fail(`Agent ${agentId} not found in openclaw.json`);
  return agent;
}

function resolveTarget(config, options) {
  if ((options.provider && !options.model) || (!options.provider && options.model)) {
    fail("Use --provider and --model together");
  }
  if (options.agentId && options.allAgents) fail("Use either --agent or --all-agents, not both");

  if (options.provider && options.model) {
    return { provider: options.provider, model: options.model };
  }
  if (options.allAgents) fail("--all-agents requires --provider and --model");

  const modelRef = options.agentId
    ? effectiveAgentModel(config, ensureAgent(config, options.agentId))
    : primaryModel(config?.agents?.defaults?.model);
  return splitModelRef(modelRef);
}

function selectAgents(config, options, target) {
  const agents = Array.isArray(config?.agents?.list) ? config.agents.list : [];
  if (options.agentId) return [ensureAgent(config, options.agentId)];
  if (!options.allAgents) return [];

  return agents.filter((agent) => {
    const modelRef = effectiveAgentModel(config, agent);
    if (!modelRef.includes("/")) return false;
    const resolved = splitModelRef(modelRef);
    return sameValue(resolved.provider, target.provider) && sameValue(resolved.model, target.model);
  });
}

function defaultBackupRoot(homeDir) {
  const stateRoot = process.env.XDG_STATE_HOME || path.join(homeDir, ".local", "state");
  return path.join(stateRoot, "set-openclaw-thinking-levels", "backups");
}

function timestamp() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function backupFile(sourcePath, destinationPath) {
  fs.mkdirSync(path.dirname(destinationPath), { recursive: true, mode: 0o700 });
  fs.copyFileSync(sourcePath, destinationPath);
  fs.chmodSync(destinationPath, fs.statSync(sourcePath).mode & 0o777);
}

function writeJsonAtomic(filePath, data) {
  const sourceMode = fs.statSync(filePath).mode & 0o777;
  const tempPath = path.join(path.dirname(filePath), `.${path.basename(filePath)}.thinking-${process.pid}.tmp`);
  fs.writeFileSync(tempPath, `${JSON.stringify(data, null, 2)}\n`, { mode: sourceMode });
  fs.chmodSync(tempPath, sourceMode);
  fs.renameSync(tempPath, filePath);
}

function redactedText(value) {
  return String(value || "")
    .replace(/sk-[A-Za-z0-9_-]{8,}/g, "sk-REDACTED")
    .replace(/(botToken|apiKey|token)\s*[:=]\s*\S+/gi, "$1=REDACTED");
}

function runOpenClaw(args, configPath) {
  return spawnSync("openclaw", args, {
    encoding: "utf8",
    env: { ...process.env, OPENCLAW_CONFIG_PATH: configPath },
  });
}

function restoreFiles(backups) {
  for (const item of backups) {
    fs.copyFileSync(item.backupPath, item.sourcePath);
    fs.chmodSync(item.sourcePath, item.mode);
  }
}

const options = parseArgs(process.argv.slice(2));
if (options.help) {
  printHelp();
  process.exit(0);
}

if (options.defaultLevel && !DEFAULT_LEVELS.has(options.defaultLevel)) {
  fail(`Invalid --default level: ${options.defaultLevel}`);
}

const homeDir = os.homedir();
const configPath = path.resolve(
  options.configPath || process.env.OPENCLAW_CONFIG_PATH || path.join(homeDir, ".openclaw", "openclaw.json"),
);
if (!fs.existsSync(configPath)) fail(`Config not found: ${configPath}`);

const originalConfig = readJson(configPath);
const updatedConfig = cloneJson(originalConfig);
const target = resolveTarget(updatedConfig, options);
const selectedAgents = selectAgents(updatedConfig, options, target);

if (options.agentId) {
  const agentRef = effectiveAgentModel(updatedConfig, selectedAgents[0]);
  const resolvedAgentRef = splitModelRef(agentRef);
  if (!sameValue(resolvedAgentRef.provider, target.provider) || !sameValue(resolvedAgentRef.model, target.model)) {
    fail(`Agent ${options.agentId} uses ${agentRef}, not ${target.provider}/${target.model}`);
  }
}
if (options.allAgents && selectedAgents.length === 0) {
  fail(`No agents use ${target.provider}/${target.model}`);
}

updateCatalogRoot(updatedConfig, target.provider, target.model, configPath, true);
if (options.defaultLevel) {
  if (selectedAgents.length > 0) {
    for (const agent of selectedAgents) agent.thinkingDefault = options.defaultLevel;
  } else {
    updatedConfig.agents = updatedConfig.agents || {};
    updatedConfig.agents.defaults = updatedConfig.agents.defaults || {};
    updatedConfig.agents.defaults.thinkingDefault = options.defaultLevel;
  }
}

const fileChanges = [];
if (JSON.stringify(originalConfig) !== JSON.stringify(updatedConfig)) {
  fileChanges.push({ sourcePath: configPath, original: originalConfig, updated: updatedConfig, label: "openclaw.json" });
}

const configDir = path.dirname(configPath);
for (const agent of selectedAgents) {
  const catalogPath = path.join(configDir, "agents", agent.id, "agent", "models.json");
  if (!fs.existsSync(catalogPath)) {
    console.log(`INFO: Agent catalog not found, main config only: ${catalogPath}`);
    continue;
  }
  const originalCatalog = readJson(catalogPath);
  const updatedCatalog = cloneJson(originalCatalog);
  updateCatalogRoot(updatedCatalog, target.provider, target.model, catalogPath, false);
  if (JSON.stringify(originalCatalog) !== JSON.stringify(updatedCatalog)) {
    fileChanges.push({
      sourcePath: catalogPath,
      original: originalCatalog,
      updated: updatedCatalog,
      label: `agent-${agent.id}-models.json`,
    });
  }
}

console.log(`Config: ${configPath}`);
console.log(`Target: ${target.provider}/${target.model}`);
console.log(`Agents: ${selectedAgents.map((agent) => agent.id).join(", ") || "main catalog only"}`);
console.log(`Levels: off, minimal->low, ${SUPPORTED_LEVELS.join(", ")}`);

if (fileChanges.length === 0) {
  console.log("OK: Configuration is already up to date.");
  process.exit(0);
}

for (const change of fileChanges) console.log(`${options.dryRun ? "WOULD UPDATE" : "UPDATE"}: ${change.sourcePath}`);
if (options.dryRun) {
  console.log("DRY-RUN OK: No files were changed.");
  process.exit(0);
}

const backupRoot = path.resolve(options.backupRoot || process.env.OPENCLAW_THINKING_BACKUP_DIR || defaultBackupRoot(homeDir));
const backupDir = path.join(backupRoot, `set-openclaw-thinking-levels-${timestamp()}`);
const backups = [];

try {
  fs.mkdirSync(backupDir, { recursive: true, mode: 0o700 });
  for (const change of fileChanges) {
    const backupPath = path.join(backupDir, change.label);
    const mode = fs.statSync(change.sourcePath).mode & 0o777;
    backupFile(change.sourcePath, backupPath);
    backups.push({ sourcePath: change.sourcePath, backupPath, mode });
    writeJsonAtomic(change.sourcePath, change.updated);
  }
} catch (error) {
  if (backups.length > 0) restoreFiles(backups);
  fail(`Write failed; restored available backups: ${error.message}`);
}

const validation = runOpenClaw(["config", "validate"], configPath);
if (validation.error || validation.status !== 0) {
  restoreFiles(backups);
  const details = redactedText(validation.stderr || validation.stdout || validation.error?.message);
  fail(`Validation failed; configuration restored. ${details.trim()}`);
}

console.log(`Backup: ${backupDir}`);
console.log("VALIDATION OK");

if (!options.restart) {
  console.log("DONE: Gateway restart skipped by --no-restart.");
  process.exit(0);
}

const restart = runOpenClaw(["gateway", "restart"], configPath);
if (restart.error || restart.status !== 0) {
  const details = redactedText(restart.stderr || restart.stdout || restart.error?.message);
  fail(`Config is valid but Gateway restart failed: ${details.trim()}`);
}

const status = runOpenClaw(["gateway", "status"], configPath);
if (status.error || status.status !== 0) {
  const details = redactedText(status.stderr || status.stdout || status.error?.message);
  fail(`Gateway restart completed but status check failed: ${details.trim()}`);
}

console.log("GATEWAY OK");
console.log("DONE: Thinking levels are configured.");


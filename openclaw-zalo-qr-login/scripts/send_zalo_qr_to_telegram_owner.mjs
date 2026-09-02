#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

function fail(message) {
  throw new Error(message);
}

function parseArgs(argv) {
  const options = {
    accountId: "default",
    timeoutSeconds: 180,
    apply: false,
    dryRun: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--target") {
      options.target = argv[++index];
    } else if (arg === "--account") {
      options.accountId = argv[++index];
    } else if (arg === "--timeout-seconds") {
      options.timeoutSeconds = Number(argv[++index]);
    } else if (arg === "--apply") {
      options.apply = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else {
      fail(`Unknown argument: ${arg}`);
    }
  }

  if (!/^\d+$/.test(options.target ?? "")) {
    fail("--target must be a numeric Telegram user ID");
  }
  if (!/^[A-Za-z0-9_-]+$/.test(options.accountId)) {
    fail("--account contains unsupported characters");
  }
  if (!Number.isInteger(options.timeoutSeconds) || options.timeoutSeconds < 30 || options.timeoutSeconds > 300) {
    fail("--timeout-seconds must be an integer from 30 to 300");
  }
  if (options.apply === options.dryRun) {
    fail("Choose exactly one mode: --dry-run or --apply");
  }

  return options;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function valuesAsStrings(value) {
  return Array.isArray(value) ? value.map((entry) => String(entry)) : [];
}

function validateOwnerPermissions(config, target) {
  const telegram = config.channels?.telegram ?? {};
  const ownerEntries = valuesAsStrings(config.commands?.ownerAllowFrom);
  const checks = {
    telegramDm: valuesAsStrings(telegram.allowFrom).includes(target),
    commandOwner: ownerEntries.includes(target) || ownerEntries.includes(`telegram:${target}`),
    elevated: valuesAsStrings(config.tools?.elevated?.allowFrom?.telegram).includes(target),
    execApprover: valuesAsStrings(telegram.execApprovals?.approvers).includes(target),
    approvalTarget: (config.approvals?.plugin?.targets ?? []).some(
      (entry) => entry?.channel === "telegram" && String(entry?.to) === target,
    ),
  };
  const missing = Object.entries(checks)
    .filter(([, allowed]) => !allowed)
    .map(([name]) => name);
  if (missing.length > 0) {
    fail(`Telegram target is missing required permissions: ${missing.join(", ")}`);
  }
}

function resolveTelegramAccount(config, target) {
  const accountIds = (config.approvals?.plugin?.targets ?? [])
    .filter(
      (entry) =>
        entry?.channel === "telegram" &&
        String(entry?.to) === target &&
        typeof entry?.accountId === "string",
    )
    .map((entry) => entry.accountId);
  const uniqueAccountIds = [...new Set(accountIds)];
  if (uniqueAccountIds.length !== 1) {
    fail("Telegram owner must resolve to exactly one delivery account");
  }
  if (!config.channels?.telegram?.accounts?.[uniqueAccountIds[0]]) {
    fail("Resolved Telegram delivery account is not configured");
  }
  return uniqueAccountIds[0];
}

function runOpenClaw(args, timeoutMs = 60_000) {
  const result = spawnSync("openclaw", args, {
    encoding: "utf8",
    env: process.env,
    timeout: timeoutMs,
  });
  if (result.error) {
    fail(`OpenClaw command failed to start: ${result.error.message}`);
  }
  if (result.status !== 0) {
    const details = `${result.stdout}\n${result.stderr}`
      .replace(/(token|secret|password|cookie|authorization)[=: ]+[^\s,}]*/gi, "$1=[redacted]")
      .replace(/\b\d{7,}\b/g, "[redacted-number]")
      .trim()
      .slice(0, 500);
    fail(`OpenClaw command failed with exit code ${result.status}${details ? `: ${details}` : ""}`);
  }
  return result.stdout.trim();
}

function gatewayCall(method, params, timeoutMs = 30_000) {
  const output = runOpenClaw(
    [
      "gateway",
      "call",
      method,
      "--params",
      JSON.stringify(params),
      "--timeout",
      String(timeoutMs),
      "--json",
    ],
    timeoutMs + 5_000,
  );
  const parsed = JSON.parse(output);
  if (parsed?.ok === false) {
    fail(`Gateway method ${method} failed: ${parsed.error?.message ?? "unknown error"}`);
  }
  return parsed;
}

function findZalouserPlugin(stateDir) {
  const projectsDir = path.join(stateDir, "npm", "projects");
  if (!fs.existsSync(projectsDir)) {
    fail("OpenClaw npm projects directory was not found");
  }
  const candidates = [];
  for (const projectName of fs.readdirSync(projectsDir)) {
    const candidate = path.join(
      projectsDir,
      projectName,
      "node_modules",
      "@openclaw",
      "zalouser",
      "dist",
      "channel-plugin-api.js",
    );
    if (fs.existsSync(candidate)) {
      candidates.push({ candidate, mtimeMs: fs.statSync(candidate).mtimeMs });
    }
  }
  candidates.sort((left, right) => right.mtimeMs - left.mtimeMs);
  if (candidates.length === 0) {
    fail("Zalo Personal plugin runtime was not found");
  }
  return candidates[0].candidate;
}

function secureTree(rootPath) {
  fs.chmodSync(rootPath, 0o700);
  for (const entry of fs.readdirSync(rootPath, { withFileTypes: true })) {
    const entryPath = path.join(rootPath, entry.name);
    if (entry.isDirectory()) {
      secureTree(entryPath);
    } else if (entry.isFile()) {
      fs.chmodSync(entryPath, 0o600);
    }
  }
}

function createBackup(stateDir, configPath) {
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace("Z", "Z");
  const backupDir = path.join(stateDir, "backups", `zalo-qr-${timestamp}`);
  fs.mkdirSync(backupDir, { recursive: true, mode: 0o700 });
  fs.copyFileSync(configPath, path.join(backupDir, "openclaw.json.before"));
  const credentialsDir = path.join(stateDir, "credentials", "zalouser");
  if (fs.existsSync(credentialsDir)) {
    fs.cpSync(credentialsDir, path.join(backupDir, "zalouser-credentials.before"), {
      recursive: true,
      errorOnExist: true,
    });
  }
  secureTree(backupDir);
  return backupDir;
}

function processIsAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

function acquireWorkflowLock(stateDir) {
  const lockDir = path.join(stateDir, "state");
  const lockPath = path.join(lockDir, "zalo-qr-owner-login.lock");
  fs.mkdirSync(lockDir, { recursive: true, mode: 0o700 });

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const fd = fs.openSync(lockPath, "wx", 0o600);
      fs.writeFileSync(fd, JSON.stringify({ pid: process.pid, startedAt: Date.now() }) + "\n");
      fs.fsyncSync(fd);
      return { fd, lockPath };
    } catch (error) {
      if (error?.code !== "EEXIST") {
        throw error;
      }
      let ownerPid = null;
      try {
        ownerPid = Number(JSON.parse(fs.readFileSync(lockPath, "utf8")).pid);
      } catch {
        // Malformed locks are stale unless a live PID can be proven.
      }
      if (Number.isInteger(ownerPid) && ownerPid > 0 && processIsAlive(ownerPid)) {
        fail("A Zalo QR delivery workflow is already running");
      }
      fs.unlinkSync(lockPath);
    }
  }
  fail("Could not acquire the Zalo QR delivery lock");
}

function releaseWorkflowLock(lock) {
  if (!lock) {
    return;
  }
  try {
    fs.closeSync(lock.fd);
  } catch {
    // Cleanup remains best-effort if the descriptor was already closed.
  }
  try {
    const ownerPid = Number(JSON.parse(fs.readFileSync(lock.lockPath, "utf8")).pid);
    if (ownerPid === process.pid) {
      fs.unlinkSync(lock.lockPath);
    }
  } catch {
    // A missing or replaced lock must not delete another workflow's lock.
  }
}

function stripAnsi(value) {
  return value.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, "");
}

function sanitizeLoginOutput(value) {
  return stripAnsi(value)
    .replace(/(token|secret|password|cookie|authorization)[=: ]+[^\s,}]*/gi, "$1=[redacted]")
    .replace(/\b\d{7,}\b/g, "[redacted-number]")
    .trim()
    .slice(-800);
}

function runOfficialZaloLogin(accountId, timeoutSeconds, onQrReady) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      "openclaw",
      ["channels", "login", "--channel", "zalouser", "--account", accountId, "--verbose"],
      { env: process.env, stdio: ["ignore", "pipe", "pipe"] },
    );
    let output = "";
    let qrHandled = false;
    let settled = false;

    const finish = (error) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    };

    const inspectOutput = (chunk) => {
      output = `${output}${chunk}`.slice(-12_000);
      if (qrHandled) {
        return;
      }
      const match = /Scan QR image:\s*([^\r\n]+)/.exec(stripAnsi(output));
      const qrSourcePath = match?.[1]?.trim();
      if (!qrSourcePath || !fs.existsSync(qrSourcePath)) {
        return;
      }
      try {
        onQrReady(qrSourcePath);
        qrHandled = true;
      } catch (error) {
        child.kill("SIGTERM");
        finish(error);
      }
    };

    child.stdout.on("data", inspectOutput);
    child.stderr.on("data", inspectOutput);
    child.on("error", (error) => finish(new Error(`OpenClaw login failed to start: ${error.message}`)));
    child.on("close", (code) => {
      const cleanOutput = stripAnsi(output);
      if (code === 0 && qrHandled && /Login successful\./.test(cleanOutput)) {
        finish();
        return;
      }
      finish(
        new Error(
          `OpenClaw Zalo login failed${code === null ? "" : ` with exit code ${code}`}: ${sanitizeLoginOutput(output) || "unknown error"}`,
        ),
      );
    });

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      finish(new Error("OpenClaw Zalo login timed out"));
    }, (timeoutSeconds + 45) * 1_000);
  });
}

function sendTelegram(accountId, target, message, mediaPath) {
  const args = [
    "message",
    "send",
    "--channel",
    "telegram",
    "--account",
    accountId,
    "--target",
    target,
    "--message",
    message,
    "--json",
  ];
  if (mediaPath) {
    args.push("--media", mediaPath);
  }
  const result = JSON.parse(runOpenClaw(args, 60_000));
  // OpenClaw 2026.8.x plugin sends expose chatId instead of payload.to.
  const destination = String(
    result?.payload?.to ??
      result?.payload?.chatId ??
      result?.payload?.target ??
      result?.payload?.result?.to ??
      result?.payload?.result?.chatId ??
      result?.payload?.result?.chat?.id ??
      result?.target ??
      "",
  );
  const messageId = String(
    result?.messageId ??
      result?.payload?.messageId ??
      result?.payload?.result?.messageId ??
      result?.payload?.result?.message_id ??
      result?.payload?.receipt?.primaryPlatformMessageId ??
      result?.payload?.result?.receipt?.primaryPlatformMessageId ??
      "",
  );
  if (
    result?.channel !== "telegram" ||
    !messageId.trim() ||
    ![target, `telegram:${target}`].includes(destination)
  ) {
    fail("Telegram delivery did not return a matching message receipt");
  }
  return {
    messageId,
    destination,
  };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const runtimeHome = process.env.HOME || os.homedir();
  const stateDir = process.env.OPENCLAW_STATE_DIR || path.join(runtimeHome, ".openclaw");
  const configPath = process.env.OPENCLAW_CONFIG_PATH || path.join(stateDir, "openclaw.json");
  const config = readJson(configPath);

  validateOwnerPermissions(config, options.target);
  const telegramAccountId = resolveTelegramAccount(config, options.target);
  if (config.channels?.zalouser?.enabled !== true) {
    fail("Zalo Personal channel is not enabled");
  }
  runOpenClaw(["config", "validate"], 30_000);

  const pluginPath = findZalouserPlugin(stateDir);
  if (!fs.statSync(pluginPath).isFile()) {
    fail("Zalo Personal plugin runtime was not found");
  }

  const status = gatewayCall("channels.status", {}, 15_000);
  const telegramRunning = status.channels?.telegram?.running === true;
  if (!telegramRunning) {
    fail("Telegram channel must be running before sending a Zalo QR");
  }

  if (options.dryRun) {
    console.log(
      JSON.stringify({
        ok: true,
        mode: "dry-run",
        targetSuffix: options.target.slice(-4),
        pluginReady: true,
        telegramRunning: true,
        zalouserConfigured: status.channels?.zalouser?.configured === true,
      }),
    );
    return;
  }

  const workflowLock = acquireWorkflowLock(stateDir);
  let backupDir = null;
  let qrPath = null;
  const channelWasRunning = status.channels?.zalouser?.running === true;
  let loginConnected = false;
  let qrReceipt = null;
  let completionReceipt = null;

  try {
    backupDir = createBackup(stateDir, configPath);
    // OpenClaw only permits outbound media from its managed media directory.
    const qrDir = path.join(stateDir, "media", "outbound");
    fs.mkdirSync(qrDir, { recursive: true, mode: 0o700 });
    qrPath = path.join(qrDir, `openclaw-zalouser-owner-qr-${process.pid}.png`);

    if (channelWasRunning) {
      gatewayCall(
        "channels.stop",
        { channel: "zalouser", accountId: options.accountId },
        30_000,
      );
    }

    try {
      await runOfficialZaloLogin(options.accountId, options.timeoutSeconds, (qrSourcePath) => {
        fs.copyFileSync(qrSourcePath, qrPath);
        fs.chmodSync(qrPath, 0o600);
        qrReceipt = sendTelegram(
          telegramAccountId,
          options.target,
          "Mã QR đăng nhập lại Zalo Personal cho OpenClaw. Hãy quét ngay bằng Zalo và xác nhận trên điện thoại; mã chỉ có hiệu lực trong thời gian ngắn.",
          qrPath,
        );
      });
    } catch (error) {
      if (qrReceipt) {
        sendTelegram(
          telegramAccountId,
          options.target,
          "QR Zalo đã hết thời gian chờ hoặc chưa được xác nhận. Hãy yêu cầu tạo QR mới để thử lại.",
        );
      }
      throw error;
    }

    loginConnected = true;
    completionReceipt = sendTelegram(
      telegramAccountId,
      options.target,
      "Đăng nhập Zalo Personal đã thành công. Kênh Zalo của OpenClaw đã được bật lại.",
    );

    console.log(
      JSON.stringify({
        ok: true,
        mode: "apply",
        targetSuffix: options.target.slice(-4),
        backupDir,
        loginConnected: true,
        qrMessageId: qrReceipt.messageId,
        completionMessageId: completionReceipt.messageId,
      }),
    );
  } finally {
    if (qrPath && fs.existsSync(qrPath)) {
      fs.unlinkSync(qrPath);
    }
    if (channelWasRunning && !loginConnected) {
      try {
        gatewayCall(
          "channels.start",
          { channel: "zalouser", accountId: options.accountId },
          30_000,
        );
      } catch {
        // The caller receives the original failure; recovery is best-effort.
      }
    }
    releaseWorkflowLock(workflowLock);
  }
}

main().then(
  () => process.exit(0),
  (error) => {
    console.error(JSON.stringify({ ok: false, error: error.message }));
    process.exit(1);
  },
);

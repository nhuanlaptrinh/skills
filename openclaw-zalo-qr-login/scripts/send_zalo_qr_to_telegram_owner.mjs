#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

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

function writeQrImage(dataUrl, qrPath) {
  const match = /^data:image\/png;base64,([A-Za-z0-9+/=]+)$/.exec(dataUrl ?? "");
  if (!match) {
    fail("Zalo plugin did not return a PNG QR image");
  }
  fs.writeFileSync(qrPath, Buffer.from(match[1], "base64"), { mode: 0o600 });
}

function sendTelegram(target, message, mediaPath) {
  const args = ["message", "send", "--channel", "telegram", "--target", target, "--message", message];
  if (mediaPath) {
    args.push("--media", mediaPath);
  }
  runOpenClaw(args, 60_000);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const runtimeHome = process.env.HOME || os.homedir();
  const stateDir = process.env.OPENCLAW_STATE_DIR || path.join(runtimeHome, ".openclaw");
  const configPath = process.env.OPENCLAW_CONFIG_PATH || path.join(stateDir, "openclaw.json");
  const config = readJson(configPath);

  validateOwnerPermissions(config, options.target);
  if (config.channels?.zalouser?.enabled !== true) {
    fail("Zalo Personal channel is not enabled");
  }
  runOpenClaw(["config", "validate"], 30_000);

  const pluginPath = findZalouserPlugin(stateDir);
  const { zalouserPlugin } = await import(pathToFileURL(pluginPath).href);
  if (
    typeof zalouserPlugin?.gateway?.loginWithQrStart !== "function" ||
    typeof zalouserPlugin?.gateway?.loginWithQrWait !== "function"
  ) {
    fail("Zalo Personal plugin does not expose QR login methods");
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

  const backupDir = createBackup(stateDir, configPath);
  // OpenClaw only permits outbound media from its managed media directory.
  const qrDir = path.join(stateDir, "media", "outbound");
  fs.mkdirSync(qrDir, { recursive: true, mode: 0o700 });
  const qrPath = path.join(qrDir, `openclaw-zalouser-owner-qr-${process.pid}.png`);
  let channelStopped = false;
  let loginConnected = false;

  try {
    // A kicked Zalo listener may already be stopped; only stop a running channel.
    if (status.channels?.zalouser?.running === true) {
      gatewayCall(
        "channels.stop",
        { channel: "zalouser", accountId: options.accountId },
        30_000,
      );
      channelStopped = true;
    }

    const started = await zalouserPlugin.gateway.loginWithQrStart({
      accountId: options.accountId,
      force: true,
      timeoutMs: 35_000,
    });
    if (!started?.qrDataUrl) {
      fail(started?.message ?? "Zalo QR login did not start");
    }

    writeQrImage(started.qrDataUrl, qrPath);
    sendTelegram(
      options.target,
      "Mã QR đăng nhập lại Zalo Personal cho OpenClaw. Hãy quét ngay bằng Zalo và xác nhận trên điện thoại; mã chỉ có hiệu lực trong thời gian ngắn.",
      qrPath,
    );

    const waited = await zalouserPlugin.gateway.loginWithQrWait({
      accountId: options.accountId,
      timeoutMs: options.timeoutSeconds * 1_000,
      currentQrDataUrl: started.qrDataUrl,
    });
    if (!waited?.connected) {
      sendTelegram(
        options.target,
        "QR Zalo đã hết thời gian chờ hoặc chưa được xác nhận. Hãy yêu cầu tạo QR mới để thử lại.",
      );
      fail(waited?.message ?? "Zalo QR login timed out");
    }

    loginConnected = true;
    gatewayCall(
      "channels.start",
      { channel: "zalouser", accountId: options.accountId },
      30_000,
    );
    channelStopped = false;
    sendTelegram(
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
      }),
    );
  } finally {
    if (fs.existsSync(qrPath)) {
      fs.unlinkSync(qrPath);
    }
    if (channelStopped && loginConnected) {
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
  }
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: error.message }));
  process.exitCode = 1;
});

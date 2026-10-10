import { spawn } from "node:child_process";
import { appendFileSync, chmodSync, copyFileSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import os from "node:os";
import path from "node:path";

const settings = JSON.parse(readFileSync(new URL("./settings.json", import.meta.url), "utf8"));
const stateRoot = settings.runtimeRoot;
let loginActive = false;

function normalizedTarget(value) {
  return String(value ?? "").replace(/^telegram:/, "").replace(/^user:/, "");
}

export function telegramOwners(config) {
  return new Set((config.commands?.ownerAllowFrom ?? []).flatMap((entry) => {
    const match = String(entry).match(/^(?:telegram:)?([1-9]\d*)$/);
    return match ? [match[1]] : [];
  }));
}

function currentConfig() {
  return JSON.parse(readFileSync(path.join(stateRoot, "openclaw.json"), "utf8"));
}

export function authorizedToolContext(context, config = currentConfig()) {
  const route = context.deliveryContext ?? {};
  const sender = String(context.requesterSenderId ?? "");
  return context.senderIsOwner === true && telegramOwners(config).has(sender)
    && (route.channel ?? context.messageChannel) === "telegram"
    && route.accountId === settings.telegramAccount && normalizedTarget(route.to) === sender
    && context.agentId === settings.agentId && typeof context.assertInvocationCurrent === "function";
}

export function authorizedCommandContext(context, config = currentConfig()) {
  const sender = String(context.senderId ?? "");
  return context.isAuthorizedSender === true && context.senderIsOwner === true && telegramOwners(config).has(sender)
    && (context.channelId ?? context.channel) === "telegram"
    && context.accountId === settings.telegramAccount && normalizedTarget(context.to) === sender
    && context.agentId === settings.agentId && typeof context.assertOwnerCurrent === "function";
}

function cliProcess(args, { signal, timeoutMs, logPath }) {
  const environment = { ...process.env, HOME: settings.runtimeHome, OPENCLAW_STATE_DIR: stateRoot, OPENCLAW_CONFIG_PATH: `${stateRoot}/openclaw.json` };
  delete environment.OPENCLAW_PROFILE;
  delete environment.OPENCLAW_HOME;
  const child = spawn("/usr/bin/openclaw", args, {
    detached: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: environment,
  });
  let output = "";
  let closed = false;
  let killTimer;
  const stop = () => {
    if (closed || !child.pid) return;
    try { process.kill(-child.pid, "SIGTERM"); } catch {}
    killTimer ??= setTimeout(() => {
      try { process.kill(-child.pid, "SIGKILL"); } catch {}
    }, 1500);
  };
  const collect = (chunk) => {
    const text = chunk.toString();
    output = (output + text).slice(-131072);
    appendFileSync(logPath, text, { mode: 0o600 });
  };
  child.stdout.on("data", collect);
  child.stderr.on("data", collect);
  const timeout = setTimeout(stop, timeoutMs);
  signal?.addEventListener("abort", stop, { once: true });
  if (signal?.aborted) stop();
  const done = new Promise((resolve) => {
    const finish = (code) => {
      if (closed) return;
      closed = true;
      clearTimeout(timeout);
      clearTimeout(killTimer);
      signal?.removeEventListener("abort", stop);
      resolve({ code, output });
    };
    child.once("error", () => finish(-1));
    child.once("close", (code) => finish(code ?? -1));
  });
  return { done, stop, get output() { return output; }, get closed() { return closed; } };
}

function parseReceipt(output, ownerId) {
  for (let offset = output.indexOf("{"); offset >= 0; offset = output.indexOf("{", offset + 1)) {
    try {
      const value = JSON.parse(output.slice(offset).trim());
      const payload = value.payload ?? value;
      const messageId = value.messageId ?? payload.messageId;
      if (payload.ok === true && String(payload.chatId) === ownerId && messageId) return String(messageId);
    } catch {}
  }
  throw new Error("Telegram chưa trả biên nhận ảnh rõ ràng; không gửi lại tự động để tránh trùng QR.");
}

export async function loginAndSendQr(ownerId, assertCurrent, signal) {
  assertCurrent();
  if (loginActive) return { status: "already_running", message: "Đang có lượt đăng nhập chờ quét; không tạo phiên song song." };
  loginActive = true;
  let login;
  let mediaDirectory;
  let receipt;
  let lockDirectory;
  let lockToken;
  try {
    const locksRoot = path.join(stateRoot, "locks");
    mkdirSync(locksRoot, { recursive: true, mode: 0o700 });
    const requestedLock = path.join(locksRoot, "telegram-zalo-owner-login");
    try {
      mkdirSync(requestedLock, { mode: 0o700 });
    } catch (error) {
      if (error.code === "EEXIST") return { status: "already_running", message: "Có lượt đăng nhập/lock đang tồn tại. Không tạo phiên song song hoặc tự xóa lock." };
      throw error;
    }
    lockDirectory = requestedLock;
    lockToken = randomUUID();
    writeFileSync(path.join(lockDirectory, "owner.json"), JSON.stringify({ token: lockToken, pid: process.pid, startedAt: Date.now() }), { mode: 0o600 });
    const startedAt = Date.now();
    const privateRoot = path.join(stateRoot, "tmp", "telegram-zalo-login");
    mkdirSync(privateRoot, { recursive: true, mode: 0o700 });
    const privateDirectory = mkdtempSync(path.join(privateRoot, "attempt-"));
    chmodSync(privateDirectory, 0o700);
    assertCurrent();
    login = cliProcess(["channels", "login", "--channel", "zalouser", "--account", settings.zaloAccount, "--agent", settings.agentId, "--verbose"], {
      signal, timeoutMs: 180000, logPath: path.join(privateDirectory, "login.log"),
    });
    while (!login.closed && Date.now() - startedAt < 170000) {
      assertCurrent();
      if (signal?.aborted) throw new Error("Lượt đăng nhập đã bị hủy.");
      if (/Scan QR image: [^\r\n]+\.png/.test(login.output)) break;
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    assertCurrent();
    const qrMatch = login.output.match(/Scan QR image: ([^\r\n]+\.png)/);
    if (!qrMatch) {
      return { status: "qr_unavailable", message: "Runtime chưa tạo ảnh QR; không gửi ảnh cũ hoặc yêu cầu mở dashboard thay cho lỗi thực tế." };
    }
    const qrSource = path.resolve(qrMatch[1].trim());
    if (path.dirname(qrSource) !== path.join(os.tmpdir(), "openclaw")
      || !/^openclaw-zalouser-qr-[A-Za-z0-9_-]+\.png$/.test(path.basename(qrSource))
      || lstatSync(qrSource).isSymbolicLink() || statSync(qrSource).size > 5242880) {
      throw new Error("Runtime trả đường dẫn QR ngoài vị trí/tên file đã xác minh.");
    }
    const image = readFileSync(qrSource);
    if (statSync(qrSource).mtimeMs < startedAt - 1000 || image.length < 32
      || !image.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
      throw new Error("Ảnh QR không hợp lệ hoặc không thuộc lượt đăng nhập hiện tại.");
    }
    const mediaRoot = path.join(stateRoot, "media", "outbound");
    mkdirSync(mediaRoot, { recursive: true, mode: 0o700 });
    mediaDirectory = mkdtempSync(path.join(mediaRoot, "zalo-login-"));
    chmodSync(mediaDirectory, 0o700);
    const mediaPath = path.join(mediaDirectory, "qr.png");
    copyFileSync(qrSource, mediaPath);
    chmodSync(mediaPath, 0o600);
    assertCurrent();
    const delivery = cliProcess(["message", "send", "--channel", "telegram", "--account", settings.telegramAccount,
      "--target", ownerId, "--media", mediaPath, "--message",
      "Anh/chị quét QR bằng Zalo trên điện thoại và xác nhận đăng nhập ngay nhé. Em đang chờ kết quả; mã có thời hạn ngắn.", "--json"],
    { signal, timeoutMs: 30000, logPath: path.join(privateDirectory, "delivery.log") });
    const deliveryResult = await delivery.done;
    assertCurrent();
    if (deliveryResult.code !== 0) throw new Error("Gửi ảnh Telegram chưa thành công; không tự gửi lại khi biên nhận chưa rõ.");
    receipt = parseReceipt(deliveryResult.output, ownerId);
    while (!login.closed && Date.now() - startedAt < 180000) {
      assertCurrent();
      if (signal?.aborted) throw new Error("Lượt đăng nhập đã bị hủy sau khi gửi QR.");
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    const outcome = await login.done;
    assertCurrent();
    return {
      status: outcome.code === 0 ? "login_completed" : "qr_sent_not_logged_in",
      telegramMessageId: receipt,
      message: outcome.code === 0
        ? "Đã gửi ảnh QR có biên nhận và CLI đăng nhập thành công. Kiểm tra status của Zalo trước khi khẳng định listener đang kết nối."
        : "Đã gửi ảnh QR có biên nhận, nhưng chưa xác minh đăng nhập; QR có thể hết hạn hoặc chưa được xác nhận.",
    };
  } catch (error) {
    return { status: "failed", qrSent: Boolean(receipt), message: error.message };
  } finally {
    login?.stop();
    if (login) await login.done;
    if (mediaDirectory) rmSync(mediaDirectory, { recursive: true, force: true });
    if (lockDirectory) {
      try {
        const lock = JSON.parse(readFileSync(path.join(lockDirectory, "owner.json"), "utf8"));
        if (lock.token === lockToken) rmSync(lockDirectory, { recursive: true, force: true });
      } catch {}
    }
    loginActive = false;
  }
}

export default {
  id: settings.pluginId,
  name: "Owner Telegram Zalo QR Login",
  register(api) {
    api.registerTool({
      contextVersion: 2,
      create(context) {
        if (!authorizedToolContext(context)) return null;
        return {
          name: "telegram_zalo_login_qr",
          label: "Tạo và gửi QR đăng nhập Zalo",
          description: "Khi owner yêu cầu đăng nhập Zalo qua Telegram riêng: tạo QR và tự gửi ảnh ngay trong lúc chờ quét. Không dùng exec channels login. Không cần dashboard. Chỉ dùng khi owner yêu cầu tạo QR/đăng nhập, không dùng để kiểm tra trạng thái.",
          parameters: { type: "object", properties: { confirm: { type: "boolean", const: true } }, required: ["confirm"], additionalProperties: false },
          async execute(_toolCallId, params, signal) {
            if (params.confirm !== true) throw new Error("Cần yêu cầu đăng nhập rõ ràng từ owner.");
            const guard = () => {
              context.assertInvocationCurrent();
              if (!authorizedToolContext(context)) throw new Error("Quyền owner hoặc Telegram riêng không còn hợp lệ.");
            };
            const result = await loginAndSendQr(String(context.requesterSenderId), guard, signal);
            return { content: [{ type: "text", text: JSON.stringify(result) }], details: result };
          },
        };
      },
    }, { name: "telegram_zalo_login_qr" });
    api.registerCommand({
      name: "zaloqr",
      description: "Tạo QR đăng nhập Zalo và gửi riêng cho owner",
      channels: ["telegram"],
      requireAuth: true,
      requiredScopes: ["operator.admin"],
      exposeSenderIsOwner: true,
      acceptsArgs: false,
      nativeProgressMessages: { telegram: "Em đang tạo QR Zalo và sẽ gửi ảnh ngay tại đây." },
      async handler(context) {
        if (!authorizedCommandContext(context)) return { text: "Lệnh này chỉ dành cho Telegram owner đã cấu hình, trong chat riêng của đúng bot." };
        const guard = () => {
          context.assertOwnerCurrent();
          if (!authorizedCommandContext(context)) throw new Error("Quyền owner hoặc Telegram riêng không còn hợp lệ.");
        };
        const result = await loginAndSendQr(String(context.senderId), guard);
        return { text: result.message };
      },
    });
  },
};

import fs from "node:fs";
import path from "node:path";
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const DEFAULT_GROUP_ID = "";
const DEFAULT_ACCOUNT_ID = "default";
const DEFAULT_STATE_FILE = `${process.env.HOME ?? "/root"}/.openclaw/workspace/state/telegram-customer-inbox/state.json`;
const DEFAULT_STAFF_IDS = [];
const MAX_TEXT_LENGTH = 3500;
const MAX_MAPPED_MESSAGES = 5000;

function asString(value) {
  return value === undefined || value === null ? "" : String(value);
}

function normalizeId(value) {
  const text = asString(value).trim();
  return text || null;
}

function numericIds(value) {
  return asString(value).match(/-?\d{5,}/g) ?? [];
}

function positiveTelegramId(...values) {
  for (const value of values) {
    for (const candidate of numericIds(value)) {
      if (!candidate.startsWith("-")) return candidate;
    }
  }
  return null;
}

function containsId(value, id) {
  return asString(value) === id || asString(value).includes(id);
}

function removeDiacritics(value) {
  return asString(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function splitText(text) {
  const value = asString(text).trim();
  if (!value) return ["[Tin nhắn không có nội dung văn bản]"];
  const chunks = [];
  for (let offset = 0; offset < value.length; offset += MAX_TEXT_LENGTH) {
    chunks.push(value.slice(offset, offset + MAX_TEXT_LENGTH));
  }
  return chunks;
}

function isGroupConversation(event, ctx, groupId) {
  return [
    event?.from,
    event?.conversationId,
    event?.sessionKey,
    ctx?.conversationId,
    ctx?.sessionKey,
  ].some((value) => containsId(value, groupId));
}

function isAccountContext(ctx, accountId) {
  if (ctx?.channelId !== "telegram") return false;
  if (ctx?.accountId) return ctx.accountId === accountId;
  return asString(ctx?.sessionKey).includes(`telegram:${accountId}`);
}

function resolveCustomerId(event, ctx, groupId) {
  const candidates = [
    ctx?.conversationId,
    event?.from,
    ctx?.senderId,
    event?.senderId,
    ctx?.sessionKey,
  ];
  for (const candidate of candidates) {
    const id = positiveTelegramId(candidate);
    if (id && id !== groupId) return id;
  }
  return null;
}

function resolveStaffId(event, ctx, staffIds) {
  const candidates = [ctx?.senderId, event?.senderId, event?.from];
  for (const candidate of candidates) {
    const id = positiveTelegramId(candidate);
    if (id && staffIds.has(id)) return id;
  }
  return null;
}

function resolveReplyId(event, ctx) {
  return normalizeId(event?.replyToId ?? ctx?.replyToId ?? event?.metadata?.replyToMessageId);
}

function parseStaffAction(text) {
  const normalized = removeDiacritics(text).toLowerCase().trim();
  const command = normalized.replace(/^\/[a-z0-9_]+(?:@\w+)?/, (value) => value.split("@")[0]);
  if (/^\/(takeover|human|handoff)$/.test(command) || /^(tiep quan|nhan vien tiep quan|chuyen nhan vien)$/.test(normalized)) {
    return "takeover";
  }
  if (/^\/(bot|resume|release)$/.test(command) || /^(tra lai bot|bat lai bot|cho bot tra loi)$/.test(normalized)) {
    return "resume";
  }
  return null;
}

function readState(stateFile) {
  try {
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    if (parsed && typeof parsed === "object") {
      return {
        version: 1,
        customers: parsed.customers && typeof parsed.customers === "object" ? parsed.customers : {},
        groupMessages: parsed.groupMessages && typeof parsed.groupMessages === "object" ? parsed.groupMessages : {},
        topics: parsed.topics && typeof parsed.topics === "object" ? parsed.topics : {},
      };
    }
  } catch {}
  return { version: 1, customers: {}, groupMessages: {}, topics: {} };
}

function writeState(stateFile, state) {
  fs.mkdirSync(path.dirname(stateFile), { recursive: true, mode: 0o700 });
  fs.chmodSync(path.dirname(stateFile), 0o700);
  const temporaryFile = `${stateFile}.${process.pid}.tmp`;
  fs.writeFileSync(temporaryFile, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporaryFile, stateFile);
}

function pruneMappings(state) {
  const entries = Object.entries(state.groupMessages);
  if (entries.length <= MAX_MAPPED_MESSAGES) return;
  entries.sort((left, right) => (left[1].createdAt ?? 0) - (right[1].createdAt ?? 0));
  for (const [messageId] of entries.slice(0, entries.length - MAX_MAPPED_MESSAGES)) {
    delete state.groupMessages[messageId];
  }
}

function buildCustomerMirror(customerId, content, paused) {
  const status = paused ? "⏸ AI TẠM DỪNG - NHÂN VIÊN ĐANG TIẾP QUẢN" : "🟢 AI ĐANG HOẠT ĐỘNG";
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    "🔵 LUỒNG KHÁCH HÀNG",
    `Mã khách: #${customerId}`,
    `Trạng thái: ${status}`,
    "",
    "💬 TIN NHẮN KHÁCH:",
    content || "[Tin nhắn không có nội dung văn bản]",
    "",
    "↩️ Reply đúng tin nhắn 🔵 này để xử lý khách",
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function buildBotMirror(customerId, content, brandName) {
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    `🤖 LUỒNG ${brandName} / AI`,
    `Phản hồi tự động cho khách #${customerId}`,
    "",
    "💬 PHẢN HỒI AI:",
    content || "[Phản hồi không có nội dung văn bản]",
    "",
    "↩️ Reply tin nhắn này nếu nhân viên muốn trả lời trực tiếp",
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function buildTakeoverButtons(customerId, paused) {
  return {
    inline_keyboard: [[{
      text: paused ? "🟢 Trả lại bot" : "🟡 Tiếp quản khách này",
      callback_data: `telegram-customer-inbox:${paused ? "resume" : "takeover"}:${customerId}`,
    }]],
  };
}

function buildStaffMessage(content, brandName) {
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    "🟢 LUỒNG NHÂN VIÊN → KHÁCH",
    `👩‍💼 Nhân viên ${brandName}:`,
    "",
    content,
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function buildStaffAck(customerId, staffId, brandName, paused) {
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    `🟢 LUỒNG NHÂN VIÊN → KHÁCH #${customerId}`,
    `✅ Đã gửi trực tiếp cho khách`,
    `👤 Nhân viên: #${staffId}`,
    paused ? `⏸ ${brandName} đang tạm dừng (nhân viên tiếp quản)` : `🤖 ${brandName} vẫn đang hoạt động bình thường`,
    paused ? "🟢 Muốn bật bot: bấm Trả lại bot hoặc reply /bot" : "🟡 Muốn dừng bot: bấm Tiếp quản hoặc reply /takeover",
    "↩️ Reply tin này để tiếp tục trả lời cùng khách",
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function buildTakeoverNotice(customerId, staffId, brandName) {
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    "🟡 QUẢN LÝ TRẠNG THÁI",
    `🔵 Khách: #${customerId}`,
    `🟢 Đã chuyển cho nhân viên #${staffId}`,
    `🤖 ${brandName} / AI đã tạm dừng cho riêng khách này`,
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function buildResumeNotice(customerId, staffId, brandName) {
  return [
    "━━━━━━━━━━━━━━━━━━━━",
    "🟡 QUẢN LÝ TRẠNG THÁI",
    `🔵 Khách: #${customerId}`,
    `🤖 Đã trả lại cho ${brandName} theo yêu cầu của #${staffId}`,
    "🟢 AI đã hoạt động lại",
    "━━━━━━━━━━━━━━━━━━━━",
  ].join("\n");
}

function getAccountToken(api, accountId) {
  const account = api.config?.channels?.telegram?.accounts?.[accountId] ?? {};
  if (account.tokenFile) return fs.readFileSync(account.tokenFile, "utf8").trim();
  if (account.token) return String(account.token).trim();
  return "";
}

async function telegramCall(token, method, payload) {
  if (!token) throw new Error("Telegram token is not configured for the inbox account");
  const response = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok || !body.ok) {
    throw new Error(`Telegram ${method} failed (${response.status}): ${asString(body.description).slice(0, 180)}`);
  }
  return body.result;
}

async function sendTelegram(token, chatId, text, options = {}) {
  let firstMessageId = null;
  for (const [index, chunk] of splitText(text).entries()) {
    const payload = {
      chat_id: chatId,
      text: chunk,
      disable_web_page_preview: true,
    };
    if (index === 0 && options.replyToId && /^\d+$/.test(String(options.replyToId))) {
      payload.reply_to_message_id = Number(options.replyToId);
    }
    if (options.threadId && Number(options.threadId) > 1) {
      payload.message_thread_id = Number(options.threadId);
    }
    if (index === 0 && options.replyMarkup) {
      payload.reply_markup = options.replyMarkup;
    }
    const result = await telegramCall(token, "sendMessage", payload);
    if (!firstMessageId) firstMessageId = String(result.message_id);
  }
  return firstMessageId;
}

function registerInbox(api) {
  const config = api.pluginConfig ?? {};
  const groupId = normalizeId(config.groupId) ?? DEFAULT_GROUP_ID;
  const accountId = normalizeId(config.accountId) ?? DEFAULT_ACCOUNT_ID;
  const staffIds = new Set((Array.isArray(config.staffIds) ? config.staffIds : DEFAULT_STAFF_IDS).map(String));
  const brandName = normalizeId(config.brandName) ?? "Bot";
  const stateFile = normalizeId(config.stateFile) ?? DEFAULT_STATE_FILE;
  const token = getAccountToken(api, accountId);
  const state = readState(stateFile);
  const botId = positiveTelegramId(api.config?.channels?.telegram?.accounts?.[accountId]?.botId);
  let forumMode;

  if (!groupId || staffIds.size === 0) {
    api.logger.error?.("telegram-customer-inbox requires config.groupId and at least one config.staffIds entry");
    return;
  }

  const save = () => {
    pruneMappings(state);
    writeState(stateFile, state);
  };

  const customerRecord = (customerId) => {
    state.customers[customerId] ??= {
      paused: false,
      lastGroupMessageId: null,
      lastSeenAt: null,
    };
    return state.customers[customerId];
  };

  const sendToGroup = async (text, replyToId, threadId, replyMarkup) => sendTelegram(token, groupId, text, { replyToId, threadId, replyMarkup });
  const sendToCustomer = async (customerId, text) => sendTelegram(token, customerId, text);

  const mapGroupMessage = (messageId, customerId, kind) => {
    if (!messageId) return;
    const customer = customerRecord(customerId);
    customer.lastGroupMessageId = messageId;
    state.groupMessages[messageId] = { customerId, kind, createdAt: Date.now() };
  };

  const isForumGroup = async () => {
    if (forumMode !== undefined) return forumMode;
    try {
      const chat = await telegramCall(token, "getChat", { chat_id: groupId });
      forumMode = chat?.is_forum === true;
    } catch (error) {
      forumMode = false;
      reportError("forum check", error);
    }
    return forumMode;
  };

  const ensureCustomerTopic = async (customerId, customer) => {
    if (!(await isForumGroup()) || customer.topicId) return customer.topicId ?? null;
    const topic = await telegramCall(token, "createForumTopic", {
      chat_id: groupId,
      name: `Khách #${customerId}`.slice(0, 128),
    });
    customer.topicId = String(topic.message_thread_id);
    state.topics[customer.topicId] = customerId;
    return customer.topicId;
  };

  const reportError = (operation, error) => {
    api.logger.error?.(`telegram-customer-inbox ${operation}: ${error instanceof Error ? error.message : String(error)}`);
  };

  const handleTakeover = async (customerId, staffId, replyToId, threadId) => {
    const customer = customerRecord(customerId);
    customer.paused = true;
    customer.pausedBy = staffId;
    customer.pausedAt = new Date().toISOString();
    save();
    await sendToCustomer(customerId, `👩‍💼 Nhân viên đã tiếp nhận cuộc trò chuyện và sẽ hỗ trợ anh/chị ngay.`);
    const noticeId = await sendToGroup(buildTakeoverNotice(customerId, staffId, brandName), replyToId, threadId);
    mapGroupMessage(noticeId, customerId, "takeover");
    save();
  };

  const handleResume = async (customerId, staffId, replyToId, threadId) => {
    const customer = customerRecord(customerId);
    customer.paused = false;
    customer.resumedBy = staffId;
    customer.resumedAt = new Date().toISOString();
    save();
    await sendToCustomer(customerId, `🤖 ${brandName} đã quay lại hỗ trợ anh/chị. Nhân viên vẫn có thể tham gia bất cứ lúc nào.`);
    const noticeId = await sendToGroup(buildResumeNotice(customerId, staffId, brandName), replyToId, threadId);
    mapGroupMessage(noticeId, customerId, "resume");
    save();
  };

  api.registerInteractiveHandler?.({
    channel: "telegram",
    namespace: "telegram-customer-inbox",
    handler: async (interactive) => {
      if (interactive.accountId !== accountId || interactive.callback.chatId !== groupId) return { handled: false };
      const staffId = normalizeId(interactive.senderId);
      if (!staffId || !staffIds.has(staffId) || !interactive.auth.isAuthorizedSender) return { handled: true };
      const [action, customerId] = asString(interactive.callback.payload).split(":");
      if (!customerId || !["takeover", "resume"].includes(action)) return { handled: true };
      if (state.groupMessages[String(interactive.callback.messageId)]?.customerId !== customerId) return { handled: true };
      try {
        const replyToId = String(interactive.callback.messageId);
        const threadId = interactive.threadId ? String(interactive.threadId) : null;
        if (action === "takeover") await handleTakeover(customerId, staffId, replyToId, threadId);
        else await handleResume(customerId, staffId, replyToId, threadId);
        await interactive.respond.clearButtons();
        return { handled: true };
      } catch (error) {
        reportError("button route", error);
        return { handled: true };
      }
    },
  });

  api.on("message_received", async (event, ctx) => {
    if (!isAccountContext(ctx, accountId)) return;
    if (isGroupConversation(event, ctx, groupId)) {
      const staffId = resolveStaffId(event, ctx, staffIds);
      if (!staffId) return;
      const replyToId = resolveReplyId(event, ctx);
      const threadId = normalizeId(event?.threadId ?? ctx?.threadId ?? event?.metadata?.messageThreadId);
      const mapping = (replyToId && state.groupMessages[replyToId]) || (threadId && state.topics[threadId] ? { customerId: state.topics[threadId] } : null);
      if (!mapping?.customerId) return;
      const customer = customerRecord(mapping.customerId);
      const content = asString(event.content).trim();
      const action = parseStaffAction(content);
      try {
        if (action === "takeover") {
          await handleTakeover(mapping.customerId, staffId, event.messageId, threadId);
          return;
        }
        if (action === "resume") {
          await handleResume(mapping.customerId, staffId, event.messageId, threadId);
          return;
        }
        if (content) {
          await sendToCustomer(mapping.customerId, buildStaffMessage(content, brandName));
          customer.lastStaffId = staffId;
          customer.lastStaffAt = new Date().toISOString();
          const noticeId = await sendToGroup(buildStaffAck(mapping.customerId, staffId, brandName, customer.paused), event.messageId, threadId);
          mapGroupMessage(noticeId, mapping.customerId, "staff");
          save();
        }
      } catch (error) {
        reportError("staff route", error);
      }
      return;
    }

    const customerId = resolveCustomerId(event, ctx, groupId);
    if (!customerId || customerId === botId) return;
    const customer = customerRecord(customerId);
    customer.lastSeenAt = new Date().toISOString();
    const content = asString(event.content).trim() || (event.media?.length ? "[Khách gửi tệp đính kèm]" : "[Tin nhắn không có nội dung văn bản]");
    try {
      const topicId = await ensureCustomerTopic(customerId, customer);
      const groupMessageId = await sendToGroup(buildCustomerMirror(customerId, content, customer.paused), customer.lastGroupMessageId, topicId, buildTakeoverButtons(customerId, customer.paused));
      if (groupMessageId) {
        mapGroupMessage(groupMessageId, customerId, "customer");
      }
      save();
    } catch (error) {
      reportError("customer mirror", error);
    }
  });

  api.on("message_sent", async (event, ctx) => {
    if (!isAccountContext(ctx, accountId) || !event.success) return;
    if (containsId(event.to, groupId)) return;
    const customerId = positiveTelegramId(event.to);
    if (!customerId || customerId === botId) return;
    const customer = customerRecord(customerId);
    try {
      const groupMessageId = await sendToGroup(buildBotMirror(customerId, event.content, brandName), customer.lastGroupMessageId, customer.topicId, buildTakeoverButtons(customerId, customer.paused));
      if (groupMessageId) {
        mapGroupMessage(groupMessageId, customerId, "bot");
      }
      save();
    } catch (error) {
      reportError("bot mirror", error);
    }
  });

  api.on("message_sending", async (event, ctx) => {
    if (!isAccountContext(ctx, accountId)) return;
    if (containsId(event.to, groupId)) return;
    const customerId = positiveTelegramId(event.to);
    if (customerId && state.customers[customerId]?.paused) {
      return { cancel: true, cancelReason: "customer_taken_over" };
    }
  });

  api.on("before_dispatch", async (event, ctx) => {
    if (!isAccountContext(ctx, accountId)) return;
    if (isGroupConversation(event, ctx, groupId)) return { handled: true };
    const customerId = resolveCustomerId(event, ctx, groupId);
    if (customerId && state.customers[customerId]?.paused) return { handled: true };
  });

  api.logger.info?.(`telegram-customer-inbox enabled for group ${groupId}; staff ${[...staffIds].join(", ")}`);
}

export default definePluginEntry({
  id: "telegram-customer-inbox",
  name: "Telegram Customer Inbox",
  description: "Routes Telegram customer DMs to a staff group with AI-default and per-customer takeover control.",
  configSchema: {
    type: "object",
    additionalProperties: false,
    properties: {
      groupId: { type: "string" },
      accountId: { type: "string" },
      brandName: { type: "string" },
      staffIds: { type: "array", items: { type: "string" } },
      stateFile: { type: "string" },
    },
  },
  register(api) {
    if (api.registrationMode !== "full") return;
    registerInbox(api);
  },
});

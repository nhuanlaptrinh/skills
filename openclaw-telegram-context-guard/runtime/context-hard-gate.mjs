import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// Runtime guard for shared Telegram/Zalo groups. Prompt instructions remain
// useful guidance, but this hook is the terminal tool-call enforcement layer.
const GROUP_SESSION = /^agent:main:(?:telegram|zalouser):group:-?\d+(?::topic:\d+)?$/;
const COORDINATORS = [
  "scripts/excel_task.py",
  "scripts/safe_excel_intake.py",
  "scripts/pdf_task.py",
  "scripts/media_task.py",
  "scripts/report_task.py",
];
const FORBIDDEN_SHELL = /[;&|`$()<>\n\r]|\b(?:cat|head|tail|sed|find|curl|wget|rm|openpyxl|read_excel|zipfile|xml\.etree)\b/i;
const callsByRun = new Map();
const progressReceipts = new Map();
const RECEIPT_TTL_MS = 120000;

function groupContext(ctx) {
  return typeof ctx?.sessionKey === "string" && GROUP_SESSION.test(ctx.sessionKey);
}

function command(params) {
  if (!params || typeof params !== "object") return "";
  return typeof params.command === "string" ? params.command.trim() : "";
}

function coordinatorCommand(value) {
  if (!value || FORBIDDEN_SHELL.test(value)) return false;
  if (!/^\s*(?:python|python3|\/usr\/bin\/python3|\/home\/[^\s]+\/\.venv-[^\s]+\/bin\/python)\b/.test(value)) return false;
  return COORDINATORS.some((name) => value.includes(name));
}

function safeRead(params) {
  const path = typeof params?.path === "string" ? params.path : typeof params?.file_path === "string" ? params.file_path : "";
  if (!path) return false;
  const normalized = path.replaceAll("\\", "/");
  const isOutput = /(?:^|\/)output\/(?:file-tasks\/[^/]+\/)?(?:summary|detail)\.json$/.test(normalized);
  const isApprovedSkill = /\/agents\/main\/agent\/workshop-skills\/doi-chieu-cuoc-van-chuyen\/SKILL\.md$/.test(normalized);
  if (!isOutput && !isApprovedSkill) return false;
  if (/\.(?:sqlite|sqlite-wal|sqlite-shm|out|log)$|\/scripts(?:\/|$)/i.test(normalized)) return false;
  const limit = params?.limit;
  return limit === undefined || (Number.isInteger(limit) && limit >= 1 && limit <= (isApprovedSkill ? 80 : 40));
}

const FILE_TASK_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    action: { type: "string", enum: ["discover", "inspect", "process", "status"] },
    inputs: { type: "array", items: { type: "string" }, maxItems: 2 },
    taskId: { type: "string", maxLength: 80 },
    customer: { type: "string", maxLength: 120 },
    sheets: { type: "array", items: { type: "string" }, maxItems: 8 },
    mapping: { type: "object", additionalProperties: { type: "string" } },
  },
  required: ["action"],
};

function isGroupKey(key) {
  return typeof key === "string" && GROUP_SESSION.test(key);
}

function hasMessageId(value) {
  if (!value || typeof value !== "object") return false;
  if (typeof value.messageId === "string" || typeof value.message_id === "string" || typeof value.id === "string") return true;
  return Object.values(value).some((v) => v && typeof v === "object" && hasMessageId(v));
}

function boundedText(value) {
  const text = String(value ?? "").trim();
  if (Buffer.byteLength(text, "utf8") <= 2000) return text;
  return text.slice(0, 1600) + "\n[Kết quả đã rút gọn; xem artifact output].";
}

function fileTaskTool(ctx) {
  if (!isGroupKey(ctx?.sessionKey)) return null;
  const workspace = ctx.workspaceDir || "/home/lehuynhphong/.openclaw/workspace";
  const script = `${workspace}/scripts/file_task.py`;
  const python = `${workspace}/.venv-excel/bin/python`;
  return {
    name: "file_task",
    label: "Bounded file task",
    description: "Process at most two supplied workbook files with bounded metadata, inspection, or scoped calculation. Return a short summary and artifact path.",
    parameters: FILE_TASK_SCHEMA,
    async execute(_toolCallId, params, signal) {
      const request = { ...params, inputs: Array.isArray(params?.inputs) ? params.inputs.slice(0, 2) : [] };
      const controller = new AbortController();
      const onAbort = () => controller.abort();
      signal?.addEventListener("abort", onAbort, { once: true });
      try {
        const result = await execFileAsync(python, [script, "--request-json", JSON.stringify(request)], {
          cwd: workspace, shell: false, timeout: 45000, maxBuffer: 12000, signal: controller.signal,
        });
        const text = boundedText(result.stdout || result.stderr);
        let parsed;
        try { parsed = JSON.parse(text); } catch { parsed = null; }
        return { content: [{ type: "text", text }], details: { bounded: true }, terminate: parsed?.ok === false };
      } catch (error) {
        const detail = error?.killed ? "file_task_timeout" : "file_task_failed";
        return { content: [{ type: "text", text: JSON.stringify({ ok: false, error: detail }) }], details: { bounded: true }, terminate: true };
      } finally { signal?.removeEventListener("abort", onAbort); }
    },
  };
}

export default definePluginEntry({
  id: "context-hard-gate",
  name: "OpenClaw context hard gate",
  description: "Fail-closed tool policy for shared Telegram and Zalo group runs.",
  register(api) {
    api.registerTool(fileTaskTool, { name: "file_task", optional: false });
    api.on("before_prompt_build", (event, ctx) => {
      if (!isGroupKey(ctx?.sessionKey)) return;
      if (/xlsx|xlsm|csv|excel|book xe|tính cước|đối chiếu|vin[aă]liam|SO_delivery/i.test(event?.prompt || "")) {
        return { toolsAllow: ["file_task", "progress_card"] };
      }
    }, { priority: 1000, timeoutMs: 15000 });
    api.on(
      "before_tool_call",
      (event, ctx) => {
        if (!groupContext(ctx)) return;
        const tool = event.toolName;
        if (["sessions_history", "sessions_spawn", "sessions_send", "sessions_yield", "subagents", "process", "write", "edit", "apply_patch"].includes(tool)) {
          return { block: true, blockReason: "Group runtime gate: use one bounded coordinator; this tool is disabled." };
        }
        if (tool === "read" && !safeRead(event.params)) {
          return { block: true, blockReason: "Group runtime gate: read only bounded output artifacts." };
        }
        if (["exec", "file_task"].includes(tool)) {
          const receipt = progressReceipts.get(ctx.sessionKey);
          if (!receipt || receipt.expiresAt < Date.now()) {
            progressReceipts.delete(ctx.sessionKey);
            return { block: true, blockReason: "Group runtime gate: send a native progress message first and wait for its messageId before starting work." };
          }
        }
        if (tool === "exec") {
          const cmd = command(event.params);
          if (!coordinatorCommand(cmd)) {
            return { block: true, blockReason: "Group runtime gate: run only an approved coordinator script." };
          }
          const runKey = `${ctx.sessionKey}:${ctx.runId ?? event.runId ?? "unknown"}`;
          const count = callsByRun.get(runKey) ?? 0;
          if (count >= 2) {
            return { block: true, blockReason: "Group runtime gate: coordinator call limit reached; return a bounded result or start a new session." };
          }
          callsByRun.set(runKey, count + 1);
          if (callsByRun.size > 256) callsByRun.delete(callsByRun.keys().next().value);
        }
        if (tool === "file_task" && ctx.runId) {
          const runKey = `${ctx.sessionKey}:${ctx.runId}`;
          const count = callsByRun.get(runKey) ?? 0;
          if (count >= 2) return { block: true, blockReason: "Group runtime gate: file task call limit reached; return the bounded result." };
          callsByRun.set(runKey, count + 1);
        }
      },
      { matcher: ["exec", "read", "file_task", "message", "process", "write", "edit", "apply_patch", "sessions_history", "sessions_spawn", "sessions_send", "sessions_yield", "subagents"], priority: 1000, timeoutMs: 15000 },
    );
    api.on("after_tool_call", (event, ctx) => {
      if (!groupContext(ctx) || event?.toolName !== "message") return;
      if (hasMessageId(event?.result) || hasMessageId(event?.details)) {
        progressReceipts.set(ctx.sessionKey, { expiresAt: Date.now() + RECEIPT_TTL_MS });
      }
    }, { matcher: ["message"], priority: 1000, timeoutMs: 15000 });
  },
});

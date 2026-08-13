---
name: set-openclaw-thinking-levels
description: Bật, kiểm tra hoặc sửa các mức `/thinking off|minimal|low|medium|high|xhigh` cho agent OpenClaw dùng model reasoning qua provider OpenAI-compatible tùy chỉnh như 9Router/9r. Use khi VPS báo một mức thinking không được hỗ trợ, catalog chỉ khai báo một mức, cần áp dụng cấu hình tương tự cho VPS/OpenClaw khác, hoặc cần đồng bộ `openclaw.json` với catalog riêng của agent mà không làm lộ secret.
---

# Set OpenClaw Thinking Levels

## Mục tiêu

Cấu hình model reasoning để OpenClaw dùng được:

```text
off, minimal, low, medium, high, xhigh
```

Với backend không nhận `minimal`, ánh xạ `minimal -> low`. Không tự bật `max` hoặc `ultra`: custom provider của OpenClaw 2026.7.1 chỉ quảng bá extra effort `xhigh`, và backend/model có thể từ chối hai mức này.

## Quy trình bắt buộc

1. Xác định file active từ `OPENCLAW_CONFIG_PATH` hoặc `${HOME}/.openclaw/openclaw.json`.
2. Xác định đúng agent, provider và model; không đọc/in API key, bot token hoặc toàn bộ config.
3. Chạy dry-run trước:

```bash
node scripts/set_openclaw_thinking_levels.mjs --agent <agent-id> --default off --dry-run
```

4. Áp dụng thật:

```bash
node scripts/set_openclaw_thinking_levels.mjs --agent <agent-id> --default off
```

5. Script phải backup trước khi ghi, cập nhật catalog chính và catalog riêng của agent nếu có, chạy `openclaw config validate`, rollback khi validation lỗi và restart Gateway trừ khi dùng `--no-restart`.
6. Kiểm thử không deliver sau khi áp dụng:

```bash
node scripts/verify_openclaw_thinking_levels.mjs --agent <agent-id>
```

Không gửi tin Telegram thật trong bước kiểm tra.

## Chọn phạm vi

- Một agent: dùng `--agent <agent-id>`. Đây là lựa chọn mặc định nên dùng.
- Tất cả agent dùng cùng model: dùng `--all-agents --provider <provider> --model <model>`.
- Chỉ catalog chính: truyền `--provider` và `--model`, không truyền `--agent` hoặc `--all-agents`.
- Config không ở vị trí mặc định: thêm `--config /duong/dan/openclaw.json`.
- Backup theo chuẩn VPS ALT: thêm `--backup-dir /root/_Backups/openclaw`.
- Chỉ ghi config, chưa restart: thêm `--no-restart`.

Ví dụ nhiều agent:

```bash
node scripts/set_openclaw_thinking_levels.mjs \
  --all-agents \
  --provider 9r \
  --model GPT-5.6-sol \
  --default off \
  --dry-run
```

Sau khi duyệt dry-run, bỏ `--dry-run` để áp dụng.

## Thay đổi được phép

Chỉ sửa model đích:

```json
{
  "reasoning": true,
  "compat": {
    "supportedReasoningEfforts": ["low", "medium", "high", "xhigh"],
    "reasoningEffortMap": {
      "minimal": "low"
    }
  }
}
```

Nếu có `--default`, chỉ sửa `thinkingDefault` ở agent được chọn hoặc các agent khớp model. Giữ nguyên provider URL, API key, model khác, fallback, binding, Telegram account, allowlist, workspace và session hiện tại.

## Input và output

Input:

- File `openclaw.json` hợp lệ.
- Agent ID hoặc cặp provider/model.
- Tùy chọn mức mặc định: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`.

Output:

- Config và catalog agent đã đồng bộ.
- Backup timestamped chứa các file trước thay đổi.
- Kết quả validation/restart không chứa secret.
- Báo cáo kiểm thử từng mức với provider/model thực tế và marker `LEVEL_OK`.

## Rerun và rollback

- Có thể chạy lại an toàn; script là idempotent và chỉ ghi khi nội dung thay đổi.
- Mỗi lần ghi tạo backup mới. Khi validation lỗi, script tự phục hồi toàn bộ file vừa sửa.
- Nếu Gateway restart lỗi nhưng validation đạt, không tự rollback; kiểm tra service/log rồi chạy lại với `--no-restart` nếu cần.
- Không xóa session hoặc transcript. Các session chẩn đoán dùng prefix `diagnostic:thinking-levels:` và không deliver.

## Quy tắc an toàn

- Không in hoặc copy toàn bộ `openclaw.json`/`models.json` vì có thể chứa secret.
- Không ghi secret vào skill, log, ví dụ hoặc câu trả lời.
- Không sửa package OpenClaw trong `/usr/lib/node_modules`; giới hạn `max` của custom provider phải được báo rõ thay vì patch runtime.
- Không tự đổi model/provider của agent.
- Không gửi tin Telegram/Zalo thật khi verify.
- Trên production, luôn backup và validate trước khi restart.


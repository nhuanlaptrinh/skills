---
name: cap-full-quyen-telegram-openclaw
description: Chuẩn hóa một Telegram bot OpenClaw về agent main/workspace chính, cấp một hoặc nhiều Telegram user làm owner và approver đầy đủ, rồi bật Full Exec không hỏi duyệt cho main trong một workflow có dry-run, backup, kiểm tra, đồng bộ skill và rollback. Use khi người dùng yêu cầu cấp chủ sở hữu/full quyền Telegram cho member VPS OpenClaw, gộp owner-admin legacy, sửa quyền duyệt còn thiếu, hoặc muốn chạy thay cho bộ ba unify-openclaw-bot-workspace, cap-quyen-telegram-admin-openclaw và set-openclaw-agent-full-exec.
---

# Cấp Full Quyền Telegram OpenClaw

Điều phối ba skill gốc theo thứ tự an toàn. Không sao chép logic sửa JSON vào skill này.

## Chuẩn bị

1. Đọc runbook VPS, project note, `AGENTS.md` gần member và checklist production.
2. Đọc ba skill phụ thuộc và các reference bảo mật của chúng:
   - `unify-openclaw-bot-workspace`
   - `cap-quyen-telegram-admin-openclaw`
   - `set-openclaw-agent-full-exec`
3. Xác định chính xác member và Telegram user ID được chủ VPS cho phép.
4. Không sửa token, model, `.env`, credential hoặc gửi tin Telegram thật để thử.

## Chạy

Dry-run:

```bash
python3 scripts/apply_owner_full_access.py \
  --member <MEMBER> \
  --telegram-id <TELEGRAM_USER_ID> \
  --dry-run
```

Áp dụng:

```bash
python3 scripts/apply_owner_full_access.py \
  --member <MEMBER> \
  --telegram-id <TELEGRAM_USER_ID> \
  --apply
```

Kiểm tra độc lập:

```bash
python3 scripts/apply_owner_full_access.py \
  --member <MEMBER> \
  --telegram-id <TELEGRAM_USER_ID> \
  --check
```

Lặp `--telegram-id` để cấp nhiều owner trong cùng transaction. Script tự suy ra Telegram account khi member chỉ có một account hoặc account key trùng tên member. Dùng `--account-id` nếu cấu hình có nhiều account.

## Trình tự áp dụng

1. Kiểm tra target, binding, agent path, dependency scripts và trạng thái cuối hiện tại.
2. Chạy dry-run đã khử ID; cấu hình legacy chỉ hoãn owner dry-run tới sau bước unify.
3. Backup root-only ngoài persistent member data và quiesce riêng Gateway dưới Supervisor.
4. Chạy normalize/merge bằng `unify-openclaw-bot-workspace`.
5. Cấp owner bằng `cap-quyen-telegram-admin-openclaw` và kiểm tra policy guarded.
6. Bật Full Exec bằng `set-openclaw-agent-full-exec --no-restart`.
7. Đồng bộ bốn skill liên quan vào workspace, validate config, respawn Gateway một lần và probe Telegram.
8. Nếu lỗi trước khi hoàn tất, khôi phục skill, config và workspace/source agent bằng transaction unify rồi đưa Gateway lên lại.

Policy cuối của `main`:

```text
host=gateway
mode=full
security=full
ask=off
askFallback=full
strictInlineEval=false
```

Owner exact sender giữ full tools; sender khác vẫn phải bị wildcard deny ít nhất `group:runtime`, `group:fs`, `group:messaging`, session-control và subagents.

## Legacy và rollback

- `--source-agent auto` chỉ tự gộp agent tên `owner-admin` khi không mơ hồ.
- Dùng `--source-agent none` cho normalize-only hoặc chỉ định rõ agent legacy nếu đã kiểm tra.
- Rerun `--apply` là idempotent: trạng thái cuối đã compliant thì không backup hoặc restart.
- Rollback toàn operation bằng lệnh trong `references/safety-and-rollback.md`.

## Hoàn tất

1. Chạy lại `--check`, `openclaw skills check` và secret scan.
2. Yêu cầu owner tự thử lệnh chỉ đọc trong DM/group; không tự gửi tin thật.
3. Cập nhật project note và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` nhưng không ghi Telegram ID hoặc secret.
4. Ghi lại operation manifest và backup path để rollback.

Đọc `references/safety-and-rollback.md` trước khi apply hoặc rollback.

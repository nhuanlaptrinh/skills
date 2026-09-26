---
name: openclaw-telegram-group-full-auto-approval
description: Cấp full exec/process cho mọi sender trong một Telegram group OpenClaw và bật tự động duyệt không hỏi cho runtime member/host. Dùng khi cần triển khai trọn bộ quyền group + approval trên VPS khác.
---

# OpenClaw Telegram Group Full Exec + Auto Approval

Dùng khi người dùng đã chỉ rõ OpenClaw runtime và Telegram group ID, đồng thời muốn thành viên trong group chạy terminal/script/process mà không phải bấm duyệt từng lần.

Đây là quyền cao: mọi sender được group policy cho phép có thể chạy lệnh trên Gateway. Chỉ áp dụng khi chủ hệ thống yêu cầu rõ ràng.

## Member VPS Docker

Xác định đúng member và config trước khi chạy. Config thường là:

```text
/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/openclaw.json
```

Legacy home có thể là:

```text
/root/Apps/member_vps/docker-users/data/<member>/.openclaw/openclaw.json
```

### 1. Dry-run

```bash
CFG=/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/openclaw.json
GROUP_ID=<telegram-group-id>

bash /root/.agents/skills/openclaw-group-full-exec/scripts/set_group_full_exec.sh \
  --config "$CFG" --group-id "$GROUP_ID" --account default \
  --scope global --dry-run

python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
  --member <member> --dry-run
```

### 2. Apply

```bash
bash /root/.agents/skills/openclaw-group-full-exec/scripts/set_group_full_exec.sh \
  --config "$CFG" --group-id "$GROUP_ID" --account default \
  --scope global --apply

python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
  --member <member> --apply
```

### 3. Check

```bash
bash /root/.agents/skills/openclaw-group-full-exec/scripts/set_group_full_exec.sh \
  --config "$CFG" --group-id "$GROUP_ID" --account default \
  --scope global --check

python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
  --member <member> --check
```

Dùng `--scope global` khi group nằm ở `channels.telegram.groups`. Dùng `--scope account` khi group nằm ở `channels.telegram.accounts.<account>.groups`.

## Host OpenClaw độc lập

```bash
python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
  --openclaw-root /root/.openclaw --dry-run

python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
  --openclaw-root /root/.openclaw --apply
```

Sau đó chạy group helper với `--config /root/.openclaw/openclaw.json` và đúng group ID.

## Kết quả mong đợi

- Group wildcard `toolsBySender["*"].alsoAllow` có `exec` và `process`.
- Không còn deny group-local cho `exec` hoặc `process`.
- Agent `main`: `host=gateway`, `mode=full`, `strictInlineEval=false`.
- Approval: `security=full`, `ask=off`, `askFallback=full`, `autoAllowSkills=true`.
- Config hợp lệ, native approvals cập nhật, Gateway restart thành công.

## An toàn, backup và rollback

Hai helper tự tạo backup trước khi sửa và validate config. Không gửi tin Telegram test tự động. Sau khi check PASS, yêu cầu người dùng thử lại trong group.

Rollback dùng cặp file trong backup timestamp tương ứng, validate lại rồi restart Gateway. Không sửa token, allowlist sender, model, workspace hoặc deny policy ngoài phạm vi group/approval.

Không dùng wildcard group nếu người dùng chưa chỉ rõ group ID. Không áp dụng cho group khác chỉ dựa trên tên hiển thị.

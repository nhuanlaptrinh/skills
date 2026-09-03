---
name: cap-full-quyen-owner-telegram-zalo-openclaw
description: Cấp và kiểm tra quyền chủ sở hữu đầy đủ cho một hoặc nhiều ID Telegram và Zalo Personal trên OpenClaw, trong đó owner exact mặc định có quyền duyệt từng proposal Skill Workshop và cấu hình system-agent, cùng full tools/Exec, owner commands, elevated access và training qua DM/group đã được phép. Dùng khi chủ VPS yêu cầu hợp nhất toàn quyền owner cross-channel trong một agent/workspace canonical; không dùng để mở wildcard, đổi credential, hoặc mở nhóm ngoài policy hiện hữu.
---

# Cấp Full Quyền Owner Telegram + Zalo OpenClaw

Skill composite này điều phối các skill gốc theo một workflow có backup, dry-run,
validation, apply, check và rollback. Người sở hữu đã xác minh được coi là owner
đầy đủ trong phạm vi OpenClaw của VPS đó; không tạo agent/workspace riêng cho owner.

## Phạm vi quyền cuối

- Telegram và Zalo Personal: channel/account DM allowlist, owner commands,
  `tools.elevated.allowFrom` và exact `toolsBySender`.
- Mọi owner Telegram/Zalo đã xác minh và đồng bộ đủ owner layers mặc định có
  thẩm quyền duyệt từng proposal Skill Workshop và proposal cấu hình
  `system-agent` của agent canonical. Đây là quyền duyệt explicit từng proposal,
  không phải tự động áp dụng hoặc đặt `approvalPolicy=auto`.
- Telegram: exec approver, bật plugin approval forwarding tới exact target cho
  Skill Workshop, và approval bridge cho proposal `system-agent` nếu runtime
  chưa hỗ trợ native approval.
- Agent canonical (thường `main`): Full Exec qua Gateway (`host=gateway`,
  `mode=full`, `security=full`, `ask=off`, `askFallback=full`,
  `strictInlineEval=false`) và giữ nguyên deny safeguards cho sender không phải owner.
- Training: owner đã xác minh được dạy bot qua Telegram/Zalo DM và các group mà
  channel policy hiện tại đã deliver message; policy lưu summary an toàn, không
  chép raw transcript hay secret.

“Toàn quyền” ở đây là quyền owner exact trên agent hiện hữu. Không dùng wildcard
owner/elevated/approver, không tự mở Zalo group hoặc bỏ mention nếu người dùng
không yêu cầu rõ ràng.

## Skill phụ thuộc và thứ tự

Đọc các skill này trước khi chạy; composite không sao chép logic sửa JSON:

1. `unify-openclaw-bot-workspace` - bắt buộc nếu account đang route nhiều agent,
   có peer-specific binding hoặc workspace tách rời.
2. `set-openclaw-agent-full-exec` - bật Full Exec cho agent canonical trước khi
   chạy owner updater (updater yêu cầu trạng thái này đã có). Nếu config dùng
   `agents.entries` hoặc runtime lưu approval trong SQLite, phải dùng CLI để kiểm
   tra trạng thái hiện hữu; không ép script legacy tạo `agents.list`/file approval.
3. `openclaw-zalouser-owner-access` - thêm ID Telegram/Zalo vào toàn bộ owner,
   elevated, approval và exact sender layers.
4. `cap-quyen-telegram-admin-openclaw` - dùng để kiểm tra/hoàn thiện Telegram
   owner khi cần; bước này nằm trong updater cross-channel nếu đã đủ input.
5. `openclaw-telegram-approval-bridge` - bảo đảm verified Telegram owner có thể
   thực thi thẩm quyền duyệt mặc định cho proposal `system-agent` khi runtime
   chưa có native support (đây là transport, không phải cấp thêm owner).
6. `sync-openclaw-owner-training` - cài policy training vào `AGENTS.md` workspace.

## Preconditions và an toàn

Trước khi sửa production, đọc `/root/_Second_AI_Brain/START_HERE.md`, bản đồ,
registry, project note liên quan, checklist production và `AGENTS.md` gần target.

- Xác định chính xác member, host/runtime OpenClaw root, container, Telegram
  account, Zalo account, canonical agent/workspace và Gateway manager; không đoán
  khi có nhiều account.
- Chỉ nhận ID số đã được chủ VPS xác minh. ID Telegram và Zalo có thể khác nhau;
  không suy diễn một ID từ display name, username hay group membership.
- Backup `openclaw.json`, `exec-approvals.json` khi có thay đổi approval và
  workspace `AGENTS.md`/skill trước apply, dưới `/root/_Backups` quyền root-only.
- Không sửa token, provider, model, `.env`, credential, session, QR/profile hoặc
  dữ liệu hội thoại. Không gửi tin nhắn thật trong kiểm thử tự động.
- Không mở `groupPolicy=open`, `groupAllowFrom=["*"]` hay `requireMention=false`
  trừ khi yêu cầu nêu rõ; đó là thay đổi policy riêng cần review.

## Cách chạy

### 1. Dry-run bắt buộc

Chạy Full Exec dry-run trước. `update_owner_access.py` cố ý yêu cầu Full Exec đã
compliant; nếu target chưa compliant, apply riêng bước Full Exec có backup và
`--no-restart`, rồi mới chạy owner updater dry-run trước khi apply owner. Không
bỏ qua owner dry-run chỉ vì Full Exec vừa được áp dụng. Với schema mới, kiểm tra
CLI trước và coi trạng thái `full/off` trong runtime approval store là compliant;
không chạy script legacy nếu nó chỉ hiểu `agents.list`.

```bash
bash /root/.agents/skills/set-openclaw-agent-full-exec/scripts/set_openclaw_agent_full_exec.sh \
  --openclaw-root <HOST_OPENCLAW_ROOT> --container <CONTAINER> \
  --runtime-home <RUNTIME_HOME> --agent main --no-restart --dry-run

docker exec -e HOME=<RUNTIME_HOME> <CONTAINER> openclaw approvals get --json

python3 /root/.agents/skills/openclaw-zalouser-owner-access/scripts/update_owner_access.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --telegram-account-id <TELEGRAM_ACCOUNT> --telegram-id <TELEGRAM_OWNER_ID> \
  --zalo-account-id <ZALO_ACCOUNT> --zalo-id <ZALO_OWNER_ID> \
  --container <CONTAINER> --runtime-home <RUNTIME_HOME> \
  --runtime-openclaw-root <RUNTIME_ROOT> --dry-run
```

Sau khi owner policy đã compliant hoặc vừa apply, dry-run training và approval
bridge theo target workspace:

```bash

python3 /root/.agents/skills/sync-openclaw-owner-training/scripts/sync_owner_training_policy.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> --dry-run

python3 /root/.agents/skills/openclaw-telegram-approval-bridge/scripts/install_approval_bridge.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> --runtime-openclaw-root <RUNTIME_ROOT> \
  --workspace <HOST_WORKSPACE> --telegram-id <telegram_user_id> \
  --account-id <telegram_account> --agent-id main --dry-run
```

Approval bridge chỉ cần khi native Telegram approval không đủ; owner updater vẫn
phải chạy trước để installer fail-closed kiểm tra owner.

Giữ đúng host/runtime path thực tế. Với host runtime, bỏ `--container`; với layout
member chuẩn có thể dùng `data/<member>/root/.openclaw` và runtime HOME `/root`,
hoặc layout `data/<member>/.openclaw` và runtime HOME `/home/<member>`.

### 2. Apply theo transaction

1. Quiesce đúng Gateway dưới Supervisor/tmux/systemd hiện hữu; không tạo process
   hoặc container mới.
2. Apply Full Exec với `--no-restart` trong maintenance window và backup riêng;
   nếu CLI đã xác nhận `full/off` trên schema mới thì ghi nhận no-op và không ép
   script legacy.
3. Apply `update_owner_access.py` với backup riêng và `--apply`.
4. Apply `sync_owner_training_policy.py` với backup `AGENTS.md`.
5. Khi runtime chưa có native `system-agent` approval, apply approval bridge với
   backup manifest để owner có transport duyệt qua Telegram DM.
6. Validate config/skills, kiểm tra owner exact và respawn đúng Gateway process một
   lần. Có thể dùng `cap-full-quyen-telegram-openclaw` cho Telegram-only legacy,
   nhưng không chạy song song với transaction composite trên cùng target.

Mỗi bước phải ghi lại manifest/backup path; nếu lỗi, rollback đúng transaction,
validate lại rồi respawn Gateway cũ. Các script đều idempotent, nhưng phải review
dry-run trước lần apply đầu tiên.

Ví dụ apply owner cross-channel sau khi Full Exec đã apply:

```bash
bash /root/.agents/skills/set-openclaw-agent-full-exec/scripts/set_openclaw_agent_full_exec.sh \
  --openclaw-root <HOST_OPENCLAW_ROOT> --container <CONTAINER> \
  --runtime-home <RUNTIME_HOME> --agent main --no-restart \
  --backup-dir /root/_Backups/openclaw-owner-full-access/<target>/<timestamp>/full-exec \
  --apply

python3 /root/.agents/skills/openclaw-zalouser-owner-access/scripts/update_owner_access.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --telegram-account-id <TELEGRAM_ACCOUNT> --telegram-id <TELEGRAM_OWNER_ID> \
  --zalo-account-id <ZALO_ACCOUNT> --zalo-id <ZALO_OWNER_ID> \
  --container <CONTAINER> --runtime-home <RUNTIME_HOME> \
  --runtime-openclaw-root <RUNTIME_ROOT> \
  --backup-dir /root/_Backups/openclaw-owner-full-access/<target>/<timestamp>/owner \
  --apply

python3 /root/.agents/skills/sync-openclaw-owner-training/scripts/sync_owner_training_policy.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --backup-dir /root/_Backups/openclaw-owner-full-access/<target>/<timestamp>/training \
  --apply

python3 /root/.agents/skills/openclaw-telegram-approval-bridge/scripts/install_approval_bridge.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> --runtime-openclaw-root <RUNTIME_ROOT> \
  --workspace <HOST_WORKSPACE> --telegram-id <TELEGRAM_OWNER_ID> \
  --account-id <TELEGRAM_ACCOUNT> --agent-id main \
  --backup-dir /root/_Backups/openclaw-owner-full-access/<target>/<timestamp>/approval \
  --apply
```

Omit approval bridge apply khi runtime đã có native support đầy đủ và bước kiểm
tra native xác nhận exact Telegram owner có thể duyệt đúng loại proposal cần dùng.

## Input và output

Input bắt buộc: target/member, exact Telegram owner ID, exact Zalo owner ID,
Telegram/Zalo account ID, host/runtime OpenClaw root, canonical workspace, agent
ID và Gateway process manager. Có thể lặp ID để thêm nhiều co-owner; không thay
owner hiện hữu. `--open-zalo-groups` chỉ được thêm khi yêu cầu nêu rõ.

Output: owner policy cross-channel đầy đủ, Full Exec cho agent canonical, training
managed block trong `AGENTS.md`, approval bridge khi cần, backup/manifest root-only
và báo cáo check đã khử ID/secret. Skill không ghi Sheet/API và không tạo nội dung
memory ngay lúc cài; memory chỉ được cập nhật về sau từ hướng dẫn owner hợp lệ.

## Verification bắt buộc

```bash
docker exec -e HOME=<RUNTIME_HOME> <CONTAINER> openclaw config validate
docker exec -e HOME=<RUNTIME_HOME> <CONTAINER> openclaw plugins doctor
docker exec -e HOME=<RUNTIME_HOME> <CONTAINER> openclaw skills check
docker exec -e HOME=<RUNTIME_HOME> <CONTAINER> openclaw approvals get --json
python3 .../update_owner_access.py <same identity/account args> --check
python3 .../sync_owner_training_policy.py --openclaw-root <HOST_OPENCLAW_ROOT> --check
python3 .../install_approval_bridge.py <same owner args> --check  # nếu đã cài
```

Xác nhận một account-level binding về `main`, Telegram/Zalo configured/running/
connected/works, Full Exec đúng policy, owner/elevated/approval counts đầy đủ,
training block chỉ xuất hiện một lần, và sender không-owner vẫn giữ deny ít nhất
`group:runtime`, `group:fs`, `group:messaging`. Yêu cầu owner tự kiểm tra một
lệnh chỉ đọc; không tự gửi tin nhắn.

## Training và approval semantics

- “Owner training” là hướng dẫn vận hành rõ ràng, có thể tái sử dụng; lưu summary
  không nhạy cảm vào memory/workspace sau review.
- Từ chối lưu token, API key, cookie, mật khẩu, OTP, payment data, session secret
  hoặc raw DM/group transcript.
- `openclaw-zalouser-owner-access` đồng bộ Telegram exec/plugin approver; Full Exec
  `ask=off` khiến owner không bị chặn bởi approval cho Exec thông thường.
- Verified owner exact luôn có thẩm quyền duyệt Skill Workshop và proposal cấu
  hình `system-agent` theo mặc định sau khi owner layers đã đồng bộ. Skill
  Workshop vẫn giữ `approvalPolicy=pending`, nên phải có consent rõ ràng cho
  từng proposal; không biến quyền owner thành auto-apply.
- Approval bridge proposal `system-agent` hiện là workflow duyệt từ Telegram DM;
  exact Telegram owner có thể duyệt proposal ngay trước đó phát sinh từ direct
  Telegram/Zalo owner session hoặc Zalo group đã khai báo/enabled trên cùng agent.
  Kiểm tra queue live, source policy và summary; chỉ dùng `allow-once`, không dùng
  `allow-always`.
  Không tuyên bố Zalo có bridge approval riêng nếu runtime chưa hỗ trợ native.
- Quyền owner không tự mở group mới, không bypass group mention policy và không
  biến người tham gia group thành owner.

## Rerun, rollback và nhật ký

- Rerun `--check` sau restart; rerun `--apply` chỉ khi check còn thiếu.
- Rollback không xóa credential/session; chỉ khôi phục file backup thuộc đúng
  operation sau khi kiểm tra checksum và live state không đổi ngoài dự kiến.
- Sau thay đổi quan trọng, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`
  và project note, không ghi ID thật, token hay secret.

## Secret scan và validation skill

Skill phải không chứa ID thật hoặc secret. Trước bàn giao chạy:

```bash
python3 /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /root/.agents/skills/cap-full-quyen-owner-telegram-zalo-openclaw
python3 - <<'PY'
from pathlib import Path
import re

root = Path('/root/.agents/skills/cap-full-quyen-owner-telegram-zalo-openclaw')
patterns = [
    re.compile('sk-' + r'[A-Za-z0-9_-]{20,}'),
    re.compile(r'BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY'),
    re.compile('password' + r'\s*=\s*[^ <\n]{16,}', re.I),
    re.compile('token' + r'\s*=\s*[^ <\n]{16,}', re.I),
]
hits = [path for path in root.rglob('*') if path.is_file()
        and any(pattern.search(path.read_text(errors='ignore')) for pattern in patterns)]
if hits:
    raise SystemExit('secret-like content found: ' + ', '.join(map(str, hits)))
print('secret_scan=clean')
PY
```

Kết quả secret scan phải không có secret thật; placeholder dạng `<...>` được phép.

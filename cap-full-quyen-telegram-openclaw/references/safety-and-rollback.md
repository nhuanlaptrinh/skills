# Safety And Rollback

## Policy staging

`unify-openclaw-bot-workspace` và `cap-quyen-telegram-admin-openclaw` tạo trạng thái guarded `auto/allowlist/on-miss`. Workflow phải kiểm tra trạng thái này trước khi `set-openclaw-agent-full-exec` đổi trạng thái cuối thành `full/off`.

Không chạy `unify --check` hoặc owner `--check` để đánh giá policy Exec sau bước Full Exec; chúng sẽ báo khác biệt có chủ đích. Dùng checker tổng hợp và Full Exec runtime check ở trạng thái cuối.

## Backup

Mỗi apply tạo transaction riêng:

```text
/root/_Backups/openclaw-owner-full-access/<member>/<timestamp>/
```

Transaction chứa snapshot trước thay đổi, snapshot ngay sau unify, manifest unify, backup riêng của các skill gốc và bản skill workspace trước khi đồng bộ. File backup có thể chứa credential production nên phải giữ `0700/0600`, không copy vào tài liệu hoặc câu trả lời.

## Rollback

Dry-run rollback:

```bash
python3 scripts/apply_owner_full_access.py \
  --member <MEMBER> \
  --rollback-operation <OPERATION_MANIFEST> \
  --dry-run-rollback
```

Rollback thật:

```bash
python3 scripts/apply_owner_full_access.py \
  --member <MEMBER> \
  --rollback-operation <OPERATION_MANIFEST>
```

Rollback quiesce riêng Gateway, khôi phục bản skill workspace cũ, đưa config về đúng checksum sau unify, gọi rollback transaction unify để phục hồi config/source workspace/source agent, validate và respawn Gateway. Không rollback nếu manifest, path, ownership hoặc checksum không hợp lệ.

## Stop conditions

Dừng trước apply khi:

- Telegram account không suy ra duy nhất.
- `main` không dùng `/root/.openclaw/workspace` và `/root/.openclaw/agents/main/agent`.
- Có nhiều source agent, source không phải `owner-admin` mà chưa chỉ định rõ, hoặc config có symlink/path escape.
- Gateway không do Supervisor quản lý hoặc không có đúng một pane `tmux` live khớp Gateway PID. Với `tmux`, chỉ được giữ tạm pane hiện có, cho Gateway thoát sạch rồi respawn chính pane đó; không tạo session/pane Gateway mới để vượt qua kiểm tra này.
- Candidate validation, guarded check, Full Exec check, skill sync hoặc cả Telegram probe và status fallback đều lỗi.

Không restart/recreate container, không sửa Docker Compose, token, model, provider, `.env`, auth profile, session store hoặc raw transcript.

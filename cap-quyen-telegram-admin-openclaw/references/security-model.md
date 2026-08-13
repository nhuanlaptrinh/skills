# Mô Hình Bảo Mật

## Một Bot, Một Agent

Một Telegram `accountId` phải có đúng một account-level binding tới một agent. DM và group dùng cùng agent/workspace nhưng giữ session riêng. Thêm owner không được tạo agent/workspace mới.

Owner là sender có quyền đầy đủ trên canonical agent. Không tạo identity/agent/workspace riêng cho owner và không thêm field Telegram ngoài schema; `commands.ownerAllowFrom` là nguồn owner.

## Các Lớp Owner

Một owner đầy đủ phải xuất hiện đồng bộ tại:

1. `channels.telegram.allowFrom` và account `allowFrom`.
2. `commands.ownerAllowFrom` dạng `telegram:<ID>`.
3. Telegram exec approvers với target `dm`.
4. Plugin approval target đúng account.
5. `tools.elevated.allowFrom.telegram`.
6. Exact `agents.list[].tools.toolsBySender["channel:telegram:<ID>"] = {}`.

Owner dùng full profile của canonical agent. Wildcard sender policy phải deny công cụ quản trị cho người khác. Không đặt deny ở group base rồi cố `alsoAllow` cho owner vì deny luôn thắng.

## Exec

- Canonical agent: `host=gateway`, `mode=auto`, `strictInlineEval=true`.
- Host approvals: `security=allowlist`, `ask=on-miss`, `askFallback=deny`.
- Không dùng `full/off` cho agent có mặt trong group.
- Không copy rộng các rule `allow-always` từ một agent admin legacy sang agent chung mà chưa audit.

## Ranh Giới

- Không wildcard owner hoặc elevated allowlist.
- Không để peer-specific binding tách owner DM sang agent khác.
- `tools.fs.workspaceOnly=true` giới hạn file tools vào workspace, nhưng không hạn chế shell; non-owner phải mất `group:runtime`.
- Shared workspace giảm file isolation. Không đưa transcript DM thô hoặc bí mật hạ tầng vào memory dùng chung.

## Kiểm Thử

- `openclaw config validate`.
- `openclaw agents list --bindings` chỉ ra một binding account-level.
- `openclaw approvals get` cho thấy allowlist/on-miss/deny.
- Owner trong DM/group có tool đầy đủ và exec cần duyệt.
- Non-owner group không có runtime, filesystem, memory, session-control, messaging hoặc admin tools.
- `openclaw channels status --probe` báo connected/works/audit ok.

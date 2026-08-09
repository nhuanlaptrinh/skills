---
name: cap-quyen-telegram-admin-openclaw
description: Cấp hoặc kiểm tra một Telegram user ID có quyền quản trị toàn VPS qua OpenClaw bằng DM riêng, owner commands, exec approvals và direct binding tới agent tool profile full. Use khi người dùng yêu cầu thêm Telegram ID toàn quyền VPS/OpenClaw, tạo owner-admin cho VPS khác, đồng bộ quyền admin Telegram, hoặc kiểm tra một ID đã đủ quyền quản trị mà không mở quyền cho group.
---

# Cấp Quyền Telegram Admin OpenClaw

## Nguyên Tắc Bắt Buộc

- Chỉ thao tác khi người dùng cung cấp rõ Telegram user ID dạng số dương.
- Chỉ cấp qua DM chính xác của user; không dùng wildcard cho DM và không bind agent admin vào group.
- Giữ `dmPolicy: pairing`, đồng thời thêm đúng ID đã được người dùng xác nhận vào allowlist cấp Telegram và account.
- Thêm đồng bộ `commands.ownerAllowFrom`, Telegram exec approver và direct peer binding.
- Dùng agent riêng `owner-admin` với `tools.profile: full`; không đổi tool profile toàn cục sang `full`.
- Giữ Telegram exec approvals ở `auto`; không tắt approval chỉ để tạo cảm giác “toàn quyền”.
- Không mở Gateway public, không sửa firewall/SSH và không in token hoặc toàn bộ `openclaw.json`.
- Đọc tài liệu vận hành của VPS, backup trước khi sửa và cập nhật nhật ký sau thay đổi.

## Quy Trình

1. Đọc entrypoint vận hành, hồ sơ OpenClaw và `AGENTS.md` áp dụng cho VPS đích.
2. Xác minh runtime đang chạy bằng `root`, `HOME=/root`, OpenClaw root `/root/.openclaw` và Telegram account cần dùng.
3. Kiểm tra version, service, config mode và binding hiện tại mà không in credential.
4. Chạy dry-run:

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root /root/.openclaw \
  --account-id main
```

5. Đọc danh sách thay đổi. Nếu ID đang có direct binding tới agent khác, dừng và xác minh; chỉ dùng `--replace-binding` khi người dùng cho phép thay route.
6. Áp dụng:

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root /root/.openclaw \
  --account-id main \
  --apply
```

7. Đồng bộ toàn bộ skill vào OpenClaw root bằng script chuẩn của skill cài OpenClaw, rồi chạy `--check` và `openclaw skills check`.
8. Source file env của provider, chạy `openclaw config validate`, restart đúng Gateway process manager và probe Telegram.
9. Kiểm tra trạng thái quyền bằng:

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root /root/.openclaw \
  --account-id main \
  --check
```

10. Yêu cầu người dùng nhắn DM cho bot và thử lệnh chỉ đọc như `id`, `pwd` hoặc kiểm tra trạng thái service. Không tự gửi tin Telegram nếu chưa được phép.
11. Cập nhật nhật ký thay đổi bằng thông tin đã làm sạch; không ghi bot token, API key hoặc nội dung DM.

## Script

`scripts/grant_telegram_admin.py` thực hiện idempotent:

- Kiểm tra Telegram ID, config JSON và Telegram account.
- Giữ `dmPolicy: pairing` và merge ID vào allowlist chính xác.
- Merge `telegram:<ID>` vào owner allowlist.
- Bật exec approvals `auto` và merge ID vào approver list.
- Tạo hoặc chuẩn hóa agent `owner-admin` với workspace/agent state riêng và profile `full`.
- Thêm direct binding đúng account và Telegram peer.
- Backup config bằng mode `600`, ghi file atomically và không đọc/in secret.
- Hỗ trợ dry-run mặc định, `--apply`, `--check` và `--replace-binding`.

## Thu Hồi Quyền

Không tự xóa bằng tay từng chỗ khi người dùng yêu cầu thu hồi. Trước tiên backup config, sau đó xóa đồng bộ ID khỏi direct binding, owner allowlist, exec approvers, Telegram allowlist cấp chung/account và credential pairing liên quan. Validate, restart, probe và ghi nhật ký. Không xóa agent `owner-admin` nếu vẫn còn operator khác sử dụng.

## Tham Khảo

- Đọc `references/security-model.md` trước khi thay đổi policy hoặc xử lý binding xung đột.
- Dùng `references/owner-admin-AGENTS.md` làm guardrail ban đầu khi script phải tạo workspace admin mới.
